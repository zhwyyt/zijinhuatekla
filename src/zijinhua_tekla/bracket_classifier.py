from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppendageClusterFeatures:
    cluster_id: str
    part_ids: list[str] = field(default_factory=list)
    root_contact_ratio: float = 0.0
    cantilever_ratio: float = 0.0
    span_along_axis: float = 0.0
    assembly_span: float = 0.0
    centroid_outside_body: bool = False
    has_end_connection_signal: bool = False
    bolt_count: int = 0
    cluster_volume: float = 0.0
    max_thickness: float = 0.0
    attached_face_type: str = "Unknown"


@dataclass(frozen=True)
class AppendageRoleClassification:
    cluster_id: str
    role: str
    confidence: float
    part_ids: list[str] = field(default_factory=list)
    evidence_codes: list[str] = field(default_factory=list)
    missing_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BracketClassifierOptions:
    bracket_root_contact_ratio_max: float = 0.45
    bracket_overhang_ratio_min: float = 1.35
    bracket_axis_span_ratio_max: float = 0.35


def _bracket_evidence(
    features: AppendageClusterFeatures,
    options: BracketClassifierOptions,
) -> list[str]:
    evidence = []
    if features.root_contact_ratio <= options.bracket_root_contact_ratio_max:
        evidence.append("ROOT_LOCAL_ATTACHMENT")
    if features.cantilever_ratio >= options.bracket_overhang_ratio_min:
        evidence.append("OVERHANG_DOMINANT")
    if (
        features.assembly_span > 1e-6
        and features.span_along_axis / features.assembly_span <= options.bracket_axis_span_ratio_max
    ):
        evidence.append("AXIS_SPAN_LIMITED")
    if features.centroid_outside_body:
        evidence.append("EXTERNAL_CENTROID")
    if not features.has_end_connection_signal:
        evidence.append("NOT_END_CONNECTION")
    return evidence


def classify_appendage_cluster(
    features: AppendageClusterFeatures,
    options: BracketClassifierOptions | None = None,
) -> AppendageRoleClassification:
    options = options or BracketClassifierOptions()
    required = [
        "ROOT_LOCAL_ATTACHMENT",
        "OVERHANG_DOMINANT",
        "AXIS_SPAN_LIMITED",
        "EXTERNAL_CENTROID",
        "NOT_END_CONNECTION",
    ]
    evidence = _bracket_evidence(features, options)
    missing = [code for code in required if code not in evidence]

    if "NOT_END_CONNECTION" in evidence and len(evidence) >= 4:
        return AppendageRoleClassification(
            cluster_id=features.cluster_id,
            role="Bracket",
            confidence=min(0.98, 0.70 + 0.06 * len(evidence)),
            part_ids=features.part_ids,
            evidence_codes=evidence,
            missing_codes=missing,
        )

    return AppendageRoleClassification(
        cluster_id=features.cluster_id,
        role="Unknown",
        confidence=0.30,
        part_ids=features.part_ids,
        evidence_codes=evidence,
        missing_codes=missing,
    )
