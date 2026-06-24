"""Assembly step and dimension annotation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DimensionAnnotation:
    """尺寸标注 -- 附着在装配步骤上."""
    label: str
    value_mm: float
    reference_part_ids: list[str] = field(default_factory=list)
    annotation_type: str = ""  # length / width / thickness / spacing


@dataclass(frozen=True)
class AssemblyStep:
    """装配步骤 -- 由 sequence_builder 拓扑排序产出."""
    step_number: int
    description: str
    part_ids: list[str] = field(default_factory=list)
    action: str = "place"  # place / weld / bolt / measure
    dimensions: list[DimensionAnnotation] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)