from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..pipeline.offline import OfflinePipelineResult
from ..quality.candidates import (
    build_conflict_candidate_report,
    build_missing_candidate_report,
    flatten_conflict_candidate_report,
    flatten_missing_candidate_report,
)
from ..quality.manufacturing_scope import build_manufacturing_scope_report, flatten_manufacturing_scope_report
from ..quality.review import build_review_tasks, save_review_tasks_csv, save_review_tasks_json, summarize_review_tasks


@dataclass(frozen=True)
class OfflineReportPaths:
    csv_path: Path
    json_path: Path
    spatial_csv_path: Path
    spatial_json_path: Path
    quality_csv_path: Path
    quality_json_path: Path
    quality_review_tasks_path: Path
    quality_review_tasks_csv_path: Path
    quality_review_summary_path: Path
    quality_review_summary_csv_path: Path
    missing_candidates_path: Path
    missing_candidates_csv_path: Path
    conflict_candidates_path: Path
    conflict_candidates_csv_path: Path
    manufacturing_scope_path: Path
    manufacturing_scope_csv_path: Path
    box_main_material_segments_path: Path
    box_main_material_segments_csv_path: Path
    box_part_spatial_relations_path: Path
    box_part_spatial_relations_csv_path: Path
    box_station_topology_diagnostics_path: Path
    box_station_topology_diagnostics_csv_path: Path
    h_beam_part_sides_path: Path
    h_beam_part_sides_csv_path: Path
    markdown_path: Path

    def as_tuple(self) -> tuple[Path, ...]:
        return (
            self.csv_path,
            self.json_path,
            self.spatial_csv_path,
            self.spatial_json_path,
            self.quality_csv_path,
            self.quality_json_path,
            self.quality_review_tasks_path,
            self.quality_review_tasks_csv_path,
            self.quality_review_summary_path,
            self.quality_review_summary_csv_path,
            self.missing_candidates_path,
            self.missing_candidates_csv_path,
            self.conflict_candidates_path,
            self.conflict_candidates_csv_path,
            self.manufacturing_scope_path,
            self.manufacturing_scope_csv_path,
            self.box_main_material_segments_path,
            self.box_main_material_segments_csv_path,
            self.box_part_spatial_relations_path,
            self.box_part_spatial_relations_csv_path,
            self.box_station_topology_diagnostics_path,
            self.box_station_topology_diagnostics_csv_path,
            self.h_beam_part_sides_path,
            self.h_beam_part_sides_csv_path,
            self.markdown_path,
        )


def write_offline_analysis_report(result: OfflinePipelineResult, out_dir: Path, member_id: str) -> OfflineReportPaths:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{member_id}-alignment.csv"
    json_path = out_dir / f"{member_id}-alignment.json"
    spatial_csv_path = out_dir / f"{member_id}-spatial-classifications.csv"
    spatial_json_path = out_dir / f"{member_id}-spatial-classifications.json"
    quality_csv_path = out_dir / f"{member_id}-quality-issues.csv"
    quality_json_path = out_dir / f"{member_id}-quality-issues.json"
    quality_review_tasks_path = out_dir / f"{member_id}-quality-review-tasks.json"
    quality_review_tasks_csv_path = out_dir / f"{member_id}-quality-review-tasks.csv"
    quality_review_summary_path = out_dir / f"{member_id}-quality-review-summary.json"
    quality_review_summary_csv_path = out_dir / f"{member_id}-quality-review-summary.csv"
    missing_candidates_path = out_dir / f"{member_id}-missing-candidates.json"
    missing_candidates_csv_path = out_dir / f"{member_id}-missing-candidates.csv"
    conflict_candidates_path = out_dir / f"{member_id}-conflict-candidates.json"
    conflict_candidates_csv_path = out_dir / f"{member_id}-conflict-candidates.csv"
    manufacturing_scope_path = out_dir / f"{member_id}-manufacturing-scope-candidates.json"
    manufacturing_scope_csv_path = out_dir / f"{member_id}-manufacturing-scope-candidates.csv"
    box_main_material_segments_path = out_dir / f"{member_id}-box-main-material-segment-groups.json"
    box_main_material_segments_csv_path = out_dir / f"{member_id}-box-main-material-segment-groups.csv"
    box_part_spatial_relations_path = out_dir / f"{member_id}-box-part-spatial-relations.json"
    box_part_spatial_relations_csv_path = out_dir / f"{member_id}-box-part-spatial-relations.csv"
    box_station_topology_diagnostics_path = out_dir / f"{member_id}-box-station-topology-diagnostics.json"
    box_station_topology_diagnostics_csv_path = out_dir / f"{member_id}-box-station-topology-diagnostics.csv"
    h_beam_part_sides_path = out_dir / f"{member_id}-h-beam-part-sides.json"
    h_beam_part_sides_csv_path = out_dir / f"{member_id}-h-beam-part-sides.csv"
    md_path = out_dir / f"{member_id}-analysis.md"

    aligned = result.aligned_rows
    spatial_rows = _spatial_rows(result)
    quality_rows = _quality_rows(result)
    pd.DataFrame(aligned).to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(aligned, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(spatial_rows).to_csv(spatial_csv_path, index=False, encoding="utf-8-sig")
    spatial_json_path.write_text(json.dumps(spatial_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(quality_rows).to_csv(quality_csv_path, index=False, encoding="utf-8-sig")
    quality_json_path.write_text(json.dumps(quality_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    review_tasks = build_review_tasks(member_id, result.quality_report)
    save_review_tasks_json(review_tasks, quality_review_tasks_path)
    save_review_tasks_csv(review_tasks, quality_review_tasks_csv_path)
    review_summary = summarize_review_tasks(review_tasks)
    quality_review_summary_path.write_text(json.dumps(review_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(review_summary).to_csv(quality_review_summary_csv_path, index=False, encoding="utf-8-sig")
    missing_candidates = build_missing_candidate_report(member_id, aligned, result.bundle)
    missing_candidates_path.write_text(json.dumps(missing_candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(flatten_missing_candidate_report(missing_candidates)).to_csv(
        missing_candidates_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    conflict_candidates = build_conflict_candidate_report(member_id, aligned, result.bundle)
    conflict_candidates_path.write_text(json.dumps(conflict_candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(flatten_conflict_candidate_report(conflict_candidates)).to_csv(
        conflict_candidates_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    manufacturing_scope = build_manufacturing_scope_report(member_id, aligned, result.bundle)
    manufacturing_scope_path.write_text(json.dumps(manufacturing_scope, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(flatten_manufacturing_scope_report(manufacturing_scope)).to_csv(
        manufacturing_scope_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    box_main_material_segments = [group.to_dict() for group in result.box_main_material_segment_groups]
    box_main_material_segments_path.write_text(json.dumps(box_main_material_segments, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(_flatten_box_main_material_segment_groups(box_main_material_segments)).to_csv(
        box_main_material_segments_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    box_part_spatial_relations = [item.to_dict() for item in result.box_part_spatial_relations]
    box_part_spatial_relations_path.write_text(
        json.dumps(box_part_spatial_relations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(_flatten_box_part_spatial_relations(box_part_spatial_relations)).to_csv(
        box_part_spatial_relations_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    box_station_topology_diagnostics = [item.to_dict() for item in result.box_station_topology_diagnostics]
    box_station_topology_diagnostics_path.write_text(
        json.dumps(box_station_topology_diagnostics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(_flatten_box_station_topology_diagnostics(box_station_topology_diagnostics)).to_csv(
        box_station_topology_diagnostics_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    h_beam_part_sides = [item.to_dict() for item in result.h_beam_part_sides]
    h_beam_part_sides_path.write_text(
        json.dumps(h_beam_part_sides, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(_flatten_h_beam_part_sides(h_beam_part_sides)).to_csv(
        h_beam_part_sides_csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    md_path.write_text(
        _build_markdown(
            result,
            member_id,
            csv_path,
            json_path,
            quality_csv_path,
            quality_json_path,
            quality_review_tasks_path,
            quality_review_tasks_csv_path,
            quality_review_summary_path,
            quality_review_summary_csv_path,
            missing_candidates_path,
            missing_candidates_csv_path,
            conflict_candidates_path,
            conflict_candidates_csv_path,
            manufacturing_scope_path,
            manufacturing_scope_csv_path,
            box_main_material_segments_path,
            box_main_material_segments_csv_path,
            box_part_spatial_relations_path,
            box_part_spatial_relations_csv_path,
            box_station_topology_diagnostics_path,
            box_station_topology_diagnostics_csv_path,
            h_beam_part_sides_path,
            h_beam_part_sides_csv_path,
        ),
        encoding="utf-8",
    )
    return OfflineReportPaths(
        csv_path=csv_path,
        json_path=json_path,
        spatial_csv_path=spatial_csv_path,
        spatial_json_path=spatial_json_path,
        quality_csv_path=quality_csv_path,
        quality_json_path=quality_json_path,
        quality_review_tasks_path=quality_review_tasks_path,
        quality_review_tasks_csv_path=quality_review_tasks_csv_path,
        quality_review_summary_path=quality_review_summary_path,
        quality_review_summary_csv_path=quality_review_summary_csv_path,
        missing_candidates_path=missing_candidates_path,
        missing_candidates_csv_path=missing_candidates_csv_path,
        conflict_candidates_path=conflict_candidates_path,
        conflict_candidates_csv_path=conflict_candidates_csv_path,
        manufacturing_scope_path=manufacturing_scope_path,
        manufacturing_scope_csv_path=manufacturing_scope_csv_path,
        box_main_material_segments_path=box_main_material_segments_path,
        box_main_material_segments_csv_path=box_main_material_segments_csv_path,
        box_part_spatial_relations_path=box_part_spatial_relations_path,
        box_part_spatial_relations_csv_path=box_part_spatial_relations_csv_path,
        box_station_topology_diagnostics_path=box_station_topology_diagnostics_path,
        box_station_topology_diagnostics_csv_path=box_station_topology_diagnostics_csv_path,
        h_beam_part_sides_path=h_beam_part_sides_path,
        h_beam_part_sides_csv_path=h_beam_part_sides_csv_path,
        markdown_path=md_path,
    )


def _spatial_rows(result: OfflinePipelineResult) -> list[dict[str, object]]:
    return [
        {
            "cluster_id": item.cluster_id,
            "role": item.role,
            "confidence": item.confidence,
            "part_ids": ";".join(item.part_ids),
            "evidence_codes": ";".join(item.evidence_codes),
            "missing_codes": ";".join(item.missing_codes),
        }
        for item in result.spatial_classifications
    ]


def _quality_rows(result: OfflinePipelineResult) -> list[dict[str, object]]:
    return [
        {
            "issue_type": item.issue_type.value,
            "part_name": item.part_name,
            "status": item.status,
            "match_method": item.match_method,
            "evidence": item.evidence,
        }
        for item in result.quality_report.issues
    ]


def _flatten_box_main_material_segment_groups(groups: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for group in groups:
        part_ids = [str(value) for value in group.get("part_ids", [])]
        positions = [str(value) for value in group.get("part_positions", [])]
        for index, part_id in enumerate(part_ids):
            rows.append(
                {
                    "assembly_id": group.get("assembly_id", ""),
                    "group_type": group.get("group_type", ""),
                    "face_id": group.get("face_id", ""),
                    "part_id": part_id,
                    "part_position": positions[index] if index < len(positions) else "",
                    "station_ranges": group.get("station_ranges", ""),
                    "gap_summary": group.get("gap_summary", ""),
                    "continuity_level": group.get("continuity_level", ""),
                    "confidence": group.get("confidence", ""),
                    "issue_category": group.get("issue_category", ""),
                    "evidence_codes": ";".join(str(value) for value in group.get("evidence_codes", [])),
                }
            )
    return rows

def _flatten_box_part_spatial_relations(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "assembly_id": row.get("assembly_id", ""),
            "part_id": row.get("part_id", ""),
            "part_position": row.get("part_position", ""),
            "relation_to_box_body": row.get("relation_to_box_body", ""),
            "station_range": row.get("station_range", ""),
            "section_relation": row.get("section_relation", ""),
            "connected_main_wall_ids": ";".join(str(value) for value in row.get("connected_main_wall_ids", [])),
            "confidence": row.get("confidence", ""),
            "issue_category": row.get("issue_category", ""),
            "evidence_codes": ";".join(str(value) for value in row.get("evidence_codes", [])),
        }
        for row in rows
    ]


def _flatten_box_station_topology_diagnostics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    flattened = []
    for row in rows:
        loop_summaries = row.get("loop_summaries", [])
        trigger_summaries = row.get("trigger_part_summaries", [])
        degenerate_positions = []
        trigger_positions = []
        if isinstance(loop_summaries, list):
            for loop in loop_summaries:
                if isinstance(loop, dict) and loop.get("is_degenerate"):
                    degenerate_positions.append(str(loop.get("part_position", "")))
        if isinstance(trigger_summaries, list):
            for trigger in trigger_summaries:
                if isinstance(trigger, dict):
                    trigger_positions.append(str(trigger.get("part_position", "")))
        flattened.append(
            {
                "assembly_id": row.get("assembly_id", ""),
                "station": row.get("station", ""),
                "topology_status": row.get("topology_status", ""),
                "station_scope": row.get("station_scope", ""),
                "main_wall_loop_count": row.get("main_wall_loop_count", ""),
                "usable_loop_count": row.get("usable_loop_count", ""),
                "degenerate_loop_count": row.get("degenerate_loop_count", ""),
                "union_geometry_type": row.get("union_geometry_type", ""),
                "union_component_count": row.get("union_component_count", ""),
                "inner_loop_count": row.get("inner_loop_count", ""),
                "topology_area": row.get("topology_area", ""),
                "topology_bounds": row.get("topology_bounds", ""),
                "evidence_codes": ";".join(str(value) for value in row.get("evidence_codes", [])),
                "degenerate_part_positions": ";".join(value for value in degenerate_positions if value),
                "trigger_part_positions": ";".join(value for value in trigger_positions if value),
            }
        )
    return flattened


def _flatten_h_beam_part_sides(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "assembly_id": row.get("assembly_id", ""),
            "part_id": row.get("part_id", ""),
            "part_position": row.get("part_position", ""),
            "part_name": row.get("part_name", ""),
            "h_side": row.get("h_side", ""),
            "confidence": row.get("confidence", ""),
            "issue_category": row.get("issue_category", ""),
            "evidence_codes": ";".join(str(value) for value in row.get("evidence_codes", [])),
        }
        for row in rows
    ]


def _build_markdown(
    result: OfflinePipelineResult,
    member_id: str,
    csv_path: Path,
    json_path: Path,
    quality_csv_path: Path,
    quality_json_path: Path,
    quality_review_tasks_path: Path,
    quality_review_tasks_csv_path: Path,
    quality_review_summary_path: Path,
    quality_review_summary_csv_path: Path,
    missing_candidates_path: Path,
    missing_candidates_csv_path: Path,
    conflict_candidates_path: Path,
    conflict_candidates_csv_path: Path,
    manufacturing_scope_path: Path,
    manufacturing_scope_csv_path: Path,
    box_main_material_segments_path: Path,
    box_main_material_segments_csv_path: Path,
    box_part_spatial_relations_path: Path,
    box_part_spatial_relations_csv_path: Path,
    box_station_topology_diagnostics_path: Path,
    box_station_topology_diagnostics_csv_path: Path,
    h_beam_part_sides_path: Path,
    h_beam_part_sides_csv_path: Path,
) -> str:
    member = result.member
    assembly = result.assembly
    aligned = result.aligned_rows
    status_counts = Counter(item["prediction_status"] for item in aligned)
    method_counts = Counter(item["match_method"] for item in aligned)
    unmatched = [item for item in aligned if item["tekla_count"] == 0]
    conflicts = [item for item in aligned if item["prediction_status"] == "MATCH_CONFLICT"]
    residual = [item for item in aligned if item["prediction_status"] not in {"MATCH", "MATCH_CONFLICT"}]
    spatial_counts = Counter(item.role for item in result.spatial_classifications)
    box_relation_counts = Counter(item.relation_to_box_body for item in result.box_part_spatial_relations)
    box_topology_counts = Counter(item.topology_status for item in result.box_station_topology_diagnostics)
    h_side_counts = Counter(item.h_side for item in result.h_beam_part_sides)

    lines = [
        f"# {member_id} 加工识别对齐分析",
        "",
        "## 构件结论",
        "",
        f"- 主材判定：`{member.get('Classification', {}).get('KeyDimensionsDisplay')}`，置信度 `{member.get('Classification', {}).get('Confidence')}`。",
        f"- bundle assembly：`{assembly.get('assemblyId')}`；主零件 `{assembly.get('mainPartId')}`；零件数 `{len(assembly.get('parts', []))}`；关系数 `{len(assembly.get('relationships', []))}`。",
        "",
        "## 命中概览",
        "",
        "- 预测状态：" + "；".join(f"`{key}`={value}" for key, value in status_counts.most_common()),
        "- 匹配方式：" + "；".join(f"`{key}`={value}" for key, value in method_counts.most_common()),
        f"- Excel 行数 `{len(aligned)}`；完全自动对齐 `{status_counts.get('MATCH', 0)}` 行。",
        f"- 缺 Tekla 实体 `{len(unmatched)}` 行；同名但规格/长度冲突 `{len(conflicts)}` 行。",
        "",
        "## 已固化口径",
        "",
        "- `*-H-xxx[s/x/f]` 可由对应 `*-H-xxx` 的 BH 型钢拆板派生，不当作缺件。",
        "- `ContourPlate` 优先用轮廓边长匹配 Excel 加工尺寸，避免斜放 OBB 外包盒误判。",
        "- 同名 `partPosition` 与规格/长度不一致时保留冲突证据，不算自动成功。",
        "",
    ]

    if result.spatial_classifications:
        lines += [
            "## 空间关系诊断",
            "",
            "- 附属件簇角色：" + "；".join(f"`{key}`={value}" for key, value in spatial_counts.most_common()),
            "",
        ]
        bracket_candidates = [item for item in result.spatial_classifications if item.role == "Bracket"]
        if bracket_candidates:
            lines += ["### Bracket 候选", ""]
            for item in bracket_candidates:
                lines.append(
                    f"- `{item.cluster_id}`：零件 `{';'.join(item.part_ids)}`；置信度 `{item.confidence}`；"
                    f"证据 `{';'.join(item.evidence_codes)}`；缺失 `{';'.join(item.missing_codes)}`。"
                )
            lines.append("")


    if result.box_part_spatial_relations:
        lines += [
            "## BOX 内外关系",
            "",
            "- 关系分布：" + "；".join(f"`{key}`={value}" for key, value in box_relation_counts.most_common()),
            "",
        ]
    if result.box_station_topology_diagnostics:
        lines += [
            "## BOX Station Topology 诊断",
            "",
            "- topology 状态：" + "；".join(f"`{key}`={value}" for key, value in box_topology_counts.most_common()),
            "",
        ]
    if result.h_beam_part_sides:
        lines += [
            "## H 钢零件侧面",
            "",
            "- 侧面分布：" + "；".join(f"`{key}`={value}" for key, value in h_side_counts.most_common()),
            "",
        ]
    if unmatched:
        lines += ["## 未匹配行", ""]
        for item in unmatched:
            lines.append(f"- `{item['零件名称']}` `{item['规格']}` 长 `{item['长度']}`；候选：`{item.get('match_note', '')}`")
        lines.append("")

    if conflicts:
        lines += ["## 同名冲突行", ""]
        for item in conflicts:
            lines.append(
                f"- `{item['零件名称']}` `{item['规格']}` 长 `{item['长度']}`："
                f"Tekla `{item.get('match_note', '')}`"
            )
        lines.append("")

    if residual:
        lines += ["## 仍需复核", ""]
        for item in residual:
            lines.append(
                f"- `{item['零件名称']}` `{item['规格']}` 长 `{item['长度']}`："
                f"真实 `{item['工序']}/{item['形状分类']}/{item['备注']}`，"
                f"预测 `{item['predicted_process']}/{item['predicted_shape']}/{item['predicted_role']}`，"
                f"状态 `{item['prediction_status']}`。"
            )
        lines.append("")

    lines += [
        "## 输出文件",
        "",
        f"- CSV：`{csv_path}`",
        f"- JSON：`{json_path}`",
        f"- Quality Issues CSV：`{quality_csv_path}`",
        f"- Quality Issues JSON：`{quality_json_path}`",
        f"- Quality Review Tasks JSON：`{quality_review_tasks_path}`",
        f"- Quality Review Tasks CSV：`{quality_review_tasks_csv_path}`",
        f"- Quality Review Summary JSON：`{quality_review_summary_path}`",
        f"- Quality Review Summary CSV：`{quality_review_summary_csv_path}`",
        f"- Missing Candidates JSON：`{missing_candidates_path}`",
        f"- Missing Candidates CSV：`{missing_candidates_csv_path}`",
        f"- Conflict Candidates JSON：`{conflict_candidates_path}`",
        f"- Conflict Candidates CSV：`{conflict_candidates_csv_path}`",
        f"- Manufacturing Scope Candidates JSON：`{manufacturing_scope_path}`",
        f"- Manufacturing Scope Candidates CSV：`{manufacturing_scope_csv_path}`",
        f"- BOX Main Material Segment Groups JSON：`{box_main_material_segments_path}`",
        f"- BOX Main Material Segment Groups CSV：`{box_main_material_segments_csv_path}`",
        f"- BOX Part Spatial Relations JSON：`{box_part_spatial_relations_path}`",
        f"- BOX Part Spatial Relations CSV：`{box_part_spatial_relations_csv_path}`",
        f"- BOX Station Topology Diagnostics JSON：`{box_station_topology_diagnostics_path}`",
        f"- BOX Station Topology Diagnostics CSV：`{box_station_topology_diagnostics_csv_path}`",
        f"- H Beam Part Sides JSON：`{h_beam_part_sides_path}`",
        f"- H Beam Part Sides CSV：`{h_beam_part_sides_csv_path}`",
    ]
    return "\n".join(lines)


