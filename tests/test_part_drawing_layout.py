import unittest
from dataclasses import replace
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.dimension_optimizer import optimize_dimension_layout
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingLayoutTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_part_snapshot(FIXTURE)
        self.geometry = analyze_plate_geometry(self.snapshot).geometry
        self.intents = generate_dimension_intents(self.snapshot, self.geometry, ()).intents

    def test_places_rectangle_dimensions_without_collision(self):
        layout = optimize_dimension_layout(self.snapshot, self.geometry, self.intents, quantity=2)
        self.assertEqual("OK", layout.status.value)
        self.assertEqual(0, layout.collision_count)
        self.assertFalse(layout.unplaced_intents)
        self.assertIn(layout.scale, (1.0, 0.5, 0.2, 0.1, 0.05))

    def test_places_rectangle_dimensions_as_semantic_linear_dimensions(self):
        layout = optimize_dimension_layout(self.snapshot, self.geometry, self.intents, quantity=2)
        by_id = {item.dimension_id: item for item in layout.placed_dimensions}
        self.assertEqual("LINEAR_HORIZONTAL", by_id["overall-x"].kind.value)
        self.assertEqual("LINEAR_VERTICAL", by_id["overall-y"].kind.value)
        self.assertEqual(200.0, by_id["overall-x"].measured_value_mm)
        self.assertEqual(100.0, by_id["overall-y"].measured_value_mm)
        self.assertEqual(2, len(by_id["overall-x"].source_points))
        self.assertNotEqual(
            by_id["overall-x"].source_points[0],
            by_id["overall-x"].source_points[1],
        )

    def test_places_hole_diameter_as_semantic_diameter_dimension(self):
        snapshot = replace(
            self.snapshot,
            holes=(HoleSnapshot("H1", "ROUND", Point3D(60, 70, 30), diameter=22),),
        )
        geometry = analyze_plate_geometry(snapshot).geometry
        features = recognize_plate_features(snapshot, geometry).features
        intents = generate_dimension_intents(snapshot, geometry, features).intents
        layout = optimize_dimension_layout(snapshot, geometry, intents, quantity=1)
        diameter = next(
            item for item in layout.placed_dimensions if item.dimension_id == "hole-H1-dia"
        )
        self.assertEqual("DIAMETER", diameter.kind.value)
        self.assertEqual(22.0, diameter.measured_value_mm)
        self.assertEqual(11.0 * layout.scale, diameter.paper_radius)

    def test_dense_intents_request_review_instead_of_overlap(self):
        dense = tuple(replace(self.intents[0], intent_id=f"dense-{index}", text=str(index)) for index in range(80))
        layout = optimize_dimension_layout(self.snapshot, self.geometry, dense, quantity=1)
        self.assertEqual("REVIEW_REQUIRED", layout.status.value)
        self.assertGreater(len(layout.unplaced_intents), 0)
        self.assertLessEqual(len(layout.placed_dimensions) + len(layout.annotation_texts), 26)


if __name__ == "__main__":
    unittest.main()
