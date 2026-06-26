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


class CompositePrimaryRole(str, Enum):
    CROSS_CORE_MAIN_PLATE = "CROSS_CORE_MAIN_PLATE"
    CROSS_FLANGE_MAIN_PLATE = "CROSS_FLANGE_MAIN_PLATE"
    BOX_MAIN_WALL_PLATE = "BOX_MAIN_WALL_PLATE"
    BOX_FORMING_MAIN_PLATE = "BOX_FORMING_MAIN_PLATE"
    TRANSITION_MAIN_PLATE = "TRANSITION_MAIN_PLATE"
    END_NODE_MAIN_PLATE_CANDIDATE = "END_NODE_MAIN_PLATE_CANDIDATE"


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


def classify_composite_main_material_segments(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
) -> list[CompositeMainMaterialSegment]:
    return []
