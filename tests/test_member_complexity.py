import unittest

from zijinhua_tekla.classifiers.corbel_units import CorbelUnit
from zijinhua_tekla.reports.member_complexity import (
    classify_member_complexity,
    is_embedded_member_id,
    main_material_geometry_type,
)


class MemberComplexityTests(unittest.TestCase):
    def test_hxz_direct_h_profile_is_not_overridden_to_one_plate(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-4HXZ-1"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "BH200*300*30*30"}],
        }
        member = {"AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}]}
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("H钢", result.main_material_type)
        self.assertIn("profile.H", result.evidence_codes)

    def test_plate_without_composite_signature_is_one_plate(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-4HXZ-2"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL40*600", "isPlateLike": True}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [{"SectionFeatures": {"MajorPlateCount": 1}}],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("一字板", result.main_material_type)
        self.assertIn("section.plate_signature:1/1", result.evidence_codes)

    def test_plate_composing_h_section_is_h(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-6GL-144"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL12*200", "isPlateLike": True}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 3,
                        "CentralVerticalPlateCount": 1,
                        "CentralHorizontalPlateCount": 2,
                    }
                }
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("H钢", result.main_material_type)
        self.assertIn("section.h_signature:1/1", result.evidence_codes)

    def test_box_with_h_like_counts_and_closed_loop_is_box(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-5GKZ-2"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL20*600", "isPlateLike": True}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 12,
                        "CentralVerticalPlateCount": 6,
                        "CentralHorizontalPlateCount": 6,
                        "ClosedLoops": 1,
                        "CavityCount": 1,
                    }
                }
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("BOX", result.main_material_type)
        self.assertIn("section.box_signature:1/1", result.evidence_codes)

    def test_cross_signature_is_cross(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-4MQ-13"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL20*300", "isPlateLike": True}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 5,
                        "CentralVerticalPlateCount": 2,
                        "CentralHorizontalPlateCount": 3,
                        "ClosedLoops": 0,
                        "CavityCount": 0,
                    }
                }
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("十字", result.main_material_type)
        self.assertIn("section.cross_signature:1/1", result.evidence_codes)

    def test_attached_plates_do_not_make_box_cross_conflict(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-5GKZ-4"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL16*968", "isPlateLike": True}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 20,
                        "CentralVerticalPlateCount": 6,
                        "CentralHorizontalPlateCount": 14,
                        "ClosedLoops": 0,
                        "CavityCount": 0,
                    }
                },
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 12,
                        "CentralVerticalPlateCount": 6,
                        "CentralHorizontalPlateCount": 6,
                        "ClosedLoops": 1,
                        "CavityCount": 1,
                    }
                },
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("BOX", result.main_material_type)
        self.assertIn("section.box_signature:1/2", result.evidence_codes)

    def test_conflicting_section_signatures_are_unknown(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-CONFLICT-1"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL20*600", "isPlateLike": True}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 3,
                        "CentralVerticalPlateCount": 1,
                        "CentralHorizontalPlateCount": 2,
                        "ClosedLoops": 0,
                        "CavityCount": 0,
                    }
                },
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 4,
                        "CentralVerticalPlateCount": 2,
                        "CentralHorizontalPlateCount": 2,
                        "ClosedLoops": 1,
                        "CavityCount": 1,
                    }
                },
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("UNKNOWN", result.main_material_type)
        self.assertIn("section.conflict", result.evidence_codes)

    def test_direct_profile_body_is_not_plate_signature(self):
        assembly = {
            "assemblyId": "A1",
            "metadata": {"assemblyPosition": "T3-4HXZ-10"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "BH950*250*40*60"}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {
                    "SectionFeatures": {"MajorPlateCount": 1},
                    "SectionParts": [{"PartId": 10, "RoleHint": "direct_profile_body"}],
                }
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("H钢", result.main_material_type)
        self.assertIn("profile.H", result.evidence_codes)

    def test_section_variation_is_tapered(self):
        assembly = {
            "assemblyId": "A2",
            "metadata": {"assemblyPosition": "T3-5GKZ-1"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL16*968"}],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}],
            "Samples": [
                {"SectionFeatures": {"OuterWidth": 1000, "OuterHeight": 1000}},
                {"SectionFeatures": {"OuterWidth": 1289, "OuterHeight": 1000}},
            ],
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("一字板", result.main_material_type)
        self.assertEqual("变截面", result.main_material_form)

    def test_axis_shape_is_straight_without_direction_changes(self):
        assembly = {
            "assemblyId": "A2",
            "metadata": {"assemblyPosition": "T3-AXIS-1"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL16*968"}],
        }
        member = {
            "AxisSegments": [
                {"Length": 1000, "Direction": {"X": 1, "Y": 0, "Z": 0}},
                {"Length": 1000, "Direction": {"X": 1, "Y": 0.0001, "Z": 0}},
            ]
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("直线", result.axis_shape)
        self.assertEqual(0, result.axis_bend_count)
        self.assertIn("axis.bend_count:0", result.evidence_codes)

    def test_axis_shape_counts_geometry_bends(self):
        assembly = {
            "assemblyId": "A2",
            "metadata": {"assemblyPosition": "T3-AXIS-2"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL16*968"}],
        }
        member = {
            "AxisSegments": [
                {"Length": 1000, "Direction": {"X": 1, "Y": 0, "Z": 0}},
                {"Length": 1000, "Direction": {"X": 0, "Y": 1, "Z": 0}},
                {"Length": 1000, "Direction": {"X": 0, "Y": 0, "Z": 1}},
            ]
        }
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("折线", result.axis_shape)
        self.assertEqual(2, result.axis_bend_count)
        self.assertIn("axis.bend_count:2", result.evidence_codes)

    def test_axis_shape_is_unknown_without_axis_evidence(self):
        assembly = {
            "assemblyId": "A2",
            "metadata": {"assemblyPosition": "T3-AXIS-3"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "PL16*968"}],
        }
        result = classify_member_complexity(assembly, {}, corbel_units=[])
        self.assertEqual("未知", result.axis_shape)
        self.assertIsNone(result.axis_bend_count)
        self.assertIn("axis.no_segments", result.evidence_codes)

    def test_member_id_with_mj_is_embedded_before_main_material(self):
        assembly = {
            "assemblyId": "A3",
            "metadata": {"assemblyPosition": "T3-MJ-1"},
            "mainPartId": 10,
            "parts": [{"partId": 10, "profileString": "BH300*150*6*8"}],
        }
        member = {
            "Samples": [
                {
                    "SectionFeatures": {
                        "MajorPlateCount": 3,
                        "CentralVerticalPlateCount": 1,
                        "CentralHorizontalPlateCount": 2,
                    }
                }
            ],
            "AxisSegments": [{"Length": 1000, "Direction": {"X": 1, "Y": 0, "Z": 0}}],
        }

        self.assertTrue(is_embedded_member_id("T3-MJ-1"))
        self.assertEqual("埋件", main_material_geometry_type(assembly, member, "T3-MJ-1"))
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("埋件", result.main_material_type)
        self.assertEqual("不适用", result.main_material_form)
        self.assertIn("member.id_mj", result.evidence_codes)
        self.assertEqual("直线", result.axis_shape)

    def test_corbel_level_and_orientation(self):
        assembly = {
            "assemblyId": "A3",
            "metadata": {"assemblyPosition": "T3-6GKL-1"},
            "mainPartId": 10,
            "parts": [
                {
                    "partId": 10,
                    "profileString": "BH300*200*10*14",
                    "partCoordinateSystem": {"axisX": {"x": 1, "y": 0, "z": 0}},
                    "centroid": {"x": 0, "y": 0, "z": 0},
                },
                {
                    "partId": 20,
                    "profileString": "BH200*100*10*10",
                    "volume": 10,
                    "partCoordinateSystem": {"axisX": {"x": 0, "y": 1, "z": 0}},
                    "centroid": {"x": 100, "y": 0, "z": 3000},
                },
                {
                    "partId": 21,
                    "profileString": "BH200*100*10*10",
                    "volume": 10,
                    "partCoordinateSystem": {"axisX": {"x": 0, "y": 1, "z": 0}},
                    "centroid": {"x": 100, "y": 0, "z": 7000},
                },
            ],
        }
        member = {"AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}}]}
        units = [
            CorbelUnit("U1", "C1", ["20"], ["20"], [], 0.9),
            CorbelUnit("U2", "C1", ["21"], ["21"], [], 0.9),
        ]
        result = classify_member_complexity(assembly, member, corbel_units=units)
        self.assertEqual(2, result.corbel_count)
        self.assertEqual("多楼层高度", result.corbel_floor_distribution)
        self.assertEqual("垂直", result.corbel_orientation)


if __name__ == "__main__":
    unittest.main()
