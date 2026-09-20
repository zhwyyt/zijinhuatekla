import unittest

from zijinhua_tekla.bracket_classifier import AppendageRoleClassification
from zijinhua_tekla.classifiers.corbel_units import classify_corbel_units, is_rolled_spine_profile


class CorbelUnitTests(unittest.TestCase):
    def test_bh_and_h_profiles_are_rolled_spines(self):
        self.assertTrue(is_rolled_spine_profile("BH400*200*7*10"))
        self.assertTrue(is_rolled_spine_profile("H400*200*8*13"))
        self.assertFalse(is_rolled_spine_profile("PL16*558"))
        self.assertFalse(is_rolled_spine_profile("C6.5"))

    def test_two_bh_spines_in_one_bracket_cluster_count_as_two_units(self):
        assembly = {
            "parts": [
                {"partId": "1", "profileString": "BH400*200*7*10"},
                {"partId": "2", "profileString": "BH400*200*7*10"},
                {"partId": "3", "profileString": "PL10*100"},
            ]
        }
        clusters = [
            AppendageRoleClassification(
                cluster_id="100:0",
                role="Bracket",
                confidence=0.9,
                part_ids=["1", "2", "3"],
            )
        ]

        units = classify_corbel_units(assembly, clusters)

        self.assertEqual(2, len(units))
        self.assertEqual(["1"], units[0].spine_part_ids)
        self.assertEqual(["2"], units[1].spine_part_ids)

    def test_fabricated_three_plate_bracket_is_one_unit(self):
        assembly = {
            "parts": [
                {"partId": "10", "profileString": "PL16*558"},
                {"partId": "11", "profileString": "PL30*400"},
                {"partId": "12", "profileString": "PL30*400"},
            ]
        }
        clusters = [
            AppendageRoleClassification(
                cluster_id="100:1",
                role="Bracket",
                confidence=0.95,
                part_ids=["10", "11", "12"],
            )
        ]

        units = classify_corbel_units(assembly, clusters)

        self.assertEqual(1, len(units))
        self.assertIn("FABRICATED_BRACKET_CLUSTER", units[0].evidence_codes)
        self.assertEqual(["10", "11", "12"], units[0].part_ids)

    def test_connection_plate_cluster_is_not_a_corbel_unit(self):
        assembly = {"parts": [{"partId": "11", "profileString": "PL16*230"}]}
        clusters = [
            AppendageRoleClassification(
                cluster_id="100:2",
                role="ConnectionPlate",
                confidence=0.86,
                part_ids=["11"],
            )
        ]

        self.assertEqual([], classify_corbel_units(assembly, clusters))


if __name__ == "__main__":
    unittest.main()
