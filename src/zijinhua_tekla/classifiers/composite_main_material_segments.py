from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CompositeSegmentType(str, Enum):
    CROSS_CORE_WITH_FLANGES = "CROSS_CORE_WITH_FLANGES"
    CROSS_TO_BOX_TRANSITION = "CROSS_TO_BOX_TRANSITION"
    PARTIAL_BOX_FORMING = "PARTIAL_BOX_FORMING"
    BOX_CLOSED_SECTION = "BOX_CLOSED_SECTION"
    END_OR_NODE_ZONE = "END_OR_NODE_ZONE"
    MIXED_OR_INSUFFICIENT_EVIDENCE = "MIXED_OR_INSUFFICIENT_EVIDENCE"
    H_OR_BH_SECTION = "H_OR_BH_SECTION"


class CompositePrimaryRole(str, Enum):
    CROSS_CORE_MAIN_PLATE = "CROSS_CORE_MAIN_PLATE"
    CROSS_FLANGE_MAIN_PLATE = "CROSS_FLANGE_MAIN_PLATE"
    BOX_MAIN_WALL_PLATE = "BOX_MAIN_WALL_PLATE"
    BOX_FORMING_MAIN_PLATE = "BOX_FORMING_MAIN_PLATE"
    TRANSITION_MAIN_PLATE = "TRANSITION_MAIN_PLATE"
    END_NODE_MAIN_PLATE_CANDIDATE = "END_NODE_MAIN_PLATE_CANDIDATE"
    H_TOP_FLANGE_MAIN_PLATE = "H_TOP_FLANGE_MAIN_PLATE"
    H_BOTTOM_FLANGE_MAIN_PLATE = "H_BOTTOM_FLANGE_MAIN_PLATE"
    H_WEB_MAIN_PLATE = "H_WEB_MAIN_PLATE"
    H_FLANGE_MAIN_PLATE = "H_FLANGE_MAIN_PLATE"


@dataclass(frozen=True)
class CompositeMainPlate:
    part_id: str
    part_position: str
    primary_role: CompositePrimaryRole
    secondary_evidence: list[str] = field(default_factory=list)
    evidence_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "primary_role": self.primary_role.value,
            "secondary_evidence": list(self.secondary_evidence),
            "evidence_codes": list(self.evidence_codes),
        }


@dataclass(frozen=True)
class CompositeMainMaterialSegment:
    assembly_id: str
    segment_id: str
    station_start: float
    station_end: float
    segment_type: CompositeSegmentType
    main_plates: list[CompositeMainPlate]
    confidence: float
    evidence_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "segment_id": self.segment_id,
            "station_start": round(self.station_start, 3),
            "station_end": round(self.station_end, 3),
            "segment_type": self.segment_type.value,
            "confidence": round(self.confidence, 3),
            "evidence_codes": list(self.evidence_codes),
            "main_plates": [plate.to_dict() for plate in self.main_plates],
        }


@dataclass(frozen=True)
class _StationSnapshot:
    station: float
    segment_type: CompositeSegmentType
    active_part_ids: list[str]
    evidence_codes: list[str]


def classify_composite_main_material_segments(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
    main_material_groups: list[Any] | None = None,
) -> list[CompositeMainMaterialSegment]:
    adapted = _adapt_h_or_gl_main_material_groups(assembly, main_material_groups or [])
    if adapted:
        return adapted
    snapshots = _station_snapshots(assembly)
    if not snapshots:
        return []
    return _merge_snapshots_into_segments(str(assembly.get("assemblyId", "")), snapshots, assembly)



def _adapt_h_or_gl_main_material_groups(
    assembly: dict[str, Any],
    groups: list[Any],
) -> list[CompositeMainMaterialSegment]:
    plates: list[CompositeMainPlate] = []
    evidence_codes = ["adapted_from_main_material_segment_groups"]
    starts: list[float] = []
    ends: list[float] = []
    for group in groups:
        role = str(getattr(group, "evidence_summary", {}).get("main_material_role", ""))
        primary_role = _h_or_gl_primary_role(role)
        if primary_role is None:
            continue
        evidence_codes.extend(str(code) for code in getattr(group, "evidence_codes", []))
        part_ids = [str(value) for value in getattr(group, "part_ids", [])]
        part_positions = [str(value) for value in getattr(group, "part_positions", [])]
        for index, part_id in enumerate(part_ids):
            part_position = part_positions[index] if index < len(part_positions) else ""
            plates.append(
                CompositeMainPlate(
                    part_id=part_id,
                    part_position=part_position,
                    primary_role=primary_role,
                    secondary_evidence=["h_or_gl_main_material_group"],
                    evidence_codes=["H_OR_GL_MAIN_MATERIAL_GROUP", primary_role.value],
                )
            )
        starts.extend(_group_station_starts(getattr(group, "station_ranges", "")))
        ends.extend(_group_station_ends(getattr(group, "station_ranges", "")))
    if not plates:
        return []
    return [
        CompositeMainMaterialSegment(
            assembly_id=str(assembly.get("assemblyId", "")),
            segment_id="S1",
            station_start=min(starts) if starts else 0.0,
            station_end=max(ends) if ends else _member_axis_length(assembly),
            segment_type=CompositeSegmentType.H_OR_BH_SECTION,
            main_plates=sorted(plates, key=lambda plate: (plate.primary_role.value, plate.part_position, plate.part_id)),
            confidence=0.86,
            evidence_codes=_dedupe(evidence_codes),
        )
    ]


def _h_or_gl_primary_role(role: str) -> CompositePrimaryRole | None:
    if role == "TOP_FLANGE":
        return CompositePrimaryRole.H_TOP_FLANGE_MAIN_PLATE
    if role == "BOTTOM_FLANGE":
        return CompositePrimaryRole.H_BOTTOM_FLANGE_MAIN_PLATE
    if role == "WEB":
        return CompositePrimaryRole.H_WEB_MAIN_PLATE
    if role == "FLANGE":
        return CompositePrimaryRole.H_FLANGE_MAIN_PLATE
    return None


def _group_station_starts(station_ranges: str) -> list[float]:
    return [start for start, _end in _parse_group_station_ranges(station_ranges)]


def _group_station_ends(station_ranges: str) -> list[float]:
    return [end for _start, end in _parse_group_station_ranges(station_ranges)]


def _parse_group_station_ranges(station_ranges: str) -> list[tuple[float, float]]:
    ranges = []
    for item in str(station_ranges).split(";"):
        if ":" not in item or "-" not in item:
            continue
        value = item.rsplit(":", 1)[-1]
        start_text, end_text = value.split("-", 1)
        try:
            ranges.append((float(start_text), float(end_text)))
        except ValueError:
            continue
    return ranges

def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
def _station_snapshots(assembly: dict[str, Any]) -> list[_StationSnapshot]:
    parts = [part for part in assembly.get("parts", []) if _is_main_candidate(part)]
    station_loops = (
        assembly.get("metadata", {})
        .get("boxSectionEvidence", {})
        .get("stationLoops", [])
    )
    snapshots = []
    for station_loop in station_loops:
        station = float(station_loop.get("station", 0.0))
        active = [part for part in parts if _part_active_at(part, station)]
        segment_type = _classify_station_type(station_loop, active)
        snapshots.append(
            _StationSnapshot(
                station=station,
                segment_type=segment_type,
                active_part_ids=[str(part.get("partId", "")) for part in active],
                evidence_codes=["STATION_REGIME_CLASSIFIED"],
            )
        )
    return sorted(snapshots, key=lambda item: item.station)


def _classify_station_type(
    station_loop: dict[str, Any],
    active_parts: list[dict[str, Any]],
) -> CompositeSegmentType:
    if _has_box_closed_section_evidence(station_loop):
        return CompositeSegmentType.BOX_CLOSED_SECTION
    normal_axes = {_normal_axis(part) for part in active_parts}
    has_cross_core = "X" in normal_axes and "Y" in normal_axes
    has_outer_flange = any(_is_outer_offset(part) for part in active_parts)
    has_box_forming = sum(1 for part in active_parts if _is_box_forming_candidate(part)) >= 2
    if has_cross_core and has_box_forming:
        return CompositeSegmentType.CROSS_TO_BOX_TRANSITION
    if has_cross_core and has_outer_flange:
        return CompositeSegmentType.CROSS_CORE_WITH_FLANGES
    if has_box_forming:
        return CompositeSegmentType.PARTIAL_BOX_FORMING
    if int(station_loop.get("closedLoopCount") or 0) > 0:
        return CompositeSegmentType.BOX_CLOSED_SECTION
    return CompositeSegmentType.MIXED_OR_INSUFFICIENT_EVIDENCE


def _has_box_closed_section_evidence(station_loop: dict[str, Any]) -> bool:
    if int(station_loop.get("innerLoopCount") or 0) > 0:
        return True
    status = str(station_loop.get("topologyStatus") or station_loop.get("topology_status") or "")
    if status == "CLOSED_WITH_CAVITY":
        return True
    diagnostics = station_loop.get("diagnostics", [])
    if isinstance(diagnostics, list) and "compositeTestRegime=box" in diagnostics:
        return True
    return False


def _merge_snapshots_into_segments(
    assembly_id: str,
    snapshots: list[_StationSnapshot],
    assembly: dict[str, Any],
) -> list[CompositeMainMaterialSegment]:
    result = []
    group_start = 0
    for index in range(1, len(snapshots) + 1):
        if index < len(snapshots) and snapshots[index].segment_type == snapshots[group_start].segment_type:
            continue
        first = snapshots[group_start]
        last = snapshots[index - 1]
        station_start = first.station
        station_end = last.station
        if index < len(snapshots):
            station_end = snapshots[index].station
        else:
            station_end = max(_member_axis_length(assembly), _max_candidate_station_end(assembly), last.station)
        main_plates = _assign_main_plates(assembly, station_start, station_end, first.segment_type)
        result.append(
            CompositeMainMaterialSegment(
                assembly_id=assembly_id,
                segment_id=f"S{len(result) + 1}",
                station_start=station_start,
                station_end=station_end,
                segment_type=first.segment_type,
                main_plates=main_plates,
                confidence=0.75,
                evidence_codes=["STATION_REGIME_SEGMENT"],
            )
        )
        group_start = index
    return result


def _member_axis_length(assembly: dict[str, Any]) -> float:
    return float(
        assembly.get("metadata", {})
        .get("memberAxisEvidence", {})
        .get("length")
        or 0.0
    )


def _max_candidate_station_end(assembly: dict[str, Any]) -> float:
    station_ends = []
    for part in assembly.get("parts", []):
        if _is_main_candidate(part):
            station_ends.append(_station_end(part))
    return max(station_ends, default=0.0)


def _is_main_candidate(part: dict[str, Any]) -> bool:
    return part.get("mainMaterialEvidence", {}).get("isBodyWallPlateCandidate") is True


def _part_active_at(part: dict[str, Any], station: float) -> bool:
    return _station_start(part) <= station <= _station_end(part)


def _station_start(part: dict[str, Any]) -> float:
    evidence = part.get("mainMaterialEvidence", {})
    return float(evidence.get("axisStationStart") or 0.0)


def _station_end(part: dict[str, Any]) -> float:
    evidence = part.get("mainMaterialEvidence", {})
    return float(evidence.get("axisStationEnd") or 0.0)


def _interval_overlaps(part: dict[str, Any], start: float, end: float) -> bool:
    return _station_start(part) < end and _station_end(part) > start


def _assign_main_plates(
    assembly: dict[str, Any],
    station_start: float,
    station_end: float,
    segment_type: CompositeSegmentType,
) -> list[CompositeMainPlate]:
    parts = [
        part for part in assembly.get("parts", [])
        if _is_main_candidate(part) and _interval_overlaps(part, station_start, station_end)
    ]
    plates = []
    for part in parts:
        primary_role, secondary = _primary_role_for_part(part, segment_type)
        if primary_role is None:
            continue
        plates.append(
            CompositeMainPlate(
                part_id=str(part.get("partId", "")),
                part_position=str(part.get("partPosition", "")),
                primary_role=primary_role,
                secondary_evidence=secondary,
                evidence_codes=[segment_type.value, primary_role.value],
            )
        )
    return sorted(plates, key=lambda plate: (plate.primary_role.value, plate.part_position, plate.part_id))


def _primary_role_for_part(
    part: dict[str, Any],
    segment_type: CompositeSegmentType,
) -> tuple[CompositePrimaryRole | None, list[str]]:
    if segment_type == CompositeSegmentType.CROSS_CORE_WITH_FLANGES:
        if _is_outer_offset(part):
            return CompositePrimaryRole.CROSS_FLANGE_MAIN_PLATE, ["parallel_to_cross_core_plate"]
        if _is_cross_core_candidate(part):
            return CompositePrimaryRole.CROSS_CORE_MAIN_PLATE, []
        return None, []
    if segment_type == CompositeSegmentType.CROSS_TO_BOX_TRANSITION:
        if _is_box_forming_candidate(part):
            return CompositePrimaryRole.BOX_FORMING_MAIN_PLATE, ["overlaps_with_cross_column_transition"]
        return CompositePrimaryRole.TRANSITION_MAIN_PLATE, ["continues_from_lower_cross_column"]
    if segment_type == CompositeSegmentType.PARTIAL_BOX_FORMING:
        return CompositePrimaryRole.BOX_FORMING_MAIN_PLATE, []
    if segment_type == CompositeSegmentType.BOX_CLOSED_SECTION:
        return CompositePrimaryRole.BOX_MAIN_WALL_PLATE, []
    if segment_type == CompositeSegmentType.END_OR_NODE_ZONE:
        return CompositePrimaryRole.END_NODE_MAIN_PLATE_CANDIDATE, []
    return None, []


def _normal_axis(part: dict[str, Any]) -> str:
    normal = (
        part.get("mainMaterialEvidence", {})
        .get("sectionProjectionEvidence", {})
        .get("normalProjection", {})
    )
    u = abs(float(normal.get("u") or 0.0))
    v = abs(float(normal.get("v") or 0.0))
    return "X" if u >= v else "Y"


def _is_outer_offset(part: dict[str, Any]) -> bool:
    centroid = (
        part.get("mainMaterialEvidence", {})
        .get("sectionProjectionEvidence", {})
        .get("projectedCentroid", {})
    )
    u = abs(float(centroid.get("u") or 0.0))
    v = abs(float(centroid.get("v") or 0.0))
    return u >= 150 or v >= 150


def _is_cross_core_candidate(part: dict[str, Any]) -> bool:
    if _is_outer_offset(part):
        return False
    return _section_projection_major_span(part) >= 250


def _section_projection_major_span(part: dict[str, Any]) -> float:
    projection = part.get("mainMaterialEvidence", {}).get("sectionProjectionEvidence", {})
    bounds_min = projection.get("projectedBoundsMin", {})
    bounds_max = projection.get("projectedBoundsMax", {})
    span_u = abs(float(bounds_max.get("u") or 0.0) - float(bounds_min.get("u") or 0.0))
    span_v = abs(float(bounds_max.get("v") or 0.0) - float(bounds_min.get("v") or 0.0))
    return max(span_u, span_v)


def _is_box_forming_candidate(part: dict[str, Any]) -> bool:
    if not _is_main_candidate(part) or not _is_outer_offset(part):
        return False
    evidence = part.get("mainMaterialEvidence", {})
    length = float(evidence.get("axisStationLength") or 0.0)
    return length >= 1000 and _has_box_section_projection_evidence(part)


def _has_box_section_projection_evidence(part: dict[str, Any]) -> bool:
    projection = part.get("mainMaterialEvidence", {}).get("sectionProjectionEvidence", {})
    bounds_min = projection.get("projectedBoundsMin", {})
    bounds_max = projection.get("projectedBoundsMax", {})
    span_u = abs(float(bounds_max.get("u") or 0.0) - float(bounds_min.get("u") or 0.0))
    span_v = abs(float(bounds_max.get("v") or 0.0) - float(bounds_min.get("v") or 0.0))
    return max(span_u, span_v) >= 400



