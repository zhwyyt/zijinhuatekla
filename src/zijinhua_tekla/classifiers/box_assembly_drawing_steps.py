from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import re
from typing import Any

from ..rules import as_float, text


@dataclass(frozen=True)
class DrawingPartMarkTarget:
    part_id: str
    part_position: str
    profile: str
    name: str

    def to_dict(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "profile": self.profile,
            "name": self.name,
        }


@dataclass(frozen=True)
class DrawingDimensionTarget:
    kind: str
    part_ids: list[str]
    from_ref: str
    to_ref: str
    label: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "part_ids": list(self.part_ids),
            "from": self.from_ref,
            "to": self.to_ref,
            "label": self.label,
        }


@dataclass(frozen=True)
class DrawingViewHint:
    view_mode: str
    purpose: str
    preferred_detail: str = "main"

    def to_dict(self) -> dict[str, object]:
        return {
            "view_mode": self.view_mode,
            "purpose": self.purpose,
            "preferred_detail": self.preferred_detail,
        }


@dataclass(frozen=True)
class BoxAssemblyDrawingStep:
    assembly_id: str
    member_id: str
    step_no: int
    step_type: str
    title: str
    station_range: str
    new_part_ids: list[str]
    visible_part_ids: list[str]
    reference_part_ids: list[str]
    hidden_part_ids: list[str]
    part_mark_targets: list[DrawingPartMarkTarget]
    dimension_targets: list[DrawingDimensionTarget]
    view_hints: list[DrawingViewHint]
    evidence_codes: list[str]
    confidence: float
    issue_category: str = ""
    evidence_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "member_id": self.member_id,
            "step_no": self.step_no,
            "step_type": self.step_type,
            "title": self.title,
            "station_range": self.station_range,
            "new_part_ids": list(self.new_part_ids),
            "visible_part_ids": list(self.visible_part_ids),
            "reference_part_ids": list(self.reference_part_ids),
            "hidden_part_ids": list(self.hidden_part_ids),
            "part_mark_targets": [target.to_dict() for target in self.part_mark_targets],
            "dimension_targets": [target.to_dict() for target in self.dimension_targets],
            "view_hints": [hint.to_dict() for hint in self.view_hints],
            "evidence_codes": list(self.evidence_codes),
            "confidence": round(self.confidence, 3),
            "issue_category": self.issue_category,
            "evidence_summary": dict(self.evidence_summary),
        }


def build_box_assembly_drawing_steps(
    assembly: dict[str, Any],
    member_id: str,
    aligned_rows: list[dict[str, Any]],
    main_wall_groups: list[Any],
    box_part_spatial_relations: list[Any],
    spatial_classifications: list[Any],
) -> list[BoxAssemblyDrawingStep]:
    assembly_id = text(assembly.get("assemblyId"))
    parts_by_id = _parts_by_id(assembly)
    ordered_part_ids = [part_id for part_id in (text(part.get("partId")) for part in assembly.get("parts", [])) if part_id]
    all_part_ids = set(ordered_part_ids)
    main_wall_ids = _main_wall_part_ids(main_wall_groups)
    relation_by_part = {text(getattr(item, "part_id", "")): item for item in box_part_spatial_relations}
    steps: list[dict[str, Any]] = []

    base_ids, side_ids, cover_ids = _main_wall_step_groups(main_wall_ids, parts_by_id)
    if base_ids:
        steps.append(
            _draft_step(
                "BASE_MAIN_WALL",
                "基准主板",
                base_ids,
                [],
                parts_by_id,
                ["BOX_MAIN_WALL_CONFIRMED_SET", "BASE_WALL_SELECTED"],
                [DrawingDimensionTarget("station_range", base_ids, "member_start", "member_end", "基准主板 station 范围")],
                [DrawingViewHint("box_base_reference", "show_base_wall_reference")],
                0.9,
            )
        )
    if side_ids:
        steps.append(
            _draft_step(
                "ADD_SIDE_WALLS",
                "增加侧壁板形成开口截面",
                side_ids,
                base_ids,
                parts_by_id,
                ["BOX_MAIN_WALL_CONFIRMED_SET", "SIDE_WALLS_GROUPED"],
                [
                    DrawingDimensionTarget(
                        "section_offset_to_base_wall",
                        side_ids,
                        "base_main_wall",
                        "side_wall",
                        "侧壁相对基准主板定位",
                    )
                ],
                [DrawingViewHint("box_open_top", "show_u_shape_body")],
                0.86,
            )
        )
    for internal_ids in _internal_part_groups(relation_by_part, parts_by_id):
        steps.append(
            _draft_step(
                "ADD_INTERNAL_GROUP",
                "增加内部零件组",
                internal_ids,
                base_ids + side_ids,
                parts_by_id,
                ["BOX_PART_SPATIAL_RELATION_INSIDE_BODY", "INTERNAL_PARTS_STATION_GROUPED"],
                [
                    DrawingDimensionTarget("station_position", internal_ids, "member_start", "internal_group", "内部组 station 定位"),
                    DrawingDimensionTarget("offset_to_main_wall", internal_ids, "main_wall", "internal_group", "内部组相对主壁板定位"),
                ],
                [DrawingViewHint("box_open_top_detail", "show_internal_group", "detail")],
                0.82,
            )
        )
    if cover_ids:
        steps.append(
            _draft_step(
                "ADD_COVER_WALL",
                "增加盖板闭合 BOX",
                cover_ids,
                base_ids + side_ids,
                parts_by_id,
                ["BOX_MAIN_WALL_CONFIRMED_SET", "COVER_WALL_SELECTED"],
                [DrawingDimensionTarget("box_closure_station_range", cover_ids, "member_start", "member_end", "盖板闭合范围")],
                [DrawingViewHint("box_closed_section", "show_box_closure")],
                0.86,
            )
        )
    for external_ids, cluster in _external_cluster_groups(spatial_classifications, relation_by_part, parts_by_id):
        evidence = ["OUTSIDE_APPENDAGE_CLUSTER"]
        evidence.extend(text(code) for code in getattr(cluster, "evidence_codes", []) if text(code))
        steps.append(
            _draft_step(
                "ADD_EXTERNAL_CLUSTER",
                f"增加外部零件簇 {text(getattr(cluster, 'cluster_id', ''))}",
                external_ids,
                base_ids + side_ids + cover_ids,
                parts_by_id,
                evidence,
                [
                    DrawingDimensionTarget(
                        "appendage_cluster_root_station",
                        external_ids,
                        "member_start",
                        "appendage_cluster_root",
                        "外部簇根部 station 定位",
                    )
                ],
                [DrawingViewHint("external_cluster_detail", "show_appendage_cluster", "detail")],
                min(as_float(getattr(cluster, "confidence", 0.74)), 0.92),
                {"cluster_id": text(getattr(cluster, "cluster_id", "")), "role": text(getattr(cluster, "role", ""))},
            )
        )

    return _number_and_accumulate_steps(assembly_id, member_id, steps, ordered_part_ids, all_part_ids)


def _draft_step(
    step_type: str,
    title: str,
    new_part_ids: list[str],
    reference_part_ids: list[str],
    parts_by_id: dict[str, dict[str, Any]],
    evidence_codes: list[str],
    dimension_targets: list[DrawingDimensionTarget],
    view_hints: list[DrawingViewHint],
    confidence: float,
    evidence_summary: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "step_type": step_type,
        "title": title,
        "new_part_ids": _ordered_existing(new_part_ids, parts_by_id),
        "reference_part_ids": _ordered_existing(reference_part_ids, parts_by_id),
        "station_range": _station_range_for_parts(new_part_ids, parts_by_id),
        "part_mark_targets": [_mark_target(parts_by_id[part_id]) for part_id in _ordered_existing(new_part_ids, parts_by_id)],
        "dimension_targets": dimension_targets,
        "view_hints": view_hints,
        "evidence_codes": _dedupe(evidence_codes),
        "confidence": confidence,
        "evidence_summary": evidence_summary or {},
    }


def _number_and_accumulate_steps(
    assembly_id: str,
    member_id: str,
    draft_steps: list[dict[str, Any]],
    ordered_part_ids: list[str],
    all_part_ids: set[str],
) -> list[BoxAssemblyDrawingStep]:
    visible: list[str] = []
    result = []
    order_index = {part_id: index for index, part_id in enumerate(ordered_part_ids)}
    for index, draft in enumerate(draft_steps, start=1):
        for part_id in draft["new_part_ids"]:
            if part_id not in visible:
                visible.append(part_id)
        visible_sorted = sorted(visible, key=lambda part_id: order_index.get(part_id, len(order_index)))
        hidden = sorted(all_part_ids - set(visible_sorted), key=lambda part_id: order_index.get(part_id, len(order_index)))
        result.append(
            BoxAssemblyDrawingStep(
                assembly_id=assembly_id,
                member_id=member_id,
                step_no=index,
                step_type=draft["step_type"],
                title=draft["title"],
                station_range=draft["station_range"],
                new_part_ids=list(draft["new_part_ids"]),
                visible_part_ids=visible_sorted,
                reference_part_ids=list(draft["reference_part_ids"]),
                hidden_part_ids=hidden,
                part_mark_targets=list(draft["part_mark_targets"]),
                dimension_targets=list(draft["dimension_targets"]),
                view_hints=list(draft["view_hints"]),
                evidence_codes=list(draft["evidence_codes"]),
                confidence=draft["confidence"],
                evidence_summary=dict(draft["evidence_summary"]),
            )
        )
    return result


def _main_wall_part_ids(main_wall_groups: list[Any]) -> set[str]:
    return {
        text(part_id)
        for group in main_wall_groups
        if text(getattr(group, "group_type", "")) == "BOX_MAIN_WALL_CONFIRMED_SET"
        for part_id in getattr(group, "part_ids", [])
        if text(part_id)
    }


def _main_wall_step_groups(
    main_wall_ids: set[str],
    parts_by_id: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    by_face: dict[str, list[str]] = defaultdict(list)
    for part_id in main_wall_ids:
        part = parts_by_id.get(part_id)
        if not part:
            continue
        by_face[_face_key(part)].append(part_id)
    groups = [(face, _sort_part_ids(part_ids, parts_by_id)) for face, part_ids in by_face.items()]
    groups.sort(key=lambda item: (_face_role_priority(item[0]), item[0], _station_start(parts_by_id[item[1][0]]) if item[1] else 0.0))
    if not groups:
        return [], [], []
    base_face, base_ids = groups[0]
    cover_candidates = [item for item in groups[1:] if _face_role_priority(item[0]) >= 2]
    if cover_candidates:
        cover_face, cover_ids = cover_candidates[-1]
    elif len(groups) > 1:
        cover_face, cover_ids = groups[-1]
    else:
        cover_face, cover_ids = "", []
    side_ids = []
    for face, part_ids in groups:
        if face in {base_face, cover_face}:
            continue
        side_ids.extend(part_ids)
    return base_ids, _sort_part_ids(side_ids, parts_by_id), cover_ids


def _internal_part_groups(
    relation_by_part: dict[str, Any],
    parts_by_id: dict[str, dict[str, Any]],
) -> list[list[str]]:
    buckets: dict[int, list[str]] = defaultdict(list)
    for part_id, relation in relation_by_part.items():
        if text(getattr(relation, "relation_to_box_body", "")) != "INSIDE_BODY" or part_id not in parts_by_id:
            continue
        station_start = _station_start(parts_by_id[part_id])
        buckets[int(station_start // 500)].append(part_id)
    return [_sort_part_ids(part_ids, parts_by_id) for _bucket, part_ids in sorted(buckets.items())]


def _external_cluster_groups(
    spatial_classifications: list[Any],
    relation_by_part: dict[str, Any],
    parts_by_id: dict[str, dict[str, Any]],
) -> list[tuple[list[str], Any]]:
    result = []
    used: set[str] = set()
    for cluster in spatial_classifications:
        part_ids = [
            text(part_id)
            for part_id in getattr(cluster, "part_ids", [])
            if text(part_id) in parts_by_id and _is_outside_relation(text(part_id), relation_by_part)
        ]
        part_ids = _ordered_existing(part_ids, parts_by_id)
        if not part_ids:
            continue
        used.update(part_ids)
        result.append((part_ids, cluster))
    unclustered = [
        part_id
        for part_id, relation in relation_by_part.items()
        if part_id not in used and part_id in parts_by_id and text(getattr(relation, "relation_to_box_body", "")) == "OUTSIDE_ATTACHMENT"
    ]
    for part_ids in _bucket_part_ids(unclustered, parts_by_id):
        result.append((part_ids, _SyntheticCluster(part_ids)))
    return sorted(result, key=lambda item: (_station_start(parts_by_id[item[0][0]]) if item[0] else 0.0, ";".join(item[0])))


@dataclass(frozen=True)
class _SyntheticCluster:
    part_ids: list[str]
    cluster_id: str = "unclustered-outside"
    role: str = "OutsideAttachment"
    confidence: float = 0.62
    evidence_codes: list[str] = field(default_factory=lambda: ["OUTSIDE_RELATION_UNCLUSTERED"])


def _is_outside_relation(part_id: str, relation_by_part: dict[str, Any]) -> bool:
    relation = relation_by_part.get(part_id)
    return text(getattr(relation, "relation_to_box_body", "")) == "OUTSIDE_ATTACHMENT"


def _bucket_part_ids(part_ids: list[str], parts_by_id: dict[str, dict[str, Any]]) -> list[list[str]]:
    buckets: dict[int, list[str]] = defaultdict(list)
    for part_id in part_ids:
        buckets[int(_station_start(parts_by_id[part_id]) // 500)].append(part_id)
    return [_sort_part_ids(values, parts_by_id) for _bucket, values in sorted(buckets.items())]


def _parts_by_id(assembly: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {text(part.get("partId")): part for part in assembly.get("parts", []) if text(part.get("partId"))}


def _mark_target(part: dict[str, Any]) -> DrawingPartMarkTarget:
    return DrawingPartMarkTarget(
        part_id=text(part.get("partId")),
        part_position=text(part.get("partPosition")),
        profile=text(part.get("profileString") or part.get("profile")),
        name=text(part.get("name")),
    )


def _face_key(part: dict[str, Any]) -> str:
    evidence = part.get("mainMaterialEvidence", {})
    return text(evidence.get("bodyFaceId")) or "UNKNOWN_FACE"


def _face_role_priority(face: str) -> int:
    value = face.upper()
    if any(token in value for token in ("BOTTOM", "BASE", "LOWER", "底")):
        return 0
    if any(token in value for token in ("TOP", "COVER", "UPPER", "盖")):
        return 2
    return 1


def _station_start(part: dict[str, Any]) -> float:
    return as_float(part.get("mainMaterialEvidence", {}).get("axisStationStart"))


def _station_end(part: dict[str, Any]) -> float:
    return as_float(part.get("mainMaterialEvidence", {}).get("axisStationEnd"))


def _station_range_for_parts(part_ids: list[str], parts_by_id: dict[str, dict[str, Any]]) -> str:
    starts = [_station_start(parts_by_id[part_id]) for part_id in part_ids if part_id in parts_by_id]
    ends = [_station_end(parts_by_id[part_id]) for part_id in part_ids if part_id in parts_by_id]
    if not starts or not ends:
        return ""
    return f"{min(starts):.1f}-{max(ends):.1f}"


def _sort_part_ids(part_ids: list[str], parts_by_id: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        _dedupe([part_id for part_id in part_ids if part_id in parts_by_id]),
        key=lambda part_id: (_station_start(parts_by_id[part_id]), _station_end(parts_by_id[part_id]), text(parts_by_id[part_id].get("partPosition")), part_id),
    )


def _ordered_existing(part_ids: list[str], parts_by_id: dict[str, dict[str, Any]]) -> list[str]:
    return [part_id for part_id in _dedupe(part_ids) if part_id in parts_by_id]


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        item = text(value)
        if item and item not in result:
            result.append(item)
    return result


def _parse_station_range(value: str) -> tuple[float, float]:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", value)
    if match is None:
        return 0.0, 0.0
    return float(match.group(1)), float(match.group(2))
