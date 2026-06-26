import unittest

from zijinhua_tekla.classifiers.box_main_material_segments import (
    SegmentContinuityLevel,
    classify_box_main_material_segment_groups,
)


class BoxMainMaterialSegmentTests(unittest.TestCase):
    def test_groups_same_face_adjacent_station_segments_without_requiring_same_thickness(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [_weld("1", "2")],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000, thickness=16, next_id="2", next_gap=4),
                _wall_part("2", "A-P-2", "FACE_A", 3004, 6100, thickness=20, previous_id="1", previous_gap=4),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual(1, len(groups))
        group = groups[0]
        self.assertEqual("BOX_MAIN_MATERIAL_SEGMENT_GROUP", group.group_type)
        self.assertEqual("FACE_A", group.face_id)
        self.assertEqual(["A-P-1", "A-P-2"], group.part_positions)
        self.assertEqual(["1", "2"], group.part_ids)
        self.assertEqual("A-P-1:0.0-3000.0;A-P-2:3004.0-6100.0", group.station_ranges)
        self.assertEqual(SegmentContinuityLevel.CONTINUOUS, group.continuity_level)
        self.assertIn("THICKNESS_AUXILIARY_ONLY", group.evidence_codes)
        self.assertEqual("16;20", group.evidence_summary["thicknesses"])

    def test_does_not_merge_different_body_faces(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [_weld("1", "2"), _weld("3", "4")],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000, next_id="2", next_gap=0),
                _wall_part("2", "A-P-2", "FACE_A", 3000, 6000, previous_id="1", previous_gap=0),
                _wall_part("3", "A-P-3", "FACE_B", 0, 3000, next_id="4", next_gap=0),
                _wall_part("4", "A-P-4", "FACE_B", 3000, 6000, previous_id="3", previous_gap=0),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual(["FACE_A", "FACE_B"], [group.face_id for group in groups])
        self.assertEqual([["A-P-1", "A-P-2"], ["A-P-3", "A-P-4"]], [group.part_positions for group in groups])

    def test_marks_large_station_gap_as_insufficient_evidence_segments(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [_weld("1", "2")],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000, next_id="2", next_gap=420),
                _wall_part("2", "A-P-2", "FACE_A", 3420, 6500, previous_id="1", previous_gap=420),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual([["A-P-1"], ["A-P-2"]], [group.part_positions for group in groups])
        self.assertEqual(
            [SegmentContinuityLevel.INSUFFICIENT_EVIDENCE, SegmentContinuityLevel.INSUFFICIENT_EVIDENCE],
            [group.continuity_level for group in groups],
        )

    def test_splits_same_face_into_station_runs_instead_of_merging_every_face_part(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [_weld("1", "2"), _weld("3", "4")],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000, next_id="2", next_gap=0),
                _wall_part("2", "A-P-2", "FACE_A", 3000, 6000, previous_id="1", previous_gap=0),
                _wall_part("3", "A-P-3", "FACE_A", 12000, 15000, next_id="4", next_gap=0),
                _wall_part("4", "A-P-4", "FACE_A", 15000, 18000, previous_id="3", previous_gap=0),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual([ ["A-P-1", "A-P-2"], ["A-P-3", "A-P-4"] ], [group.part_positions for group in groups])
        self.assertEqual([SegmentContinuityLevel.CONTINUOUS, SegmentContinuityLevel.CONTINUOUS], [group.continuity_level for group in groups])

    def test_same_face_station_neighbors_without_relationship_stay_separate_evidence(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000),
                _wall_part("2", "A-P-2", "FACE_A", 3000, 6000),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual([["A-P-1"], ["A-P-2"]], [group.part_positions for group in groups])
        self.assertEqual(
            [SegmentContinuityLevel.INSUFFICIENT_EVIDENCE, SegmentContinuityLevel.INSUFFICIENT_EVIDENCE],
            [group.continuity_level for group in groups],
        )

    def test_relationship_graph_does_not_merge_across_face_buckets_without_better_face_evidence(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [
                {"partIdA": "1", "partIdB": "2", "edgeType": "Weld"},
                {"partIdA": "2", "partIdB": "3", "edgeType": "Contact"},
            ],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000),
                _wall_part("2", "A-P-2", "FACE_B", 3000, 6000),
                _wall_part("3", "A-P-3", "FACE_B", 6000, 9000),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual([["A-P-1"], ["A-P-2", "A-P-3"]], [group.part_positions for group in groups])
        self.assertEqual(
            [SegmentContinuityLevel.INSUFFICIENT_EVIDENCE, SegmentContinuityLevel.CONTINUOUS],
            [group.continuity_level for group in groups],
        )
        self.assertIn("RELATIONSHIP_TOPOLOGY_CHAIN", groups[1].evidence_codes)

    def test_large_station_overlap_relationship_does_not_merge_parallel_parts(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [_weld("1", "2")],
            "parts": [
                _wall_part("1", "A-P-1", "FACE_A", 0, 3000),
                _wall_part("2", "A-P-2", "FACE_B", 100, 2900),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual([["A-P-1"], ["A-P-2"]], [group.part_positions for group in groups])
    def test_single_segment_candidate_is_kept_as_insufficient_evidence(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "parts": [_wall_part("1", "A-P-1", "FACE_A", 0, 3000)],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual(1, len(groups))
        self.assertEqual(["A-P-1"], groups[0].part_positions)
        self.assertEqual(SegmentContinuityLevel.INSUFFICIENT_EVIDENCE, groups[0].continuity_level)
    def test_missing_main_material_evidence_is_reported_as_feature_gap(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "parts": [
                {"partId": "1", "partPosition": "A-P-1", "isPlateLike": True},
                _wall_part("2", "A-P-2", "FACE_A", 0, 3000),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly)

        self.assertEqual(1, len(groups))
        self.assertEqual(SegmentContinuityLevel.INSUFFICIENT_EVIDENCE, groups[0].continuity_level)
        self.assertEqual("FEATURE", groups[0].issue_category)
        self.assertIn("MISSING_MAIN_MATERIAL_EVIDENCE", groups[0].evidence_codes)

    def test_prefers_member_section_samples_over_radial_face_buckets_for_box(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [],
            "parts": [
                _wall_part("1", "A-P-left-1", "RADIAL_X_NEG", 0, 3000),
                _wall_part("2", "A-P-left-2", "RADIAL_Y_NEG", 3000, 6000),
                _wall_part("3", "A-P-right-1", "RADIAL_X_POS", 0, 3000),
                _wall_part("4", "A-P-right-2", "RADIAL_Y_POS", 3000, 6000),
                _wall_part("5", "A-P-stiffener", "RADIAL_Y_POS", 1000, 1200),
            ],
        }
        member = {
            "Samples": [
                {
                    "SampleId": "S01",
                    "IsAbnormal": True,
                    "SectionFeatures": {"ClosedLoops": 0, "CavityCount": 0},
                    "SectionParts": [
                        {"PartId": "1", "RoleHint": "flange_candidate"},
                        {"PartId": "2", "RoleHint": "flange_candidate"},
                        {"PartId": "5", "RoleHint": "stiffener_candidate"},
                    ],
                },
                {
                    "SampleId": "S02",
                    "IsAbnormal": False,
                    "SectionFeatures": {"ClosedLoops": 1, "CavityCount": 1, "OuterWidth": 1000, "OuterHeight": 1000},
                    "SectionParts": [
                        {"PartId": "1", "RoleHint": "flange_candidate", "TotalCutLength": 960},
                        {"PartId": "2", "RoleHint": "flange_candidate", "TotalCutLength": 970},
                        {"PartId": "3", "RoleHint": "web_candidate", "TotalCutLength": 980},
                        {"PartId": "4", "RoleHint": "web_candidate", "TotalCutLength": 990},
                        {"PartId": "5", "RoleHint": "flange_candidate", "TotalCutLength": 120},
                    ],
                },
            ]
        }

        groups = classify_box_main_material_segment_groups(assembly, member)

        self.assertEqual(1, len(groups))
        group = groups[0]
        self.assertEqual("BOX_MAIN_WALL_CONFIRMED_SET", group.group_type)
        self.assertEqual("BOX_MAIN_WALL_CONFIRMED", group.face_id)
        self.assertEqual(
            ["A-P-left-1", "A-P-right-1", "A-P-left-2", "A-P-right-2"],
            group.part_positions,
        )
        self.assertNotIn("A-P-stiffener", group.part_positions)
        self.assertIn("BOX_WALL_TRACE_SEED", group.evidence_codes)
        self.assertIn("BOX_OUTER_WALL_TRACE_CONFIRMED", group.evidence_codes)
        self.assertIn("AXIS_CONTINUITY_EXPANDED", group.evidence_codes)
        self.assertIn("SECTION_VALIDATED", group.evidence_codes)
        self.assertNotIn("SAME_BODY_FACE_BUCKET", group.evidence_codes)
        self.assertIn("A-P-left-1", group.evidence_summary["trace_seed_part_positions"])
        self.assertIn("A-P-right-2", group.evidence_summary["trace_seed_part_positions"])

    def test_does_not_confirm_isolated_unsampled_wall_candidate_from_section_seed(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [],
            "parts": [
                _wall_part("1", "A-P-sampled", "RADIAL_X_NEG", 0, 3000),
                {**_wall_part("2", "A-P-unsampled", "RADIAL_Y_NEG", 9000, 9300), "name": "COLUMN"},
            ],
        }
        member = {
            "Samples": [
                {
                    "SampleId": "S02",
                    "IsAbnormal": False,
                    "SectionFeatures": {"ClosedLoops": 1, "CavityCount": 1},
                    "SectionParts": [{"PartId": "1", "RoleHint": "flange_candidate"}],
                }
            ],
            "Parts": [
                {"PartId": "1", "AxisProjection": {"Start": 10, "End": 3010, "Length": 3000}},
                {"PartId": "2", "AxisProjection": {"Start": 9010, "End": 9410, "Length": 400}},
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly, member)

        self.assertEqual(1, len(groups))
        group = groups[0]
        self.assertEqual("BOX_MAIN_WALL_CONFIRMED_SET", group.group_type)
        self.assertEqual(["A-P-sampled"], group.part_positions)
        self.assertNotIn("A-P-unsampled", group.part_positions)
        self.assertIn("SECTION_VALIDATED", group.evidence_codes)

    def test_expands_section_seed_along_axis_into_confirmed_wall_set(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [],
            "parts": [
                {**_wall_part("1", "A-P-seed-a", "RADIAL_X_NEG", 0, 3000), "name": "COLUMN"},
                {**_wall_part("2", "A-P-seed-b", "RADIAL_X_POS", 0, 3000), "name": "COLUMN"},
                {**_wall_part("3", "A-P-next-a", "RADIAL_X_NEG", 3005, 6000), "name": "COLUMN"},
                {**_wall_part("4", "A-P-next-b", "RADIAL_X_POS", 3005, 6000), "name": "COLUMN"},
                {**_wall_part("5", "A-P-short-local", "RADIAL_X_POS", 9000, 9100), "name": "连接板"},
            ],
        }
        member = {
            "Samples": [
                {
                    "SampleId": "S02",
                    "IsAbnormal": False,
                    "SectionFeatures": {"ClosedLoops": 1, "CavityCount": 1, "OuterWidth": 1000, "OuterHeight": 1000},
                    "SectionParts": [
                        {"PartId": "1", "RoleHint": "flange_candidate", "TotalCutLength": 960},
                        {"PartId": "2", "RoleHint": "flange_candidate", "TotalCutLength": 970},
                    ],
                }
            ],
            "Parts": [
                {"PartId": "1", "AxisProjection": {"Start": 0, "End": 3000, "Length": 3000}},
                {"PartId": "2", "AxisProjection": {"Start": 0, "End": 3000, "Length": 3000}},
                {"PartId": "3", "AxisProjection": {"Start": 3005, "End": 6000, "Length": 2995}},
                {"PartId": "4", "AxisProjection": {"Start": 3005, "End": 6000, "Length": 2995}},
                {"PartId": "5", "AxisProjection": {"Start": 9000, "End": 9100, "Length": 100}},
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly, member)

        self.assertEqual(1, len(groups))
        group = groups[0]
        self.assertEqual("BOX_MAIN_WALL_CONFIRMED_SET", group.group_type)
        self.assertEqual("BOX_MAIN_WALL_CONFIRMED", group.face_id)
        self.assertEqual(["A-P-seed-a", "A-P-seed-b", "A-P-next-a", "A-P-next-b"], group.part_positions)
        self.assertNotIn("A-P-short-local", group.part_positions)
        self.assertIn("BOX_WALL_TRACE_SEED", group.evidence_codes)
        self.assertIn("AXIS_CONTINUITY_EXPANDED", group.evidence_codes)
        self.assertIn("SECTION_VALIDATED", group.evidence_codes)


    def test_uses_box_section_evidence_loops_as_main_wall_seed_without_member_samples(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "memberAxisEvidence": {"source": "mainPart.longestLocalAxis"},
                "boxSectionEvidence": {
                    "source": "teklaSolidFaceSectionSegments.v2",
                    "stationLoops": [
                        {
                            "station": 100,
                            "partLoops": [
                                _section_loop_part("1", 0, 0, 100, 10),
                                _section_loop_part("2", 0, 90, 100, 100),
                                _section_loop_part("3", 0, 0, 10, 100),
                                _section_loop_part("4", 90, 0, 100, 100),
                                _section_loop_part("5", 40, 40, 60, 60),
                            ],
                        }
                    ],
                },
            },
            "relationships": [],
            "parts": [
                _wall_part("1", "A-P-bottom", "RADIAL_Y_NEG", 0, 3000),
                _wall_part("2", "A-P-top", "RADIAL_Y_POS", 0, 3000),
                _wall_part("3", "A-P-left", "RADIAL_X_NEG", 0, 3000),
                _wall_part("4", "A-P-right", "RADIAL_X_POS", 0, 3000),
                _wall_part("5", "A-P-inside", "RADIAL_INNER", 500, 800),
            ],
        }

        groups = classify_box_main_material_segment_groups(assembly, member=None)

        self.assertEqual(1, len(groups))
        group = groups[0]
        self.assertEqual("BOX_MAIN_WALL_CONFIRMED_SET", group.group_type)
        self.assertCountEqual(
            ["A-P-bottom", "A-P-top", "A-P-left", "A-P-right"],
            group.part_positions,
        )
        self.assertNotIn("A-P-inside", group.part_positions)
        self.assertIn("BOX_SECTION_LOOP_TOPOLOGY_SEED", group.evidence_codes)
        self.assertIn("SECTION_VALIDATED", group.evidence_codes)

    def test_box_section_topology_seed_ignores_short_transition_loops_even_when_large(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "memberAxisEvidence": {"length": 3000},
                "boxSectionEvidence": {
                    "source": "teklaSolidFaceSectionSegments.v2",
                    "stationLoops": [
                        {
                            "station": 100,
                            "partLoops": [
                                _section_loop_part("end", -100, -100, 200, 200),
                                _section_loop_part("1", 0, 0, 100, 10),
                                _section_loop_part("2", 0, 90, 100, 100),
                                _section_loop_part("3", 0, 0, 10, 100),
                                _section_loop_part("4", 90, 0, 100, 100),
                            ],
                        }
                    ],
                },
            },
            "relationships": [],
            "parts": [
                _wall_part("end", "A-P-short-transition", "RADIAL_Y_NEG", 1200, 1350, thickness=32),
                _wall_part("1", "A-P-bottom", "RADIAL_Y_NEG", 0, 3000),
                _wall_part("2", "A-P-top", "RADIAL_Y_POS", 0, 3000),
                _wall_part("3", "A-P-left", "RADIAL_X_NEG", 0, 3000),
                _wall_part("4", "A-P-right", "RADIAL_X_POS", 0, 3000),
            ],
        }
        assembly["parts"][0]["mainMaterialEvidence"]["sectionProjectionEvidence"] = {
            "normalProjectionMagnitude": 0.17
        }

        groups = classify_box_main_material_segment_groups(assembly, member=None)

        self.assertEqual(1, len(groups))
        self.assertCountEqual(
            ["A-P-bottom", "A-P-top", "A-P-left", "A-P-right"],
            groups[0].part_positions,
        )
        self.assertNotIn("A-P-short-transition", groups[0].part_positions)

    def test_expands_section_seed_to_adjacent_flange_role_wall_candidates(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {"memberAxisEvidence": {"source": "mainPart.longestLocalAxis"}},
            "relationships": [],
            "parts": [
                _wall_part("1", "A-P-seed-a", "RADIAL_X_NEG", 0, 3165, thickness=16),
                _wall_part("2", "A-P-seed-b", "RADIAL_X_POS", 0, 3165, thickness=16),
                _wall_part("3", "A-P-next-a", "RADIAL_X_NEG", 3164.98, 6016, thickness=30),
                _wall_part("4", "A-P-next-b", "RADIAL_X_POS", 3165.02, 6016, thickness=30),
                _wall_part("5", "A-P-local-attachment", "RADIAL_X_POS", 9000, 9200, thickness=16),
            ],
        }
        member = {
            "Samples": [
                {
                    "SampleId": "S02",
                    "IsAbnormal": False,
                    "SectionFeatures": {"ClosedLoops": 1, "CavityCount": 1, "OuterWidth": 1000, "OuterHeight": 1000},
                    "SectionParts": [
                        {"PartId": "1", "RoleHint": "flange_candidate", "TotalCutLength": 960},
                        {"PartId": "2", "RoleHint": "web_candidate", "TotalCutLength": 970},
                    ],
                }
            ],
            "Parts": [
                {"PartId": "1", "AxisProjection": {"Start": 0, "End": 3165, "Length": 3165}},
                {"PartId": "2", "AxisProjection": {"Start": 0, "End": 3165, "Length": 3165}},
                {"PartId": "3", "AxisProjection": {"Start": 3164.98, "End": 6016, "Length": 2851.02}},
                {"PartId": "4", "AxisProjection": {"Start": 3165.02, "End": 6016, "Length": 2850.98}},
                {"PartId": "5", "AxisProjection": {"Start": 9000, "End": 9200, "Length": 200}},
            ],
            "Classification": {
                "PartRoles": [
                    {"PartId": "1", "Role": "flange_candidate"},
                    {"PartId": "2", "Role": "web_candidate"},
                    {"PartId": "3", "Role": "flange_candidate"},
                    {"PartId": "4", "Role": "web_candidate"},
                    {"PartId": "5", "Role": "flange_candidate"},
                ]
            },
        }

        groups = classify_box_main_material_segment_groups(assembly, member)

        self.assertEqual(1, len(groups))
        group = groups[0]
        self.assertEqual(
            ["A-P-seed-a", "A-P-seed-b", "A-P-next-a", "A-P-next-b"],
            group.part_positions,
        )
        self.assertNotIn("A-P-local-attachment", group.part_positions)
        self.assertIn("AXIS_CONTINUITY_EXPANDED", group.evidence_codes)

def _wall_part(
    part_id,
    position,
    face_id,
    start,
    end,
    thickness=16,
    previous_id=0,
    next_id=0,
    previous_gap=0,
    next_gap=0,
):
    return {
        "partId": part_id,
        "partPosition": position,
        "profileString": f"PL{thickness}*900",
        "thickness": thickness,
        "mainMaterialEvidence": {
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "bodyFaceId": face_id,
            "bodyFaceOffset": 100,
            "isBodyWallPlateCandidate": True,
            "evidenceSource": "axisProjection+radialFaceBucket",
            "segmentAdjacency": {
                "previousPartId": previous_id,
                "nextPartId": next_id,
                "previousGap": previous_gap,
                "nextGap": next_gap,
                "evidenceSource": "sameFaceStationSort",
            },
        },
    }

def _section_loop_part(part_id, min_u, min_v, max_u, max_v):
    return {
        "partId": part_id,
        "sectionLoops": [
            {
                "points": [
                    {"u": min_u, "v": min_v},
                    {"u": max_u, "v": min_v},
                    {"u": max_u, "v": max_v},
                    {"u": min_u, "v": max_v},
                ],
                "isClosed": True,
                "isValid": True,
            }
        ],
    }


def _weld(part_a, part_b):
    return {"partIdA": part_a, "partIdB": part_b, "edgeType": "Weld"}

if __name__ == "__main__":
    unittest.main()
