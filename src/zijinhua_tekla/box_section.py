from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .rules import as_float, text


@dataclass(frozen=True)
class BoxSectionEvidence:
    part_id: str
    part_position: str
    face_id: str
    side: str
    body_face_offset: float
    axis_coverage_ratio: float
    related_wall_count: int
    evidence_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "face_id": self.face_id,
            "side": self.side,
            "body_face_offset": round(self.body_face_offset, 3),
            "axis_coverage_ratio": round(self.axis_coverage_ratio, 3),
            "related_wall_count": self.related_wall_count,
            "evidence_codes": list(self.evidence_codes),
        }


def classify_box_section_evidence(assembly: dict[str, Any]) -> dict[str, BoxSectionEvidence]:
    parts = [part for part in assembly.get("parts", []) if _has_main_material_evidence(part)]
    axis_length = _axis_length(assembly, parts)
    wall_offsets = _wall_core_offsets(parts, axis_length)
    wall_part_ids = _wall_part_ids(parts, axis_length)
    relationships = _relationship_neighbors(assembly)
    result: dict[str, BoxSectionEvidence] = {}
    for part in parts:
        part_id = text(part.get("partId"))
        evidence = part.get("mainMaterialEvidence", {})
        face_id = text(evidence.get("bodyFaceId"))
        offset = as_float(evidence.get("bodyFaceOffset"))
        coverage = _axis_coverage_ratio(part, axis_length)
        related_wall_count = len({item for item in relationships.get(part_id, set()) if item in wall_part_ids})
        side, codes = _classify_side(part, face_id, offset, coverage, related_wall_count, wall_offsets)
        result[part_id] = BoxSectionEvidence(
            part_id=part_id,
            part_position=text(part.get("partPosition")),
            face_id=face_id,
            side=side,
            body_face_offset=offset,
            axis_coverage_ratio=coverage,
            related_wall_count=related_wall_count,
            evidence_codes=codes,
        )
    return result


def _has_main_material_evidence(part: dict[str, Any]) -> bool:
    return isinstance(part.get("mainMaterialEvidence"), dict)


def _axis_length(assembly: dict[str, Any], parts: list[dict[str, Any]]) -> float:
    length = as_float(assembly.get("metadata", {}).get("memberAxisEvidence", {}).get("length"))
    if length > 0:
        return length
    return max((_station_end(part) - _station_start(part) for part in parts), default=0.0)


def _wall_core_offsets(parts: list[dict[str, Any]], axis_length: float) -> dict[str, float]:
    offsets: dict[str, float] = {}
    for part in parts:
        face_id = text(part.get("mainMaterialEvidence", {}).get("bodyFaceId"))
        if not face_id or _axis_coverage_ratio(part, axis_length) < 0.65:
            continue
        offset = as_float(part.get("mainMaterialEvidence", {}).get("bodyFaceOffset"))
        if face_id not in offsets or offset > offsets[face_id]:
            offsets[face_id] = offset
    return offsets


def _wall_part_ids(parts: list[dict[str, Any]], axis_length: float) -> set[str]:
    return {text(part.get("partId")) for part in parts if _axis_coverage_ratio(part, axis_length) >= 0.65}


def _relationship_neighbors(assembly: dict[str, Any]) -> dict[str, set[str]]:
    neighbors: dict[str, set[str]] = {}
    for rel in assembly.get("relationships", []):
        edge_type = text(rel.get("edgeType")).lower()
        if edge_type not in {"weld", "contact"}:
            continue
        part_a = text(rel.get("partIdA"))
        part_b = text(rel.get("partIdB"))
        if not part_a or not part_b or part_a == part_b:
            continue
        neighbors.setdefault(part_a, set()).add(part_b)
        neighbors.setdefault(part_b, set()).add(part_a)
    return neighbors


def _classify_side(
    part: dict[str, Any],
    face_id: str,
    offset: float,
    coverage: float,
    related_wall_count: int,
    wall_offsets: dict[str, float],
) -> tuple[str, list[str]]:
    codes = []
    if coverage >= 0.65:
        codes.append("AXIS_COVERAGE_LONG")
        return "WALL_CORE", codes

    codes.append("SHORT_AXIS_PART")
    wall_offset = wall_offsets.get(face_id, 0.0)
    if wall_offset > 0 and offset >= wall_offset + 100.0:
        codes.append("FACE_OFFSET_OUTSIDE_WALL_CORE")
        return "OUTER_ATTACHMENT", codes
    if wall_offset > 0 and offset <= wall_offset - 100.0:
        codes.append("FACE_OFFSET_INSIDE_WALL_CORE")
    if related_wall_count >= 2:
        codes.append("MULTI_WALL_RELATIONSHIP")
        return "INNER_STIFFENER_OR_DIAPHRAGM", codes
    name = text(part.get("name"))
    if "隔" in name or "劲" in name:
        codes.append("NAME_INNER_STIFFENER_HINT")
        return "INNER_STIFFENER_OR_DIAPHRAGM", codes
    if wall_offset > 0 and offset <= wall_offset - 100.0:
        return "INNER_STIFFENER_OR_DIAPHRAGM", codes
    return "UNKNOWN", codes


def _axis_coverage_ratio(part: dict[str, Any], axis_length: float) -> float:
    if axis_length <= 0:
        return 0.0
    return max(0.0, (_station_end(part) - _station_start(part)) / axis_length)


def _station_start(part: dict[str, Any]) -> float:
    return as_float(part.get("mainMaterialEvidence", {}).get("axisStationStart"))


def _station_end(part: dict[str, Any]) -> float:
    return as_float(part.get("mainMaterialEvidence", {}).get("axisStationEnd"))
