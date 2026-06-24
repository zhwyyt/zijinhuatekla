from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Any

from ..adapters.offline import (
    load_bundle,
    load_member,
    load_member_assembly_id,
    load_roles,
    load_truth_rows,
)
from ..casebank import CaseBank
from ..classifiers import classify_part
from ..classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, classify_main_material_segment_groups
from ..classifiers.box_part_spatial_relations import BoxPartSpatialRelation, classify_box_part_spatial_relations
from ..features import build_feature_index, feature_snapshots_from_bundle_parts
from ..quality.gate import DataQualityReport
from ..quality.gate import quality_report_from_aligned_rows
from ..quality.manufacturing_scope import apply_confirmed_segment_groups, apply_manufacturing_scope_hints
from ..rules import find_equivalent_parts, summarize_parts, text
from ..spatial_features import classify_appendage_clusters_from_bundle


@dataclass(frozen=True)
class OfflinePipelineResult:
    member: dict[str, Any]
    bundle: dict[str, Any]
    assembly: dict[str, Any]
    aligned_rows: list[dict[str, Any]]
    quality_report: DataQualityReport
    spatial_classifications: list[Any] = field(default_factory=list)
    box_main_material_segment_groups: list[BoxMainMaterialSegmentGroup] = field(default_factory=list)
    box_part_spatial_relations: list[BoxPartSpatialRelation] = field(default_factory=list)


def run_offline_analysis(
    root: Path,
    truth_root: Path,
    member_id: str,
    assembly_id: str | None = None,
) -> OfflinePipelineResult:
    member = load_member(root, member_id)
    resolved_assembly_id = assembly_id or load_member_assembly_id(root, member_id)
    assembly, _by_pos, rel_by_part, bundle = load_bundle(root, resolved_assembly_id)
    roles = load_roles(member)
    rows = load_truth_rows(truth_root, member_id)
    snapshots = feature_snapshots_from_bundle_parts(assembly.get("parts", []), rel_by_part)
    feature_index = build_feature_index(snapshots)
    aligned = []
    for row in rows:
        parts, match_method, match_note = find_equivalent_parts(
            row,
            feature_index.by_position,
            feature_index.part_dicts,
        )
        summary = summarize_parts(parts, rel_by_part, roles, row)
        summary["match_method"] = match_method
        summary["match_note"] = match_note
        aligned.append({**row, **summary, **_predict(row, summary)})
    case_bank = _load_seed_case_bank()
    aligned = apply_confirmed_segment_groups(aligned, member_id, case_bank)
    aligned = apply_manufacturing_scope_hints(aligned, bundle)
    main_material_groups = classify_main_material_segment_groups(
        assembly, member, _confirmed_segment_positions(member_id, case_bank)
    )
    spatial_classifications = classify_appendage_clusters_from_bundle(assembly, member)
    outside_part_ids = _outside_part_ids(spatial_classifications)
    return OfflinePipelineResult(
        member=member,
        bundle=bundle,
        assembly=assembly,
        aligned_rows=aligned,
        quality_report=quality_report_from_aligned_rows(aligned),
        spatial_classifications=spatial_classifications,
        box_main_material_segment_groups=main_material_groups,
        box_part_spatial_relations=classify_box_part_spatial_relations(
            assembly, member, main_material_groups, outside_part_ids=outside_part_ids
        ),
    )



def _outside_part_ids(spatial_classifications: list[Any]) -> set[str]:
    result: set[str] = set()
    for item in spatial_classifications:
        role = text(getattr(item, "role", ""))
        if role not in {"Bracket"}:
            continue
        result.update(text(part_id) for part_id in getattr(item, "part_ids", []) if text(part_id))
    return result
def _predict(row: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    role_result = classify_part(row, summary)
    return {
        "predicted_role": role_result.role,
        "predicted_process": role_result.process,
        "predicted_shape": role_result.shape,
        "predicted_delivery": "组立用" if role_result.role in {"箱型柱主材壁板", "内隔板", "电渣焊块"} else "",
        "prediction_status": _score_prediction(row, summary, role_result.process, role_result.shape),
        "evidence": ";".join(role_result.evidence),
    }


def _score_prediction(row: dict[str, Any], summary: dict[str, Any], process: str, shape: str) -> str:
    process_match = process == row["工序"]
    shape_match = (not row["形状分类"]) or shape == row["形状分类"]
    if summary["tekla_count"] == 0:
        return "DATA_MISSING"
    if summary["match_method"] == "partPositionConflict":
        return "MATCH_CONFLICT"
    if process_match and shape_match:
        return "MATCH"
    if process_match:
        return "PROCESS_MATCH"
    return "DIFF"


def _load_seed_case_bank() -> CaseBank:
    seed_path = Path(__file__).resolve().parents[3] / "cases" / "seed.json"
    if seed_path.exists():
        return CaseBank.load_json(seed_path)
    return CaseBank()








def _confirmed_segment_positions(member_id: str, case_bank: CaseBank) -> set[str]:
    feedback = case_bank.get(f"{member_id}:box-column-main-material-segments")
    if feedback is None or feedback.expected_label != "BOX_COLUMN_MAIN_MATERIAL_SEGMENT_GROUP":
        return set()
    return set(re.findall(r"T3-P-\d+", feedback.human_note))

