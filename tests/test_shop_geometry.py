import unittest

from zijinhua_tekla.contracts.normalized import NormalizedPart, PartSpatialHints
from zijinhua_tekla.geom.shop import classify_shop_process, classify_shop_shape
from zijinhua_tekla.part_roles import classify_part_role


class ShopGeometryTests(unittest.TestCase):
    def test_rectangle_without_holes_is_blanking_square(self):
        process, _ = classify_shop_process(
            profile="PL16*200",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=16,
            obb_dims=(400, 200, 16),
            bolt_hole_count=0,
            hole_like_feature_count=0,
        )
        shape, evidence = classify_shop_shape(
            profile="PL16*200",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=16,
            obb_dims=(400, 200, 16),
            contour_vertex_count=4,
            concave_corner_count=0,
            contour_points=((0, 0, 0), (400, 0, 0), (400, 200, 0), (0, 200, 0)),
        )
        self.assertEqual("下料", process)
        self.assertEqual("方块", shape)
        self.assertTrue(any("矩形" in item for item in evidence))

    def test_corner_chamfer_is_not_square(self):
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
        self.assertTrue(any("倒角" in item for item in evidence))

    def test_holes_on_rectangle_are_irregular(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="1",
                part_position="A-P-1",
                name="连接板",
                profile="PL14*243",
                is_plate_like=True,
                thickness=14,
                length=281,
                width=243,
                obb_dims=(281, 243, 14),
                contour_vertex_count=4,
                bolt_hole_count=1,
                hole_like_feature_count=1,
                contour_points=((0, 0, 0), (281, 0, 0), (281, 243, 0), (0, 243, 0)),
            )
        )
        self.assertEqual("下料割孔", result.process)
        self.assertEqual("异形", result.shape)

    def test_bevel_cut_on_rectangle_stays_square(self):
        shape, evidence = classify_shop_shape(
            profile="PL16*200",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=16,
            obb_dims=(400, 200, 16),
            contour_vertex_count=4,
            concave_corner_count=0,
            contour_points=((0, 0, 0), (400, 0, 0), (400, 200, 0), (0, 200, 0)),
            contour_chamfer_types=("CHAMFER_NONE", "CHAMFER_NONE", "CHAMFER_NONE", "CHAMFER_NONE"),
            hole_like_feature_count=0,
            bolt_hole_count=0,
            has_edge_bevel=True,
        )
        self.assertEqual("方块", shape)
        self.assertTrue(any("剖口" in item for item in evidence))
        self.assertFalse(any("倒角" in item for item in evidence))

    def test_missing_contour_beam_plate_is_square(self):
        shape, evidence = classify_shop_shape(
            profile="PL16*90",
            runtime_type="Beam",
            is_plate_like=True,
            thickness=16,
            obb_dims=(680, 90, 16),
            contour_vertex_count=0,
            concave_corner_count=0,
        )
        self.assertEqual("方块", shape)
        self.assertTrue(any("矩形" in item for item in evidence))

    def test_beam_plate_corner_cut_is_chamfer_not_square(self):
        shape, evidence = classify_shop_shape(
            profile="PL16*200",
            runtime_type="Beam",
            is_plate_like=True,
            thickness=16,
            obb_dims=(360, 200, 16),
            contour_vertex_count=0,
            concave_corner_count=0,
            has_end_chamfer=True,
        )
        self.assertEqual("异形", shape)
        self.assertTrue(any("倒角" in item for item in evidence))
        self.assertFalse(any("洞口" in item for item in evidence))

    def test_holes_on_rectangle_use_opening_evidence(self):
        shape, evidence = classify_shop_shape(
            profile="PL14*243",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=14,
            obb_dims=(281, 243, 14),
            contour_vertex_count=4,
            concave_corner_count=0,
            contour_points=((0, 0, 0), (281, 0, 0), (281, 243, 0), (0, 243, 0)),
            bolt_hole_count=1,
            hole_like_feature_count=1,
        )
        self.assertEqual("异形", shape)
        self.assertTrue(any("洞口" in item for item in evidence))

    def test_polybeam_without_contour_stays_irregular(self):
        shape, _ = classify_shop_shape(
            profile="PL30*1000",
            runtime_type="PolyBeam",
            is_plate_like=True,
            thickness=30,
            obb_dims=(2850, 1000, 80),
            contour_vertex_count=0,
            concave_corner_count=0,
        )
        self.assertEqual("异形", shape)

    def test_inner_opening_makes_irregular(self):
        shape, _ = classify_shop_shape(
            profile="PL16*968",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=16,
            obb_dims=(968, 968, 16),
            contour_vertex_count=4,
            concave_corner_count=0,
            contour_points=((0, 0, 0), (968, 0, 0), (968, 968, 0), (0, 968, 0)),
            hole_like_feature_count=3,
            bolt_hole_count=2,
        )
        self.assertEqual("异形", shape)

    def test_concave_outline_is_irregular(self):
        shape, _ = classify_shop_shape(
            profile="PL14*296",
            runtime_type="ContourPlate",
            is_plate_like=True,
            thickness=14,
            obb_dims=(380, 296, 14),
            contour_vertex_count=8,
            concave_corner_count=2,
            bolt_hole_count=1,
            hole_like_feature_count=1,
        )
        self.assertEqual("异形", shape)

    def test_folded_main_wall_is_bent_formed_main(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="91",
                part_position="A-P-91",
                name="变截面",
                profile="PL16*1000",
                runtime_type="PolyBeam",
                is_plate_like=True,
                is_special_shape=True,
                thickness=16,
                length=10478,
                width=1000,
                obb_dims=(10478, 1000, 1617),
                bolt_hole_count=3,
                hole_like_feature_count=9,
                boolean_cut_count=6,
            ),
            PartSpatialHints(member_body_type="BOX", relation_to_box_body="MAIN_WALL"),
        )
        self.assertEqual("下料折弯", result.process)
        self.assertEqual("异形主材", result.shape)

    def test_role_keeps_square_when_part_has_edge_bevel(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="2",
                part_position="A-P-2",
                name="连接板",
                profile="PL16*200",
                is_plate_like=True,
                thickness=16,
                length=400,
                width=200,
                obb_dims=(400, 200, 16),
                contour_vertex_count=4,
                contour_points=((0, 0, 0), (400, 0, 0), (400, 200, 0), (0, 200, 0)),
                has_edge_bevel=True,
                edge_bevel_count=1,
            )
        )
        self.assertEqual("方块", result.shape)
        self.assertTrue(any("剖口" in item for item in result.evidence))

    def test_rolled_bh_is_not_cut(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="558",
                part_position="T3-H-558",
                name="钢梁",
                profile="BH400*200*7*10",
                runtime_type="Beam",
                thickness=200,
                obb_dims=(389, 400, 200),
            )
        )
        self.assertEqual("不下", result.process)
        self.assertEqual("", result.shape)

    def test_rolled_bh_end_bevel_is_reported_not_a_shape(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="574",
                part_position="T3-H-574",
                name="钢梁",
                profile="BH950*400*16*30",
                runtime_type="Beam",
                thickness=400,
                obb_dims=(9890, 950, 400),
                has_edge_bevel=True,
                edge_bevel_count=4,
            )
        )
        self.assertEqual("不下", result.process)
        self.assertEqual("", result.shape)
        self.assertTrue(any("剖口" in item for item in result.evidence))

    def test_rolled_section_holes_are_openings_not_blanking(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="574",
                part_position="A-H-1",
                name="钢梁",
                profile="BH950*400*16*30",
                runtime_type="Beam",
                thickness=400,
                obb_dims=(9890, 950, 400),
                bolt_hole_count=4,
                hole_like_feature_count=8,
                boolean_cut_count=10,
                edge_bevel_count=6,
                has_edge_bevel=True,
            )
        )
        self.assertEqual("不下", result.process)
        self.assertTrue(any("剖口" in item for item in result.evidence))
        self.assertTrue(any("洞口" in item for item in result.evidence))

    def test_channel_angle_pipe_report_bevel_chamfer_and_openings(self):
        channel = classify_part_role(
            NormalizedPart(
                part_id="c1",
                part_position="A-C-1",
                profile="C160*63*6.5",
                runtime_type="Beam",
                thickness=160,
                obb_dims=(2400, 160, 63),
                bolt_hole_count=2,
                hole_like_feature_count=2,
                has_edge_bevel=True,
                edge_bevel_count=1,
            )
        )
        self.assertEqual("成品槽", channel.process)
        self.assertTrue(any("剖口" in item for item in channel.evidence))
        self.assertTrue(any("洞口" in item for item in channel.evidence))

        angle = classify_part_role(
            NormalizedPart(
                part_id="l1",
                part_position="A-L-1",
                profile="L75*5",
                runtime_type="Beam",
                thickness=5,
                obb_dims=(1800, 75, 75),
                has_end_chamfer=True,
                end_chamfer_count=1,
            )
        )
        self.assertEqual("不下", angle.process)
        self.assertTrue(any("倒角" in item for item in angle.evidence))

        pipe = classify_part_role(
            NormalizedPart(
                part_id="p1",
                part_position="A-P-1",
                profile="PIPE76.1*4",
                runtime_type="Beam",
                thickness=76.1,
                obb_dims=(3200, 76.1, 76.1),
                boolean_cut_count=1,
                hole_like_feature_count=1,
                has_edge_bevel=True,
                edge_bevel_count=1,
            )
        )
        self.assertEqual("不下", pipe.process)
        self.assertTrue(any("剖口" in item for item in pipe.evidence))
        self.assertFalse(any("洞口" in item for item in pipe.evidence))

        rhs = classify_part_role(
            NormalizedPart(
                part_id="r1",
                part_position="A-R-1",
                profile="RHS300*200*10",
                runtime_type="Beam",
                thickness=300,
                obb_dims=(4000, 300, 200),
                boolean_cut_count=2,
                hole_like_feature_count=2,
            )
        )
        self.assertEqual("不下", rhs.process)
        self.assertTrue(any("洞口" in item for item in rhs.evidence))

        ub = classify_part_role(
            NormalizedPart(
                part_id="u1",
                part_position="A-H-2",
                profile="UB406*178*54",
                runtime_type="Beam",
                obb_dims=(5000, 406, 178),
            )
        )
        self.assertEqual("不下", ub.process)

        chs = classify_part_role(
            NormalizedPart(
                part_id="s1",
                part_position="A-S-1",
                profile="CHS219.1*6",
                runtime_type="Beam",
                obb_dims=(2800, 219.1, 219.1),
                has_edge_bevel=True,
                edge_bevel_count=1,
            )
        )
        self.assertEqual("不下", chs.process)
        self.assertTrue(any("剖口" in item for item in chs.evidence))
