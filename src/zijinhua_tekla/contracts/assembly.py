"""Assembly contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RelationshipType(str, Enum):
    WELD = "Weld"
    BOLT = "Bolt"
    CONTACT = "Contact"
    BOOLEAN = "Boolean"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class Relationship:
    part_id_a: str
    part_id_b: str
    edge_type: RelationshipType
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AssemblyRecord:
    assembly_id: str
    member_id: str = ""
    main_part_id: str = ""
    part_ids: list[str] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)