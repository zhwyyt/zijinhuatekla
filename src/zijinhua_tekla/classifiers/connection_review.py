"""Review candidates for a missing modeled connection.

Distance never becomes a weld, a bolt, or a role. A brace keeps the role
given by its own geometry. A nearby assembly stays unchanged and is only
listed for a person to confirm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .member_structural_role import pose_of, single_inclined_bar

REVIEW_GAP_MM = 250.0
SHORT_ASSEMBLY_MM = 2000.0
ISSUE_TYPE = "MODEL_CONNECTION_MISSING"
ISSUE_NOTE = "模型中没有焊缝或螺栓"


@dataclass(frozen=True)
class ConnectionReviewCandidate:
    assembly_id: str
    assembly_position: str
    other_assembly_id: str
    other_assembly_position: str
    gap_mm: float
    issue_type: str = ISSUE_TYPE
    note: str = ISSUE_NOTE

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "assembly_position": self.assembly_position,
            "other_assembly_id": self.other_assembly_id,
            "other_assembly_position": self.other_assembly_position,
            "gap_mm": self.gap_mm,
            "issue_type": self.issue_type,
            "note": self.note,
        }


def connection_review_candidates(assemblies: list[dict[str, Any]]) -> list[ConnectionReviewCandidate]:
    braces = [item for item in assemblies if _brace_geometry(item)]
    others = [item for item in assemblies if item not in braces and _short_plate_assembly(item)]
    candidates: list[ConnectionReviewCandidate] = []
    for brace in braces:
        brace_ends = _axis_ends(brace)
        if brace_ends is None:
            continue
        for other in others:
            if _modeled_connection(brace, other):
                continue
            other_ends = _axis_ends(other)
            if other_ends is None:
                continue
            gap = min(_point_segment_distance(end, other_ends[0], other_ends[1]) for end in brace_ends)
            if gap > REVIEW_GAP_MM:
                continue
            candidates.append(
                ConnectionReviewCandidate(
                    assembly_id=_text(brace.get("assemblyId")),
                    assembly_position=_label(brace),
                    other_assembly_id=_text(other.get("assemblyId")),
                    other_assembly_position=_label(other),
                    gap_mm=round(gap, 1),
                )
            )
    return candidates


def _brace_geometry(assembly: dict[str, Any]) -> bool:
    ends = _axis_ends(assembly)
    if ends is None:
        return False
    direction = (
        ends[1][0] - ends[0][0],
        ends[1][1] - ends[0][1],
        ends[1][2] - ends[0][2],
    )
    return single_inclined_bar(assembly, pose_of(direction))


def _short_plate_assembly(assembly: dict[str, Any]) -> bool:
    ends = _axis_ends(assembly)
    if ends is None or _length(ends) > SHORT_ASSEMBLY_MM:
        return False
    return any(
        isinstance(part, dict) and part.get("isPlateLike") is True
        for part in assembly.get("parts") or []
    )


def _modeled_connection(left: dict[str, Any], right: dict[str, Any]) -> bool:
    pairs = (
        (left, _text(right.get("assemblyId"))),
        (right, _text(left.get("assemblyId"))),
    )
    for assembly, other_id in pairs:
        evidence = (assembly.get("metadata") or {}).get("externalConnectionEvidence") or {}
        for link in evidence.get("links") or []:
            if _text(link.get("otherAssemblyId")) != other_id:
                continue
            if link.get("relation") in {"Weld", "Bolt"}:
                return True
    return False


def _axis_ends(assembly: dict[str, Any]) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    axis = (assembly.get("metadata") or {}).get("memberAxisEvidence") or {}
    origin = _point(axis.get("origin"))
    direction = _point(axis.get("direction"))
    try:
        length = float(axis.get("length") or 0.0)
    except (TypeError, ValueError):
        return None
    if origin is None or direction is None or length <= 0.0:
        return None
    end = tuple(origin[index] + direction[index] * length for index in range(3))
    return origin, end


def _point(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return (float(value.get("x")), float(value.get("y")), float(value.get("z")))
    except (TypeError, ValueError):
        return None


def _length(ends: tuple[tuple[float, float, float], tuple[float, float, float]]) -> float:
    return math.sqrt(sum((ends[1][index] - ends[0][index]) ** 2 for index in range(3)))


def _point_segment_distance(
    point: tuple[float, float, float],
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> float:
    segment = tuple(end[index] - start[index] for index in range(3))
    offset = tuple(point[index] - start[index] for index in range(3))
    denominator = sum(item * item for item in segment) or 1.0
    ratio = max(0.0, min(1.0, sum(offset[index] * segment[index] for index in range(3)) / denominator))
    projection = tuple(start[index] + segment[index] * ratio for index in range(3))
    return math.sqrt(sum((point[index] - projection[index]) ** 2 for index in range(3)))


def _label(assembly: dict[str, Any]) -> str:
    metadata = assembly.get("metadata") or {}
    return _text(metadata.get("assemblyPosition") or assembly.get("assemblyId"))


def _text(value: Any) -> str:
    return "" if value is None else str(value)
