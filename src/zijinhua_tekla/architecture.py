from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureLayer:
    name: str
    responsibility: str
    allowed_inputs: tuple[str, ...]
    outputs: tuple[str, ...]


ARCHITECTURE_LAYERS: tuple[ArchitectureLayer, ...] = (
    ArchitectureLayer(
        name="adapters",
        responsibility="Read source-specific Tekla bundle, Excel, teklatest, plugin, or MCP data and normalize it.",
        allowed_inputs=("Tekla bundle JSON", "member JSON", "Excel truth rows", "teklatest PartFeatures", "future MCP/plugin data"),
        outputs=("source-neutral records",),
    ),
    ArchitectureLayer(
        name="quality",
        responsibility="Detect data missing, exact-number conflicts, review-only geometry candidates, and model/manufacturing mouthpiece differences.",
        allowed_inputs=("source-neutral records", "aligned rows"),
        outputs=("DataQualityReport",),
    ),
    ArchitectureLayer(
        name="features",
        responsibility="Build factual part/member feature snapshots without business labels.",
        allowed_inputs=("source-neutral part records", "teklatest PartFeatures"),
        outputs=("PartFeatureSnapshot", "FeatureIndex"),
    ),
    ArchitectureLayer(
        name="spatial",
        responsibility="Compute relationship, cluster, root-contact, overhang, and position evidence.",
        allowed_inputs=("FeatureIndex", "assembly relationships", "member axis/body roles"),
        outputs=("AppendageClusterFeatures",),
    ),
    ArchitectureLayer(
        name="classifiers",
        responsibility="Classify member body, part role, bracket, process, and shape from features/evidence.",
        allowed_inputs=("PartFeatureSnapshot", "spatial evidence", "quality report"),
        outputs=("label", "confidence", "evidence"),
    ),
    ArchitectureLayer(
        name="cases",
        responsibility="Record human feedback, expected labels, issue attribution, and regression cases.",
        allowed_inputs=("classifier outputs", "human confirmation", "quality issues"),
        outputs=("CaseFeedback", "regression samples"),
    ),
    ArchitectureLayer(
        name="pipeline",
        responsibility="Coordinate offline and future live runs from adapters through reports.",
        allowed_inputs=("adapters", "quality", "features", "spatial", "classifiers", "cases"),
        outputs=("PipelineResult",),
    ),
    ArchitectureLayer(
        name="reports",
        responsibility="Write CSV, JSON, Markdown, and future drawing annotations from pipeline results.",
        allowed_inputs=("PipelineResult",),
        outputs=("human-readable reports", "machine-readable outputs"),
    ),
)


def layer_names() -> list[str]:
    return [layer.name for layer in ARCHITECTURE_LAYERS]
