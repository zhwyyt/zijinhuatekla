import unittest

from zijinhua_tekla.adapters.normalized import normalized_part_from_bundle_part


class NormalizedAdapterTests(unittest.TestCase):
    def test_normalized_part_uses_model_profile_and_holes(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 11,
                "partPosition": "A-P-11",
                "name": "肋板",
                "profileString": "PL16*230",
                "material": "Q355B",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 16,
                "obbDims": {"x": 230.0, "y": 90.0, "z": 16.0},
                "boltHoles": [{"diameter": 22}, {"diameter": 22}],
                "weldDetails": [{"weldType": "FILLET"}],
                "booleanCutCount": 1,
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "EDGE_CHAMFER",
                        "chamferType": "CHAMFER_LINE",
                        "chamferX": 8,
                        "chamferY": 8,
                        "isBevel": True,
                    }
                ],
                "contourSegments": [
                    {"chamferType": "CHAMFER_LINE", "chamferX": 12, "chamferY": 12},
                    {"chamferType": "CHAMFER_NONE", "chamferX": 0, "chamferY": 0},
                ],
            }
        )

        self.assertEqual("11", part.part_id)
        self.assertEqual("A-P-11", part.part_position)
        self.assertEqual("PL16*230", part.profile)
        self.assertEqual(2, part.bolt_hole_count)
        self.assertEqual(1, part.weld_count)
        self.assertEqual((230.0, 90.0, 16.0), part.obb_dims)
        self.assertEqual((("CHAMFER_LINE", 12.0, 12.0), ("CHAMFER_NONE", 0.0, 0.0)), part.contour_chamfers)
        self.assertEqual(1, part.edge_bevel_count)
        self.assertTrue(part.has_edge_bevel)
        self.assertGreater(part.length, 0)

    def test_square_fitting_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 12,
                "partPosition": "A-P-12",
                "profileString": "PL16*200",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "edgeBevels": [
                    {
                        "kind": "FITTING",
                        "angleToPlateNormalDeg": 90.0,
                        "isBevel": False,
                    }
                ],
                "edgeBevelCount": 0,
                "hasEdgeBevel": False,
            }
        )
        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_boolean_cut_larger_than_part_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 13,
                "partPosition": "A-P-13",
                "profileString": "PL20",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "obbDims": {"x": 367.0, "y": 340.0, "z": 20.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 83.0,
                        "chamferY": 700.0,
                        "dz1": 90.0,
                        "isBevel": True,
                    }
                ],
            }
        )
        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_boolean_cut_proven_not_to_cut_solid_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 24,
                "partPosition": "A-PX-4",
                "profileString": "PL20*490",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 20.0,
                        "chamferY": 20.0,
                        "dz1": 490.0,
                        "isBevel": True,
                        "cutsFatherSolid": False,
                        "cutProof": "AABB_MISS",
                    }
                ],
            }
        )
        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_zero_dimension_cut_plane_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 70851331,
                "partPosition": "T3-H-528",
                "profileString": "BH300*150*6*8",
                "runtimeType": "Beam",
                "isPlateLike": False,
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "CUT_PLANE",
                        "chamferX": 0,
                        "chamferY": 0,
                        "dz1": 0,
                        "dz2": 0,
                        "firstBevelDimension": 0,
                        "secondBevelDimension": 0,
                        "isBevel": True,
                    }
                ],
            }
        )

        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_boolean_cut_proven_to_cut_solid_keeps_plate_edge_wedge(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 25,
                "partPosition": "A-PX-5",
                "profileString": "PL14",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 14,
                "obbDims": {"x": 840.0, "y": 310.0, "z": 14.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 14.0,
                        "chamferY": 14.0,
                        "dz1": 1150.0,
                        "isBevel": True,
                        "cutsFatherSolid": True,
                        "cutProof": "GET_CUT_PART",
                    }
                ],
            }
        )
        self.assertEqual(1, part.edge_bevel_count)
        self.assertTrue(part.has_edge_bevel)

    def test_boolean_cut_that_misses_part_box_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 23,
                "partPosition": "A-PX-3",
                "profileString": "PL20*490",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
                "boundingBox": {
                    "min": {"x": 1169.9, "y": 9451.2, "z": 30580.0},
                    "max": {"x": 1356.6, "y": 9659.7, "z": 31070.0},
                },
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 20.0,
                        "chamferY": 20.0,
                        "dz1": 490.0,
                        "isBevel": True,
                        "boundingBox": {
                            "min": {"x": 519.3, "y": 9449.5, "z": 31258.0},
                            "max": {"x": 1571.3, "y": 9479.5, "z": 31288.0},
                        },
                    }
                ],
            }
        )
        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_long_bar_boolean_cut_missing_dz_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 20,
                "partPosition": "A-PX-2",
                "profileString": "PL20*490",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 1052.0019,
                        "chamferY": 30.0666,
                        "dz1": 30.0,
                        "isBevel": True,
                        "operativePartId": 99,
                    }
                ],
            }
        )
        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_missed_boolean_cut_is_not_counted(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 27,
                "partPosition": "A-PX-7",
                "profileString": "PL20*490",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
                "boltHoleCount": 2,
                "booleanCutCount": 1,
                "holeLikeFeatureCount": 3,
                "booleanCutDetails": [
                    {
                        "operativePartId": 99,
                        "cutsFatherSolid": False,
                        "cutProof": "AABB_MISS",
                        "boundingBox": {
                            "min": {"x": 519.3, "y": 9449.5, "z": 31258.0},
                            "max": {"x": 1571.3, "y": 9479.5, "z": 31288.0},
                        },
                    }
                ],
            }
        )
        self.assertEqual(0, part.boolean_cut_count)
        self.assertEqual(2, part.hole_like_feature_count)

    def test_proven_edge_wedge_is_an_edge_bevel_without_size_threshold(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 28,
                "partPosition": "A-PX-8",
                "profileString": "PL20*490",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 30.0,
                        "chamferY": 30.0,
                        "dz1": 490.0,
                        "isBevel": True,
                        "cutsFatherSolid": True,
                        "cutProof": "GET_CUT_PART",
                    }
                ],
            }
        )
        self.assertEqual(1, part.edge_bevel_count)
        self.assertTrue(part.has_edge_bevel)

    def test_proven_long_bar_cut_is_an_edge_bevel_without_size_threshold(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 26,
                "partPosition": "A-PX-6",
                "profileString": "PL20*490",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 1052.0019,
                        "chamferY": 30.0666,
                        "dz1": 30.0,
                        "isBevel": True,
                        "cutsFatherSolid": True,
                        "cutProof": "GET_CUT_PART",
                    }
                ],
            }
        )
        self.assertEqual(1, part.edge_bevel_count)
        self.assertTrue(part.has_edge_bevel)

    def test_unproven_plate_edge_wedge_is_not_an_edge_bevel(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 16,
                "partPosition": "A-PX-1",
                "profileString": "PL14",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 14,
                "obbDims": {"x": 840.0, "y": 310.0, "z": 14.0},
                "hasEdgeBevel": True,
                "edgeBevelCount": 1,
                "edgeBevels": [
                    {
                        "kind": "BOOLEAN_CUT",
                        "chamferX": 14.0,
                        "chamferY": 14.0,
                        "dz1": 1150.0,
                        "isBevel": True,
                    }
                ],
            }
        )
        self.assertEqual(0, part.edge_bevel_count)
        self.assertFalse(part.has_edge_bevel)

    def test_exported_end_chamfer_is_kept_for_sections(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 14,
                "partPosition": "A-L-1",
                "profileString": "L75*5",
                "runtimeType": "Beam",
                "isPlateLike": False,
                "obbDims": {"x": 1800.0, "y": 75.0, "z": 75.0},
                "endChamferCount": 2,
                "hasEndChamfer": True,
            }
        )
        self.assertEqual(2, part.end_chamfer_count)
        self.assertTrue(part.has_end_chamfer)

    def test_foreign_boolean_cut_on_plate_is_not_an_opening(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 17,
                "partPosition": "A-P-17",
                "profileString": "PL20",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 20,
                "obbDims": {"x": 367.0, "y": 340.0, "z": 20.0},
                "boundingBox": {
                    "min": {"x": 18600.0, "y": 280.0, "z": 35730.0},
                    "max": {"x": 18967.0, "y": 620.0, "z": 35750.0},
                },
                "boltHoleCount": 0,
                "holeLikeFeatureCount": 1,
                "booleanCutCount": 1,
                "booleanCutDetails": [
                    {
                        "operativePartId": 99,
                        "cutType": "BOOLEAN_CUT",
                        "boundingBox": {
                            "min": {"x": 18947.0, "y": 100.0, "z": 35665.0},
                            "max": {"x": 19030.0, "y": 800.0, "z": 35755.0},
                        },
                    }
                ],
            }
        )
        self.assertEqual(0, part.hole_like_feature_count)
        self.assertFalse(part.has_end_chamfer)

    def test_interior_boolean_cut_on_plate_is_an_opening(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 18,
                "partPosition": "A-P-18",
                "profileString": "PL12",
                "runtimeType": "ContourPlate",
                "isPlateLike": True,
                "thickness": 12,
                "obbDims": {"x": 524.0, "y": 524.0, "z": 12.0},
                "boundingBox": {
                    "min": {"x": 10633.0, "y": 458.0, "z": 34994.0},
                    "max": {"x": 11157.0, "y": 470.0, "z": 35516.0},
                },
                "boltHoleCount": 0,
                "holeLikeFeatureCount": 1,
                "booleanCutCount": 1,
                "booleanCutDetails": [
                    {
                        "operativePartId": 88,
                        "cutType": "BOOLEAN_CUT",
                        "boundingBox": {
                            "min": {"x": 10733.0, "y": 439.0, "z": 35094.0},
                            "max": {"x": 11057.0, "y": 489.0, "z": 35416.0},
                        },
                    }
                ],
            }
        )
        self.assertEqual(1, part.hole_like_feature_count)
        self.assertFalse(part.has_end_chamfer)

    def test_plate_corner_boolean_cut_is_chamfer_not_opening(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 19,
                "partPosition": "A-P-19",
                "profileString": "PL16*200",
                "runtimeType": "Beam",
                "isPlateLike": True,
                "thickness": 16,
                "obbDims": {"x": 364.0, "y": 200.0, "z": 16.0},
                "boundingBox": {
                    "min": {"x": 19012.0, "y": 54592.0, "z": 30912.0},
                    "max": {"x": 19229.0, "y": 54608.0, "z": 31268.0},
                },
                "boltHoleCount": 0,
                "holeLikeFeatureCount": 2,
                "booleanCutCount": 2,
                "booleanCutDetails": [
                    {
                        "operativePartId": 21,
                        "cutType": "BOOLEAN_CUT",
                        "boundingBox": {
                            "min": {"x": 19006.0, "y": 54589.0, "z": 30912.0},
                            "max": {"x": 19071.0, "y": 54611.0, "z": 30952.0},
                        },
                    },
                    {
                        "operativePartId": 22,
                        "cutType": "BOOLEAN_CUT",
                        "boundingBox": {
                            "min": {"x": 19026.0, "y": 54590.0, "z": 31228.0},
                            "max": {"x": 19091.0, "y": 54611.0, "z": 31268.0},
                        },
                    },
                ],
            }
        )
        self.assertEqual(0, part.hole_like_feature_count)
        self.assertTrue(part.has_end_chamfer)
        self.assertEqual(2, part.end_chamfer_count)

    def test_end_boolean_cut_on_section_is_inferred_as_chamfer(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 15,
                "partPosition": "A-L-2",
                "profileString": "L75*5",
                "runtimeType": "Beam",
                "isPlateLike": False,
                "obbDims": {"x": 2000.0, "y": 75.0, "z": 5.0},
                "boundingBox": {
                    "min": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "max": {"x": 2000.0, "y": 75.0, "z": 5.0},
                },
                "booleanCutDetails": [
                    {
                        "operativePartId": 99,
                        "cutType": "BOOLEAN_CUT",
                        "boundingBox": {
                            "min": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "max": {"x": 80.0, "y": 40.0, "z": 5.0},
                        },
                    }
                ],
            }
        )
        self.assertTrue(part.has_end_chamfer)
        self.assertEqual(1, part.end_chamfer_count)

    def test_declared_process_from_custom_properties(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 21,
                "partPosition": "A-P-21",
                "profileString": "PL16*30",
                "customProperties": {"工序": "不下"},
            }
        )
        self.assertEqual("不下", part.declared_process)

    def test_declared_process_from_property_list(self):
        part = normalized_part_from_bundle_part(
            {
                "partId": 22,
                "partPosition": "A-P-22",
                "profileString": "PL16*30",
                "customProperties": [{"name": "工序", "value": "不下"}],
            }
        )
        self.assertEqual("不下", part.declared_process)


if __name__ == "__main__":
    unittest.main()
