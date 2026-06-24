"""Data contracts layer -- typed dataclasses for cross-layer communication."""

from __future__ import annotations

from .member import MemberBodyType, MemberRecord, MemberType
from .part import PartFeatureSnapshot, PartRecord
from .assembly import AssemblyRecord, Relationship
from .role import Evidence, PartRole
from .process import ProcessRoute, ProcessType
from .sequence import AssemblyStep, DimensionAnnotation

__all__ = [
    "MemberType", "MemberBodyType", "MemberRecord",
    "PartRecord", "PartFeatureSnapshot",
    "AssemblyRecord", "Relationship",
    "PartRole", "Evidence",
    "ProcessType", "ProcessRoute",
    "AssemblyStep", "DimensionAnnotation",
]