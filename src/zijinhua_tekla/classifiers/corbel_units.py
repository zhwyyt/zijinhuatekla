"""Countable corbel units. A unit is an outward support, not a plate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..rules import norm_spec, text


_ROLLED_PREFIXES = ("BH", "HN", "HM", "HW", "HI", "IPE", "HEA", "HEB", "UB", "UC")


@dataclass(frozen=True)
class CorbelUnit:
    unit_id: str
    cluster_id: str
    part_ids: list[str]
    spine_part_ids: list[str]
    evidence_codes: list[str]
    confidence: float
    issue_category: str = ""
    evidence_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "unit_id": self.unit_id,
            "cluster_id": self.cluster_id,
            "part_ids": list(self.part_ids),
            "spine_part_ids": list(self.spine_part_ids),
            "evidence_codes": list(self.evidence_codes),
            "confidence": round(self.confidence, 3),
            "issue_category": self.issue_category,
            "evidence_summary": dict(self.evidence_summary),
        }


def is_rolled_spine_profile(profile: str) -> bool:
    spec = norm_spec(profile)
    if not spec:
        return False
    if spec.startswith(_ROLLED_PREFIXES):
        return True
    return spec.startswith("H") and "*" in spec and not spec.startswith(("HP", "H-", "HS"))


def classify_corbel_units(assembly: dict[str, Any], spatial_classifications: list[Any]) -> list[CorbelUnit]:
    parts_by_id = {text(part.get("partId")): part for part in assembly.get("parts", []) if text(part.get("partId"))}
    units: list[CorbelUnit] = []
    unit_no = 0
    for cluster in spatial_classifications:
        if text(getattr(cluster, "role", "")) != "Bracket":
            continue
        part_ids = [text(part_id) for part_id in getattr(cluster, "part_ids", []) if text(part_id)]
        if not part_ids:
            continue
        cluster_id = text(getattr(cluster, "cluster_id", ""))
        confidence = float(getattr(cluster, "confidence", 0.0) or 0.0)
        spines = [
            part_id
            for part_id in part_ids
            if is_rolled_spine_profile(text((parts_by_id.get(part_id) or {}).get("profileString")))
        ]
        if len(spines) >= 2:
            for spine in spines:
                unit_no += 1
                units.append(
                    CorbelUnit(
                        unit_id=f"{cluster_id}:U{unit_no}",
                        cluster_id=cluster_id,
                        part_ids=[spine],
                        spine_part_ids=[spine],
                        evidence_codes=["BRACKET_CLUSTER", "ROLLED_SPINE_INSTANCE"],
                        confidence=confidence,
                        evidence_summary={"spine_profile": text((parts_by_id.get(spine) or {}).get("profileString"))},
                    )
                )
            continue
        unit_no += 1
        evidence = ["BRACKET_CLUSTER"]
        if spines:
            evidence.append("ROLLED_SPINE_INSTANCE")
        else:
            evidence.append("FABRICATED_BRACKET_CLUSTER")
        units.append(
            CorbelUnit(
                unit_id=f"{cluster_id}:U{unit_no}",
                cluster_id=cluster_id,
                part_ids=list(part_ids),
                spine_part_ids=list(spines),
                evidence_codes=evidence,
                confidence=confidence,
                evidence_summary={"part_count": str(len(part_ids))},
            )
        )
    return units
