"""Offline analysis configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ColumnMapping:
    part_position: str = "零件名称"
    part_name: str = "零件名称"
    spec: str = "规格"
    length: str = "长度"
    material: str = "材质"


@dataclass(frozen=True)
class AnalysisContext:
    bundle_root: Path = field(default_factory=lambda: Path("."))
    truth_root: Path = field(default_factory=lambda: Path("."))
    member_id: str = ""
    assembly_id: str = ""
    output_dir: Path = field(default_factory=lambda: Path("outputs"))
    column_mapping: ColumnMapping = field(default_factory=ColumnMapping)