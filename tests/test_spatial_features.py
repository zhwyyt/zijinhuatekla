import unittest

from zijinhua_tekla.spatial_features import (
    appendage_cluster_features_from_bundle,
    body_part_ids_from_member_roles,
    classify_appendage_clusters_from_bundle,
)


def part(part_id, name, min_xyz, max_xyz, role_name="板"):
    min_x, min_y, min_z = min_xyz
    max_x, max_y, max_z = max_xyz
    return {
        "partId": part_id,
        "name": role_name,
        "partPosition": name,
        "centroid": {
            "x": (min_x + max_x) / 2.0,
            "y": (min_y + max_y) / 2.0,
            "z": (min_z + max_z) / 2.0,
        },
        "boundingBox": {
            "min": {"x": min_x, "y": min_y, "z": min_z},
            "max": {"x": max_x, "y": max_y, "z": max_z},
        },
        "volume": max(1.0, (max_x - min_x) * (max_y - min_y) * (max_z - min_z)),
        "thickness": min(max_x - min_x, max_y - min_y, max_z - min_z),
    }


class SpatialFeatureTests(unittest.TestCase):
    def test_body_part_ids_from_member_roles_uses_main_material_roles(self):
        member = {
            "Classification": {
                "PartRoles": [
                    {"PartId": "1", "Role": "wall_candidate"},
                    {"PartId": "2", "Role": "flange_candidate"},
                    {"PartId": "10", "Role": "stiffener_candidate"},
                ]
            }
        }

        self.assertEqual({"1", "2"}, body_part_ids_from_member_roles(member))

    def test_bundle_relationships_build_appendage_cluster_features_for_bracket(self):
        assembly = {
            "assemblyId": "A1",
            "mainPartId": 1,
            "parts": [
                part(1, "A1-BODY", (0, 0, 0), (1000, 100, 100), "主体板"),
                part(10, "A1-BR-ROOT", (400, 100, 30), (430, 130, 70), "牛腿根部板"),
                part(11, "A1-BR-RIB1", (430, 130, 30), (520, 360, 50), "牛腿肋板"),
                part(12, "A1-BR-RIB2", (430, 130, 50), (520, 360, 70), "牛腿肋板"),
            ],
            "relationships": [
                {"partIdA": 1, "partIdB": 10, "edgeType": "Contact"},
                {"partIdA": 10, "partIdB": 11, "edgeType": "Weld"},
                {"partIdA": 10, "partIdB": 12, "edgeType": "Weld"},
            ],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}, "Length": 1000}],
            "Classification": {"PartRoles": [{"PartId": "1", "Role": "wall_candidate"}]},
        }

        features = appendage_cluster_features_from_bundle(assembly, member)

        self.assertEqual(1, len(features))
        cluster = features[0]
        self.assertEqual("A1:0", cluster.cluster_id)
        self.assertAlmostEqual(1 / 3, cluster.root_contact_ratio, places=4)
        self.assertAlmostEqual(120.0, cluster.span_along_axis, places=1)
        self.assertAlmostEqual(1000.0, cluster.assembly_span, places=1)
        self.assertGreater(cluster.cantilever_ratio, 1.35)
        self.assertTrue(cluster.centroid_outside_body)
        self.assertFalse(cluster.has_end_connection_signal)
        self.assertEqual(["10", "11", "12"], cluster.part_ids)

    def test_bundle_cluster_uses_confirmed_body_ids_when_old_member_roles_are_missing(self):
        assembly = {
            "assemblyId": "A1",
            "mainPartId": 1,
            "parts": [
                part(1, "A1-BODY-A", (0, 0, 0), (1000, 100, 100), "主体板"),
                part(2, "A1-BODY-B", (0, 100, 0), (1000, 200, 100), "主体板"),
                part(10, "A1-BR-ROOT", (400, 200, 30), (430, 230, 70), "牛腿根部板"),
                part(11, "A1-BR-RIB", (430, 230, 30), (520, 460, 50), "牛腿肋板"),
            ],
            "relationships": [
                {"partIdA": 2, "partIdB": 10, "edgeType": "Contact"},
                {"partIdA": 10, "partIdB": 11, "edgeType": "Weld"},
            ],
        }
        member = {"AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}, "Length": 1000}]}

        features = appendage_cluster_features_from_bundle(assembly, member, body_part_ids={"1", "2"})

        self.assertEqual(1, len(features))
        self.assertEqual(["10", "11"], features[0].part_ids)
        self.assertAlmostEqual(0.5, features[0].root_contact_ratio, places=4)

    def test_bundle_cluster_features_feed_bracket_classifier(self):
        assembly = {
            "assemblyId": "A1",
            "mainPartId": 1,
            "parts": [
                part(1, "A1-BODY", (0, 0, 0), (1000, 100, 100), "主体板"),
                part(10, "A1-BR-ROOT", (400, 100, 30), (430, 130, 70), "牛腿根部板"),
                part(11, "A1-BR-RIB1", (430, 130, 30), (520, 360, 50), "牛腿肋板"),
                part(12, "A1-BR-RIB2", (430, 130, 50), (520, 360, 70), "牛腿肋板"),
            ],
            "relationships": [
                {"partIdA": 1, "partIdB": 10, "edgeType": "Contact"},
                {"partIdA": 10, "partIdB": 11, "edgeType": "Weld"},
                {"partIdA": 10, "partIdB": 12, "edgeType": "Weld"},
            ],
        }
        member = {
            "AxisSegments": [{"Direction": {"X": 1, "Y": 0, "Z": 0}, "Length": 1000}],
            "Classification": {"PartRoles": [{"PartId": "1", "Role": "wall_candidate"}]},
        }

        classifications = classify_appendage_clusters_from_bundle(assembly, member)

        self.assertEqual(1, len(classifications))
        self.assertEqual("Bracket", classifications[0].role)
        self.assertEqual(["10", "11", "12"], classifications[0].part_ids)
        self.assertIn("OVERHANG_DOMINANT", classifications[0].evidence_codes)


if __name__ == "__main__":
    unittest.main()
