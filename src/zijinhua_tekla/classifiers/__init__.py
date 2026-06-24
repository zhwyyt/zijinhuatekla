from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..bracket_classifier import (
    AppendageClusterFeatures,
    AppendageRoleClassification,
    classify_appendage_cluster,
)
from ..member_classifier import MemberBodyClassification, classify_member_body
from ..part_roles import PartRoleResult, classify_part_role


@dataclass(frozen=True)
class ClassificationFacade:
    """Stable entrypoint for current member, part-role, and appendage classifiers."""

    def classify_member(self, member: dict[str, Any], snapshots: list[Any]) -> MemberBodyClassification:
        return classify_member_body(member, snapshots)

    def classify_part(self, row: dict[str, Any], summary: dict[str, Any]) -> PartRoleResult:
        return classify_part_role(row, summary)

    def classify_appendage(self, features: AppendageClusterFeatures) -> AppendageRoleClassification:
        return classify_appendage_cluster(features)


DEFAULT_FACADE = ClassificationFacade()


def classify_member(member: dict[str, Any], snapshots: list[Any]) -> MemberBodyClassification:
    return DEFAULT_FACADE.classify_member(member, snapshots)


def classify_part(row: dict[str, Any], summary: dict[str, Any]) -> PartRoleResult:
    return DEFAULT_FACADE.classify_part(row, summary)


def classify_appendage(features: AppendageClusterFeatures) -> AppendageRoleClassification:
    return DEFAULT_FACADE.classify_appendage(features)


__all__ = [
    "ClassificationFacade",
    "classify_member",
    "classify_part",
    "classify_appendage",
]
