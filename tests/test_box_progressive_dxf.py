import io
import unittest

import ezdxf

from zijinhua_tekla.reports.box_progressive_dxf import build_box_assembly_drawing_steps_dxf


class BoxProgressiveDxfTests(unittest.TestCase):
    def test_renders_cumulative_process_state_with_part_marks_dimension_chain_welds_and_bom(self):
        payload = {
            "assembly_id": "100",
            "member_id": "A-GKZ-1",
            "parts": [
                {
                    "part_id": "base",
                    "part_position": "A-P-base",
                    "profile": "PL20*500",
                    "name": "基准主板",
                    "material": "Q355B",
                    "station_start": 0.0,
                    "station_end": 3000.0,
                    "welds": [{"text": "全熔透"}],
                },
                {
                    "part_id": "side",
                    "part_position": "A-P-side",
                    "profile": "PL16*500",
                    "name": "侧壁板",
                    "material": "Q355B",
                    "station_start": 0.0,
                    "station_end": 3000.0,
                    "welds": [{"size": 6}],
                },
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "基准主板",
                    "station_range": "0.0-3000.0",
                    "new_part_ids": ["base"],
                    "visible_part_ids": ["base"],
                    "part_mark_targets": [
                        {
                            "part_id": "base",
                            "part_position": "A-P-base",
                            "profile": "PL20*500",
                            "name": "基准主板",
                        }
                    ],
                    "dimension_targets": [
                        {
                            "kind": "station_range",
                            "label": "基准主板 station 范围",
                        }
                    ],
                },
                {
                    "step_no": 2,
                    "step_type": "ADD_SIDE_WALLS",
                    "title": "增加侧壁板形成开口截面",
                    "station_range": "0.0-3000.0",
                    "new_part_ids": ["side"],
                    "visible_part_ids": ["base", "side"],
                    "part_mark_targets": [
                        {
                            "part_id": "side",
                            "part_position": "A-P-side",
                            "profile": "PL16*500",
                            "name": "侧壁板",
                        }
                    ],
                    "dimension_targets": [
                        {
                            "kind": "section_offset_to_base_wall",
                            "label": "侧壁相对基准主板定位",
                        }
                    ],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("SECTION", dxf)
        self.assertIn("TABLES", dxf)
        self.assertIn("BLOCKS", dxf)
        self.assertIn("AcDbLine", dxf)
        self.assertIn("AcDbText", dxf)
        self.assertIn("$ACADVER", dxf)
        self.assertIn("AC1021", dxf)
        self.assertIn("$DWGCODEPAGE", dxf)
        self.assertIn("ANSI_1252", dxf)
        self.assertIn("A-GKZ-1 BOX 工序图", dxf)
        self.assertIn("DrawingSheet", dxf)
        self.assertIn("Part", dxf)
        self.assertIn("Z-DIMENSIONS", dxf)
        self.assertIn("PartMark", dxf)
        self.assertIn("文本", dxf)
        self.assertIn("OVERALL 3000", dxf)
        self.assertIn("STEP 2 ADD_SIDE_WALLS", dxf)
        self.assertIn("STEP 1 BASE_MAIN_WALL", dxf)
        self.assertEqual(2, dxf.count("BOX PROCESS DRAWING"))
        self.assertIn("CONTINUOUS HEIGHT CHAIN", dxf)
        self.assertIn("A-P-base / PL20*500", dxf)
        self.assertIn("A-P-side / PL16*500", dxf)
        self.assertIn("角焊缝 6mm", dxf)
        self.assertIn("BOM STEP 2 CUMULATIVE PARTS 2", dxf)
        step_2_region = dxf[dxf.index("STEP 2 ADD_SIDE_WALLS") :]
        self.assertIn("A-P-base", step_2_region)
        self.assertIn("A-P-side", step_2_region)
        self.assertTrue(_dxf_has_colored_text(dxf, "3000", "Z-DIMENSIONS", 1))
        self.assertIn("零件号", dxf)
        self.assertIn("数量", dxf)
        self.assertIn("侧壁相对基准主板定位", dxf)
        self.assertNotIn("SECTION VIEW: NOT REQUIRED IN THIS PASS", dxf)
        self.assertNotIn("BOX progressive drawing steps", dxf)

    def test_prioritizes_new_part_marks_when_cumulative_list_is_long(self):
        old_parts = [
            {
                "part_id": f"old-{index}",
                "part_position": f"A-P-{index:02d}",
                "profile": "PL8",
                "name": "旧零件",
                "station_start": float(index * 100),
                "station_end": float(index * 100 + 50),
            }
            for index in range(13)
        ]
        payload = {
            "assembly_id": "100",
            "member_id": "A-GKZ-1",
            "parts": old_parts
            + [
                {
                    "part_id": "new-late",
                    "part_position": "Z-P-new",
                    "profile": "PL1",
                    "name": "后续新增零件",
                    "station_start": 1600.0,
                    "station_end": 1700.0,
                }
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "旧累计",
                    "station_range": "0.0-1500.0",
                    "new_part_ids": [part["part_id"] for part in old_parts],
                    "visible_part_ids": [part["part_id"] for part in old_parts],
                },
                {
                    "step_no": 2,
                    "step_type": "ADD_INTERNAL_GROUP",
                    "title": "后续新增",
                    "station_range": "1600.0-1700.0",
                    "new_part_ids": ["new-late"],
                    "visible_part_ids": [part["part_id"] for part in old_parts] + ["new-late"],
                },
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        step_2_region = dxf[dxf.index("STEP 2 ADD_INTERNAL_GROUP") :]
        self.assertIn("Z-P-new / PL1", step_2_region)

    def test_renders_external_cluster_as_local_detail_with_bolts_and_weld_text(self):
        payload = {
            "assembly_id": "100",
            "member_id": "A-GKZ-1",
            "parts": [
                {
                    "part_id": "bracket",
                    "part_position": "A-PR-1",
                    "profile": "PL20",
                    "name": "牛腿连接板",
                    "material": "Q355B",
                    "station_start": 1200.0,
                    "station_end": 1450.0,
                    "requires_detail": True,
                    "bolt_hole_count": 2,
                    "bolt_diameter": 25,
                    "welds": [{"size": 8}],
                }
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "ADD_EXTERNAL_CLUSTER",
                    "title": "增加外部零件簇 100:1",
                    "station_range": "1200.0-1450.0",
                    "new_part_ids": ["bracket"],
                    "visible_part_ids": ["bracket"],
                    "part_mark_targets": [
                        {
                            "part_id": "bracket",
                            "part_position": "A-PR-1",
                            "profile": "PL20",
                            "name": "牛腿连接板",
                        }
                    ],
                    "dimension_targets": [{"kind": "appendage_cluster_root_station", "label": "外部簇根部 station 定位"}],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("LOCAL DETAIL", dxf)
        self.assertIn("Bolt", dxf)
        self.assertIn("BoltMark", dxf)
        self.assertIn("2Φ25", dxf)
        self.assertIn("A-PR-1 / PL20", dxf)
        self.assertIn("角焊缝 8mm", dxf)

    def test_renders_fixture_and_flip_notes_from_step_summary(self):
        payload = {
            "assembly_id": "100",
            "member_id": "A-GKZ-1",
            "parts": [
                {
                    "part_id": "base",
                    "part_position": "A-P-base",
                    "profile": "PL20*500",
                    "name": "基准主板",
                    "station_start": 0.0,
                    "station_end": 3000.0,
                },
                {
                    "part_id": "ext",
                    "part_position": "A-P-ext",
                    "profile": "PL12*180",
                    "name": "侧焊连接板",
                    "station_start": 1200.0,
                    "station_end": 1320.0,
                },
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "胎架基准主板",
                    "station_range": "0.0-3000.0",
                    "new_part_ids": ["base"],
                    "visible_part_ids": ["base"],
                    "evidence_summary": {"fixture_face": "FACE_BOTTOM", "fixture_role": "fixture_base"},
                },
                {
                    "step_no": 2,
                    "step_type": "ADD_EXTERNAL_CLUSTER",
                    "title": "翻面至 FACE_A 朝上，侧焊 FACE_B",
                    "station_range": "1200.0-1320.0",
                    "new_part_ids": ["ext"],
                    "visible_part_ids": ["base", "ext"],
                    "evidence_summary": {"up_face": "FACE_A", "side_work_faces": "FACE_B", "flip_from_previous": "90"},
                },
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("FIXTURE FACE_BOTTOM", dxf)
        self.assertIn("UP FACE FACE_A", dxf)
        self.assertIn("SIDE WELD FACE_B", dxf)
        self.assertIn("FLIP 90", dxf)

    def test_renders_true_projection_edges_instead_of_lane_rectangles(self):
        payload = {
            "assembly_id": "100",
            "member_id": "A-GKZ-1",
            "parts": [
                {
                    "part_id": "skew",
                    "part_position": "A-P-skew",
                    "profile": "PL20",
                    "name": "真实斜边板",
                    "station_start": 0.0,
                    "station_end": 1000.0,
                    "projectionEdges": [
                        {"start": {"x": 0.0, "y": 0.0}, "end": {"x": 100.0, "y": 1000.0}},
                        {"start": {"x": 100.0, "y": 1000.0}, "end": {"x": 220.0, "y": 1000.0}},
                    ],
                }
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "真实投影",
                    "station_range": "0.0-1000.0",
                    "new_part_ids": ["skew"],
                    "visible_part_ids": ["skew"],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertTrue(_has_diagonal_part_line(dxf))

    def test_renders_projection_arcs_with_radius_annotation(self):
        payload = {
            "assembly_id": "100",
            "member_id": "ARC-GZ-1",
            "parts": [
                {
                    "part_id": "arc",
                    "part_position": "A-P-arc",
                    "profile": "PL20",
                    "name": "弧形板",
                    "station_start": 0.0,
                    "station_end": 1000.0,
                    "projectionArcs": [
                        {
                            "center": {"x": 500.0, "y": 500.0},
                            "radius": 500.0,
                            "start_angle": 0.0,
                            "end_angle": 90.0,
                        }
                    ],
                }
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "弧形真实投影",
                    "station_range": "0.0-1000.0",
                    "new_part_ids": ["arc"],
                    "visible_part_ids": ["arc"],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("ARC", dxf)
        self.assertIn("R500", dxf)

    def test_renders_small_bend_as_true_rotated_projection_with_section_marker(self):
        payload = {
            "assembly_id": "100",
            "member_id": "BEND-GZ-1",
            "segments": [
                {"segment_id": "lower", "station_start": 0.0, "station_end": 1000.0, "angle_deg": 0.0},
                {"segment_id": "upper", "station_start": 1000.0, "station_end": 1800.0, "angle_deg": 8.0},
            ],
            "bend_joints": [
                {"station": 1000.0, "label": "B-B", "bend_angle_deg": 8.0},
            ],
            "parts": [
                {
                    "part_id": "wall",
                    "part_position": "B-P-1",
                    "profile": "PL20*500",
                    "name": "折弯段壁板",
                    "station_start": 0.0,
                    "station_end": 1800.0,
                }
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "折弯柱真实投影",
                    "station_range": "0.0-1800.0",
                    "new_part_ids": ["wall"],
                    "visible_part_ids": ["wall"],
                    "part_mark_targets": [
                        {
                            "part_id": "wall",
                            "part_position": "B-P-1",
                            "profile": "PL20*500",
                            "name": "折弯段壁板",
                        }
                    ],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("BEND STRATEGY single_view_true_rotation", dxf)
        self.assertIn("BEND 8°", dxf)
        self.assertIn("B-B", dxf)
        self.assertIn("全部通高 1800", dxf)
        self.assertIn("DETAIL CHAIN", dxf)
        self.assertNotIn("偏转角", dxf)
        self.assertNotIn("BREAK SYMBOL", dxf)

    def test_infers_small_bend_joint_from_adjacent_axis_segments(self):
        payload = {
            "assembly_id": "100",
            "member_id": "BEND-GZ-1",
            "segments": [
                {"segment_id": "lower", "station_start": 0.0, "station_end": 1000.0, "angle_deg": 0.0},
                {"segment_id": "upper", "station_start": 1000.0, "station_end": 1800.0, "angle_deg": 8.0},
            ],
            "parts": [
                {
                    "part_id": "wall",
                    "part_position": "B-P-1",
                    "profile": "PL20*500",
                    "name": "折弯段壁板",
                    "station_start": 0.0,
                    "station_end": 1800.0,
                }
            ],
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "折弯柱真实投影",
                    "station_range": "0.0-1800.0",
                    "new_part_ids": ["wall"],
                    "visible_part_ids": ["wall"],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("BEND STRATEGY single_view_true_rotation", dxf)
        self.assertIn("BEND 8°", dxf)
        self.assertIn("B-B", dxf)
        self.assertNotIn("偏转角", dxf)
        self.assertNotIn("BREAK SYMBOL", dxf)

    def test_can_render_annotation_layout_items_into_dxf(self):
        from zijinhua_tekla.reports.annotation_layout import (
            AnnotationKind,
            AnnotationLayout,
            LayoutLine,
            LayoutStatus,
            LayoutText,
            Rect,
        )
        from zijinhua_tekla.reports.box_progressive_dxf import _DxfWriter, _draw_annotation_layout

        layout = AnnotationLayout(
            status=LayoutStatus.OK,
            lines=[
                LayoutLine(
                    id="line-overall-length",
                    intent_id="overall-length",
                    annotation_kind=AnnotationKind.OVERALL_DIMENSION,
                    x1=10.0,
                    y1=20.0,
                    x2=100.0,
                    y2=20.0,
                    role="DIMENSION",
                ),
                LayoutLine(
                    id="line-part-mark-leader",
                    intent_id="part-mark",
                    annotation_kind=AnnotationKind.PART_MARK,
                    x1=35.0,
                    y1=45.0,
                    x2=50.0,
                    y2=52.0,
                    role="LEADER",
                ),
            ],
            texts=[
                LayoutText(
                    id="text-overall-length",
                    intent_id="overall-length",
                    annotation_kind=AnnotationKind.OVERALL_DIMENSION,
                    text="3505",
                    x=57.0,
                    y=25.0,
                    box=Rect(50.0, 23.5, 64.0, 31.0),
                    height=2.6,
                    align="center",
                ),
                LayoutText(
                    id="text-part-mark",
                    intent_id="part-mark",
                    annotation_kind=AnnotationKind.PART_MARK,
                    text="10-3Z-128",
                    x=54.0,
                    y=54.0,
                    box=Rect(54.0, 52.5, 75.0, 60.0),
                    height=2.6,
                ),
                LayoutText(
                    id="text-fixture-note",
                    intent_id="fixture-note",
                    annotation_kind=AnnotationKind.FIXTURE_NOTE,
                    text="胎架面",
                    x=15.0,
                    y=70.0,
                    box=Rect(15.0, 68.5, 35.0, 76.0),
                    height=2.6,
                ),
            ],
            unplaced_items=[],
            collision_count=0,
            debug_boxes=[],
        )
        writer = _DxfWriter()
        writer.start()
        _draw_annotation_layout(writer, layout)
        writer.finish()

        doc = ezdxf.read(io.StringIO(writer.content()))
        modelspace = doc.modelspace()

        dimension_lines = [entity for entity in modelspace.query("LINE") if entity.dxf.layer == "Z-DIMENSIONS"]
        dimension_texts = [
            entity
            for entity in modelspace.query("TEXT")
            if entity.dxf.layer == "Z-DIMENSIONS" and entity.dxf.text == "3505"
        ]
        part_mark_entities = [entity for entity in modelspace if entity.dxf.layer == "PartMark"]
        note_texts = [
            entity
            for entity in modelspace.query("TEXT")
            if entity.dxf.layer == "文本" and entity.dxf.text == "胎架面"
        ]

        self.assertTrue(dimension_lines)
        self.assertTrue(dimension_texts)
        self.assertAlmostEqual(50.0, dimension_texts[0].dxf.insert.x)
        self.assertTrue(part_mark_entities)
        self.assertTrue(note_texts)


def _has_diagonal_part_line(dxf: str) -> bool:
    doc = ezdxf.read(io.StringIO(dxf))
    for entity in doc.modelspace().query("LINE[layer=='Part']"):
        start = entity.dxf.start
        end = entity.dxf.end
        if abs(start.x - end.x) > 0.01 and abs(start.y - end.y) > 0.01:
            return True
    return False


def _dxf_has_colored_text(dxf: str, value: str, layer: str, color: int) -> bool:
    doc = ezdxf.read(io.StringIO(dxf))
    for entity in doc.modelspace().query("TEXT"):
        if entity.dxf.layer == layer and entity.dxf.color == color and entity.dxf.text == value:
            return True
    return False


if __name__ == "__main__":
    unittest.main()
