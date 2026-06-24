import unittest

from zijinhua_tekla.rules import find_equivalent_parts, row_part_score


class DerivedProfilePartTests(unittest.TestCase):
    def test_h_suffix_plate_is_derived_from_base_bh_profile_part(self):
        parent_parts = [
            {
                "partId": 68294737,
                "partPosition": "T3-H-558",
                "name": "钢梁",
                "profileString": "BH400*200*7*10",
                "isPlateLike": False,
                "thickness": 400,
                "obbDims": {"x": 400.0, "y": 389.4, "z": 200.0},
            },
            {
                "partId": 68294750,
                "partPosition": "T3-H-558",
                "name": "钢梁",
                "profileString": "BH400*200*7*10",
                "isPlateLike": False,
                "thickness": 400,
                "obbDims": {"x": 400.0, "y": 389.4, "z": 200.0},
            },
        ]

        cases = [
            {"零件名称": "T3-H-558s", "规格": "PL10*200", "长度": 320, "数量": 2},
            {"零件名称": "T3-H-558x", "规格": "PL10*200", "长度": 389, "数量": 2},
            {"零件名称": "T3-H-558f", "规格": "PL7*380", "长度": 389, "数量": 2},
        ]

        for row in cases:
            with self.subTest(part=row["零件名称"]):
                parts, match_method, match_note = find_equivalent_parts(
                    row,
                    {"T3-H-558": parent_parts},
                    parent_parts,
                )

                self.assertEqual("derivedFromProfilePart", match_method)
                self.assertEqual(parent_parts, parts)
                self.assertIn("T3-H-558", match_note)
                self.assertIn("BH400*200*7*10", match_note)

    def test_h_suffix_plate_derivation_is_not_tied_to_t3_project_prefix(self):
        parent_parts = [
            {
                "partId": 1001,
                "partPosition": "A1-H-558",
                "name": "钢梁",
                "profileString": "BH400*200*7*10",
                "isPlateLike": False,
                "thickness": 400,
                "obbDims": {"x": 400.0, "y": 389.4, "z": 200.0},
            }
        ]
        row = {"零件名称": "A1-H-558f", "规格": "PL7*380", "长度": 389, "数量": 1}

        parts, match_method, match_note = find_equivalent_parts(
            row,
            {"A1-H-558": parent_parts},
            parent_parts,
        )

        self.assertEqual("derivedFromProfilePart", match_method)
        self.assertEqual(parent_parts, parts)
        self.assertIn("A1-H-558", match_note)

    def test_non_derived_part_requires_exact_part_position_even_when_geometry_matches(self):
        row = {"零件名称": "A-P-100", "规格": "PL10*200", "长度": 1000, "数量": 1}
        geometry_match_with_different_number = {
            "partId": 200,
            "partPosition": "A-P-200",
            "name": "连接板",
            "profileString": "PL10",
            "runtimeType": "ContourPlate",
            "isPlateLike": True,
            "thickness": 10,
            "obbDims": {"x": 1000.0, "y": 200.0, "z": 10.0},
        }

        parts, match_method, match_note = find_equivalent_parts(
            row,
            {"A-P-200": [geometry_match_with_different_number]},
            [geometry_match_with_different_number],
        )

        self.assertEqual([], parts)
        self.assertEqual("missing", match_method)
        self.assertIn("A-P-200", match_note)


class ContourPlateDimensionTests(unittest.TestCase):
    def test_contour_segments_provide_nominal_processing_dimensions(self):
        cases = [
            (
                {"零件名称": "T3-P-4869", "规格": "PL14*243", "长度": 281},
                {
                    "runtimeType": "ContourPlate",
                    "profileString": "PL14",
                    "isPlateLike": True,
                    "thickness": 14,
                    "obbDims": {"x": 318.5, "y": 239.8, "z": 14},
                    "contourSegments": [
                        {"length": 285.4},
                        {"length": 243.3},
                        {"length": 281.3},
                        {"length": 194.8},
                    ],
                },
                281.3,
                243.3,
            ),
            (
                {"零件名称": "T3-P-4885", "规格": "PL14*278", "长度": 325},
                {
                    "runtimeType": "ContourPlate",
                    "profileString": "PL14",
                    "isPlateLike": True,
                    "thickness": 14,
                    "obbDims": {"x": 388.3, "y": 267.3, "z": 14},
                    "contourSegments": [
                        {"length": 337.7},
                        {"length": 185.9},
                        {"length": 325.0},
                        {"length": 277.7},
                    ],
                },
                325.0,
                277.7,
            ),
        ]

        for row, part, expected_length, expected_width in cases:
            with self.subTest(part=row["零件名称"]):
                spec_ok, length_ok, _, _, part_len, part_width = row_part_score(row, part)

                self.assertTrue(spec_ok)
                self.assertTrue(length_ok)
                self.assertAlmostEqual(expected_length, part_len, places=1)
                self.assertAlmostEqual(expected_width, part_width, places=1)

    def test_contour_plate_dimensions_can_use_obb_or_segments_as_candidates(self):
        cases = [
            (
                {"零件名称": "T3-P-3245", "规格": "PL20*219", "长度": 340},
                {
                    "runtimeType": "ContourPlate",
                    "profileString": "PL20",
                    "isPlateLike": True,
                    "thickness": 20,
                    "obbDims": {"x": 218.9, "y": 340.0, "z": 20},
                    "contourSegments": [
                        {"length": 321.6},
                        {"length": 340.0},
                        {"length": 321.6},
                        {"length": 340.0},
                    ],
                },
                340.0,
                218.9,
            ),
            (
                {"零件名称": "T3-P-4546", "规格": "PL30*400", "长度": 529},
                {
                    "runtimeType": "ContourPlate",
                    "profileString": "PL30",
                    "isPlateLike": True,
                    "thickness": 30,
                    "obbDims": {"x": 528.5, "y": 400.0, "z": 30},
                    "contourSegments": [
                        {"length": 676.1},
                        {"length": 400.0},
                        {"length": 717.2},
                        {"length": 402.1},
                    ],
                },
                528.5,
                400.0,
            ),
            (
                {"零件名称": "T3-P-4775", "规格": "PL14*297", "长度": 380},
                {
                    "runtimeType": "ContourPlate",
                    "profileString": "PL14",
                    "isPlateLike": True,
                    "thickness": 14,
                    "obbDims": {"x": 380.0, "y": 296.5, "z": 14},
                    "contourSegments": [
                        {"length": 380.0},
                        {"length": 96.5},
                        {"length": 95.0},
                        {"length": 200.0},
                        {"length": 190.0},
                        {"length": 200.0},
                        {"length": 95.0},
                        {"length": 96.5},
                    ],
                },
                380.0,
                296.5,
            ),
            (
                {"零件名称": "T3-P-4942", "规格": "PL16*558", "长度": 890},
                {
                    "runtimeType": "ContourPlate",
                    "profileString": "PL16",
                    "isPlateLike": True,
                    "thickness": 16,
                    "obbDims": {"x": 890.0, "y": 558.3, "z": 16},
                    "contourSegments": [
                        {"length": 890.0},
                        {"length": 679.0},
                        {"length": 890.0},
                        {"length": 679.0},
                    ],
                },
                890.0,
                558.3,
            ),
        ]

        for row, part, expected_length, expected_width in cases:
            with self.subTest(part=row["零件名称"]):
                spec_ok, length_ok, _, _, part_len, part_width = row_part_score(row, part)

                self.assertTrue(spec_ok)
                self.assertTrue(length_ok)
                self.assertAlmostEqual(expected_length, part_len, places=1)
                self.assertAlmostEqual(expected_width, part_width, places=1)

    def test_same_edge_cannot_be_reused_as_both_length_and_width(self):
        row = {"零件名称": "T3-P-4661", "规格": "PL12*845", "长度": 868}
        narrow_plate = {
            "runtimeType": "ContourPlate",
            "profileString": "PL12",
            "isPlateLike": True,
            "thickness": 12,
            "obbDims": {"x": 116.3, "y": 890.0, "z": 12},
            "contourSegments": [
                {"length": 116.3},
                {"length": 890.0},
                {"length": 116.3},
                {"length": 890.0},
            ],
        }

        spec_ok, length_ok, _, _, part_len, part_width = row_part_score(row, narrow_plate)

        self.assertFalse(spec_ok)
        self.assertTrue(length_ok)
        self.assertAlmostEqual(890.0, part_len, places=1)
        self.assertAlmostEqual(116.3, part_width, places=1)


if __name__ == "__main__":
    unittest.main()
