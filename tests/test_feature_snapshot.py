import unittest
from collections import Counter

from zijinhua_tekla.features import (
    build_feature_index,
    feature_snapshots_from_bundle_parts,
    feature_snapshot_from_teklatest_part_features,
    snapshot_to_part_dict,
)
from zijinhua_tekla.rules import find_equivalent_parts, row_part_score


class FeatureSnapshotTests(unittest.TestCase):
    def test_bundle_part_maps_to_stable_part_feature_snapshot(self):
        part = {
            "partId": 70835880,
            "runtimeType": "ContourPlate",
            "name": "连接板",
            "material": "Q355B",
            "profileString": "PL14",
            "isPlateLike": True,
            "isSpecialShape": False,
            "obbDims": {"x": 318.5, "y": 239.8, "z": 14},
            "thickness": 14,
            "partPosition": "T3-P-4869",
            "contourVertexCount": 4,
            "concaveCornerCount": 0,
            "holeLikeFeatureCount": 1,
            "booleanCutCount": 0,
            "boltHoleCount": 1,
            "hasArcContour": True,
            "contourSegments": [
                {"length": 285.4},
                {"length": 243.3},
                {"length": 281.3},
                {"length": 194.8},
            ],
            "weldDetails": [{"type": "shop"}],
        }

        snapshot = feature_snapshots_from_bundle_parts(
            [part],
            rel_by_part={"70835880": Counter({"Contact": 2, "Bolt": 1})},
        )[0]

        self.assertEqual("70835880", snapshot.part_id)
        self.assertEqual("T3-P-4869", snapshot.position)
        self.assertEqual("PL14", snapshot.profile)
        self.assertTrue(snapshot.is_plate_like)
        self.assertEqual(1, snapshot.bolt_hole_count)
        self.assertEqual(0, snapshot.boolean_cut_count)
        self.assertEqual(4, snapshot.contour_vertex_count)
        self.assertEqual(1, snapshot.weld_count)
        self.assertEqual(2, snapshot.relationship_counts["Contact"])
        self.assertEqual([285.4, 243.3, 281.3, 194.8], snapshot.contour_segment_lengths)

    def test_snapshot_can_drive_existing_dimension_and_matching_rules(self):
        parent = {
            "partId": 68294737,
            "runtimeType": "Beam",
            "name": "钢梁",
            "profileString": "BH400*200*7*10",
            "isPlateLike": False,
            "obbDims": {"x": 400.0, "y": 389.4, "z": 200.0},
            "thickness": 400,
            "partPosition": "T3-H-558",
        }
        child_row = {"零件名称": "T3-H-558f", "规格": "PL7*380", "长度": 389, "数量": 2}
        snapshots = feature_snapshots_from_bundle_parts([parent])
        index = build_feature_index(snapshots)

        parts, method, note = find_equivalent_parts(child_row, index.by_position, index.part_dicts)

        self.assertEqual("derivedFromProfilePart", method)
        self.assertEqual(1, len(parts))
        self.assertIn("BH400*200*7*10", note)

    def test_snapshot_to_part_dict_preserves_rule_compatibility(self):
        row = {"零件名称": "T3-P-4885", "规格": "PL14*278", "长度": 325}
        snapshot = feature_snapshots_from_bundle_parts(
            [
                {
                    "partId": 70786583,
                    "runtimeType": "ContourPlate",
                    "name": "连接板",
                    "profileString": "PL14",
                    "isPlateLike": True,
                    "obbDims": {"x": 388.3, "y": 267.3, "z": 14},
                    "thickness": 14,
                    "partPosition": "T3-P-4885",
                    "contourSegments": [
                        {"length": 337.7},
                        {"length": 185.9},
                        {"length": 325.0},
                        {"length": 277.7},
                    ],
                }
            ]
        )[0]

        spec_ok, length_ok, _, _, part_len, part_width = row_part_score(row, snapshot_to_part_dict(snapshot))

        self.assertTrue(spec_ok)
        self.assertTrue(length_ok)
        self.assertAlmostEqual(325.0, part_len, places=1)
        self.assertAlmostEqual(277.7, part_width, places=1)

    def test_teklatest_part_features_map_to_snapshot_contract(self):
        part_features = {
            "BasicInfo": {
                "PartGuid": "guid-100",
                "PartMark": "A1-P-100",
                "PartName": "连接板",
                "Profile": "PL12",
                "Material": "Q355B",
                "PartType": "PLATE",
                "Length": 320,
                "Width": 180,
                "Height": 12,
            },
            "Holes": [{}, {}, {}],
            "BoltHoles": [{}, {}],
            "InternalHoles": [{}],
            "Bendings": [{}],
            "Chamfers": [{}, {}],
            "Cutouts": [{}],
            "Notches": [{}],
            "Welds": [{}, {}, {}],
            "ShapeInfo": {
                "IsRegular": False,
                "ShapeType": "异形板",
                "ContourPointCount": 6,
            },
        }

        snapshot = feature_snapshot_from_teklatest_part_features(part_features)

        self.assertEqual("guid-100", snapshot.part_id)
        self.assertEqual("A1-P-100", snapshot.position)
        self.assertEqual("PL12", snapshot.profile)
        self.assertTrue(snapshot.is_plate_like)
        self.assertTrue(snapshot.is_special_shape)
        self.assertEqual({"x": 320.0, "y": 180.0, "z": 12.0}, snapshot.obb_dims)
        self.assertEqual(3, snapshot.hole_like_feature_count)
        self.assertEqual(2, snapshot.bolt_hole_count)
        self.assertEqual(1, snapshot.internal_hole_count)
        self.assertEqual(2, snapshot.chamfer_count)
        self.assertEqual(1, snapshot.cutout_count)
        self.assertEqual(1, snapshot.notch_count)
        self.assertEqual(1, snapshot.bending_count)
        self.assertEqual(3, snapshot.weld_count)
        self.assertEqual("异形板", snapshot.shape_type)
        self.assertFalse(snapshot.is_regular_shape)


if __name__ == "__main__":
    unittest.main()
