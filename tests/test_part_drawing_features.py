import unittest
from dataclasses import replace
from pathlib import Path

from zijinhua_tekla.part_drawing.contracts import ContourSegmentSnapshot, HoleSnapshot, Point3D
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingFeatureTests(unittest.TestCase):
    def setUp(self):
        self.base = load_part_snapshot(FIXTURE)

    def recognize(self, snapshot):
        analysis = analyze_plate_geometry(snapshot)
        self.assertIsNotNone(analysis.geometry, analysis.issues)
        return recognize_plate_features(snapshot, analysis.geometry)

    def round_hole(self, hole_id, x, y):
        return HoleSnapshot(hole_id, "ROUND", Point3D(x, y, 30.0), diameter=22.0)

    def line_loop(self, points):
        values = [Point3D(x, y, 30.0) for x, y in points]
        return tuple(ContourSegmentSnapshot("LINE", start, end) for start, end in zip(values, values[1:] + values[:1]))

    def arc_loop(self, centers_equal=True):
        points = [Point3D(90, 70, 30), Point3D(110, 90, 30), Point3D(130, 70, 30), Point3D(110, 50, 30)]
        center = Point3D(110, 70, 30)
        return tuple(
            ContourSegmentSnapshot(
                "ARC", points[index], points[(index + 1) % 4],
                center=center if centers_equal or index != 2 else Point3D(111, 70, 30),
                clockwise=True,
            )
            for index in range(4)
        )

    def test_recognizes_explicit_round_hole_and_slot(self):
        snapshot = replace(self.base, holes=(
            self.round_hole("H1", 60, 70),
            HoleSnapshot("S1", "SLOT", Point3D(150, 70, 30), length=40, width=18),
        ))
        result = self.recognize(snapshot)
        self.assertEqual(["ROUND_HOLE", "SLOT"], [item.feature_type.value for item in result.features])

    def test_groups_equal_round_holes_on_one_axis(self):
        snapshot = replace(self.base, holes=tuple(self.round_hole(f"H{i}", x, 70) for i, x in enumerate((60, 110, 160), 1)))
        result = self.recognize(snapshot)
        group = next(item for item in result.features if item.feature_type.value == "HOLE_GROUP")
        self.assertEqual(3, group.parameters["count"])
        self.assertEqual(50.0, group.parameters["spacing"])

    def test_recognizes_polygon_cutout(self):
        loop = self.line_loop(((80, 55), (120, 55), (120, 85), (80, 85)))
        result = self.recognize(replace(self.base, inner_loops=(loop,)))
        self.assertIn("POLYGON_CUTOUT", [item.feature_type.value for item in result.features])

    def test_recognizes_chamfer_and_notch_without_inferring_bevel(self):
        chamfer = self.line_loop(((10, 20), (190, 20), (210, 40), (210, 120), (10, 120)))
        notch = self.line_loop(((10, 20), (90, 20), (90, 40), (130, 40), (130, 20), (210, 20), (210, 120), (10, 120)))
        types = [item.feature_type.value for item in self.recognize(replace(self.base, outer_loop=chamfer)).features]
        notch_types = [item.feature_type.value for item in self.recognize(replace(self.base, outer_loop=notch)).features]
        self.assertIn("CHAMFER", types)
        self.assertIn("NOTCH", notch_types)
        self.assertNotIn("BEVEL", types + notch_types)

    def test_recognizes_consistent_arc_cutout_and_reviews_ambiguous_arc(self):
        valid = self.recognize(replace(self.base, inner_loops=(self.arc_loop(),)))
        ambiguous = self.recognize(replace(self.base, inner_loops=(self.arc_loop(False),)))
        self.assertIn("ARC_CUTOUT", [item.feature_type.value for item in valid.features])
        self.assertEqual("REVIEW_REQUIRED", ambiguous.status.value)


if __name__ == "__main__":
    unittest.main()
