import unittest

from zijinhua_tekla.geom.plate_cuts import classify_plate_boolean_cuts, rectangle_from_obb
from zijinhua_tekla.geom.shop import classify_shop_process


class PlateCutsTests(unittest.TestCase):
    def test_obb_rebuilds_in_plane_rectangle(self):
        ring = rectangle_from_obb((680.0, 90.0, 16.0), 16.0)
        self.assertEqual(4, len(ring))
        xs = {point[0] for point in ring}
        ys = {point[1] for point in ring}
        self.assertEqual({0.0, 680.0}, xs)
        self.assertEqual({0.0, 90.0}, ys)

    def test_neighbor_cut_is_foreign(self):
        roles = classify_plate_boolean_cuts(
            part_box={
                "min": {"x": 18600.0, "y": 280.0, "z": 35730.0},
                "max": {"x": 18967.0, "y": 620.0, "z": 35750.0},
            },
            thickness=20.0,
            cuts=[
                {
                    "operativePartId": 1,
                    "boundingBox": {
                        "min": {"x": 18947.0, "y": 100.0, "z": 35665.0},
                        "max": {"x": 19030.0, "y": 800.0, "z": 35755.0},
                    },
                }
            ],
        )
        self.assertEqual(0, roles.opening_count)
        self.assertEqual(0, roles.chamfer_count)
        self.assertEqual(1, roles.foreign_count)

    def test_interior_through_cut_is_opening(self):
        roles = classify_plate_boolean_cuts(
            part_box={
                "min": {"x": 10633.0, "y": 458.0, "z": 34994.0},
                "max": {"x": 11157.0, "y": 470.0, "z": 35516.0},
            },
            thickness=12.0,
            cuts=[
                {
                    "operativePartId": 2,
                    "boundingBox": {
                        "min": {"x": 10733.0, "y": 439.0, "z": 35094.0},
                        "max": {"x": 11057.0, "y": 489.0, "z": 35416.0},
                    },
                }
            ],
        )
        self.assertEqual(1, roles.opening_count)
        self.assertEqual(0, roles.chamfer_count)

    def test_long_stick_through_thickness_is_opening(self):
        roles = classify_plate_boolean_cuts(
            part_box={
                "min": {"x": 18967.0, "y": 54100.0, "z": 26585.0},
                "max": {"x": 19935.0, "y": 54116.0, "z": 29750.0},
            },
            thickness=16.0,
            cuts=[
                {
                    "operativePartId": 3,
                    "boundingBox": {
                        "min": {"x": 19538.0, "y": 53567.0, "z": 26872.0},
                        "max": {"x": 19563.0, "y": 55567.0, "z": 26897.0},
                    },
                }
            ],
        )
        self.assertEqual(1, roles.opening_count)
        self.assertEqual(0, roles.foreign_count)

    def test_corner_clip_is_chamfer(self):
        roles = classify_plate_boolean_cuts(
            part_box={
                "min": {"x": 19012.0, "y": 54592.0, "z": 30912.0},
                "max": {"x": 19229.0, "y": 54608.0, "z": 31268.0},
            },
            thickness=16.0,
            cuts=[
                {
                    "operativePartId": 4,
                    "boundingBox": {
                        "min": {"x": 19006.0, "y": 54589.0, "z": 30912.0},
                        "max": {"x": 19071.0, "y": 54611.0, "z": 30952.0},
                    },
                }
            ],
        )
        self.assertEqual(1, roles.chamfer_count)
        self.assertEqual(0, roles.opening_count)

    def test_bevel_operative_is_skipped(self):
        roles = classify_plate_boolean_cuts(
            part_box={
                "min": {"x": 18690.0, "y": 458.0, "z": 34835.0},
                "max": {"x": 19000.0, "y": 472.0, "z": 35675.0},
            },
            thickness=14.0,
            cuts=[
                {
                    "operativePartId": 5,
                    "boundingBox": {
                        "min": {"x": 18986.0, "y": 460.0, "z": 34680.0},
                        "max": {"x": 19000.0, "y": 474.0, "z": 35830.0},
                    },
                }
            ],
            bevel_operative_ids={5},
        )
        self.assertEqual(0, roles.opening_count)
        self.assertEqual(0, roles.chamfer_count)
        self.assertEqual(0, roles.foreign_count)

    def test_plate_blanking_with_hole_uses_opening_evidence(self):
        result = classify_shop_process(
            profile="PL14*243",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=14,
            obb_dims=(281, 243, 14),
            bolt_hole_count=1,
            hole_like_feature_count=1,
        )
        self.assertEqual("工序1：下料；工序2：下料钻孔", result.combined)
        self.assertIn("螺栓孔", result.evidence)


if __name__ == "__main__":
    unittest.main()
