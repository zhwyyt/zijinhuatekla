"""Member-level complexity summary used by production review reports."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
from typing import Any

from ..adapters.normalized import normalized_part_from_bundle_part
from ..classifiers.corbel_units import CorbelUnit, classify_corbel_units
from ..geom.shop import classify_shop_shape
from ..rules import as_float, norm_spec, text
from ..spatial_features import classify_appendage_clusters_from_bundle


_CHANNEL_PREFIXES = ("C", "[", "UNP", "UPN", "PFC")
_BEND_LABELS = {
    "h-irregular-folded-flange",
    "h-folded-polybeam",
    "box-folded",
    "box-curved",
    "h-curved-polybeam",
}
_VARIATION_LABELS = {
    "section-width-varies",
    "section-height-varies",
    "section-variation-irregular",
}

MEMBER_COMPLEXITY_COLUMNS = [
    "构件名称",
    "装配ID",
    "主材类型",
    "主材形态",
    "牛腿数量",
    "牛腿楼层分布",
    "牛腿方向",
    "剖口数",
    "倒角数",
    "切割数",
    "洞口数",
    "螺栓孔数",
    "证据",
]


@dataclass(frozen=True)
class MemberComplexity:
    member_id: str
    assembly_id: str
    main_material_type: str
    main_material_form: str
    corbel_count: int
    corbel_floor_distribution: str
    corbel_orientation: str
    feature_counts: dict[str, int] = field(default_factory=dict)
    evidence_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_id": self.member_id,
            "assembly_id": self.assembly_id,
            "main_material_type": self.main_material_type,
            "main_material_form": self.main_material_form,
            "corbel_count": self.corbel_count,
            "corbel_floor_distribution": self.corbel_floor_distribution,
            "corbel_orientation": self.corbel_orientation,
            "feature_counts": dict(self.feature_counts),
            "evidence_codes": list(self.evidence_codes),
        }

    def to_row(self) -> dict[str, Any]:
        return {
            "构件名称": self.member_id,
            "装配ID": self.assembly_id,
            "主材类型": self.main_material_type,
            "主材形态": self.main_material_form,
            "牛腿数量": self.corbel_count,
            "牛腿楼层分布": self.corbel_floor_distribution,
            "牛腿方向": self.corbel_orientation,
            "剖口数": self.feature_counts.get("剖口", 0),
            "倒角数": self.feature_counts.get("倒角", 0),
            "切割数": self.feature_counts.get("切割", 0),
            "洞口数": self.feature_counts.get("洞口", 0),
            "螺栓孔数": self.feature_counts.get("螺栓孔", 0),
            "证据": ";".join(self.evidence_codes),
        }


def classify_member_complexity(
    assembly: Mapping[str, Any],
    member: Mapping[str, Any],
    *,
    corbel_units: Sequence[CorbelUnit] | None = None,
) -> MemberComplexity:
    member_id = text(
        (assembly.get("metadata") or {}).get("assemblyPosition")
        or (member.get("Member") or {}).get("Position")
    )
    assembly_id = text(assembly.get("assemblyId"))
    main_part = _main_part(assembly)
    classification = member.get("Classification") or {}
    labels = {text(item).lower() for item in classification.get("Labels") or []}
    main_material_type, type_evidence = _main_material_type(assembly, main_part, member)
    main_material_form, form_evidence = _main_material_form(member, main_part, labels)

    if corbel_units is None:
        clusters = classify_appendage_clusters_from_bundle(assembly, member)
        units = classify_corbel_units(assembly, clusters, member=dict(member))
    else:
        units = list(corbel_units)

    floor_distribution, floor_evidence = _corbel_floor_distribution(assembly, units)
    orientation, orientation_evidence = _corbel_orientation(member, assembly, units)
    evidence = type_evidence + form_evidence + floor_evidence + orientation_evidence
    return MemberComplexity(
        member_id=member_id,
        assembly_id=assembly_id,
        main_material_type=main_material_type,
        main_material_form=main_material_form,
        corbel_count=len(units),
        corbel_floor_distribution=floor_distribution,
        corbel_orientation=orientation,
        feature_counts=_part_feature_counts(assembly),
        evidence_codes=tuple(dict.fromkeys(evidence)),
    )


def _main_part(assembly: Mapping[str, Any]) -> Mapping[str, Any]:
    main_id = text(assembly.get("mainPartId"))
    for part in assembly.get("parts") or []:
        if text(part.get("partId")) == main_id:
            return part
    return {}


def _main_material_type(
    assembly: Mapping[str, Any],
    main_part: Mapping[str, Any],
    member: Mapping[str, Any],
) -> tuple[str, tuple[str, ...]]:
    profile = norm_spec(text(main_part.get("profileString") or main_part.get("profile")))
    section_type, section_evidence = _section_topology_type(
        member,
        assembly,
        profile,
        main_part.get("isPlateLike") is True,
    )
    if section_type is not None:
        return section_type, section_evidence
    return _direct_profile_type(profile, main_part.get("isPlateLike") is True)


def main_material_geometry_type(assembly: Mapping[str, Any], member: Mapping[str, Any]) -> str:
    main_part = _main_part(assembly)
    material_type, _ = _main_material_type(assembly, main_part, member)
    return material_type


_SECTION_SIGNATURE_LABELS = {
    "box": "BOX",
    "h": "H钢",
    "cross": "十字",
    "plate": "一字板",
}


def _section_topology_type(
    member: Mapping[str, Any],
    assembly: Mapping[str, Any],
    profile: str,
    is_plate_like: bool,
) -> tuple[str | None, tuple[str, ...]]:
    samples = [sample for sample in member.get("Samples") or [] if isinstance(sample, Mapping)]
    signature_counts = {signature: 0 for signature in _SECTION_SIGNATURE_LABELS}
    direct_profile_count = 0
    for sample in samples:
        signature, is_direct_profile = _section_sample_signature(sample)
        direct_profile_count += int(is_direct_profile)
        if signature == "plate" and not (profile.startswith(("PL", "FLAT")) or is_plate_like):
            signature = None
        if signature is not None:
            signature_counts[signature] += 1

    matched = tuple(
        signature
        for signature, count in signature_counts.items()
        if count > 0
    )
    evidence = tuple(
        f"section.{signature}_signature:{signature_counts[signature]}/{len(samples)}"
        for signature in _SECTION_SIGNATURE_LABELS
        if signature_counts[signature] > 0
    )
    if len(matched) > 1:
        return "UNKNOWN", ("section.conflict",) + evidence
    if len(matched) == 1:
        return _SECTION_SIGNATURE_LABELS[matched[0]], evidence
    if direct_profile_count:
        return None, (f"section.direct_profile_body:{direct_profile_count}/{len(samples)}",)
    station_loop_count = _closed_station_loop_count(assembly) if not samples else 0
    if station_loop_count:
        return "BOX", (f"section.closed_station_loop:{station_loop_count}",)
    return None, ()


def _closed_station_loop_count(assembly: Mapping[str, Any]) -> int:
    evidence = (assembly.get("metadata") or {}).get("boxSectionEvidence") or {}
    loops = evidence.get("stationLoops") if isinstance(evidence, Mapping) else None
    if not isinstance(loops, list):
        return 0
    return sum(
        as_float(loop.get("closedLoopCount")) > 0 or as_float(loop.get("cavityCount")) > 0
        for loop in loops
        if isinstance(loop, Mapping)
    )


def _section_sample_signature(sample: Mapping[str, Any]) -> tuple[str | None, bool]:
    feature = sample.get("SectionFeatures") or {}
    roles = {
        text(part.get("RoleHint")).lower()
        for part in sample.get("SectionParts") or []
        if isinstance(part, Mapping)
    }
    closed = as_float(feature.get("ClosedLoops")) > 0
    cavity = as_float(feature.get("CavityCount")) > 0
    major = as_float(feature.get("MajorPlateCount"))
    vertical = as_float(feature.get("CentralVerticalPlateCount"))
    horizontal = as_float(feature.get("CentralHorizontalPlateCount"))

    if closed and cavity:
        return "box", False
    if major == 3 and vertical == 1 and horizontal == 2 and not closed:
        return "h", False
    if major == vertical + horizontal and vertical == 2 and horizontal >= 3 and not closed:
        return "cross", False
    if major == 1 and not closed and "direct_profile_body" not in roles:
        return "plate", False
    if major == 1 and roles == {"direct_profile_body"}:
        return None, True
    return None, False


def _direct_profile_type(profile: str, is_plate_like: bool) -> tuple[str, tuple[str, ...]]:
    if profile.startswith("L"):
        return "角钢", ("profile.L",)
    if profile.startswith(_CHANNEL_PREFIXES):
        return "槽钢", ("profile.CHANNEL",)
    if profile.startswith(("BOX", "BBOX")):
        return "BOX", ("profile.BOX",)
    if profile.startswith(("PIPE", "CHS")):
        return "圆管", ("profile.PIPE",)
    if profile.startswith(("PL", "FLAT")) or is_plate_like:
        return "一字板", ("profile.PL", "main_part.plate_like")
    if profile.startswith(("BH", "H")) and not profile.startswith("HP"):
        return "H钢", ("profile.H",)
    return "UNKNOWN", ("profile.unknown",)


def _main_material_form(
    member: Mapping[str, Any],
    main_part: Mapping[str, Any],
    labels: set[str],
) -> tuple[str, tuple[str, ...]]:
    samples = [
        sample.get("SectionFeatures") or {}
        for sample in member.get("Samples") or []
        if isinstance(sample, Mapping)
    ]
    widths = [as_float(item.get("OuterWidth")) for item in samples]
    heights = [as_float(item.get("OuterHeight")) for item in samples]
    variation = any(_varies(values) for values in (widths, heights)) or bool(
        labels & _VARIATION_LABELS
    )
    bend_count = 0
    if main_part.get("runtimeType", "").lower() == "polybeam":
        bend_count = 2 if variation else 1
    if labels & _BEND_LABELS:
        bend_count = max(bend_count, 2)
    if bend_count > 1:
        return "多个折弯", ("main_part.polybeam", "section_variation")
    if bend_count == 1:
        return "折弯", ("main_part.polybeam",)
    if variation:
        return "变截面", ("section_variation",)
    return "同截面", ("section_constant",)


def _varies(values: Sequence[float]) -> bool:
    positive = [value for value in values if value > 0]
    if len(positive) < 2:
        return False
    span = max(positive) - min(positive)
    return span > max(5.0, 0.02 * max(positive))


def _corbel_floor_distribution(
    assembly: Mapping[str, Any],
    units: Sequence[CorbelUnit],
) -> tuple[str, tuple[str, ...]]:
    if not units:
        return "无", ()
    heights = _unit_heights(assembly, units)
    if len(heights) <= 1 or max(heights) - min(heights) <= 200.0:
        return "同一楼层高度", ("corbel.single_level",)
    return "多楼层高度", ("corbel.multi_level",)


def _corbel_orientation(
    member: Mapping[str, Any],
    assembly: Mapping[str, Any],
    units: Sequence[CorbelUnit],
) -> tuple[str, tuple[str, ...]]:
    if not units:
        return "无", ()
    main_axis = _member_axis(member)
    if main_axis is None:
        return "UNKNOWN", ("corbel.no_main_axis",)
    angles = [
        _angle_degrees(main_axis, axis)
        for axis in _unit_axes(assembly, units)
        if axis is not None
    ]
    if not angles:
        return "UNKNOWN", ("corbel.no_axis_evidence",)
    vertical = sum(1 for angle in angles if 70.0 <= angle <= 110.0)
    if vertical == len(angles):
        return "垂直", ("corbel.perpendicular",)
    if vertical == 0:
        return "斜", ("corbel.diagonal",)
    return "混合", ("corbel.mixed_orientation",)


def _part_feature_counts(assembly: Mapping[str, Any]) -> dict[str, int]:
    counts = {
        "剖口": 0,
        "倒角": 0,
        "切割": 0,
        "洞口": 0,
        "螺栓孔": 0,
    }
    for raw in assembly.get("parts") or []:
        part = normalized_part_from_bundle_part(raw)
        counts["剖口"] += int(part.has_edge_bevel)
        counts["切割"] += int(part.boolean_cut_count)
        counts["螺栓孔"] += int(part.bolt_hole_count)
        _, evidence = classify_shop_shape(
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
            has_edge_bevel=part.has_edge_bevel,
            has_end_chamfer=part.has_end_chamfer,
        )
        counts["倒角"] += int("平面倒角" in evidence)
        counts["洞口"] += int("洞口" in evidence)
    return counts


def _unit_heights(assembly: Mapping[str, Any], units: Sequence[CorbelUnit]) -> list[float]:
    parts = {
        text(part.get("partId")): part
        for part in assembly.get("parts") or []
        if text(part.get("partId"))
    }
    heights: list[float] = []
    for unit in units:
        cluster_parts = [parts[part_id] for part_id in unit.part_ids if part_id in parts]
        if not cluster_parts:
            continue
        total_weight = sum(max(as_float(part.get("volume"), 1.0), 1.0) for part in cluster_parts)
        weighted_z = sum(
            as_float((part.get("centroid") or {}).get("z"))
            * max(as_float(part.get("volume"), 1.0), 1.0)
            for part in cluster_parts
        )
        heights.append(weighted_z / total_weight if total_weight else 0.0)
    return heights


def _unit_axes(assembly: Mapping[str, Any], units: Sequence[CorbelUnit]) -> list[tuple[float, float, float] | None]:
    parts = {
        text(part.get("partId")): part
        for part in assembly.get("parts") or []
        if text(part.get("partId"))
    }
    axes: list[tuple[float, float, float] | None] = []
    for unit in units:
        candidates = [parts[part_id] for part_id in unit.spine_part_ids if part_id in parts]
        if not candidates:
            candidates = [parts[part_id] for part_id in unit.part_ids if part_id in parts]
        if not candidates:
            axes.append(None)
            continue
        spine = max(candidates, key=lambda part: as_float(part.get("volume"), 1.0))
        axis = ((spine.get("partCoordinateSystem") or {}).get("axisX") or {})
        direction = (as_float(axis.get("x")), as_float(axis.get("y")), as_float(axis.get("z")))
        axes.append(direction if any(direction) else None)
    return axes


def _member_axis(member: Mapping[str, Any]) -> tuple[float, float, float] | None:
    segments = member.get("AxisSegments") or []
    if not segments:
        return None
    direction = segments[0].get("Direction") or {}
    vector = (as_float(direction.get("X")), as_float(direction.get("Y")), as_float(direction.get("Z")))
    return vector if any(vector) else None


def _angle_degrees(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    dot = sum(left[index] * right[index] for index in range(3))
    left_length = math.sqrt(sum(value * value for value in left))
    right_length = math.sqrt(sum(value * value for value in right))
    if left_length <= 0 or right_length <= 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (left_length * right_length)))))
