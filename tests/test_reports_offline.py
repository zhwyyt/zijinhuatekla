import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from zijinhua_tekla.bracket_classifier import AppendageRoleClassification
from zijinhua_tekla.classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, SegmentContinuityLevel
from zijinhua_tekla.classifiers.box_part_spatial_relations import BoxPartSpatialRelation
from zijinhua_tekla.classifiers.box_station_topology_diagnostics import BoxStationTopologyDiagnostic
from zijinhua_tekla.classifiers.h_beam_part_sides import HBeamPartSide
from zijinhua_tekla.pipeline.offline import OfflinePipelineResult
from zijinhua_tekla.quality.gate import quality_report_from_aligned_rows
from zijinhua_tekla.reports.offline import write_offline_analysis_report


class OfflineReportTests(unittest.TestCase):
    def test_write_offline_analysis_report_outputs_csv_json_and_markdown_summary(self):
        aligned = [
            {
                "零件名称": "A-P-1",
                "规格": "PL10*200",
                "长度": 1000,
                "工序": "下料割孔",
                "形状分类": "方块",
                "备注": "",
                "tekla_count": 1,
                "match_method": "partPosition",
                "prediction_status": "MATCH",
                "predicted_process": "下料割孔",
                "predicted_shape": "方块",
                "predicted_role": "连接板",
            },
            {
                "零件名称": "A-P-2",
                "规格": "PL8*120",
                "长度": 300,
                "工序": "下料",
                "形状分类": "异形",
                "备注": "复核",
                "tekla_count": 0,
                "match_method": "missing",
                "match_note": "no partPosition candidate",
                "prediction_status": "DATA_MISSING",
                "predicted_process": "下料",
                "predicted_shape": "异形",
                "predicted_role": "未知",
            },
            {
                "零件名称": "A-P-3",
                "规格": "PL6*100",
                "长度": 200,
                "工序": "下料",
                "形状分类": "方块",
                "备注": "冲突",
                "tekla_count": 1,
                "match_method": "partPositionConflict",
                "match_note": "Tekla PL8*120 conflicts Excel PL6*100",
                "prediction_status": "MATCH_CONFLICT",
                "predicted_process": "下料",
                "predicted_shape": "方块",
                "predicted_role": "未知",
            },
            {
                "零件名称": "A-P-4",
                "规格": "PL16*900",
                "长度": 10000,
                "工序": "下料折弯",
                "形状分类": "异形主材",
                "备注": "制造整板",
                "tekla_count": 0,
                "match_method": "missing",
                "match_note": "segmented wall candidates",
                "quality_issue_type_hint": "MANUFACTURING_MODEL_SCOPE_MISMATCH",
                "prediction_status": "DATA_MISSING",
                "predicted_process": "下料折弯",
                "predicted_shape": "异形主材",
                "predicted_role": "箱型柱主材壁板",
            },
        ]
        result = OfflinePipelineResult(
            member={"Classification": {"KeyDimensionsDisplay": "BH400*200*7*10", "Confidence": 0.92}},
            bundle={
                "assemblies": [
                    {
                        "assemblyId": "100",
                        "parts": [
                            {
                                "partId": "200",
                                "partPosition": "A-P-200",
                                "name": "PLATE",
                                "profileString": "PL8",
                                "runtimeType": "ContourPlate",
                                "isPlateLike": True,
                                "thickness": 8,
                                "obbDims": {"x": 300, "y": 120, "z": 8},
                            },
                            {
                                "partId": "300",
                                "partPosition": "A-P-3",
                                "name": "CONFLICT_PLATE",
                                "profileString": "PL8",
                                "runtimeType": "ContourPlate",
                                "isPlateLike": True,
                                "thickness": 8,
                                "obbDims": {"x": 700, "y": 260, "z": 8},
                            },
                            {
                                "partId": "301",
                                "partPosition": "A-P-301",
                                "name": "GEOMETRY_REVIEW_PLATE",
                                "profileString": "PL6",
                                "runtimeType": "ContourPlate",
                                "isPlateLike": True,
                                "thickness": 6,
                                "obbDims": {"x": 200, "y": 100, "z": 6},
                            },
                            {
                                "partId": "401",
                                "partPosition": "A-P-401",
                                "name": "COLUMN",
                                "profileString": "PL16*900",
                                "runtimeType": "ContourPlate",
                                "isPlateLike": True,
                                "thickness": 16,
                                "obbDims": {"x": 3000, "y": 900, "z": 16},
                            },
                            {
                                "partId": "402",
                                "partPosition": "A-P-402",
                                "name": "COLUMN",
                                "profileString": "PL16*900",
                                "runtimeType": "ContourPlate",
                                "isPlateLike": True,
                                "thickness": 16,
                                "obbDims": {"x": 3000, "y": 900, "z": 16},
                            },
                        ],
                    }
                ]
            },
            assembly={"assemblyId": "100", "mainPartId": "1", "parts": [{"partId": "1"}], "relationships": []},
            aligned_rows=aligned,
            quality_report=quality_report_from_aligned_rows(aligned),
            box_main_material_segment_groups=[
                BoxMainMaterialSegmentGroup(
                    assembly_id="100",
                    group_type="BOX_MAIN_MATERIAL_SEGMENT_GROUP",
                    face_id="FACE_A",
                    part_ids=["401", "402"],
                    part_positions=["A-P-401", "A-P-402"],
                    station_ranges="A-P-401:0.0-3000.0;A-P-402:3000.0-6000.0",
                    gap_summary="0.0",
                    continuity_level=SegmentContinuityLevel.CONTINUOUS,
                    evidence_codes=["BODY_FACE_GROUP", "AXIS_STATION_ORDER", "SEGMENT_ADJACENCY_EVIDENCE"],
                    confidence=0.95,
                )
            ],
            box_station_topology_diagnostics=[
                BoxStationTopologyDiagnostic(
                    assembly_id="100",
                    station=1500.0,
                    topology_status="CLOSED_WITH_CAVITY",
                    main_wall_loop_count=4,
                    usable_loop_count=4,
                    degenerate_loop_count=0,
                    union_geometry_type="MultiPolygon",
                    union_component_count=4,
                    inner_loop_count=1,
                    topology_area=120000.0,
                    topology_bounds="0.0;0.0;500.0;500.0",
                    evidence_codes=["EXPORTED_SECTION_LOOP_TOPOLOGY", "STATION_HAS_INNER_CAVITY_LOOP"],
                    station_scope="BODY_CORE",
                    trigger_part_summaries=[{"part_position": "A-P-trigger"}],
                    loop_summaries=[{"part_position": "A-P-401", "is_degenerate": False}],
                )
            ],
            box_part_spatial_relations=[
                BoxPartSpatialRelation(
                    assembly_id="100",
                    part_id="401",
                    part_position="A-P-401",
                    relation_to_box_body="MAIN_WALL",
                    station_range="0.0-3000.0",
                    section_relation="outer_wall_trace",
                    connected_main_wall_ids=[],
                    evidence_codes=["BOX_MAIN_WALL_CONFIRMED_SET"],
                    confidence=0.98,
                ),
                BoxPartSpatialRelation(
                    assembly_id="100",
                    part_id="10",
                    part_position="A-P-10",
                    relation_to_box_body="INSIDE_BODY",
                    station_range="100.0-200.0",
                    section_relation="inside_body",
                    connected_main_wall_ids=["401"],
                    evidence_codes=["SECTION_INSIDE_CAVITY_TRACE", "CONNECTED_TO_MAIN_WALL"],
                    confidence=0.86,
                ),
            ],
            h_beam_part_sides=[
                HBeamPartSide(
                    assembly_id="100",
                    part_id="20",
                    part_position="A-P-20",
                    part_name="吊耳",
                    h_side="TOP_FLANGE_OUTER",
                    confidence=0.92,
                    evidence_codes=["PROJECTED_CONTOUR_VOTE", "FLANGE_OUTER_V_BOUNDARY"],
                    evidence_summary={"vote_counts": "TOP_FLANGE_OUTER=6"},
                )
            ],
            spatial_classifications=[
                AppendageRoleClassification(
                    cluster_id="100:0",
                    role="Bracket",
                    confidence=0.94,
                    part_ids=["10", "11"],
                    evidence_codes=["ROOT_LOCAL_ATTACHMENT", "OVERHANG_DOMINANT"],
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_offline_analysis_report(result, Path(temp_dir), "A-GKZ-1")

            csv_rows = pd.read_csv(paths.csv_path)
            json_rows = json.loads(paths.json_path.read_text(encoding="utf-8"))
            spatial_csv_rows = pd.read_csv(paths.spatial_csv_path)
            spatial_json_rows = json.loads(paths.spatial_json_path.read_text(encoding="utf-8"))
            quality_csv_rows = pd.read_csv(paths.quality_csv_path)
            quality_json_rows = json.loads(paths.quality_json_path.read_text(encoding="utf-8"))
            quality_review_rows = json.loads(paths.quality_review_tasks_path.read_text(encoding="utf-8"))["tasks"]
            quality_review_csv_rows = pd.read_csv(paths.quality_review_tasks_csv_path)
            quality_review_summary_rows = json.loads(paths.quality_review_summary_path.read_text(encoding="utf-8"))
            quality_review_summary_csv_rows = pd.read_csv(paths.quality_review_summary_csv_path)
            missing_candidate_rows = json.loads(paths.missing_candidates_path.read_text(encoding="utf-8"))
            missing_candidate_csv_rows = pd.read_csv(paths.missing_candidates_csv_path)
            conflict_candidate_rows = json.loads(paths.conflict_candidates_path.read_text(encoding="utf-8"))
            conflict_candidate_csv_rows = pd.read_csv(paths.conflict_candidates_csv_path)
            manufacturing_scope_rows = json.loads(paths.manufacturing_scope_path.read_text(encoding="utf-8"))
            manufacturing_scope_csv_rows = pd.read_csv(paths.manufacturing_scope_csv_path)
            box_segment_rows = json.loads(paths.box_main_material_segments_path.read_text(encoding="utf-8"))
            box_relation_rows = json.loads(paths.box_part_spatial_relations_path.read_text(encoding="utf-8"))
            box_topology_rows = json.loads(paths.box_station_topology_diagnostics_path.read_text(encoding="utf-8"))
            h_side_rows = json.loads(paths.h_beam_part_sides_path.read_text(encoding="utf-8"))
            box_segment_csv_rows = pd.read_csv(paths.box_main_material_segments_csv_path)
            box_relation_csv_rows = pd.read_csv(paths.box_part_spatial_relations_csv_path)
            box_topology_csv_rows = pd.read_csv(paths.box_station_topology_diagnostics_csv_path)
            h_side_csv_rows = pd.read_csv(paths.h_beam_part_sides_csv_path)
            markdown = paths.markdown_path.read_text(encoding="utf-8")

        self.assertEqual("A-GKZ-1-alignment.csv", paths.csv_path.name)
        self.assertEqual("A-GKZ-1-alignment.json", paths.json_path.name)
        self.assertEqual("A-GKZ-1-spatial-classifications.csv", paths.spatial_csv_path.name)
        self.assertEqual("A-GKZ-1-spatial-classifications.json", paths.spatial_json_path.name)
        self.assertEqual("A-GKZ-1-quality-issues.csv", paths.quality_csv_path.name)
        self.assertEqual("A-GKZ-1-quality-issues.json", paths.quality_json_path.name)
        self.assertEqual("A-GKZ-1-quality-review-tasks.json", paths.quality_review_tasks_path.name)
        self.assertEqual("A-GKZ-1-quality-review-tasks.csv", paths.quality_review_tasks_csv_path.name)
        self.assertEqual("A-GKZ-1-quality-review-summary.json", paths.quality_review_summary_path.name)
        self.assertEqual("A-GKZ-1-quality-review-summary.csv", paths.quality_review_summary_csv_path.name)
        self.assertEqual("A-GKZ-1-missing-candidates.json", paths.missing_candidates_path.name)
        self.assertEqual("A-GKZ-1-missing-candidates.csv", paths.missing_candidates_csv_path.name)
        self.assertEqual("A-GKZ-1-conflict-candidates.json", paths.conflict_candidates_path.name)
        self.assertEqual("A-GKZ-1-conflict-candidates.csv", paths.conflict_candidates_csv_path.name)
        self.assertEqual("A-GKZ-1-manufacturing-scope-candidates.json", paths.manufacturing_scope_path.name)
        self.assertEqual("A-GKZ-1-manufacturing-scope-candidates.csv", paths.manufacturing_scope_csv_path.name)
        self.assertEqual("A-GKZ-1-box-main-material-segment-groups.json", paths.box_main_material_segments_path.name)
        self.assertEqual("A-GKZ-1-box-main-material-segment-groups.csv", paths.box_main_material_segments_csv_path.name)
        self.assertEqual("A-GKZ-1-box-part-spatial-relations.json", paths.box_part_spatial_relations_path.name)
        self.assertEqual("A-GKZ-1-box-part-spatial-relations.csv", paths.box_part_spatial_relations_csv_path.name)
        self.assertEqual("A-GKZ-1-box-station-topology-diagnostics.json", paths.box_station_topology_diagnostics_path.name)
        self.assertEqual("A-GKZ-1-box-station-topology-diagnostics.csv", paths.box_station_topology_diagnostics_csv_path.name)
        self.assertEqual("A-GKZ-1-h-beam-part-sides.json", paths.h_beam_part_sides_path.name)
        self.assertEqual("A-GKZ-1-h-beam-part-sides.csv", paths.h_beam_part_sides_csv_path.name)
        self.assertEqual("A-GKZ-1-analysis.md", paths.markdown_path.name)
        self.assertEqual(["A-P-1", "A-P-2", "A-P-3", "A-P-4"], list(csv_rows["零件名称"]))
        self.assertEqual("DATA_MISSING", json_rows[1]["prediction_status"])
        self.assertEqual(["100:0"], list(spatial_csv_rows["cluster_id"]))
        self.assertEqual("Bracket", spatial_json_rows[0]["role"])
        self.assertEqual("10;11", spatial_json_rows[0]["part_ids"])
        self.assertEqual(["10;11"], list(spatial_csv_rows["part_ids"]))
        self.assertEqual("ROOT_LOCAL_ATTACHMENT;OVERHANG_DOMINANT", spatial_json_rows[0]["evidence_codes"])
        self.assertEqual(["A-P-2", "A-P-3", "A-P-4"], list(quality_csv_rows["part_name"]))
        self.assertEqual("DATA_MISSING", quality_json_rows[0]["issue_type"])
        self.assertEqual("no partPosition candidate", quality_json_rows[0]["evidence"])
        self.assertEqual("A-GKZ-1:A-P-2:DATA_MISSING", quality_review_rows[0]["task_id"])
        self.assertEqual("全模型搜索候选零件并核对 Excel/模型编号", quality_review_rows[0]["recommended_action"])
        self.assertEqual(["A-P-2", "A-P-3", "A-P-4"], list(quality_review_csv_rows["part_name"]))
        self.assertEqual("DATA_MISSING", quality_review_csv_rows.iloc[0]["issue_type"])
        self.assertEqual("DATA_MISSING", quality_review_summary_rows[0]["issue_type"])
        self.assertEqual(1, quality_review_summary_rows[0]["task_count"])
        summary_by_issue = dict(zip(quality_review_summary_csv_rows["issue_type"], quality_review_summary_csv_rows["part_names"]))
        self.assertEqual("A-P-2", summary_by_issue["DATA_MISSING"])
        self.assertEqual("A-P-3", summary_by_issue["MATCH_CONFLICT"])
        self.assertEqual("A-P-4", summary_by_issue["MANUFACTURING_MODEL_SCOPE_MISMATCH"])
        self.assertEqual("A-GKZ-1:A-P-2:DATA_MISSING", missing_candidate_rows[0]["task_id"])
        self.assertEqual(1, missing_candidate_rows[0]["candidate_count"])
        self.assertEqual("200", missing_candidate_rows[0]["candidates"][0]["part_id"])
        self.assertEqual(["200"], list(missing_candidate_csv_rows["part_id"].astype(str)))
        self.assertEqual("A-GKZ-1:A-P-3:MATCH_CONFLICT", conflict_candidate_rows[0]["task_id"])
        self.assertEqual(1, conflict_candidate_rows[0]["conflict_count"])
        self.assertEqual("300", conflict_candidate_rows[0]["conflict_parts"][0]["part_id"])
        self.assertEqual(1, conflict_candidate_rows[0]["geometry_review_candidate_count"])
        self.assertEqual("301", conflict_candidate_rows[0]["geometry_review_candidates"][0]["part_id"])
        self.assertEqual(["conflict_part", "geometry_review_candidate"], list(conflict_candidate_csv_rows["candidate_kind"]))
        self.assertEqual("A-GKZ-1:A-P-4:MANUFACTURING_MODEL_SCOPE_MISMATCH", manufacturing_scope_rows[0]["task_id"])
        self.assertEqual(1, manufacturing_scope_rows[0]["candidate_count"])
        self.assertEqual(["401", "402"], list(manufacturing_scope_csv_rows["part_id"].astype(str)))
        self.assertEqual(["scope_segment", "scope_segment"], list(manufacturing_scope_csv_rows["candidate_kind"] ))
        self.assertEqual("BOX_MAIN_MATERIAL_SEGMENT_GROUP", box_segment_rows[0]["group_type"] )
        self.assertEqual("FACE_A", box_segment_rows[0]["face_id"] )
        self.assertEqual(["401", "402"], list(box_segment_csv_rows["part_id"].astype(str)))
        self.assertEqual(["CONTINUOUS", "CONTINUOUS"], list(box_segment_csv_rows["continuity_level"] ))
        self.assertEqual("MAIN_WALL", box_relation_rows[0]["relation_to_box_body"])
        self.assertEqual(["401", "10"], list(box_relation_csv_rows["part_id"].astype(str)))
        self.assertEqual(["MAIN_WALL", "INSIDE_BODY"], list(box_relation_csv_rows["relation_to_box_body"]))
        self.assertEqual("CLOSED_WITH_CAVITY", box_topology_rows[0]["topology_status"])
        self.assertEqual(["CLOSED_WITH_CAVITY"], list(box_topology_csv_rows["topology_status"]))
        self.assertEqual(["BODY_CORE"], list(box_topology_csv_rows["station_scope"]))
        self.assertEqual(["A-P-trigger"], list(box_topology_csv_rows["trigger_part_positions"]))
        self.assertIn("EXPORTED_SECTION_LOOP_TOPOLOGY", box_topology_rows[0]["evidence_codes"])
        self.assertEqual("TOP_FLANGE_OUTER", h_side_rows[0]["h_side"])
        self.assertEqual(["A-P-20"], list(h_side_csv_rows["part_position"]))
        self.assertEqual(["TOP_FLANGE_OUTER"], list(h_side_csv_rows["h_side"]))
        self.assertIn("# A-GKZ-1 加工识别对齐分析", markdown)
        self.assertIn("`MATCH`=1", markdown)
        self.assertIn("`DATA_MISSING`=2", markdown)
        self.assertIn("缺 Tekla 实体 `2` 行", markdown)
        self.assertIn("`A-P-2` `PL8*120` 长 `300`", markdown)
        self.assertIn("## 空间关系诊断", markdown)
        self.assertIn("`Bracket`=1", markdown)
        self.assertIn("`100:0`", markdown)
        self.assertIn("零件 `10;11`", markdown)
        self.assertIn("`0.94`", markdown)
        self.assertIn("ROOT_LOCAL_ATTACHMENT;OVERHANG_DOMINANT", markdown)
        self.assertIn("Quality Issues CSV", markdown)
        self.assertIn("Quality Issues JSON", markdown)
        self.assertIn("Quality Review Tasks JSON", markdown)
        self.assertIn("Quality Review Tasks CSV", markdown)
        self.assertIn("Quality Review Summary JSON", markdown)
        self.assertIn("Quality Review Summary CSV", markdown)
        self.assertIn("Missing Candidates JSON", markdown)
        self.assertIn("Missing Candidates CSV", markdown)
        self.assertIn("Conflict Candidates JSON", markdown)
        self.assertIn("Conflict Candidates CSV", markdown)
        self.assertIn("Manufacturing Scope Candidates JSON", markdown)
        self.assertIn("Manufacturing Scope Candidates CSV", markdown)
        self.assertIn("BOX Main Material Segment Groups JSON", markdown)
        self.assertIn("BOX Main Material Segment Groups CSV", markdown)
        self.assertIn("## BOX 内外关系", markdown)
        self.assertIn("`MAIN_WALL`=1", markdown)
        self.assertIn("`INSIDE_BODY`=1", markdown)
        self.assertIn("BOX Part Spatial Relations JSON", markdown)
        self.assertIn("BOX Part Spatial Relations CSV", markdown)
        self.assertIn("## BOX Station Topology 诊断", markdown)
        self.assertIn("`CLOSED_WITH_CAVITY`=1", markdown)
        self.assertIn("BOX Station Topology Diagnostics JSON", markdown)
        self.assertIn("BOX Station Topology Diagnostics CSV", markdown)
        self.assertIn("## H 钢零件侧面", markdown)
        self.assertIn("`TOP_FLANGE_OUTER`=1", markdown)
        self.assertIn("H Beam Part Sides JSON", markdown)
        self.assertIn("H Beam Part Sides CSV", markdown)


if __name__ == "__main__":
    unittest.main()
