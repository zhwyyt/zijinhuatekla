from __future__ import annotations

import re

from dataclasses import dataclass
from typing import Any

from ..rules import as_float, norm_spec, parse_pl, part_length_approx, part_width_approx, text


SCOPE_ISSUE_TYPE = "MANUFACTURING_MODEL_SCOPE_MISMATCH"


@dataclass(frozen=True)
class ManufacturingScopeCandidate:
    assembly_id: str
    evidence_code: str
    match_level: str
    segment_count: int
    segment_total_length: float
    target_length: float
    target_width: float
    target_thickness: float
    coverage_ratio: float
    segment_part_ids: list[str]
    segment_part_positions: list[str]
    segment_profiles: list[str]
    station_ranges: str = ""
    continuity_gaps: str = ""
    continuity_level: str = ""
    confirmed_segment_positions: str = ""
    confirmation_level: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "evidence_code": self.evidence_code,
            "match_level": self.match_level,
            "segment_count": self.segment_count,
            "segment_total_length": round(self.segment_total_length, 3),
            "target_length": round(self.target_length, 3),
            "target_width": round(self.target_width, 3),
            "target_thickness": round(self.target_thickness, 3),
            "coverage_ratio": round(self.coverage_ratio, 3),
            "segment_part_ids": list(self.segment_part_ids),
            "segment_part_positions": list(self.segment_part_positions),
            "segment_profiles": list(self.segment_profiles),
            "station_ranges": self.station_ranges,
            "continuity_gaps": self.continuity_gaps,
            "continuity_level": self.continuity_level,
            "confirmed_segment_positions": self.confirmed_segment_positions,
            "confirmation_level": self.confirmation_level,
        }



def apply_confirmed_segment_groups(aligned_rows: list[dict[str, Any]], member_id: str, case_bank: Any) -> list[dict[str, Any]]:
    confirmed_positions = _confirmed_segment_positions(member_id, case_bank)
    if not confirmed_positions:
        return [dict(row) for row in aligned_rows]

    confirmed_value = ";".join(confirmed_positions)
    confirmed_set = set(confirmed_positions)
    result = []
    for row in aligned_rows:
        next_row = dict(row)
        part_name = text(row.get("零件名称") or row.get("part_name"))
        if part_name in confirmed_set:
            next_row["confirmed_segment_positions"] = confirmed_value
            next_row["confirmation_level"] = "HUMAN_CONFIRMED_SEGMENT_GROUP"
        result.append(next_row)
    return result


def _confirmed_segment_positions(member_id: str, case_bank: Any) -> list[str]:
    case_id = f"{member_id}:box-column-main-material-segments"
    feedback = case_bank.get(case_id) if case_bank is not None else None
    if feedback is None or text(getattr(feedback, "expected_label", "")) != "BOX_COLUMN_MAIN_MATERIAL_SEGMENT_GROUP":
        return []

    note = text(getattr(feedback, "human_note", ""))
    positions = []
    for value in re.findall(r"T3-P-\d+", note):
        if value not in positions:
            positions.append(value)
    return positions

def apply_manufacturing_scope_hints(aligned_rows: list[dict[str, Any]], bundle: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in aligned_rows:
        next_row = dict(row)
        candidates = find_manufacturing_scope_candidates(row, bundle, limit=1)
        if candidates:
            next_row["quality_issue_type_hint"] = SCOPE_ISSUE_TYPE
            next_row["manufacturing_scope_candidate_count"] = len(candidates)
            next_row["manufacturing_scope_evidence"] = _scope_evidence(candidates[0])
        result.append(next_row)
    return result


def find_manufacturing_scope_candidates(
    row: dict[str, Any],
    bundle: dict[str, Any],
    limit: int = 3,
) -> list[ManufacturingScopeCandidate]:
    if not _is_possible_scope_row(row):
        return []

    by_assembly: dict[str, list[dict[str, Any]]] = {}
    for assembly in bundle.get("assemblies", []):
        assembly_id = text(assembly.get("assemblyId"))
        segments = [_part for _part in assembly.get("parts", []) if _is_scope_segment(row, _part)]
        if len(segments) >= 2:
            by_assembly[assembly_id] = segments

    candidates = [_candidate_from_segments(row, assembly_id, segments) for assembly_id, segments in by_assembly.items()]
    return sorted(candidates, key=lambda item: (-item.segment_count, -item.coverage_ratio, item.assembly_id))[:limit]


def build_manufacturing_scope_report(
    member_id: str,
    aligned_rows: list[dict[str, Any]],
    bundle: dict[str, Any],
    limit: int = 3,
) -> list[dict[str, object]]:
    report = []
    for row in aligned_rows:
        candidates = find_manufacturing_scope_candidates(row, bundle, limit=limit)
        if not candidates:
            continue
        part_name = text(row.get("零件名称") or row.get("part_name"))
        report.append(
            {
                "task_id": f"{member_id}:{part_name}:{SCOPE_ISSUE_TYPE}",
                "member_id": member_id,
                "part_name": part_name,
                "spec": norm_spec(row.get("规格")),
                "length": as_float(row.get("长度")),
                "issue_type_hint": SCOPE_ISSUE_TYPE,
                "candidate_count": len(candidates),
                "candidates": [candidate.to_dict() for candidate in candidates],
            }
        )
    return report


def flatten_manufacturing_scope_report(report: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for item in report:
        candidates = item.get("candidates") or []
        if not candidates:
            rows.append(_flat_scope_row(item, {}, "", "", ""))
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                rows.append(_flat_scope_row(item, {}, "", "", ""))
                continue
            part_ids = [str(value) for value in candidate.get("segment_part_ids", [])]
            positions = [str(value) for value in candidate.get("segment_part_positions", [])]
            profiles = [str(value) for value in candidate.get("segment_profiles", [])]
            for index, part_id in enumerate(part_ids):
                rows.append(
                    _flat_scope_row(
                        item,
                        candidate,
                        part_id,
                        positions[index] if index < len(positions) else "",
                        profiles[index] if index < len(profiles) else "",
                    )
                )
    return rows


def _is_possible_scope_row(row: dict[str, Any]) -> bool:
    if text(row.get("prediction_status")) not in {"DATA_MISSING", "MATCH_CONFLICT"}:
        return False
    if text(row.get("match_method")) == "derivedFromProfilePart":
        return False

    pl = parse_pl(row.get("规格"))
    if not pl:
        return False
    _, width = pl
    length = as_float(row.get("长度"))
    if length < 6000 or width < 600:
        return False

    role_text = text(row.get("predicted_role"))
    shape_text = text(row.get("形状分类"))
    return "主材" in role_text or "主材" in shape_text


def _is_scope_segment(row: dict[str, Any], part: dict[str, Any]) -> bool:
    if not part.get("isPlateLike"):
        return False
    pl = parse_pl(row.get("规格"))
    if not pl:
        return False
    target_thickness, target_width = pl
    target_length = as_float(row.get("长度"))
    if text(part.get("partPosition")) == text(row.get("零件名称") or row.get("part_name")):
        return False

    part_thickness = as_float(part.get("thickness"))
    part_length = part_length_approx(part, row)
    part_width = part_width_approx(part, row)
    width_tolerance = max(20.0, target_width * 0.04)

    if abs(part_thickness - target_thickness) > 0.8:
        return False
    if abs(part_width - target_width) > width_tolerance:
        return False
    if part_length <= 0 or part_length >= target_length * 0.75:
        return False
    if part_length < 500:
        return False
    return _looks_like_body_segment(part)


def _looks_like_body_segment(part: dict[str, Any]) -> bool:
    name = text(part.get("name")).upper()
    profile = norm_spec(part.get("profileString"))
    return name in {"COLUMN", ""} or "柱" in text(part.get("name")) or profile.startswith("PL")


def _candidate_from_segments(row: dict[str, Any], assembly_id: str, segments: list[dict[str, Any]]) -> ManufacturingScopeCandidate:
    target_thickness, target_width = parse_pl(row.get("规格")) or (0.0, 0.0)
    target_length = as_float(row.get("长度"))
    ordered_segments, station_ranges, continuity_gaps, continuity_level = _station_continuity_evidence(segments, row)
    total_length = sum(part_length_approx(part, row) for part in ordered_segments)
    coverage = total_length / target_length if target_length > 0 else 0.0
    return ManufacturingScopeCandidate(
        assembly_id=assembly_id,
        evidence_code="BOX_WALL_LONG_PLATE_SEGMENTS",
        match_level="SEGMENTED_MODEL_REVIEW",
        segment_count=len(ordered_segments),
        segment_total_length=total_length,
        target_length=target_length,
        target_width=target_width,
        target_thickness=target_thickness,
        coverage_ratio=coverage,
        segment_part_ids=[text(part.get("partId")) for part in ordered_segments],
        segment_part_positions=[text(part.get("partPosition")) for part in ordered_segments],
        segment_profiles=[norm_spec(part.get("profileString")) for part in ordered_segments],
        station_ranges=station_ranges,
        continuity_gaps=continuity_gaps,
        continuity_level=continuity_level,
        confirmed_segment_positions=text(row.get("confirmed_segment_positions")),
        confirmation_level="HUMAN_CONFIRMED_SEGMENT_GROUP" if text(row.get("confirmed_segment_positions")) else "",
    )


def _station_continuity_evidence(segments: list[dict[str, Any]], row: dict[str, Any]) -> tuple[list[dict[str, Any]], str, str, str]:
    ranges = []
    direction = _segment_axis(segments)
    if not direction:
        return list(segments), "", "", "UNKNOWN"

    for part in segments:
        centroid = part.get("centroid") or {}
        length = part_length_approx(part, row)
        if length <= 0:
            continue
        center_station = _dot_point(centroid, direction)
        start = center_station - length / 2.0
        end = center_station + length / 2.0
        ranges.append((start, end, part))

    if not ranges:
        return list(segments), "", "", "UNKNOWN"

    ranges.sort(key=lambda item: (item[0], text(item[2].get("partPosition"))))
    origin = ranges[0][0]
    normalized = [(start - origin, end - origin, part) for start, end, part in ranges]
    ordered_segments = [part for _, _, part in normalized]
    station_ranges = ";".join(
        f"{text(part.get('partPosition'))}:{start:.1f}-{end:.1f}" for start, end, part in normalized
    )
    raw_gaps = [normalized[index][0] - normalized[index - 1][1] for index in range(1, len(normalized))]
    gaps = [max(0.0, gap) for gap in raw_gaps]
    continuity_gaps = ";".join(f"{gap:.1f}" for gap in gaps)
    continuity_level = "AXIS_OVERLAP_NEEDS_FACE_GROUPING" if any(gap < -10.0 for gap in raw_gaps) else _continuity_level(gaps)
    return ordered_segments, station_ranges, continuity_gaps, continuity_level


def _segment_axis(segments: list[dict[str, Any]]) -> tuple[float, float, float] | None:
    for part in segments:
        direction = part.get("plateLongDirection") or {}
        vector = (as_float(direction.get("x")), as_float(direction.get("y")), as_float(direction.get("z")))
        length = (vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2) ** 0.5
        if length > 0:
            return (vector[0] / length, vector[1] / length, vector[2] / length)
    return None


def _dot_point(point: dict[str, Any], direction: tuple[float, float, float]) -> float:
    return (
        as_float(point.get("x")) * direction[0]
        + as_float(point.get("y")) * direction[1]
        + as_float(point.get("z")) * direction[2]
    )


def _continuity_level(gaps: list[float]) -> str:
    if not gaps:
        return "SINGLE_OR_NO_GAP"
    max_gap = max(gaps)
    if max_gap <= 10.0:
        return "CONTINUOUS"
    if max_gap <= 150.0:
        return "NEAR_CONTINUOUS"
    return "GAPPED"


def _scope_evidence(candidate: ManufacturingScopeCandidate) -> str:
    return (
        f"{candidate.evidence_code}; segments={candidate.segment_count}; "
        f"coverage={candidate.coverage_ratio:.3f}; ids={','.join(candidate.segment_part_ids)}"
    )


def _flat_scope_row(
    item: dict[str, object],
    candidate: dict[str, object],
    part_id: str,
    part_position: str,
    profile: str,
) -> dict[str, object]:
    return {
        "task_id": item.get("task_id", ""),
        "member_id": item.get("member_id", ""),
        "part_name": item.get("part_name", ""),
        "spec": item.get("spec", ""),
        "length": item.get("length", ""),
        "issue_type_hint": item.get("issue_type_hint", ""),
        "candidate_count": item.get("candidate_count", 0),
        "candidate_kind": "scope_segment" if part_id else "",
        "assembly_id": candidate.get("assembly_id", ""),
        "part_id": part_id,
        "part_position": part_position,
        "profile": profile,
        "evidence_code": candidate.get("evidence_code", ""),
        "match_level": candidate.get("match_level", ""),
        "segment_count": candidate.get("segment_count", ""),
        "segment_total_length": candidate.get("segment_total_length", ""),
        "target_length": candidate.get("target_length", ""),
        "target_width": candidate.get("target_width", ""),
        "target_thickness": candidate.get("target_thickness", ""),
        "coverage_ratio": candidate.get("coverage_ratio", ""),
        "station_ranges": candidate.get("station_ranges", ""),
        "continuity_gaps": candidate.get("continuity_gaps", ""),
        "continuity_level": candidate.get("continuity_level", ""),
        "confirmed_segment_positions": candidate.get("confirmed_segment_positions", ""),
        "confirmation_level": candidate.get("confirmation_level", ""),
    }








