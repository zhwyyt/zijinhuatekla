import unittest

from zijinhua_tekla.classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, SegmentContinuityLevel
from zijinhua_tekla.classifiers.box_part_spatial_relations import classify_box_part_spatial_relations


class BoxPartSpatialRelationTests(unittest.TestCase):
    def test_classifies_main_wall_inside_outside_boundary_and_feature_gap(self):
        assembly = {
            "assemblyId": "A-1",
            "relationships": [
                {"partIdA": "wall", "partIdB": "inside", "edgeType": "Weld"},
                {"partIdA": "wall", "partIdB": "outside", "edgeType": "Weld"},
            ],
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall", "name": "COLUMN"},
                {"partId": "inside", "partPosition": "A-P-inside", "name": "ANY"},
                {"partId": "outside", "partPosition": "A-P-outside", "name": "ANY"},
                {"partId": "through", "partPosition": "A-P-through", "name": "ANY"},
                {"partId": "unknown", "partPosition": "A-P-unknown", "name": "ANY"},
            ],
        }
        member = {
            "Samples": [
                {
                    "SampleId": "S01",
                    "IsAbnormal": False,
                    "Station": 1000,
                    "SectionFeatures": {"ClosedLoops": 1, "CavityCount": 1, "OuterWidth": 1000, "OuterHeight": 1000},
                    "SectionParts": [
                        {"PartId": "wall", "RoleHint": "flange_candidate", "Center2D": {"X": 0, "Y": 492}, "CutSpanX": 968, "CutSpanY": 16, "TotalCutLength": 968},
                        {"PartId": "inside", "RoleHint": "stiffener_candidate", "Center2D": {"X": 10, "Y": 230}, "CutSpanX": 100, "CutSpanY": 16, "TotalCutLength": 100},
                        {"PartId": "through", "RoleHint": "stiffener_candidate", "Center2D": {"X": 0, "Y": 0}, "CutSpanX": 900, "CutSpanY": 900, "TotalCutLength": 900},
                    ],
                }
            ],
            "Parts": [
                {"PartId": "wall", "AxisProjection": {"Start": 0, "End": 3000}},
                {"PartId": "inside", "AxisProjection": {"Start": 900, "End": 1200}},
                {"PartId": "outside", "AxisProjection": {"Start": 900, "End": 1200}, "GeometryHints": {"OuterSideCandidate": True}},
                {"PartId": "through", "AxisProjection": {"Start": 900, "End": 1200}},
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="A-P-wall:0.0-3000.0",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, member, main_wall_groups, outside_part_ids={"outside"})

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("MAIN_WALL", by_position["A-P-wall"].relation_to_box_body)
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside"].relation_to_box_body)
        self.assertEqual("OUTSIDE_ATTACHMENT", by_position["A-P-outside"].relation_to_box_body)
        self.assertEqual("BOUNDARY_OR_THROUGH", by_position["A-P-through"].relation_to_box_body)
        self.assertEqual("INSUFFICIENT_EVIDENCE", by_position["A-P-unknown"].relation_to_box_body)
        self.assertIn("SECTION_INSIDE_CAVITY_TRACE", by_position["A-P-inside"].evidence_codes)
        self.assertIn("OUTSIDE_APPENDAGE_CLUSTER", by_position["A-P-outside"].evidence_codes)
        self.assertIn("SECTION_SPANS_BOX_BODY", by_position["A-P-through"].evidence_codes)
        self.assertEqual("FEATURE", by_position["A-P-unknown"].issue_category)


    def test_outer_side_geometry_hint_alone_is_not_enough_to_confirm_outside(self):
        assembly = {
            "assemblyId": "A-1",
            "parts": [
                {"partId": "local", "partPosition": "A-P-local", "name": "ANY"},
            ],
        }
        member = {
            "Parts": [
                {"PartId": "local", "AxisProjection": {"Start": 0, "End": 100}, "GeometryHints": {"OuterSideCandidate": True}},
            ],
        }

        rows = classify_box_part_spatial_relations(assembly, member, [])

        self.assertEqual(1, len(rows))
        self.assertEqual("INSUFFICIENT_EVIDENCE", rows[0].relation_to_box_body)
        self.assertIn("OUTER_SIDE_GEOMETRY_HINT_AUXILIARY", rows[0].evidence_codes)
        self.assertEqual("FEATURE", rows[0].issue_category)
    def test_classifies_unsampled_parts_by_projected_centroid_against_main_wall_enclosure(self):
        assembly = {
            "assemblyId": "A-1",
            "parts": [
                _projected_part("bottom", "A-P-bottom", -500, -10, -500, 10),
                _projected_part("top", "A-P-top", -500, 990, -500, 1010),
                _projected_part("left", "A-P-left", -510, 0, -490, 1000),
                _projected_part("right", "A-P-right", 490, 0, 510, 1000),
                _projected_part("inside", "A-P-inside-unsampled", -50, 450, 50, 550),
                _projected_part("outside", "A-P-outside-unsampled", 620, 450, 720, 550),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["bottom", "top", "left", "right"],
                part_positions=["A-P-bottom", "A-P-top", "A-P-left", "A-P-right"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside-unsampled"].relation_to_box_body)
        self.assertIn("PROJECTED_CENTROID_INSIDE_MAIN_WALL_ENCLOSURE", by_position["A-P-inside-unsampled"].evidence_codes)
        self.assertEqual("OUTSIDE_ATTACHMENT", by_position["A-P-outside-unsampled"].relation_to_box_body)
        self.assertIn("PROJECTED_CENTROID_OUTSIDE_MAIN_WALL_ENCLOSURE", by_position["A-P-outside-unsampled"].evidence_codes)


    def test_uses_exported_outer_loop_polygon_instead_of_bounding_box(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "outerLoop": [
                        {"u": 0, "v": 0},
                        {"u": 100, "v": 0},
                        {"u": 100, "v": 40},
                        {"u": 40, "v": 40},
                        {"u": 40, "v": 100},
                        {"u": 0, "v": 100},
                    ],
                    "source": "test.outerLoop",
                }
            },
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall"},
                _centroid_part("inside", "A-P-inside-l", 20, 80),
                _centroid_part("outside", "A-P-outside-l", 80, 80),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside-l"].relation_to_box_body)
        self.assertEqual("OUTSIDE_ATTACHMENT", by_position["A-P-outside-l"].relation_to_box_body)
        self.assertIn("EXPORTED_BOX_OUTER_LOOP_POLYGON", by_position["A-P-outside-l"].evidence_codes)

    def test_uses_member_section_feature_outer_loop_when_bundle_metadata_is_missing(self):
        assembly = {
            "assemblyId": "A-1",
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall"},
                _centroid_part("inside", "A-P-inside-sample-loop", 20, 80),
                _centroid_part("outside", "A-P-outside-sample-loop", 80, 80),
            ],
        }
        member = {
            "Samples": [
                {
                    "SampleId": "S01",
                    "SectionFeatures": {
                        "OuterLoop": [
                            {"X": 0, "Y": 0},
                            {"X": 100, "Y": 0},
                            {"X": 100, "Y": 40},
                            {"X": 40, "Y": 40},
                            {"X": 40, "Y": 100},
                            {"X": 0, "Y": 100},
                        ]
                    },
                }
            ]
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, member, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside-sample-loop"].relation_to_box_body)
        self.assertEqual("OUTSIDE_ATTACHMENT", by_position["A-P-outside-sample-loop"].relation_to_box_body)

    def test_marks_boundary_when_start_mid_end_station_loops_disagree(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "outerLoop": [
                        {"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 0, "v": 100},
                    ],
                    "stationLoops": [
                        {
                            "station": 10,
                            "partLoops": [{"partId": "wall", "points": [{"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 0, "v": 100}]}],
                        },
                        {
                            "station": 50,
                            "partLoops": [{"partId": "wall", "points": [{"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 0, "v": 100}]}],
                        },
                        {
                            "station": 90,
                            "partLoops": [{"partId": "wall", "points": [{"u": 0, "v": 0}, {"u": 60, "v": 0}, {"u": 60, "v": 100}, {"u": 0, "v": 100}]}],
                        },
                    ],
                    "source": "test.stationLoops",
                }
            },
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall"},
                _centroid_part("mixed", "A-P-mixed", 80, 50, station_start=0, station_end=100),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("BOUNDARY_OR_THROUGH", by_position["A-P-mixed"].relation_to_box_body)
        self.assertIn("PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS", by_position["A-P-mixed"].evidence_codes)

    def test_treats_inside_and_cavity_station_mix_as_inside_body(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "stationLoops": [
                        {
                            "station": 10,
                            "partLoops": [
                                {"partId": "bottom", "points": [{"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 20}, {"u": 0, "v": 20}]},
                                {"partId": "top", "points": [{"u": 0, "v": 80}, {"u": 100, "v": 80}, {"u": 100, "v": 100}, {"u": 0, "v": 100}]},
                                {"partId": "left", "points": [{"u": 0, "v": 0}, {"u": 20, "v": 0}, {"u": 20, "v": 100}, {"u": 0, "v": 100}]},
                                {"partId": "right", "points": [{"u": 80, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 80, "v": 100}]},
                            ],
                        },
                        {
                            "station": 50,
                            "partLoops": [
                                {"partId": "bottom", "points": [{"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 20}, {"u": 0, "v": 20}]},
                                {"partId": "top", "points": [{"u": 0, "v": 80}, {"u": 100, "v": 80}, {"u": 100, "v": 100}, {"u": 0, "v": 100}]},
                                {"partId": "left", "points": [{"u": 0, "v": 0}, {"u": 20, "v": 0}, {"u": 20, "v": 100}, {"u": 0, "v": 100}]},
                                {"partId": "right", "points": [{"u": 80, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 80, "v": 100}]},
                            ],
                        },
                        {
                            "station": 90,
                            "partLoops": [
                                {"partId": "bottom", "points": [{"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 60}, {"u": 0, "v": 60}]},
                                {"partId": "top", "points": [{"u": 0, "v": 80}, {"u": 100, "v": 80}, {"u": 100, "v": 100}, {"u": 0, "v": 100}]},
                                {"partId": "left", "points": [{"u": 0, "v": 0}, {"u": 20, "v": 0}, {"u": 20, "v": 100}, {"u": 0, "v": 100}]},
                                {"partId": "right", "points": [{"u": 80, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 80, "v": 100}]},
                            ],
                        },
                    ],
                    "source": "test.stationLoops",
                }
            },
            "parts": [
                {"partId": "bottom", "partPosition": "A-P-bottom"},
                {"partId": "top", "partPosition": "A-P-top"},
                {"partId": "left", "partPosition": "A-P-left"},
                {"partId": "right", "partPosition": "A-P-right"},
                _centroid_part("inner", "A-P-tight-inner", 30, 50, station_start=0, station_end=100),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["bottom", "top", "left", "right"],
                part_positions=["A-P-bottom", "A-P-top", "A-P-left", "A-P-right"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-tight-inner"].relation_to_box_body)
        self.assertIn("POINT_IN_CAVITY_LOOP", by_position["A-P-tight-inner"].evidence_codes)

    def test_ignores_local_incomplete_station_topology_when_cavity_reference_exists(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "stationLoops": [
                        {
                            "station": 10,
                            "partLoops": [
                                {"partId": "bottom", "points": [{"u": 0, "v": 0}, {"u": 1000, "v": 0}, {"u": 1000, "v": 20}, {"u": 0, "v": 20}]},
                                {"partId": "top", "points": [{"u": 0, "v": 980}, {"u": 1000, "v": 980}, {"u": 1000, "v": 1000}, {"u": 0, "v": 1000}]},
                                {"partId": "left", "points": [{"u": 0, "v": 0}, {"u": 20, "v": 0}, {"u": 20, "v": 1000}, {"u": 0, "v": 1000}]},
                                {"partId": "right", "points": [{"u": 980, "v": 0}, {"u": 1000, "v": 0}, {"u": 1000, "v": 1000}, {"u": 980, "v": 1000}]},
                            ],
                        },
                        {
                            "station": 500,
                            "partLoops": [
                                {"partId": "left", "points": [{"u": 0, "v": 0}, {"u": 20, "v": 0}, {"u": 20, "v": 1000}, {"u": 0, "v": 1000}]},
                            ],
                        },
                        {
                            "station": 900,
                            "partLoops": [
                                {"partId": "right", "points": [{"u": 980, "v": 0}, {"u": 1000, "v": 0}, {"u": 1000, "v": 1000}, {"u": 980, "v": 1000}]},
                            ],
                        },
                    ],
                    "source": "test.stationLoops",
                }
            },
            "parts": [
                {"partId": "bottom", "partPosition": "A-P-bottom"},
                {"partId": "top", "partPosition": "A-P-top"},
                {"partId": "left", "partPosition": "A-P-left"},
                {"partId": "right", "partPosition": "A-P-right"},
                _centroid_part("inside", "A-P-inside-local-stations", 500, 500, station_start=475, station_end=925),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["bottom", "top", "left", "right"],
                part_positions=["A-P-bottom", "A-P-top", "A-P-left", "A-P-right"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside-local-stations"].relation_to_box_body)
    def test_station_part_loop_topology_preserves_concave_outer_loop(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "stationLoops": [
                        {
                            "station": 500,
                            "partLoops": [
                                {
                                    "partId": "wall",
                                    "points": [
                                        {"u": 0, "v": 0},
                                        {"u": 100, "v": 0},
                                        {"u": 100, "v": 40},
                                        {"u": 40, "v": 40},
                                        {"u": 40, "v": 100},
                                        {"u": 0, "v": 100},
                                    ],
                                }
                            ],
                        }
                    ],
                    "source": "test.stationLoops",
                }
            },
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall"},
                _centroid_part("inside", "A-P-inside-l", 20, 80, station_start=40, station_end=60),
                _centroid_part("outside", "A-P-outside-concave-void", 80, 80, station_start=40, station_end=60),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside-l"].relation_to_box_body)
        self.assertEqual("OUTSIDE_ATTACHMENT", by_position["A-P-outside-concave-void"].relation_to_box_body)
        self.assertIn("SHAPELY_BOX_SECTION_TOPOLOGY", by_position["A-P-outside-concave-void"].evidence_codes)

    def test_station_part_loop_topology_treats_inner_cavity_as_inside_body(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "stationLoops": [
                        {
                            "station": 500,
                            "partLoops": [
                                {
                                    "partId": "wall",
                                    "points": [
                                        {"u": 0, "v": 0},
                                        {"u": 100, "v": 0},
                                        {"u": 100, "v": 10},
                                        {"u": 0, "v": 10},
                                    ],
                                },
                                {
                                    "partId": "wall",
                                    "points": [
                                        {"u": 0, "v": 90},
                                        {"u": 100, "v": 90},
                                        {"u": 100, "v": 100},
                                        {"u": 0, "v": 100},
                                    ],
                                },
                                {
                                    "partId": "wall",
                                    "points": [
                                        {"u": 0, "v": 0},
                                        {"u": 10, "v": 0},
                                        {"u": 10, "v": 100},
                                        {"u": 0, "v": 100},
                                    ],
                                },
                                {
                                    "partId": "wall",
                                    "points": [
                                        {"u": 90, "v": 0},
                                        {"u": 100, "v": 0},
                                        {"u": 100, "v": 100},
                                        {"u": 90, "v": 100},
                                    ],
                                },
                            ],
                        }
                    ],
                    "source": "test.stationLoops",
                }
            },
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall"},
                _centroid_part("inside", "A-P-inside-shell", 5, 5, station_start=40, station_end=60),
                _centroid_part("cavity", "A-P-cavity", 50, 50, station_start=40, station_end=60),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-inside-shell"].relation_to_box_body)
        self.assertEqual("INSIDE_BODY", by_position["A-P-cavity"].relation_to_box_body)
        self.assertIn("POINT_IN_CAVITY_LOOP", by_position["A-P-cavity"].evidence_codes)

    def test_prefers_exported_section_loops_over_degenerate_legacy_points(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "stationLoops": [
                        {
                            "station": 500,
                            "partLoops": [
                                {
                                    "partId": "wall",
                                    "points": [{"u": 0, "v": 0}, {"u": 50, "v": 0}, {"u": 100, "v": 0}],
                                    "sectionLoops": [
                                        {"points": [{"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 10}, {"u": 0, "v": 10}], "isClosed": True, "isValid": True, "area": 1000},
                                        {"points": [{"u": 0, "v": 90}, {"u": 100, "v": 90}, {"u": 100, "v": 100}, {"u": 0, "v": 100}], "isClosed": True, "isValid": True, "area": 1000},
                                        {"points": [{"u": 0, "v": 0}, {"u": 10, "v": 0}, {"u": 10, "v": 100}, {"u": 0, "v": 100}], "isClosed": True, "isValid": True, "area": 1000},
                                        {"points": [{"u": 90, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 100}, {"u": 90, "v": 100}], "isClosed": True, "isValid": True, "area": 1000},
                                    ],
                                }
                            ],
                        }
                    ],
                    "source": "teklaSolidFaceSectionSegments.v2",
                }
            },
            "parts": [
                {"partId": "wall", "partPosition": "A-P-wall"},
                _centroid_part("cavity", "A-P-cavity-new-loop", 50, 50, station_start=40, station_end=60),
            ],
        }
        main_wall_groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["SECTION_VALIDATED"],
                confidence=0.92,
            )
        ]

        rows = classify_box_part_spatial_relations(assembly, None, main_wall_groups)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("INSIDE_BODY", by_position["A-P-cavity-new-loop"].relation_to_box_body)
        self.assertIn("EXPORTED_SECTION_LOOP_TOPOLOGY", by_position["A-P-cavity-new-loop"].evidence_codes)
def _projected_part(part_id, position, min_u, min_v, max_u, max_v):
    return {
        "partId": part_id,
        "partPosition": position,
        "mainMaterialEvidence": {
            "sectionProjectionEvidence": {
                "projectedCentroid": {"u": (min_u + max_u) / 2, "v": (min_v + max_v) / 2},
                "projectedBoundsMin": {"u": min_u, "v": min_v},
                "projectedBoundsMax": {"u": max_u, "v": max_v},
                "projectedContour": [
                    {"u": min_u, "v": min_v},
                    {"u": max_u, "v": min_v},
                    {"u": max_u, "v": max_v},
                    {"u": min_u, "v": max_v},
                ],
            }
        },
    }

def _centroid_part(part_id, position, u, v, station_start=0, station_end=0):
    return {
        "partId": part_id,
        "partPosition": position,
        "mainMaterialEvidence": {
            "axisStationStart": station_start,
            "axisStationEnd": station_end,
            "sectionProjectionEvidence": {
                "projectedCentroid": {"u": u, "v": v},
            }
        },
    }
if __name__ == "__main__":
    unittest.main()

