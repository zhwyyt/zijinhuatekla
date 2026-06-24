from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..rules import as_float, norm_spec, parse_pl, part_length_approx, part_profile_norm, part_width_approx, row_part_score, text


@dataclass(frozen=True)
class PartCandidate:
    assembly_id: str
    part_id: str
    part_position: str
    name: str
    profile: str
    match_level: str
    score: float
    length_delta: float
    width_delta: float
    thickness_delta: float

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "part_id": self.part_id,
            "part_position": self.part_position,
            "name": self.name,
            "profile": self.profile,
            "match_level": self.match_level,
            "score": round(self.score, 3),
            "length_delta": round(self.length_delta, 3),
            "width_delta": round(self.width_delta, 3),
            "thickness_delta": round(self.thickness_delta, 3),
        }


def search_missing_part_candidates(row: dict[str, Any], bundle: dict[str, Any], limit: int = 10) -> list[PartCandidate]:
    scored: list[PartCandidate] = []
    for assembly in bundle.get("assemblies", []):
        assembly_id = text(assembly.get("assemblyId"))
        for part in assembly.get("parts", []):
            candidate = _candidate_from_part(row, assembly_id, part)
            if candidate is not None:
                scored.append(candidate)
    return sorted(scored, key=lambda item: (item.score, item.length_delta, item.width_delta, item.part_position))[:limit]


def build_missing_candidate_report(
    member_id: str,
    aligned_rows: list[dict[str, Any]],
    bundle: dict[str, Any],
    limit: int = 5,
) -> list[dict[str, object]]:
    report = []
    for row in aligned_rows:
        if text(row.get("prediction_status")) != "DATA_MISSING":
            continue
        if text(row.get("quality_issue_type_hint")):
            continue
        candidates = search_missing_part_candidates(row, bundle, limit=limit)
        part_name = text(row.get("零件名称") or row.get("part_name"))
        report.append(
            {
                "task_id": f"{member_id}:{part_name}:DATA_MISSING",
                "member_id": member_id,
                "part_name": part_name,
                "spec": norm_spec(row.get("规格")),
                "length": as_float(row.get("长度")),
                "candidate_count": len(candidates),
                "candidates": [candidate.to_dict() for candidate in candidates],
            }
        )
    return report


def flatten_missing_candidate_report(report: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for item in report:
        candidates = item.get("candidates") or []
        if not candidates:
            rows.append(_flat_missing_candidate_row(item, None))
            continue
        for candidate in candidates:
            rows.append(_flat_missing_candidate_row(item, candidate))
    return rows


def build_conflict_candidate_report(
    member_id: str,
    aligned_rows: list[dict[str, Any]],
    bundle: dict[str, Any],
    limit: int = 5,
) -> list[dict[str, object]]:
    report = []
    for row in aligned_rows:
        if text(row.get("prediction_status")) != "MATCH_CONFLICT":
            continue
        part_name = text(row.get("零件名称") or row.get("part_name"))
        conflict_parts = _parts_by_position(bundle, part_name)
        conflict_part_ids = {text(part.get("partId")) for _, part in conflict_parts}
        geometry_review_candidates = [
            candidate
            for candidate in search_missing_part_candidates(row, bundle, limit=limit + len(conflict_part_ids))
            if candidate.part_id not in conflict_part_ids
        ][:limit]
        report.append(
            {
                "task_id": f"{member_id}:{part_name}:MATCH_CONFLICT",
                "member_id": member_id,
                "part_name": part_name,
                "spec": norm_spec(row.get("规格")),
                "length": as_float(row.get("长度")),
                "conflict_count": len(conflict_parts),
                "conflict_parts": [_part_position_conflict_to_dict(row, assembly_id, part) for assembly_id, part in conflict_parts],
                "geometry_review_candidate_count": len(geometry_review_candidates),
                "geometry_review_candidates": [candidate.to_dict() for candidate in geometry_review_candidates],
            }
        )
    return report


def flatten_conflict_candidate_report(report: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for item in report:
        conflict_parts = item.get("conflict_parts") or []
        geometry_review_candidates = item.get("geometry_review_candidates") or []
        if not conflict_parts and not geometry_review_candidates:
            rows.append(_flat_conflict_candidate_row(item, None, ""))
            continue
        for candidate in conflict_parts:
            rows.append(_flat_conflict_candidate_row(item, candidate, "conflict_part"))
        for candidate in geometry_review_candidates:
            rows.append(_flat_conflict_candidate_row(item, candidate, "geometry_review_candidate"))
    return rows


def _candidate_from_part(row: dict[str, Any], assembly_id: str, part: dict[str, Any]) -> PartCandidate | None:
    spec_ok, length_ok, length_delta, part_spec, part_len, part_width = row_part_score(row, part)
    width_delta, thickness_delta = _plate_deltas(row, part, part_width)
    if spec_ok and length_ok and _is_tight_geometry(row, length_delta, width_delta, thickness_delta):
        match_level = "GEOMETRY_EXACT"
        score = length_delta + width_delta * 2 + thickness_delta * 20
    elif spec_ok and length_ok:
        match_level = "GEOMETRY_NEAR"
        score = length_delta + width_delta * 2 + thickness_delta * 20
    else:
        match_level, score = _near_match(row, part, part_len, part_width, length_delta, width_delta, thickness_delta)
        if not match_level:
            return None

    return PartCandidate(
        assembly_id=assembly_id,
        part_id=text(part.get("partId")),
        part_position=text(part.get("partPosition")),
        name=text(part.get("name")),
        profile=part_profile_norm(part, row) or part_spec or norm_spec(part.get("profileString")),
        match_level=match_level,
        score=score,
        length_delta=length_delta,
        width_delta=width_delta,
        thickness_delta=thickness_delta,
    )


def _plate_deltas(row: dict[str, Any], part: dict[str, Any], part_width: float) -> tuple[float, float]:
    pl = parse_pl(row.get("规格"))
    if not pl:
        return 0.0, 0.0
    thickness, width = pl
    return abs(part_width - width), abs(as_float(part.get("thickness")) - thickness)


def _is_tight_geometry(row: dict[str, Any], length_delta: float, width_delta: float, thickness_delta: float) -> bool:
    length = as_float(row.get("长度"))
    pl = parse_pl(row.get("规格"))
    length_ok = length_delta <= max(10.0, length * 0.02)
    if not pl:
        return length_ok
    _, width = pl
    width_ok = width_delta <= max(8.0, width * 0.04)
    thickness_ok = thickness_delta <= 0.6
    return length_ok and width_ok and thickness_ok


def _near_match(
    row: dict[str, Any],
    part: dict[str, Any],
    part_len: float,
    part_width: float,
    length_delta: float,
    width_delta: float,
    thickness_delta: float,
) -> tuple[str, float]:
    pl = parse_pl(row.get("规格"))
    if not pl or not part.get("isPlateLike"):
        return "", 0.0

    thickness, width = pl
    length = as_float(row.get("长度"))
    width_ok = width_delta <= max(20.0, width * 0.12)
    thickness_ok = thickness_delta <= 0.8
    length_ok = abs(part_len - length) <= max(80.0, min(300.0, length * 0.25))
    if not (width_ok and thickness_ok and length_ok):
        return "", 0.0
    return "GEOMETRY_NEAR", length_delta + width_delta * 2 + thickness_delta * 20


def _flat_missing_candidate_row(item: dict[str, object], candidate: object | None) -> dict[str, object]:
    candidate_data = candidate if isinstance(candidate, dict) else {}
    return {
        "task_id": item.get("task_id", ""),
        "member_id": item.get("member_id", ""),
        "part_name": item.get("part_name", ""),
        "spec": item.get("spec", ""),
        "length": item.get("length", ""),
        "candidate_count": item.get("candidate_count", 0),
        "assembly_id": candidate_data.get("assembly_id", ""),
        "part_id": candidate_data.get("part_id", ""),
        "part_position": candidate_data.get("part_position", ""),
        "name": candidate_data.get("name", ""),
        "profile": candidate_data.get("profile", ""),
        "match_level": candidate_data.get("match_level", ""),
        "score": candidate_data.get("score", ""),
        "length_delta": candidate_data.get("length_delta", ""),
        "width_delta": candidate_data.get("width_delta", ""),
        "thickness_delta": candidate_data.get("thickness_delta", ""),
    }


def _parts_by_position(bundle: dict[str, Any], part_position: str) -> list[tuple[str, dict[str, Any]]]:
    matches = []
    for assembly in bundle.get("assemblies", []):
        assembly_id = text(assembly.get("assemblyId"))
        for part in assembly.get("parts", []):
            if text(part.get("partPosition")) == part_position:
                matches.append((assembly_id, part))
    return matches


def _part_position_conflict_to_dict(row: dict[str, Any], assembly_id: str, part: dict[str, Any]) -> dict[str, object]:
    _, _, length_delta, part_spec, _, part_width = row_part_score(row, part)
    width_delta, thickness_delta = _plate_deltas(row, part, part_width)
    return {
        "assembly_id": assembly_id,
        "part_id": text(part.get("partId")),
        "part_position": text(part.get("partPosition")),
        "name": text(part.get("name")),
        "profile": part_profile_norm(part, row) or part_spec or norm_spec(part.get("profileString")),
        "match_level": "PART_POSITION_CONFLICT",
        "score": round(length_delta + width_delta * 2 + thickness_delta * 20, 3),
        "length_delta": round(length_delta, 3),
        "width_delta": round(width_delta, 3),
        "thickness_delta": round(thickness_delta, 3),
    }


def _flat_conflict_candidate_row(item: dict[str, object], candidate: object | None, candidate_kind: str) -> dict[str, object]:
    candidate_data = candidate if isinstance(candidate, dict) else {}
    return {
        "task_id": item.get("task_id", ""),
        "member_id": item.get("member_id", ""),
        "part_name": item.get("part_name", ""),
        "spec": item.get("spec", ""),
        "length": item.get("length", ""),
        "conflict_count": item.get("conflict_count", 0),
        "geometry_review_candidate_count": item.get("geometry_review_candidate_count", 0),
        "candidate_kind": candidate_kind,
        "assembly_id": candidate_data.get("assembly_id", ""),
        "part_id": candidate_data.get("part_id", ""),
        "part_position": candidate_data.get("part_position", ""),
        "name": candidate_data.get("name", ""),
        "profile": candidate_data.get("profile", ""),
        "match_level": candidate_data.get("match_level", ""),
        "score": candidate_data.get("score", ""),
        "length_delta": candidate_data.get("length_delta", ""),
        "width_delta": candidate_data.get("width_delta", ""),
        "thickness_delta": candidate_data.get("thickness_delta", ""),
    }
