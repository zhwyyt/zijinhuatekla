import unittest

from zijinhua_tekla.geom.chamfer import classify_plan_outline
from zijinhua_tekla.geom.shop import classify_shop_shape


class ChamferPlanarTests(unittest.TestCase):
    def test_line_chamfer_on_rectangle_is_planar_chamfer(self):
        kind, evidence = classify_plan_outline(
            ((0, 0), (400, 0), (400, 200), (0, 200)),
            (
                ("CHAMFER_LINE", 20, 20),
                ("CHAMFER_LINE", 20, 20),
                ("CHAMFER_LINE", 20, 20),
                ("CHAMFER_LINE", 20, 20),
            ),
        )
        self.assertEqual("CHAMFERED", kind)
        self.assertIn("平面倒角", evidence)

    def test_zero_size_line_chamfer_stays_rectangle(self):
        kind, _ = classify_plan_outline(
            ((0, 0), (400, 0), (400, 200), (0, 200)),
            (("CHAMFER_LINE", 0, 0), ("CHAMFER_LINE", 0, 0), ("CHAMFER_LINE", 0, 0), ("CHAMFER_LINE", 0, 0)),
        )
        self.assertEqual("RECTANGLE", kind)

    def test_none_type_with_leftover_xy_is_ignored(self):
        kind, _ = classify_plan_outline(
            ((0, 0), (400, 0), (400, 200), (0, 200)),
            (("CHAMFER_NONE", 25, 25), ("CHAMFER_NONE", 0, 0), ("CHAMFER_NONE", 0, 0), ("CHAMFER_NONE", 0, 0)),
        )
        self.assertEqual("RECTANGLE", kind)

    def test_tessellated_octagon_is_chamfer(self):
        kind, evidence = classify_plan_outline(
            ((10, 0), (90, 0), (100, 10), (100, 70), (90, 80), (10, 80), (0, 70), (0, 10)),
        )
        self.assertEqual("CHAMFERED", kind)
        self.assertIn("平面倒角", evidence)

    def test_notched_rounding_also_reports_planar_chamfer(self):
        kind, evidence = classify_plan_outline(
            ((0, 0), (890, 0), (890, 45), (1040, 45), (1040, 345), (890, 345), (890, 890), (0, 890)),
            (
                ("CHAMFER_ARC", 35, 35),
                ("CHAMFER_NONE", 0, 0),
                ("CHAMFER_ROUNDING", 10, 10),
                ("CHAMFER_NONE", 0, 0),
                ("CHAMFER_NONE", 0, 0),
                ("CHAMFER_ROUNDING", 10, 10),
                ("CHAMFER_NONE", 0, 0),
                ("CHAMFER_ARC", 35, 35),
            ),
        )
        self.assertEqual("NOTCHED", kind)
        self.assertTrue(any("缺口" in item for item in evidence))
        self.assertIn("平面倒角", evidence)

    def test_zero_size_arc_on_notch_is_not_chamfer(self):
        kind, evidence = classify_plan_outline(
            ((0, 0), (90, 0), (90, 20), (130, 20), (130, 0), (200, 0), (200, 80), (0, 80)),
            (("CHAMFER_ARC_POINT", 0, 0), ("CHAMFER_NONE", 0, 0)),
        )
        self.assertEqual("NOTCHED", kind)
        self.assertTrue(all("倒角" not in item for item in evidence))

    def test_collinear_sliver_vertex_is_rectangle(self):
        kind, evidence = classify_plan_outline(
            ((0, 250), (0, 0), (500, 0), (500, 250), (164, 250.16)),
        )
        self.assertEqual("RECTANGLE", kind)
        self.assertIn("标准矩形外轮廓", evidence)

    def test_mid_edge_notch_is_not_chamfer(self):
        kind, evidence = classify_plan_outline(
            ((0, 0), (90, 0), (90, 20), (130, 20), (130, 0), (200, 0), (200, 80), (0, 80)),
        )
        self.assertEqual("NOTCHED", kind)
        self.assertTrue(any("缺口" in item for item in evidence))

    def test_trapezoid_is_irregular_not_chamfer(self):
        kind, evidence = classify_plan_outline(((0, 0), (280, 0), (240, 160), (0, 160)))
        self.assertEqual("IRREGULAR", kind)
        self.assertTrue(all("倒角" not in item for item in evidence))

    def test_large_line_chamfer_is_planar_chamfer(self):
        kind, evidence = classify_plan_outline(
            ((0, 0), (400, 0), (400, 340), (0, 340)),
            (
                ("CHAMFER_NONE", 0, 0),
                ("CHAMFER_LINE", 350, 30),
                ("CHAMFER_LINE", 30, 350),
                ("CHAMFER_NONE", 0, 0),
            ),
        )
        self.assertEqual("CHAMFERED", kind)
        self.assertIn("平面倒角", evidence)

    def test_shop_shape_uses_planar_chamfer_not_type_flag(self):
        shape, evidence = classify_shop_shape(
            profile="PL16*968",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=16,
            obb_dims=(968, 968, 16),
            contour_vertex_count=4,
            concave_corner_count=0,
            contour_points=((0, 0, 0), (968, 0, 0), (968, 968, 0), (0, 968, 0)),
            contour_chamfers=(
                ("CHAMFER_LINE", 30, 30),
                ("CHAMFER_LINE", 30, 30),
                ("CHAMFER_LINE", 30, 30),
                ("CHAMFER_LINE", 30, 30),
            ),
        )
        self.assertEqual("异形", shape)
        self.assertIn("平面倒角", evidence)

    def test_shop_shape_large_line_chamfer_is_irregular_chamfer(self):
        shape, evidence = classify_shop_shape(
            profile="PL20",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=20,
            obb_dims=(367, 340, 20),
            contour_vertex_count=4,
            concave_corner_count=0,
            contour_points=((0, 0, 0), (400, 0, 0), (400, 340, 0), (0, 340, 0)),
            contour_chamfers=(
                ("CHAMFER_NONE", 0, 0),
                ("CHAMFER_LINE", 350, 30),
                ("CHAMFER_LINE", 30, 350),
                ("CHAMFER_NONE", 0, 0),
            ),
        )
        self.assertEqual("异形", shape)
        self.assertIn("平面倒角", evidence)
