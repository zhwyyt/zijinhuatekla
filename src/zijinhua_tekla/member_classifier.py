from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .rules import norm_spec, text


@dataclass(frozen=True)
class MemberBodyClassification:
    member_id: str
    body_type: str
    confidence: float
    reason_code: str
    description: str = ""
    evidence_codes: list[str] = field(default_factory=list)


def _normalize_confidence(value: Any) -> float:
    try:
        number = float(value)
    except Exception:
        return 0.0
    if number > 1.0:
        return max(0.0, min(1.0, number / 100.0))
    return max(0.0, min(1.0, number))


def _snapshot_profile(snapshot: Any) -> str:
    if hasattr(snapshot, "profile"):
        return norm_spec(getattr(snapshot, "profile"))
    if isinstance(snapshot, dict):
        return norm_spec(snapshot.get("profileString") or snapshot.get("profile"))
    return ""


def _infer_from_snapshot_profiles(snapshots: list[Any]) -> MemberBodyClassification | None:
    profiles = [_snapshot_profile(snapshot) for snapshot in snapshots]
    profiles = [profile for profile in profiles if profile]
    if not profiles:
        return None

    if any(profile.startswith("BH") for profile in profiles):
        return MemberBodyClassification(
            member_id="",
            body_type="H",
            confidence=0.78,
            reason_code="SNAPSHOT_PROFILE_FAMILY",
            description=";".join(sorted(set(profiles))[:4]),
            evidence_codes=["snapshot.profile.BH"],
        )

    if any(profile.startswith("BOX") or profile.startswith("BBOX") for profile in profiles):
        return MemberBodyClassification(
            member_id="",
            body_type="BOX",
            confidence=0.78,
            reason_code="SNAPSHOT_PROFILE_FAMILY",
            description=";".join(sorted(set(profiles))[:4]),
            evidence_codes=["snapshot.profile.BOX"],
        )

    if any(profile.startswith("H") and not profile.startswith("HP") for profile in profiles):
        return MemberBodyClassification(
            member_id="",
            body_type="H",
            confidence=0.72,
            reason_code="SNAPSHOT_PROFILE_FAMILY",
            description=";".join(sorted(set(profiles))[:4]),
            evidence_codes=["snapshot.profile.H"],
        )

    return None


def classify_member_body(member: dict[str, Any], snapshots: list[Any]) -> MemberBodyClassification:
    classification = member.get("Classification") or {}
    member_info = member.get("Member") or {}
    member_id = text(member_info.get("Name") or member_info.get("AssemblyName") or member_info.get("AssemblyId"))
    raw_code = text(
        classification.get("MainClass")
        or classification.get("CoarseMainClassCode")
        or classification.get("BodyType")
    ).upper()
    description = text(classification.get("KeyDimensionsDisplay"))
    confidence = _normalize_confidence(classification.get("Confidence"))

    if raw_code:
        return MemberBodyClassification(
            member_id=member_id,
            body_type=raw_code,
            confidence=confidence or 0.5,
            reason_code="EXISTING_MEMBER_CLASSIFICATION",
            description=description,
            evidence_codes=["member.Classification.MainClass"],
        )

    if description.upper().startswith("BOX"):
        return MemberBodyClassification(
            member_id=member_id,
            body_type="BOX",
            confidence=confidence or 0.7,
            reason_code="KEY_DIMENSIONS_BOX_PREFIX",
            description=description,
            evidence_codes=["member.Classification.KeyDimensionsDisplay"],
        )

    profile_result = _infer_from_snapshot_profiles(snapshots)
    if profile_result is not None:
        return MemberBodyClassification(
            member_id=member_id,
            body_type=profile_result.body_type,
            confidence=profile_result.confidence,
            reason_code=profile_result.reason_code,
            description=profile_result.description,
            evidence_codes=profile_result.evidence_codes,
        )

    return MemberBodyClassification(
        member_id=member_id,
        body_type="UNKNOWN",
        confidence=0.0,
        reason_code="NO_BODY_CLASSIFICATION_EVIDENCE",
        description=description,
        evidence_codes=[],
    )
