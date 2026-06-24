"""Member contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MemberType(str, Enum):
    COL = "COL"
    BEAM = "BEAM"
    BRACE = "BRACE"
    TRUSS = "TRUSS"
    PURLIN = "PURLIN"
    CRANE_BEAM = "CRANE_BEAM"
    COMP = "COMP"
    UNKNOWN = "UNKNOWN"


class MemberBodyType(str, Enum):
    BOX = "BOX"
    H_I = "H_I"
    T = "T"
    CROSS = "CROSS"
    PLATE_BODY = "PLATE_BODY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MemberRecord:
    member_id: str
    assembly_id: str
    member_type: MemberType
    body_type: MemberBodyType
    body_confidence: float = 0.0
    body_evidence: list[str] = field(default_factory=list)
    main_part_ids: list[str] = field(default_factory=list)
    total_parts: int = 0
    total_relationships: int = 0