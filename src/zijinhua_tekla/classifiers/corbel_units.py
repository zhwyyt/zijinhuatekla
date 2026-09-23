"""Countable corbel units. A unit is an outward support, not a plate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..rules import norm_spec, text
from ..spatial_features import body_part_ids_from_member_roles


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


def classify_corbel_units(
    assembly: dict[str, Any],
    spatial_classifications: list[Any],
    member: dict[str, Any] | None = None,
) -> list[CorbelUnit]:
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
    classified_part_ids = {part_id for unit in units for part_id in unit.part_ids}
    units.extend(
        _direct_rolled_spine_units(
            assembly=assembly,
            member=member,
            parts_by_id=parts_by_id,
            classified_part_ids=classified_part_ids,
            start_unit_no=unit_no + 1,
        )
    )
    return units


def _direct_rolled_spine_units(
    *,
    assembly: dict[str, Any],
    member: dict[str, Any] | None,
    parts_by_id: dict[str, dict[str, Any]],
    classified_part_ids: set[str],
    start_unit_no: int,
) -> list[CorbelUnit]:
    if member is None:
        return []
    assembly_id = text(assembly.get("assemblyId"))
    body_ids = body_part_ids_from_member_roles(member)
    main_part_id = text(assembly.get("mainPartId"))
    if main_part_id:
        body_ids.add(main_part_id)
    body_ids = {part_id for part_id in body_ids if part_id in parts_by_id}
    if not body_ids:
        return []

    units: list[CorbelUnit] = []
    unit_no = start_unit_no
    for part_id in sorted(parts_by_id):
        if part_id in body_ids or part_id in classified_part_ids:
            continue
        part = parts_by_id[part_id]
        if not is_rolled_spine_profile(text(part.get("profileString"))):
            continue
        if not _has_direct_body_root(assembly, part_id, body_ids):
            continue
        if not _centroid_outside_body_box(part, [parts_by_id[body_id] for body_id in body_ids]):
            continue
        units.append(
            CorbelUnit(
                unit_id=f"{assembly_id}:DIRECT:U{unit_no}",
                cluster_id=f"{assembly_id}:DIRECT:{part_id}",
                part_ids=[part_id],
                spine_part_ids=[part_id],
                evidence_codes=["DIRECT_ROLLED_SPINE", "DIRECT_BODY_ROOT", "CENTROID_OUTSIDE_BODY"],
                confidence=0.94,
                evidence_summary={"spine_profile": text(part.get("profileString"))},
            )
        )
        unit_no += 1
    return units


def _has_direct_body_root(assembly: dict[str, Any], part_id: str, body_ids: set[str]) -> bool:
    for relation in assembly.get("relationships", []):
        left = text(relation.get("partIdA"))
        right = text(relation.get("partIdB"))
        edge_type = text(relation.get("edgeType"))
        if edge_type not in {"Weld", "Contact"}:
            continue
        if (left == part_id and right in body_ids) or (right == part_id and left in body_ids):
            return True
    return False


def _centroid_outside_body_box(part: dict[str, Any], body_parts: list[dict[str, Any]]) -> bool:
    boxes = []
    for body_part in body_parts:
        box = body_part.get("boundingBox") or {}
        boxes.append((box.get("min") or {}, box.get("max") or {}))
    if not boxes:
        return False
    centroid = part.get("centroid") or {}
    centroid_x = float(centroid.get("x") or 0.0)
    centroid_y = float(centroid.get("y") or 0.0)
    centroid_z = float(centroid.get("z") or 0.0)
    margin = 50.0
    for minimum, maximum in boxes:
        if (
            float(minimum.get("x") or 0.0) - margin <= centroid_x <= float(maximum.get("x") or 0.0) + margin
            and float(minimum.get("y") or 0.0) - margin <= centroid_y <= float(maximum.get("y") or 0.0) + margin
            and float(minimum.get("z") or 0.0) - margin <= centroid_z <= float(maximum.get("z") or 0.0) + margin
        ):
            return False
    return True
