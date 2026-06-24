from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping

from .rules import as_float, as_int, text


@dataclass(frozen=True)
class PartFeatureSnapshot:
    """Stable, source-neutral part feature contract.

    The snapshot is intentionally small and factual. Tekla plugins, MCP query
    results, and offline bundle JSON should all adapt into this shape before
    classification logic consumes them.
    """

    part_id: str
    position: str
    name: str
    profile: str
    material: str = ""
    runtime_type: str = ""
    is_plate_like: bool = False
    is_special_shape: bool = False
    thickness: float = 0.0
    obb_dims: dict[str, float] = field(default_factory=dict)
    contour_segment_lengths: list[float] = field(default_factory=list)
    contour_vertex_count: int = 0
    concave_corner_count: int = 0
    hole_like_feature_count: int = 0
    internal_hole_count: int = 0
    boolean_cut_count: int = 0
    bolt_hole_count: int = 0
    chamfer_count: int = 0
    cutout_count: int = 0
    notch_count: int = 0
    bending_count: int = 0
    weld_count: int = 0
    has_arc_contour: bool = False
    shape_type: str = ""
    is_regular_shape: bool = True
    relationship_counts: Counter[str] = field(default_factory=Counter)


@dataclass(frozen=True)
class FeatureIndex:
    snapshots: list[PartFeatureSnapshot]
    part_dicts: list[dict[str, Any]]
    by_position: dict[str, list[dict[str, Any]]]
    by_part_id: dict[str, PartFeatureSnapshot]


def _relationship_counter(value: Mapping[str, Any] | Counter[str] | None) -> Counter[str]:
    if value is None:
        return Counter()
    if isinstance(value, Counter):
        return Counter(value)
    return Counter({text(key): as_int(count) for key, count in value.items() if text(key)})


def _obb_dims(part: Mapping[str, Any]) -> dict[str, float]:
    dims = part.get("obbDims") or {}
    return {
        key: as_float(dims.get(key))
        for key in ("x", "y", "z")
        if as_float(dims.get(key)) > 0
    }


def _contour_segment_lengths(part: Mapping[str, Any]) -> list[float]:
    result = []
    for segment in part.get("contourSegments") or []:
        length = as_float(segment.get("length"))
        if length > 0:
            result.append(length)
    return result


def feature_snapshot_from_bundle_part(
    part: Mapping[str, Any],
    relationships: Mapping[str, Any] | Counter[str] | None = None,
) -> PartFeatureSnapshot:
    return PartFeatureSnapshot(
        part_id=text(part.get("partId")),
        position=text(part.get("partPosition")),
        name=text(part.get("name")),
        profile=text(part.get("profileString")),
        material=text(part.get("material")),
        runtime_type=text(part.get("runtimeType")),
        is_plate_like=bool(part.get("isPlateLike")),
        is_special_shape=bool(part.get("isSpecialShape")),
        thickness=as_float(part.get("thickness")),
        obb_dims=_obb_dims(part),
        contour_segment_lengths=_contour_segment_lengths(part),
        contour_vertex_count=as_int(part.get("contourVertexCount")),
        concave_corner_count=as_int(part.get("concaveCornerCount")),
        hole_like_feature_count=as_int(part.get("holeLikeFeatureCount")),
        boolean_cut_count=as_int(part.get("booleanCutCount")),
        bolt_hole_count=as_int(part.get("boltHoleCount")),
        weld_count=len(part.get("weldDetails") or []),
        has_arc_contour=bool(part.get("hasArcContour")),
        relationship_counts=_relationship_counter(relationships),
    )


def _nested(source: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in source:
            return source.get(name)
    return None


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _plate_like_from_teklatest(basic: Mapping[str, Any]) -> bool:
    profile = text(_nested(basic, "Profile", "profile")).upper()
    part_type = text(_nested(basic, "PartType", "partType")).upper()
    return profile.startswith("PL") or "PLATE" in part_type


def _teklatest_shape_is_regular(shape: Mapping[str, Any]) -> bool:
    if "IsRegular" in shape:
        return bool(shape.get("IsRegular"))
    if "isRegular" in shape:
        return bool(shape.get("isRegular"))
    shape_type = text(_nested(shape, "ShapeType", "shapeType")).upper()
    return not shape_type or shape_type in {"RECTANGLE", "RECTANGULAR", "矩形板"}


def feature_snapshot_from_teklatest_part_features(features: Mapping[str, Any]) -> PartFeatureSnapshot:
    """Adapt teklatest PartFeatures JSON to the neutral snapshot contract."""
    basic = _nested(features, "BasicInfo", "basicInfo") or {}
    shape = _nested(features, "ShapeInfo", "shapeInfo") or {}
    profile = text(_nested(basic, "Profile", "profile"))
    length = as_float(_nested(basic, "Length", "length"))
    width = as_float(_nested(basic, "Width", "width"))
    height = as_float(_nested(basic, "Height", "height"))
    bolt_holes = _list_count(_nested(features, "BoltHoles", "boltHoles"))
    internal_holes = _list_count(_nested(features, "InternalHoles", "internalHoles"))
    cutouts = _list_count(_nested(features, "Cutouts", "cutouts"))
    notches = _list_count(_nested(features, "Notches", "notches"))
    chamfers = _list_count(_nested(features, "Chamfers", "chamfers"))
    bendings = _list_count(_nested(features, "Bendings", "bendings"))
    is_regular = _teklatest_shape_is_regular(shape)

    return PartFeatureSnapshot(
        part_id=text(_nested(basic, "PartGuid", "PartId", "partGuid", "partId")),
        position=text(_nested(basic, "PartMark", "partMark")),
        name=text(_nested(basic, "PartName", "partName")),
        profile=profile,
        material=text(_nested(basic, "Material", "material")),
        runtime_type=text(_nested(basic, "PartType", "partType")),
        is_plate_like=_plate_like_from_teklatest(basic),
        is_special_shape=not is_regular,
        thickness=height or as_float(profile.replace("PL", "")),
        obb_dims={key: value for key, value in {"x": length, "y": width, "z": height}.items() if value > 0},
        contour_vertex_count=as_int(_nested(shape, "ContourPointCount", "contourPointCount")),
        hole_like_feature_count=_list_count(_nested(features, "Holes", "holes")),
        internal_hole_count=internal_holes,
        boolean_cut_count=internal_holes + cutouts + notches,
        bolt_hole_count=bolt_holes,
        chamfer_count=chamfers,
        cutout_count=cutouts,
        notch_count=notches,
        bending_count=bendings,
        weld_count=_list_count(_nested(features, "Welds", "welds")),
        shape_type=text(_nested(shape, "ShapeType", "shapeType")),
        is_regular_shape=is_regular,
    )


def feature_snapshots_from_bundle_parts(
    parts: list[Mapping[str, Any]],
    rel_by_part: Mapping[str, Mapping[str, Any] | Counter[str]] | None = None,
) -> list[PartFeatureSnapshot]:
    rel_by_part = rel_by_part or {}
    return [
        feature_snapshot_from_bundle_part(part, rel_by_part.get(text(part.get("partId"))))
        for part in parts
    ]


def snapshot_to_part_dict(snapshot: PartFeatureSnapshot) -> dict[str, Any]:
    """Return the legacy dict shape consumed by the first Data Quality Gate.

    Keeping this compatibility bridge lets us move rules to snapshots in small,
    testable steps instead of rewriting all classifiers at once.
    """
    return {
        "partId": snapshot.part_id,
        "runtimeType": snapshot.runtime_type,
        "name": snapshot.name,
        "material": snapshot.material,
        "profileString": snapshot.profile,
        "isPlateLike": snapshot.is_plate_like,
        "isSpecialShape": snapshot.is_special_shape,
        "obbDims": dict(snapshot.obb_dims),
        "thickness": snapshot.thickness,
        "partPosition": snapshot.position,
        "contourVertexCount": snapshot.contour_vertex_count,
        "concaveCornerCount": snapshot.concave_corner_count,
        "holeLikeFeatureCount": snapshot.hole_like_feature_count,
        "internalHoleCount": snapshot.internal_hole_count,
        "booleanCutCount": snapshot.boolean_cut_count,
        "boltHoleCount": snapshot.bolt_hole_count,
        "chamferCount": snapshot.chamfer_count,
        "cutoutCount": snapshot.cutout_count,
        "notchCount": snapshot.notch_count,
        "bendingCount": snapshot.bending_count,
        "shapeType": snapshot.shape_type,
        "isRegularShape": snapshot.is_regular_shape,
        "hasArcContour": snapshot.has_arc_contour,
        "contourSegments": [{"length": length} for length in snapshot.contour_segment_lengths],
        "weldDetails": [{} for _ in range(snapshot.weld_count)],
    }


def build_feature_index(snapshots: list[PartFeatureSnapshot]) -> FeatureIndex:
    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    part_dicts = []
    by_part_id = {}
    for snapshot in snapshots:
        part_dict = snapshot_to_part_dict(snapshot)
        part_dicts.append(part_dict)
        by_position[snapshot.position].append(part_dict)
        by_part_id[snapshot.part_id] = snapshot
    return FeatureIndex(
        snapshots=list(snapshots),
        part_dicts=part_dicts,
        by_position=dict(by_position),
        by_part_id=by_part_id,
    )
