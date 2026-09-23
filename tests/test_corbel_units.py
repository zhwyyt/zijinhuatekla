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

    def test_direct_rolled_spine_in_unknown_cluster_is_corbel(self):
        member = {
            "Classification": {
                "PartRoles": [
                    {"PartId": "10", "Role": "web_candidate"},
                    {"PartId": "11", "Role": "flange_candidate"},
                    {"PartId": "12", "Role": "flange_candidate"},
                ]
            }
        }
        assembly = {
            "assemblyId": "100",
            "mainPartId": "10",
            "parts": [
                {"partId": "10", "profileString": "PL16*1000", "boundingBox": {"min": {"x": 0, "y": 0, "z": 0}, "max": {"x": 100, "y": 100, "z": 1000}}},
                {"partId": "11", "profileString": "PL20*400", "boundingBox": {"min": {"x": 0, "y": 50, "z": 0}, "max": {"x": 100, "y": 90, "z": 1000}}},
                {"partId": "12", "profileString": "PL20*400", "boundingBox": {"min": {"x": 0, "y": -40, "z": 0}, "max": {"x": 100, "y": 0, "z": 1000}}},
                {"partId": "20", "profileString": "BH400*200*7*10", "centroid": {"x": 50, "y": -300, "z": 800}},
                {"partId": "21", "profileString": "PL16*230", "centroid": {"x": 50, "y": -300, "z": 300}},
            ],
            "relationships": [
                {"partIdA": "20", "partIdB": "11", "edgeType": "Contact"},
                {"partIdA": "21", "partIdB": "12", "edgeType": "Contact"},
            ],
        }
        clusters = [
            AppendageRoleClassification(
                cluster_id="100:0",
                role="Unknown",
                confidence=0.4,
                part_ids=["20", "21"],
            )
        ]

        units = classify_corbel_units(assembly, clusters, member=member)

        self.assertEqual(1, len(units))
        self.assertEqual(["20"], units[0].part_ids)
        self.assertIn("DIRECT_ROLLED_SPINE", units[0].evidence_codes)

    def test_direct_spine_is_not_duplicated_in_existing_bracket_cluster(self):
        member = {"Classification": {"PartRoles": []}}
        assembly = {
            "assemblyId": "100",
            "mainPartId": "10",
            "parts": [
                {"partId": "10", "profileString": "PL16*1000"},
                {"partId": "20", "profileString": "BH400*200*7*10"},
            ],
            "relationships": [{"partIdA": "20", "partIdB": "10", "edgeType": "Weld"}],
        }
        clusters = [
            AppendageRoleClassification(
                cluster_id="100:0",
                role="Bracket",
                confidence=0.9,
                part_ids=["20"],
            )
        ]

        units = classify_corbel_units(assembly, clusters, member=member)

        self.assertEqual(1, len(units))
        self.assertEqual(0, sum(1 for unit in units if "DIRECT_ROLLED_SPINE" in unit.evidence_codes))


if __name__ == "__main__":
    unittest.main()
