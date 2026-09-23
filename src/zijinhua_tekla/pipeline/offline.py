from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from ..adapters.normalized import normalized_document_from_assembly
from ..adapters.offline import (
    load_bundle,
    load_member,
    load_member_assembly_id,
    load_roles,
    load_truth_rows,
)
from ..casebank import CaseBank
from ..classifiers import classify_member, classify_part
from ..part_roles import main_material_label
from ..classifiers.box_assembly_drawing_steps import BoxAssemblyDrawingStep, build_box_assembly_drawing_steps
from ..classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, classify_main_material_segment_groups
from ..classifiers.box_part_spatial_relations import BoxPartSpatialRelation, classify_box_part_spatial_relations
from ..classifiers.box_station_topology_diagnostics import BoxStationTopologyDiagnostic, diagnose_box_station_topology
from ..classifiers.composite_main_material_segments import (
    CompositeMainMaterialSegment,
    classify_composite_main_material_segments,
)
from ..classifiers.corbel_units import CorbelUnit, classify_corbel_units
from ..classifiers.h_beam_part_sides import HBeamPartSide, classify_h_beam_part_sides
from ..classifiers.weld_backing import classify_weld_backing_plates
from ..contracts.normalized import NormalizedPart, PartSpatialHints
from ..features import feature_snapshots_from_bundle_parts
from ..quality.gate import DataQualityReport, quality_report_from_aligned_rows
from ..rules import text
from ..spatial_features import (
    classify_appendage_clusters_from_bundle,
    main_wall_part_ids_from_groups,
    outside_box_part_ids_from_relations,
)
from .compare import compare_recognition_to_truth


_ASSEMBLY_ROLES = {"箱型柱主材壁板", "内隔板", "电渣焊块"}


@dataclass(frozen=True)
class OfflinePipelineResult:
    member: dict[str, Any]
    bundle: dict[str, Any]
    assembly: dict[str, Any]
    aligned_rows: list[dict[str, Any]]
    quality_report: DataQualityReport
    spatial_classifications: list[Any] = field(default_factory=list)
    box_main_material_segment_groups: list[BoxMainMaterialSegmentGroup] = field(default_factory=list)
    composite_main_material_segments: list[CompositeMainMaterialSegment] = field(default_factory=list)
    box_part_spatial_relations: list[BoxPartSpatialRelation] = field(default_factory=list)
    box_assembly_drawing_steps: list[BoxAssemblyDrawingStep] = field(default_factory=list)
    box_station_topology_diagnostics: list[BoxStationTopologyDiagnostic] = field(default_factory=list)
    h_beam_part_sides: list[HBeamPartSide] = field(default_factory=list)
    recognition_rows: list[dict[str, Any]] = field(default_factory=list)
    member_body_type: str = ""
    corbel_units: list[CorbelUnit] = field(default_factory=list)


def run_model_recognition(
    root: Path,
    member_id: str,
    assembly_id: str | None = None,
    include_drawings: bool = False,
) -> OfflinePipelineResult:
    member = load_member(root, member_id)
    resolved_assembly_id = assembly_id or load_member_assembly_id(root, member_id)
    assembly, _by_pos, rel_by_part, bundle = load_bundle(root, resolved_assembly_id)
    snapshots = feature_snapshots_from_bundle_parts(assembly.get("parts", []), rel_by_part)
    member_body = classify_member(member, snapshots)
    case_bank = _load_seed_case_bank()
    main_material_groups = classify_main_material_segment_groups(
        assembly, member, _confirmed_segment_positions(member_id, case_bank)
    )
    composite_main_material_segments = classify_composite_main_material_segments(
        assembly, member, main_material_groups=main_material_groups
    )
    initial_box_part_spatial_relations = classify_box_part_spatial_relations(
        assembly, member, main_material_groups
    )
    spatial_classifications = classify_appendage_clusters_from_bundle(
        assembly,
        member,
        body_part_ids=main_wall_part_ids_from_groups(main_material_groups),
        appendage_part_ids=outside_box_part_ids_from_relations(initial_box_part_spatial_relations),
    )
    box_part_spatial_relations = classify_box_part_spatial_relations(
        assembly, member, main_material_groups, outside_part_ids=_outside_part_ids(spatial_classifications)
    )
    h_beam_part_sides = classify_h_beam_part_sides(assembly, member)
    document = normalized_document_from_assembly(member_id, assembly, rel_by_part)
    hints_by_id = _hints_by_part_id(
        document.parts,
        member_body.body_type,
        main_material_groups,
        composite_main_material_segments,
        box_part_spatial_relations,
        spatial_classifications,
        classify_weld_backing_plates(assembly),
    )
    corbel_units = classify_corbel_units(assembly, spatial_classifications, member=member)
    recognition_rows = _recognition_rows(member_id, document.parts, hints_by_id, len(corbel_units))
    drawing_steps: list[BoxAssemblyDrawingStep] = []
    if include_drawings:
        drawing_steps = build_box_assembly_drawing_steps(
            assembly=assembly,
            member_id=member_id,
            aligned_rows=recognition_rows,
            main_wall_groups=main_material_groups,
            box_part_spatial_relations=box_part_spatial_relations,
            spatial_classifications=spatial_classifications,
        )
    return OfflinePipelineResult(
        member=member,
        bundle=bundle,
        assembly=assembly,
        aligned_rows=[],
        quality_report=quality_report_from_aligned_rows([]),
        spatial_classifications=spatial_classifications,
        box_main_material_segment_groups=main_material_groups,
        composite_main_material_segments=composite_main_material_segments,
        box_part_spatial_relations=box_part_spatial_relations,
        box_assembly_drawing_steps=drawing_steps,
        box_station_topology_diagnostics=diagnose_box_station_topology(assembly, main_material_groups),
        h_beam_part_sides=h_beam_part_sides,
        recognition_rows=recognition_rows,
        member_body_type=member_body.body_type,
        corbel_units=corbel_units,
    )


def run_offline_analysis(
    root: Path,
    truth_root: Path | None,
    member_id: str,
    assembly_id: str | None = None,
    include_drawings: bool = False,
) -> OfflinePipelineResult:
    result = run_model_recognition(root, member_id, assembly_id, include_drawings=include_drawings)
    if truth_root is None:
        return result
    _assembly, by_pos, rel_by_part, _bundle = load_bundle(root, text(result.assembly.get("assemblyId")))
    aligned = compare_recognition_to_truth(
        result.recognition_rows,
        load_truth_rows(truth_root, member_id),
        by_pos,
        list(result.assembly.get("parts", [])),
        rel_by_part,
        load_roles(result.member),
        member_id,
        result.bundle,
        _load_seed_case_bank(),
    )
    return OfflinePipelineResult(
        member=result.member,
        bundle=result.bundle,
        assembly=result.assembly,
        aligned_rows=aligned,
        quality_report=quality_report_from_aligned_rows(aligned),
        spatial_classifications=result.spatial_classifications,
        box_main_material_segment_groups=result.box_main_material_segment_groups,
        composite_main_material_segments=result.composite_main_material_segments,
        box_part_spatial_relations=result.box_part_spatial_relations,
        box_assembly_drawing_steps=result.box_assembly_drawing_steps,
        box_station_topology_diagnostics=result.box_station_topology_diagnostics,
        h_beam_part_sides=result.h_beam_part_sides,
        recognition_rows=result.recognition_rows,
        member_body_type=result.member_body_type,
        corbel_units=result.corbel_units,
    )


def _recognition_rows(
    member_id: str,
    parts: tuple[NormalizedPart, ...],
    hints_by_id: dict[str, PartSpatialHints],
    corbel_unit_count: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[NormalizedPart, Any]]] = {}
    for part in parts:
        classified = classify_part(part, hints_by_id.get(part.part_id))
        key = part.part_position or part.part_id
        grouped.setdefault(key, []).append((part, classified))

    rows: list[dict[str, Any]] = []
    for position, items in grouped.items():
        part = items[0][0]
        roles = {item[1].role for item in items}
        processes = {item[1].process for item in items}
        shapes = {item[1].shape for item in items}
        evidence = [code for _, classified in items for code in classified.evidence]
        if len(roles) > 1 or len(processes) > 1 or len(shapes) > 1:
            role = "UNKNOWN"
            process = "UNKNOWN"
            shape = "UNKNOWN"
            evidence = ["同号零件分类不一致"] + evidence
            confidence = 0.2
        else:
            classified = items[0][1]
            role = classified.role
            process = classified.process
            shape = classified.shape
            confidence = classified.confidence
        main_labels = [
            main_material_label(hints_by_id.get(item[0].part_id), item[1].role) for item in items
        ]
        main_label = next((label for label in main_labels if label != "否"), "否")
        rows.append(
            {
                "构件名称": member_id,
                "零件名称": position,
                "规格": part.profile,
                "长度": int(round(part.length)) if part.length else 0,
                "数量": len(items),
                "材质": part.material,
                "工序": process,
                "形状分类": shape,
                "主材": main_label,
                "牛腿实体个数": corbel_unit_count,
                "predicted_role": role,
                "predicted_process": process,
                "predicted_shape": shape,
                "predicted_delivery": "组立用" if role in _ASSEMBLY_ROLES else "",
                "confidence": round(confidence, 3),
                "evidence": ";".join(dict.fromkeys(evidence)),
                "part_ids": ",".join(item[0].part_id for item in items),
            }
        )
    return rows


def _hints_by_part_id(
    parts: tuple[NormalizedPart, ...],
    member_body_type: str,
    main_material_groups: list[BoxMainMaterialSegmentGroup],
    composite_segments: list[CompositeMainMaterialSegment],
    box_relations: list[BoxPartSpatialRelation],
    spatial_classifications: list[Any],
    weld_backing: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, PartSpatialHints]:
    main_role_by_id: dict[str, str] = {}
    for segment in composite_segments:
        for plate in segment.main_plates:
            main_role_by_id[text(plate.part_id)] = plate.primary_role.value
    for group in main_material_groups:
        if group.group_type != "BOX_MAIN_WALL_CONFIRMED_SET":
            continue
        for part_id in group.part_ids:
            main_role_by_id[text(part_id)] = "BOX_MAIN_WALL_PLATE"
    relation_by_id = {text(item.part_id): item.relation_to_box_body for item in box_relations}
    appendage_by_id: dict[str, str] = {}
    for cluster in spatial_classifications:
        role = text(getattr(cluster, "role", ""))
        for part_id in getattr(cluster, "part_ids", []):
            if text(part_id):
                appendage_by_id[text(part_id)] = role
    weld_backing = weld_backing or {}
    hints: dict[str, PartSpatialHints] = {}
    for part in parts:
        backing_evidence = weld_backing.get(part.part_id, ())
        hints[part.part_id] = PartSpatialHints(
            member_body_type=member_body_type,
            relation_to_box_body=relation_by_id.get(part.part_id, ""),
            main_material_role=main_role_by_id.get(part.part_id, ""),
            appendage_role=appendage_by_id.get(part.part_id, ""),
            weld_backing=bool(backing_evidence),
            weld_backing_evidence=backing_evidence,
        )
    return hints


def _outside_part_ids(spatial_classifications: list[Any]) -> set[str]:
    result: set[str] = set()
    for item in spatial_classifications:
        if text(getattr(item, "role", "")) != "Bracket":
            continue
        result.update(text(part_id) for part_id in getattr(item, "part_ids", []) if text(part_id))
    return result


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
