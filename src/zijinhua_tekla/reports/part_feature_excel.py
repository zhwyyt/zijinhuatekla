"""Excel rows: original H/BOX main-material fork, part features in separate columns.

Does not change main-material classifiers. H members do not inherit BOX/CROSS wall labels.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from ..adapters.normalized import normalized_part_from_bundle_part
from ..classifiers.box_main_material_segments import classify_box_main_material_segment_groups
from ..classifiers.box_part_spatial_relations import classify_box_part_spatial_relations
from ..classifiers.composite_main_material_segments import (
    CompositeSegmentType,
    classify_composite_main_material_segments,
)
from ..classifiers.weld_backing import classify_weld_backing_plates
from ..geom.shop import classify_shop_process, classify_shop_shape, is_rolled_profile
from ..part_roles import MAIN_MATERIAL_LABELS
from .member_complexity import main_material_geometry_type
from ..rules import text

FEATURE_COLUMNS = [
    "装配ID",
    "构件名称",
    "零件名称",
    "规格",
    "长度",
    "数量",
    "材质",
    "构件类型",
    "主材",
    "主材说明",
    "BOX内零件",
    "工序",
    "形状分类",
    "剖口",
    "倒角",
    "割孔",
    "洞口",
    "切割",
    "螺栓孔",
    "焊接垫板",
    "证据",
]


def algorithm_body_type(member: Mapping[str, Any] | None) -> str:
    if not member:
        return "UNKNOWN"
    classification = member.get("Classification") or {}
    main_class = text(classification.get("MainClass")).upper()
    if main_class in {"1", "H", "BH", "H_BEAM"}:
        return "H"
    if main_class in {"2", "BOX"}:
        return "BOX"
    if main_class == "3":
        return "T"
    if main_class == "4":
        return "十字"
    if main_class == "5":
        return "角钢"
    if main_class == "6":
        return "圆管"
    if main_class == "7":
        return "异形"
    key_dimensions = text(classification.get("KeyDimensionsDisplay")).upper()
    if key_dimensions.startswith(("BH", "H")) and not key_dimensions.startswith("HP"):
        return "H"
    if key_dimensions.startswith("BOX"):
        return "BOX"
    return main_class or "UNKNOWN"


def build_part_feature_rows(
    assembly: Mapping[str, Any],
    member: Mapping[str, Any] | None,
    member_id: str = "",
) -> list[dict[str, Any]]:
    assembly_id = text(assembly.get("assemblyId"))
    member_id = member_id or text((assembly.get("metadata") or {}).get("assemblyPosition"))
    geometry_type = main_material_geometry_type(assembly, member or {})
    if geometry_type == "H钢":
        body_type = "H" if geometry_type == "H钢" else geometry_type
    elif geometry_type in {"BOX", "十字", "一字板", "角钢", "槽钢", "圆管"}:
        body_type = geometry_type
    else:
        body_type = "UNKNOWN"
    main_by_id, inside_ids = _main_material_marks(assembly, member, body_type)
    if body_type == "一字板":
        main_id = text(assembly.get("mainPartId"))
        if main_id:
            main_by_id[main_id] = "一字板"
    backing = classify_weld_backing_plates(assembly)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in assembly.get("parts") or []:
        part = normalized_part_from_bundle_part(raw)
        position = part.part_position or part.part_id
        is_main = part.part_id in main_by_id
        process = classify_shop_process(
            profile=part.profile,
            runtime_type=part.runtime_type,
            is_plate_like=part.is_plate_like,
            thickness=part.thickness,
            obb_dims=part.obb_dims,
            bolt_hole_count=part.bolt_hole_count,
            hole_like_feature_count=part.hole_like_feature_count,
            boolean_cut_count=part.boolean_cut_count,
            edge_bevel_count=part.edge_bevel_count,
            end_chamfer_count=part.end_chamfer_count,
            declared_process=part.declared_process,
        )
        shape, shape_evidence = classify_shop_shape(
            profile=part.profile,
            runtime_type=part.runtime_type,
            is_plate_like=part.is_plate_like,
            thickness=part.thickness,
            obb_dims=part.obb_dims,
            contour_vertex_count=part.contour_vertex_count,
            concave_corner_count=part.concave_corner_count,
            contour_points=part.contour_points,
            contour_chamfers=part.contour_chamfers,
            hole_like_feature_count=part.hole_like_feature_count,
            bolt_hole_count=part.bolt_hole_count,
            is_main_material=is_main,
            has_edge_bevel=part.has_edge_bevel,
            has_end_chamfer=part.has_end_chamfer,
        )
        backing_evidence = backing.get(part.part_id, ())
        feature_evidence = list(process.evidence) + list(shape_evidence)
        evidence = feature_evidence + list(backing_evidence)
        grouped[position].append(
            {
                "part": part,
                "main_kind": main_by_id.get(part.part_id, ""),
                "inside": part.part_id in inside_ids,
                "process": process.combined,
                "shape": shape,
                "backing": bool(backing_evidence),
                "feature_evidence": feature_evidence,
                "evidence": evidence,
            }
        )

    rows: list[dict[str, Any]] = []
    for position, items in grouped.items():
        part = items[0]["part"]
        processes = {item["process"] for item in items}
        shapes = {item["shape"] for item in items}
        process = "UNKNOWN" if len(processes) > 1 else items[0]["process"]
        shape = "UNKNOWN" if len(shapes) > 1 else items[0]["shape"]
        evidence = list(dict.fromkeys(code for item in items for code in item["evidence"]))
        feature_evidence = list(dict.fromkeys(code for item in items for code in item["feature_evidence"]))
        if len(processes) > 1 or len(shapes) > 1:
            evidence = ["同号零件分类不一致"] + evidence
        main_kind = next((item["main_kind"] for item in items if item["main_kind"]), "")
        evidence_text = ";".join(evidence)
        feature_text = ";".join(feature_evidence)
        rows.append(
            {
                "装配ID": assembly_id,
                "构件名称": member_id,
                "零件名称": position,
                "规格": part.profile,
                "长度": int(round(part.length)) if part.length else 0,
                "数量": len(items),
                "材质": part.material,
                "构件类型": body_type,
                "主材": "是" if main_kind else "否",
                "主材说明": main_kind,
                "BOX内零件": "是" if any(item["inside"] for item in items) else "否",
                "工序": process,
                "形状分类": shape,
                "剖口": _flag(feature_text, "剖口"),
                "倒角": _flag(feature_text, "倒角"),
                "割孔": "是" if "下料割孔" in process else "否",
                "洞口": _flag(feature_text, "洞口"),
                "切割": "是" if any(item["part"].boolean_cut_count > 0 for item in items) else "否",
                "螺栓孔": "是" if any(item["part"].bolt_hole_count > 0 for item in items) else "否",
                "焊接垫板": "是" if any(item["backing"] for item in items) else "否",
                "证据": evidence_text,
            }
        )
    return rows


def _main_material_marks(
    assembly: Mapping[str, Any],
    member: Mapping[str, Any] | None,
    body_type: str,
) -> tuple[dict[str, str], set[str]]:
    groups = classify_box_main_material_segment_groups(assembly, member or {})
    composite = classify_composite_main_material_segments(
        assembly, member or {}, main_material_groups=groups
    )
    main_by_id: dict[str, str] = {}
    if body_type == "H":
        for segment in composite:
            if segment.segment_type != CompositeSegmentType.H_OR_BH_SECTION:
                continue
            for plate in segment.main_plates:
                part_id = text(plate.part_id)
                if part_id:
                    main_by_id[part_id] = MAIN_MATERIAL_LABELS.get(
                        plate.primary_role.value, "H主板"
                    )
        _mark_direct_h_profile(assembly, main_by_id)
        return main_by_id, set()

    relations = classify_box_part_spatial_relations(assembly, member or {}, groups)
    inside_ids: set[str] = set()
    for relation in relations:
        part_id = text(relation.part_id)
        if not part_id:
            continue
        if relation.relation_to_box_body == "MAIN_WALL" and body_type == "BOX":
            main_by_id.setdefault(part_id, "BOX主壁板")
        elif body_type == "BOX" and relation.relation_to_box_body == "INSIDE_BODY":
            inside_ids.add(part_id)
    for group in groups:
        if group.group_type != "BOX_MAIN_WALL_CONFIRMED_SET" or body_type != "BOX":
            continue
        for part_id in group.part_ids:
            token = text(part_id)
            if token:
                main_by_id[token] = "BOX主壁板"
    return main_by_id, inside_ids


def _mark_direct_h_profile(assembly: Mapping[str, Any], main_by_id: dict[str, str]) -> None:
    evidence = (assembly.get("metadata") or {}).get("hBeamSectionEvidence") or {}
    source = text(evidence.get("source") if isinstance(evidence, Mapping) else "")
    main_id = text(assembly.get("mainPartId"))
    if not main_id:
        return
    part = next(
        (
            item
            for item in assembly.get("parts") or []
            if text(item.get("partId")) == main_id
        ),
        None,
    )
    if part is None:
        return
    profile = text(part.get("profileString") or part.get("profile"))
    direct = source == "directHProfileSectionFrame.v1"
    rolled = is_rolled_profile(profile)
    if not (direct or (rolled and not main_by_id)):
        return
    if rolled or direct:
        main_by_id.setdefault(main_id, "型钢")


def _flag(evidence: str, token: str) -> str:
    return "是" if token in evidence else "否"
