import unittest

from zijinhua_tekla.classifiers.corbel_units import CorbelUnit
from zijinhua_tekla.reports.member_complexity import classify_member_complexity


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
        self.assertIn("main_class.H", result.evidence_codes)

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
        self.assertIn("main_part.plate_like", result.evidence_codes)

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
        self.assertIn("section.web_and_two_flanges", result.evidence_codes)

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
        self.assertIn("section.closed_loop", result.evidence_codes)

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
