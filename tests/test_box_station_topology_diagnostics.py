import unittest

from zijinhua_tekla.classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, SegmentContinuityLevel
from zijinhua_tekla.classifiers.box_station_topology_diagnostics import diagnose_box_station_topology


class BoxStationTopologyDiagnosticsTests(unittest.TestCase):
    def test_uses_exported_segments_when_section_loops_are_not_available(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "source": "teklaSolidFaceSectionSegments.v2",
                    "stationLoops": [
                        {
                            "station": 100,
                            "partLoops": [
                                {
                                    "partId": "wall",
                                    "segments": [
                                        {"start": {"u": 0, "v": 0}, "end": {"u": 100, "v": 0}},
                                        {"start": {"u": 100, "v": 0}, "end": {"u": 100, "v": 10}},
                                        {"start": {"u": 100, "v": 10}, "end": {"u": 0, "v": 10}},
                                        {"start": {"u": 0, "v": 10}, "end": {"u": 0, "v": 0}},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            },
            "parts": [{"partId": "wall", "partPosition": "A-P-wall"}],
        }
        groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["wall"],
                part_positions=["A-P-wall"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["TEST"],
                confidence=0.9,
            )
        ]

        rows = diagnose_box_station_topology(assembly, groups)

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("CLOSED_WITHOUT_CAVITY", row.topology_status)
        self.assertEqual(1, row.usable_loop_count)
        self.assertEqual(0, row.degenerate_loop_count)
        self.assertTrue(row.loop_summaries[0]["has_exported_segment_polygon"])

    def test_reports_degenerate_main_wall_loops_and_unclosed_station_topology(self):
        assembly = {
            "assemblyId": "A-1",
            "metadata": {
                "boxSectionEvidence": {
                    "stationLoops": [
                        {
                            "station": 100,
                            "partLoops": [
                                {
                                    "partId": "left",
                                    "points": [
                                        {"u": 0, "v": 0}, {"u": 10, "v": 0},
                                        {"u": 10, "v": 100}, {"u": 0, "v": 100},
                                    ],
                                },
                                {
                                    "partId": "right",
                                    "points": [
                                        {"u": 90, "v": 0}, {"u": 100, "v": 0},
                                        {"u": 100, "v": 100}, {"u": 90, "v": 100},
                                    ],
                                },
                                {
                                    "partId": "bottom",
                                    "points": [
                                        {"u": 10, "v": 0}, {"u": 90, "v": 0},
                                        {"u": 90, "v": 10}, {"u": 10, "v": 10},
                                    ],
                                },
                                {
                                    "partId": "top",
                                    "points": [
                                        {"u": 10, "v": 90}, {"u": 90, "v": 90},
                                        {"u": 90, "v": 90}, {"u": 10, "v": 90},
                                    ],
                                },
                            ],
                        }
                    ]
                }
            },
            "parts": [
                {"partId": "left", "partPosition": "A-P-left"},
                {"partId": "right", "partPosition": "A-P-right"},
                {"partId": "bottom", "partPosition": "A-P-bottom"},
                {"partId": "top", "partPosition": "A-P-top"},
            ],
        }
        groups = [
            BoxMainMaterialSegmentGroup(
                assembly_id="A-1",
                group_type="BOX_MAIN_WALL_CONFIRMED_SET",
                face_id="BOX_MAIN_WALL_CONFIRMED",
                part_ids=["left", "right", "bottom", "top"],
                part_positions=["A-P-left", "A-P-right", "A-P-bottom", "A-P-top"],
                station_ranges="",
                gap_summary="",
                continuity_level=SegmentContinuityLevel.CONTINUOUS,
                evidence_codes=["TEST"],
                confidence=0.9,
            )
        ]

        rows = diagnose_box_station_topology(assembly, groups)

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("STATION_TOPOLOGY_NOT_CLOSED", row.topology_status)
        self.assertEqual(1, row.degenerate_loop_count)
        self.assertIn("DEGENERATE_OR_INVALID_MAIN_WALL_LOOP", row.evidence_codes)
        self.assertTrue(any(loop["part_position"] == "A-P-top" for loop in row.loop_summaries))


if __name__ == "__main__":
    unittest.main()

