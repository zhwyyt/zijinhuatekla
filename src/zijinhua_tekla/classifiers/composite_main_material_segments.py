from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import re


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
    native_h_segments = _h_station_frame_segments(assembly)
    if native_h_segments:
        return native_h_segments
    adapted = _adapt_h_or_gl_main_material_groups(assembly, main_material_groups or [])
    if adapted:
        return adapted
    snapshots = _station_snapshots(assembly)
    if not snapshots:
        return []
    return _merge_snapshots_into_segments(str(assembly.get("assemblyId", "")), snapshots, assembly)


def _h_station_frame_segments(assembly: dict[str, Any]) -> list[CompositeMainMaterialSegment]:
    evidence = assembly.get("metadata", {}).get("hBeamSectionEvidence", {})
    frames = evidence.get("stationFrames", []) if isinstance(evidence, dict) else []
    if not isinstance(frames, list) or not frames:
        return []
    stats: dict[str, dict[str, Any]] = {}
    all_stations: list[float] = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        station = _as_float(frame.get("station"))
        all_stations.append(station)
        explicit_roles = {
            str(frame.get("topFlangePartId") or ""): CompositePrimaryRole.H_TOP_FLANGE_MAIN_PLATE,
            str(frame.get("webPartId") or ""): CompositePrimaryRole.H_WEB_MAIN_PLATE,
            str(frame.get("bottomFlangePartId") or ""): CompositePrimaryRole.H_BOTTOM_FLANGE_MAIN_PLATE,
        }
        for part_slice in frame.get("partSlices", []) or []:
            if not isinstance(part_slice, dict):
                continue
            part_id = str(part_slice.get("partId") or "")
            if not part_id or not _h_slice_has_section_loop(part_slice):
                continue
            item = stats.setdefault(
                part_id,
                {
                    "stations": [],
                    "role_votes": [],
                    "role_hints": set(),
                    "part_position": str(part_slice.get("partPosition") or ""),
                    "loop_count": 0,
                    "segment_count": 0,
                },
            )
            item["stations"].append(station)
            item["loop_count"] += len(part_slice.get("sectionLoops") or [])
            item["segment_count"] += len(part_slice.get("segments") or [])
            role = explicit_roles.get(part_id)
            if role is not None:
                item["role_votes"].append(role)
            role_hint = str(part_slice.get("roleHint") or "")
            if role_hint:
                item["role_hints"].add(role_hint)
            if not item["part_position"]:
                item["part_position"] = str(part_slice.get("partPosition") or "")
    axis_length = max(_station_span(all_stations), _member_axis_length(assembly))
    parts_by_id = {str(part.get("partId") or ""): part for part in assembly.get("parts", []) if str(part.get("partId") or "")}
    plates_by_id: dict[str, CompositeMainPlate] = {}
    seed_roles: dict[str, CompositePrimaryRole] = {}
    accepted_stations: list[float] = []
    for part_id, item in stats.items():
        stations = sorted(set(item["stations"]))
        if len(stations) < 3:
            continue
        span = _station_span(stations)
        coverage_ratio = span / axis_length if axis_length > 0 else 0.0
        role_hints = {str(role) for role in item["role_hints"]}
        if role_hints and role_hints.isdisjoint({"flange_candidate", "web_candidate"}):
            continue
        if span < 1800.0 or coverage_ratio < 0.50:
            continue
        primary_role = _h_native_primary_role(item["role_votes"], role_hints)
        if primary_role is None:
            continue
        part = parts_by_id.get(part_id, {})
        part_position = str(part.get("partPosition") or item["part_position"] or "")
        plates_by_id[part_id] = CompositeMainPlate(
            part_id=part_id,
            part_position=part_position,
            primary_role=primary_role,
            secondary_evidence=[
                "h_beam_station_frame",
                f"slice_station_count={len(stations)}",
                f"slice_station_span={span:.3f}",
                f"slice_axis_coverage_ratio={coverage_ratio:.3f}",
            ],
            evidence_codes=["H_GL_STATION_FRAME_NATIVE_COMPOSITE", "H_GL_STATION_SLICE_MAIN_PLATE", primary_role.value],
        )
        seed_roles[part_id] = primary_role
        accepted_stations.extend(stations)
    if not plates_by_id:
        return []
    relationship_edges = _relationship_edges(assembly)
    plates_by_id.update(_h_expand_axis_continuity_plates(stats, parts_by_id, seed_roles, plates_by_id, relationship_edges))
    plates = list(plates_by_id.values())
    plate_parts = [parts_by_id[plate.part_id] for plate in plates if plate.part_id in parts_by_id]
    station_start = min([_station_start(part) for part in plate_parts] + accepted_stations) if plate_parts or accepted_stations else 0.0
    station_end = max([_station_end(part) for part in plate_parts] + accepted_stations + [axis_length]) if plate_parts or accepted_stations else axis_length
    return [
        CompositeMainMaterialSegment(
            assembly_id=str(assembly.get("assemblyId", "")),
            segment_id="S1",
            station_start=station_start,
            station_end=station_end,
            segment_type=CompositeSegmentType.H_OR_BH_SECTION,
            main_plates=sorted(plates, key=lambda plate: (plate.primary_role.value, plate.part_position, plate.part_id)),
            confidence=0.9,
            evidence_codes=["H_GL_STATION_FRAME_NATIVE_COMPOSITE", "H_GL_STATION_SLICE_MAIN_PLATE", "hBeamSectionEvidence.stationFrames"],
        )
    ]
def _h_expand_axis_continuity_plates(
    stats: dict[str, dict[str, Any]],
    parts_by_id: dict[str, dict[str, Any]],
    seed_roles: dict[str, CompositePrimaryRole],
    seed_plates: dict[str, CompositeMainPlate],
    relationship_edges: set[tuple[str, str]],
) -> dict[str, CompositeMainPlate]:
    expanded: dict[str, CompositeMainPlate] = {}
    accepted_roles = dict(seed_roles)
    accepted_plates = dict(seed_plates)
    changed = True
    while changed:
        changed = False
        for part_id in sorted(parts_by_id):
            if part_id in accepted_plates:
                continue
            item = stats.get(part_id)
            plate = _h_axis_continuity_plate(part_id, item, parts_by_id, accepted_roles, relationship_edges)
            if plate is None:
                continue
            expanded[part_id] = plate
            accepted_plates[part_id] = plate
            accepted_roles[part_id] = plate.primary_role
            changed = True
    return expanded


def _h_axis_continuity_plate(
    part_id: str,
    item: dict[str, Any] | None,
    parts_by_id: dict[str, dict[str, Any]],
    accepted_roles: dict[str, CompositePrimaryRole],
    relationship_edges: set[tuple[str, str]],
) -> CompositeMainPlate | None:
    part = parts_by_id.get(part_id)
    if not _h_axis_continuity_candidate(part):
        return None
    primary_role = _h_native_primary_role_for_continuity_candidate(part, item, parts_by_id, accepted_roles, relationship_edges)
    if primary_role is None:
        return None
    matched_id = _h_continuity_seed_id(part, primary_role, parts_by_id, accepted_roles, relationship_edges)
    if matched_id is None:
        return None
    matched_part = parts_by_id[matched_id]
    part_position = str(part.get("partPosition") or (item or {}).get("part_position") or "")
    secondary_evidence = [
        "h_beam_station_frame",
        "h_beam_axis_continuity_expanded",
        f"continuity_seed_part={str(matched_part.get('partPosition') or matched_id)}",
    ]
    if item is not None:
        stations = sorted(set(item["stations"]))
        span = _station_span(stations)
        secondary_evidence.extend([f"slice_station_count={len(stations)}", f"slice_station_span={span:.3f}"])
    else:
        secondary_evidence.append("h_beam_axis_continuity_expanded_from_part_pool")
    return CompositeMainPlate(
        part_id=part_id,
        part_position=part_position,
        primary_role=primary_role,
        secondary_evidence=secondary_evidence,
        evidence_codes=[
            "H_GL_STATION_FRAME_NATIVE_COMPOSITE",
            "H_GL_STATION_SLICE_MAIN_PLATE",
            "H_GL_AXIS_CONTINUITY_EXPANDED",
            primary_role.value,
        ],
    )


def _h_axis_continuity_candidate(part: dict[str, Any] | None) -> bool:
    if not part or part.get("mainMaterialEvidence", {}).get("isBodyWallPlateCandidate") is not True:
        return False
    if _h_axis_length(part) < 1000.0:
        return False
    profile = str(part.get("profileString") or part.get("profile") or "").upper().strip()
    return profile.startswith("PL")


def _h_native_primary_role_for_continuity_candidate(
    part: dict[str, Any],
    item: dict[str, Any] | None,
    parts_by_id: dict[str, dict[str, Any]],
    accepted_roles: dict[str, CompositePrimaryRole],
    relationship_edges: set[tuple[str, str]],
) -> CompositePrimaryRole | None:
    if item is not None:
        stations = sorted(set(item["stations"]))
        if len(stations) < 3 or _station_span(stations) < 350.0:
            return None
        role_hints = {str(role) for role in item["role_hints"]}
        if role_hints and role_hints.isdisjoint({"flange_candidate", "web_candidate"}):
            return None
        return _h_native_primary_role(item["role_votes"], role_hints)
    roles = []
    for accepted_id, accepted_role in accepted_roles.items():
        accepted = parts_by_id.get(accepted_id)
        if accepted and _h_same_chain_plate(part, accepted, relationship_edges):
            roles.append(accepted_role)
    if not roles:
        return None
    counts = {role: roles.count(role) for role in set(roles)}
    return sorted(counts, key=lambda role: (-counts[role], role.value))[0]


def _h_continuity_seed_id(
    part: dict[str, Any],
    primary_role: CompositePrimaryRole,
    parts_by_id: dict[str, dict[str, Any]],
    accepted_roles: dict[str, CompositePrimaryRole],
    relationship_edges: set[tuple[str, str]],
) -> str | None:
    for accepted_id, accepted_role in accepted_roles.items():
        if accepted_role != primary_role:
            continue
        accepted = parts_by_id.get(accepted_id)
        if not accepted:
            continue
        if _h_same_chain_plate(part, accepted, relationship_edges):
            return accepted_id
    return None

def _h_same_chain_plate(left: dict[str, Any], right: dict[str, Any], relationship_edges: set[tuple[str, str]]) -> bool:
    if not relationship_edges or not _has_relationship(left, right, relationship_edges):
        return False
    if not _h_axis_intervals_touch(left, right):
        return False
    return _h_same_section_side(left, right)


def _h_same_section_side(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_face = str(left.get("mainMaterialEvidence", {}).get("bodyFaceId") or "")
    right_face = str(right.get("mainMaterialEvidence", {}).get("bodyFaceId") or "")
    if left_face and left_face == right_face:
        return True
    left_side = _h_projected_side_value(left)
    right_side = _h_projected_side_value(right)
    if left_side is not None and right_side is not None:
        return abs(left_side - right_side) <= 25.0
    return False


def _h_projected_side_value(part: dict[str, Any]) -> float | None:
    projection = part.get("mainMaterialEvidence", {}).get("sectionProjectionEvidence", {})
    if not isinstance(projection, dict):
        return None
    centroid = projection.get("projectedCentroid", {})
    if not isinstance(centroid, dict):
        return None
    normal = projection.get("normalProjection", {})
    normal_u = abs(_as_float(normal.get("u"))) if isinstance(normal, dict) else 0.0
    normal_v = abs(_as_float(normal.get("v"))) if isinstance(normal, dict) else 0.0
    return _as_float(centroid.get("v")) if normal_v >= normal_u else _as_float(centroid.get("u"))


def _h_axis_intervals_touch(left: dict[str, Any], right: dict[str, Any], max_gap: float = 150.0) -> bool:
    return abs(_station_end(left) - _station_start(right)) <= max_gap or abs(_station_end(right) - _station_start(left)) <= max_gap

def _relationship_edges(assembly: dict[str, Any]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for rel in assembly.get("relationships", []):
        edge_type = str(rel.get("edgeType") or "").strip().lower()
        if edge_type not in {"weld", "contact"}:
            continue
        part_a = str(rel.get("partIdA") or "").strip()
        part_b = str(rel.get("partIdB") or "").strip()
        if not part_a or not part_b or part_a == part_b:
            continue
        edges.add(tuple(sorted((part_a, part_b))))
    return edges


def _has_relationship(left: dict[str, Any], right: dict[str, Any], edges: set[tuple[str, str]]) -> bool:
    left_id = str(left.get("partId") or "").strip()
    right_id = str(right.get("partId") or "").strip()
    return tuple(sorted((left_id, right_id))) in edges

def _h_axis_length(part: dict[str, Any]) -> float:
    evidence = part.get("mainMaterialEvidence", {})
    length = _as_float(evidence.get("axisStationLength"))
    if length > 0:
        return length
    return max(0.0, _station_end(part) - _station_start(part))
def _h_native_primary_role(
    role_votes: list[CompositePrimaryRole],
    role_hints: set[str],
) -> CompositePrimaryRole | None:
    if role_votes:
        counts = {role: role_votes.count(role) for role in set(role_votes)}
        return sorted(counts, key=lambda role: (-counts[role], role.value))[0]
    if "web_candidate" in role_hints and "flange_candidate" not in role_hints:
        return CompositePrimaryRole.H_WEB_MAIN_PLATE
    if "flange_candidate" in role_hints and "web_candidate" not in role_hints:
        return CompositePrimaryRole.H_FLANGE_MAIN_PLATE
    return None

def _h_slice_has_section_loop(part_slice: dict[str, Any]) -> bool:
    section_loops = part_slice.get("sectionLoops")
    if isinstance(section_loops, list):
        for section_loop in section_loops:
            if not isinstance(section_loop, dict):
                continue
            if section_loop.get("isClosed") is False or section_loop.get("isValid") is False:
                continue
            if len(_h_loop_points(section_loop.get("points"))) >= 3:
                return True
    return len(part_slice.get("segments") or []) >= 4

def _h_loop_points(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, list):
        return []
    points = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if "u" in item or "v" in item:
            points.append((_as_float(item.get("u")), _as_float(item.get("v"))))
        elif "x" in item or "y" in item:
            points.append((_as_float(item.get("x")), _as_float(item.get("y"))))
        elif "X" in item or "Y" in item:
            points.append((_as_float(item.get("X")), _as_float(item.get("Y"))))
    return points

def _station_span(stations: list[float]) -> float:
    if not stations:
        return 0.0
    return max(stations) - min(stations)

def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0

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
        if ":" not in item:
            continue
        value = item.rsplit(":", 1)[-1]
        match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*", value)
        if match is None:
            continue
        ranges.append((float(match.group(1)), float(match.group(2))))
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










