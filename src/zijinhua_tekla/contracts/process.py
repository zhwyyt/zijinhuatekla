"""Process route contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProcessType(str, Enum):
    """加工工序枚举."""
    LASER_CUT = "LASER_CUT"
    SHEARING = "SHEARING"
    DRILLING = "DRILLING"
    PUNCHING = "PUNCHING"
    BEVELING = "BEVELING"
    WELDING = "WELDING"
    ASSEMBLY_LINE = "ASSEMBLY_LINE"
    BENDING = "BENDING"
    NONE = "NONE"


@dataclass(frozen=True)
class ProcessRoute:
    """零件工序路由 -- 由 process_router 分类器产出."""
    part_id: str
    processes: list[ProcessType]
    confidence: float
    evidence: list[str] = field(default_factory=list)