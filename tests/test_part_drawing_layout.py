import unittest
from dataclasses import replace
from pathlib import Path

from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.dimension_optimizer import optimize_dimension_layout
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

    def test_dense_intents_request_review_instead_of_overlap(self):
        dense = tuple(replace(self.intents[0], intent_id=f"dense-{index}", text=str(index)) for index in range(80))
        layout = optimize_dimension_layout(self.snapshot, self.geometry, dense, quantity=1)
        self.assertEqual("REVIEW_REQUIRED", layout.status.value)
        self.assertGreater(len(layout.unplaced_intents), 0)


if __name__ == "__main__":
    unittest.main()
