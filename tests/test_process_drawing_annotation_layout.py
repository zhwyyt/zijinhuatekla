import unittest

from zijinhua_tekla.reports.annotation_layout import (
    AnnotationKind,
    LayoutStatus,
    PartAnchor,
    ProjectionScene,
    Rect,
    build_u_stage_annotation_intents,
    layout_annotation_intents,
    layout_to_jsonable,
)


class ProcessDrawingAnnotationLayoutTests(unittest.TestCase):
    def _u_stage_scene(self) -> ProjectionScene:
        return ProjectionScene(
            view_id="main",
            drawing_bounds=Rect(0.0, 0.0, 599.0, 420.0),
            main_view_bounds=Rect(35.0, 80.0, 535.0, 165.6),
            model_length=3505.0,
            model_width=600.0,
            model_thickness=30.0,
            source_part_id="28705233",
            source_part_position="10-3Z-128",
            source_profile="BOX600*600*30*30",
            source_name="GKZ60-2",
            fixture_face="MODEL_AXIS_2_HEIGHT_1_MIN_ON_FIXTURE",
            anchors={
                "source_part": PartAnchor(
                    part_id="28705233",
                    x=285.0,
                    y=122.8,
                    label="10-3Z-128 / BOX600*600*30*30 / GKZ60-2",
                )
            },
        )

    def test_builds_u_stage_annotation_intents(self):
        scene = self._u_stage_scene()
        intents = build_u_stage_annotation_intents(scene)
        by_kind = {intent.kind for intent in intents}
        self.assertIn(AnnotationKind.OVERALL_DIMENSION, by_kind)
        self.assertIn(AnnotationKind.SECTION_DIMENSION, by_kind)
        self.assertIn(AnnotationKind.THICKNESS_CALLOUT, by_kind)
        self.assertIn(AnnotationKind.PART_MARK, by_kind)
        self.assertIn(AnnotationKind.FIXTURE_NOTE, by_kind)
        self.assertIn(AnnotationKind.STAGE_NOTE, by_kind)
        self.assertIn("3505", [intent.text for intent in intents])
        self.assertIn("600", [intent.text for intent in intents])
        self.assertIn("t=30", [intent.text for intent in intents])
        self.assertTrue(any("10-3Z-128" in intent.text for intent in intents))
        self.assertTrue(any("虚拟U形组立" in intent.text for intent in intents))

    def test_layout_u_stage_annotations_without_collisions(self):
        scene = self._u_stage_scene()
        layout = layout_annotation_intents(scene, build_u_stage_annotation_intents(scene))
        self.assertEqual(LayoutStatus.OK, layout.status)
        self.assertEqual(0, layout.collision_count)
        self.assertFalse(layout.unplaced_items)
        self.assertGreaterEqual(len(layout.lines), 10)
        self.assertGreaterEqual(len(layout.texts), 6)
        for text in layout.texts:
            self.assertFalse(text.box.intersects(scene.main_view_bounds), text.text)

    def test_dense_part_marks_request_detail_view_instead_of_overlapping(self):
        scene = self._u_stage_scene()
        intents = build_u_stage_annotation_intents(scene)
        part_mark = [item for item in intents if item.kind == AnnotationKind.PART_MARK][0]
        for index in range(12):
            intents.append(part_mark.copy_with(id=f"part-mark-extra-{index}", text=f"10-3Z-X{index:02d} / PL10*90 / 连接板", priority=50 - index))
        layout = layout_annotation_intents(scene, intents)
        self.assertEqual(LayoutStatus.NEEDS_DETAIL_VIEW, layout.status)
        self.assertGreater(len(layout.unplaced_items), 0)

    def test_layout_serializes_to_jsonable_contract(self):
        scene = self._u_stage_scene()
        layout = layout_annotation_intents(scene, build_u_stage_annotation_intents(scene))
        data = layout_to_jsonable(layout)
        self.assertEqual("OK", data["layout_status"])
        self.assertEqual(0, data["collision_count"])
        self.assertTrue(any(item["kind"] == "TEXT" for item in data["placed_items"]))
        self.assertTrue(any(item["kind"] == "LINE" for item in data["placed_items"]))


if __name__ == "__main__":
    unittest.main()
