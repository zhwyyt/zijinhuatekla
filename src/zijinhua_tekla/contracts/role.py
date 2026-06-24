"""Part role and evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PartRole(str, Enum):
    """零件角色枚举 -- 覆盖 L3-L7 层级."""
    FLANGE = "FLANGE"
    WEB = "WEB"
    TRANS_STIFFENER = "TRANS_STIFFENER"
    LONGI_STIFFENER = "LONGI_STIFFENER"
    DIAPHRAGM = "DIAPHRAGM"
    END_PLATE = "END_PLATE"
    BRACKET_WEB = "BRACKET_WEB"
    BRACKET_FLANGE = "BRACKET_FLANGE"
    BRACKET_STIFFENER = "BRACKET_STIFFENER"
    LIFTING_LUG = "LIFTING_LUG"
    SEAL_PLATE = "SEAL_PLATE"
    BACKING_PLATE = "BACKING_PLATE"
    CURTAIN_WALL_EMBED = "CURTAIN_WALL_EMBED"
    MAIN_WALL_PLATE = "MAIN_WALL_PLATE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Evidence:
    """分类证据 -- 所有分类器输出必须携带."""
    code: str
    description: str
    weight: float = 1.0


@dataclass(frozen=True)
class PartRoleResult:
    """单个零件的角色判定结果."""
    part_id: str
    role: PartRole
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)
    process: str = ""
    shape: str = ""