"""Bundle parts -> NormalizedPart. No business labels."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ..contracts.normalized import NormalizedMemberDocument, NormalizedPart
from ..geom.plate_cuts import boolean_cut_hits_part, classify_plate_boolean_cuts, solid_cut_proof
from ..rules import as_float, as_int, part_length_approx, part_profile_norm, part_width_approx, text


def normalized_part_from_bundle_part(
    part: Mapping[str, Any],
    relationships: Mapping[str, Any] | Counter[str] | None = None,
) -> NormalizedPart:
    holes = part.get("boltHoles") or []
    bolt_hole_count = as_int(part.get("boltHoleCount"))
    if bolt_hole_count <= 0 and isinstance(holes, list):
        bolt_hole_count = len(holes)
    welds = part.get("weldDetails") or []
    rel_items: tuple[tuple[str, int], ...] = ()
    if isinstance(relationships, Counter):
        rel_items = tuple(sorted((text(key), int(count)) for key, count in relationships.items() if text(key)))
    elif isinstance(relationships, Mapping):
        rel_items = tuple(sorted((text(key), as_int(count)) for key, count in relationships.items() if text(key)))
    profile = part_profile_norm(part)
    is_plate_like = bool(part.get("isPlateLike")) or profile.startswith("PL")
    obb = part.get("obbDims") or {}
    hole_like = as_int(part.get("holeLikeFeatureCount"))
    chamfers = _chamfers(part)
    obb_dims = (as_float(obb.get("x")), as_float(obb.get("y")), as_float(obb.get("z")))
    thickness = as_float(part.get("thickness"))
    edge_bevel_count, has_edge_bevel = _edge_bevels(part, obb_dims, thickness)
    end_chamfer_count, has_end_chamfer = _end_chamfers(part, is_plate_like)
    if is_plate_like:
        hole_like, end_chamfer_count, has_end_chamfer = _plate_cut_counts(
            part,
            obb_dims,
            thickness,
            bolt_hole_count,
            hole_like,
            end_chamfer_count,
            has_end_chamfer,
        )
    return NormalizedPart(
        part_id=text(part.get("partId")),
        part_position=text(part.get("partPosition")),
        name=text(part.get("name")),
        profile=profile,
        material=text(part.get("material")),
        runtime_type=text(part.get("runtimeType")),
        is_plate_like=is_plate_like,
        is_special_shape=bool(part.get("isSpecialShape")),
        thickness=thickness,
        length=part_length_approx(part),
        width=part_width_approx(part),
        contour_vertex_count=as_int(part.get("contourVertexCount")),
        concave_corner_count=as_int(part.get("concaveCornerCount")),
        has_arc_contour=bool(part.get("hasArcContour")),
        bolt_hole_count=bolt_hole_count,
        boolean_cut_count=_boolean_cut_count(part),
        weld_count=len(welds) if isinstance(welds, list) else 0,
        hole_like_feature_count=hole_like,
        obb_dims=obb_dims,
        contour_points=_contour_points(part),
        contour_chamfers=chamfers,
        contour_chamfer_types=tuple(item[0] for item in chamfers),
        edge_bevel_count=edge_bevel_count,
        has_edge_bevel=has_edge_bevel,
        end_chamfer_count=end_chamfer_count,
        has_end_chamfer=has_end_chamfer,
        relationship_counts=rel_items,
        declared_process=_declared_process(part),
    )


def _declared_process(part: Mapping[str, Any]) -> str:
    explicit = text(part.get("工序") or part.get("declaredProcess"))
    if explicit:
        return explicit
    for key, value in _custom_property_items(part.get("customProperties")):
        token = text(value)
        if not token:
            continue
        key_text = text(key)
        if "工序" in key_text or key_text.lower() in {"process", "shopprocess"}:
            return token
        if token == "不下":
            return "不下"
    return ""


def _custom_property_items(properties: Any) -> list[tuple[Any, Any]]:
    if isinstance(properties, Mapping):
        return list(properties.items())
    if isinstance(properties, list):
        items: list[tuple[Any, Any]] = []
        for item in properties:
            if not isinstance(item, Mapping):
                continue
            items.append((item.get("name") or item.get("key") or "", item.get("value")))
        return items
    return []


def _contour_points(part: Mapping[str, Any]) -> tuple[tuple[float, float, float], ...]:
    points = []
    for item in part.get("contourPoints") or []:
        if isinstance(item, Mapping):
            points.append((as_float(item.get("x")), as_float(item.get("y")), as_float(item.get("z"))))
    return tuple(points)


def _edge_bevels(
    part: Mapping[str, Any],
    obb_dims: tuple[float, float, float],
    thickness: float,
) -> tuple[int, bool]:
    items = part.get("edgeBevels") or []
    declared = as_int(part.get("edgeBevelCount"))
    if isinstance(items, list) and items:
        count = 0
        for item in items:
            if not isinstance(item, Mapping) or item.get("isBevel") is not True:
                continue
            if _bevel_belongs_to_part(item):
                count += 1
        return count, count > 0
    has_bevel = bool(part.get("hasEdgeBevel")) or declared > 0
    return declared, has_bevel


def _boolean_cut_count(part: Mapping[str, Any]) -> int:
    declared = as_int(part.get("booleanCutCount"))
    cuts = part.get("booleanCutDetails")
    if not isinstance(cuts, list) or not cuts:
        return declared
    hits = 0
    for cut in cuts:
        if not isinstance(cut, Mapping):
            continue
        if boolean_cut_hits_part(part.get("boundingBox"), cut) is False:
            continue
        hits += 1
    return hits


def _plate_cut_counts(
    part: Mapping[str, Any],
    obb_dims: tuple[float, float, float],
    thickness: float,
    bolt_hole_count: int,
    hole_like: int,
    end_chamfer_count: int,
    has_end_chamfer: bool,
) -> tuple[int, int, bool]:
    cuts = part.get("booleanCutDetails") or []
    if not isinstance(cuts, list) or not cuts:
        return hole_like, end_chamfer_count, has_end_chamfer
    roles = classify_plate_boolean_cuts(
        part_box=part.get("boundingBox") or {},
        thickness=thickness,
        cuts=cuts,
        bevel_operative_ids=_bevel_operative_ids(part, obb_dims, thickness),
    )
    hole_like = bolt_hole_count + roles.opening_count
    if roles.chamfer_count:
        return hole_like, roles.chamfer_count, True
    return hole_like, end_chamfer_count, has_end_chamfer


def _bevel_operative_ids(
    part: Mapping[str, Any],
    obb_dims: tuple[float, float, float],
    thickness: float,
) -> set[int]:
    ids: set[int] = set()
    for item in part.get("edgeBevels") or []:
        if not isinstance(item, Mapping) or item.get("isBevel") is not True:
            continue
        if not _bevel_belongs_to_part(item):
            continue
        op_id = item.get("operativePartId")
        if op_id is not None:
            ids.add(as_int(op_id))
    return ids


def _end_chamfers(part: Mapping[str, Any], is_plate_like: bool) -> tuple[int, bool]:
    if is_plate_like:
        return 0, False
    if "endChamferCount" in part or "hasEndChamfer" in part:
        count = as_int(part.get("endChamferCount"))
        if count <= 0 and bool(part.get("hasEndChamfer")):
            count = 1
        return count, count > 0 or bool(part.get("hasEndChamfer"))
    count = _infer_end_chamfer_count(part)
    return count, count > 0


def _infer_end_chamfer_count(part: Mapping[str, Any]) -> int:
    part_box = part.get("boundingBox") or {}
    cuts = part.get("booleanCutDetails") or []
    if not isinstance(part_box, Mapping) or not isinstance(cuts, list):
        return 0
    bevel_ops = set()
    for item in part.get("edgeBevels") or []:
        if not isinstance(item, Mapping) or item.get("isBevel") is not True:
            continue
        if str(item.get("kind") or "").upper() != "BOOLEAN_CUT":
            continue
        op_id = item.get("operativePartId")
        if op_id is not None:
            bevel_ops.add(as_int(op_id))
    count = 0
    for cut in cuts:
        if not isinstance(cut, Mapping):
            continue
        op_id = cut.get("operativePartId")
        if op_id is not None and as_int(op_id) in bevel_ops:
            continue
        if solid_cut_proof(cut) is False:
            continue
        if _is_end_clip(part_box, cut.get("boundingBox") or {}):
            count += 1
    return count


def _bevel_belongs_to_part(item: Mapping[str, Any]) -> bool:
    if not _has_bevel_geometry(item):
        return False
    if str(item.get("kind") or "").upper() != "BOOLEAN_CUT":
        return True
    return solid_cut_proof(item) is True


def _has_bevel_geometry(item: Mapping[str, Any]) -> bool:
    dimensions = (
        "chamferX",
        "chamferY",
        "dz1",
        "dz2",
        "firstBevelDimension",
        "secondBevelDimension",
    )
    return any(abs(as_float(item.get(key))) > 1e-9 for key in dimensions)


def _item_sizes(item: Mapping[str, Any]) -> tuple[float, float, float]:
    x = abs(as_float(item.get("chamferX")))
    y = abs(as_float(item.get("chamferY")))
    z = abs(as_float(item.get("dz1") or item.get("chamferDZ") or item.get("chamferZ")))
    if x or y or z:
        return (x, y, z)
    return _box_size(item.get("boundingBox") or {})


def _is_end_clip(part_box: Mapping[str, Any], cut_box: Mapping[str, Any]) -> bool:
    part_min, part_max = _bb_minmax(part_box)
    cut_min, cut_max = _bb_minmax(cut_box)
    if part_min is None or cut_min is None or part_max is None or cut_max is None:
        return False
    spans = [part_max[index] - part_min[index] for index in range(3)]
    long_i = max(range(3), key=lambda index: spans[index])
    length = spans[long_i]
    if length <= 1:
        return False
    cut_center = [(cut_min[index] + cut_max[index]) / 2.0 for index in range(3)]
    end_dist = min(abs(cut_center[long_i] - part_min[long_i]), abs(cut_center[long_i] - part_max[long_i]))
    if end_dist > max(250.0, min(400.0, 0.05 * length)):
        return False
    if abs(cut_max[long_i] - cut_min[long_i]) > 0.45 * length:
        return False
    for index in range(3):
        if index == long_i:
            continue
        dist = min(abs(cut_center[index] - part_min[index]), abs(cut_center[index] - part_max[index]))
        if dist <= max(40.0, 0.2 * spans[index]):
            return True
    return False


def _bb_minmax(box: Mapping[str, Any]) -> tuple[tuple[float, float, float] | None, tuple[float, float, float] | None]:
    if not isinstance(box, Mapping):
        return None, None
    minimum = box.get("min") or {}
    maximum = box.get("max") or {}
    if not isinstance(minimum, Mapping) or not isinstance(maximum, Mapping):
        return None, None
    part_min = (as_float(minimum.get("x")), as_float(minimum.get("y")), as_float(minimum.get("z")))
    part_max = (as_float(maximum.get("x")), as_float(maximum.get("y")), as_float(maximum.get("z")))
    return part_min, part_max


def _box_size(box: Mapping[str, Any]) -> tuple[float, float, float]:
    part_min, part_max = _bb_minmax(box)
    if part_min is None or part_max is None:
        return (0.0, 0.0, 0.0)
    return (
        abs(part_max[0] - part_min[0]),
        abs(part_max[1] - part_min[1]),
        abs(part_max[2] - part_min[2]),
    )


def _chamfers(part: Mapping[str, Any]) -> tuple[tuple[str, float, float], ...]:
    result = []
    for segment in part.get("contourSegments") or []:
        if not isinstance(segment, Mapping):
            continue
        result.append(
            (
                text(segment.get("chamferType")) or "NONE",
                as_float(segment.get("chamferX")),
                as_float(segment.get("chamferY")),
            )
        )
    return tuple(result)


def normalized_document_from_assembly(
    member_id: str,
    assembly: Mapping[str, Any],
    rel_by_part: Mapping[str, Counter[str]] | None = None,
) -> NormalizedMemberDocument:
    rel_by_part = rel_by_part or {}
    parts = tuple(
        normalized_part_from_bundle_part(part, rel_by_part.get(text(part.get("partId"))))
        for part in assembly.get("parts", [])
        if text(part.get("partId"))
    )
    return NormalizedMemberDocument(
        member_id=text(member_id),
        assembly_id=text(assembly.get("assemblyId")),
        parts=parts,
    )
