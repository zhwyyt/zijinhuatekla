import unittest

from zijinhua_tekla.classifiers.composite_main_material_segments import (
    CompositeMainMaterialSegment,
    CompositeMainPlate,
    CompositePrimaryRole,
    CompositeSegmentType,
    classify_composite_main_material_segments,
)


class CompositeMainMaterialSegmentTests(unittest.TestCase):
    def test_segment_to_dict_uses_string_roles(self):
        segment = CompositeMainMaterialSegment(
            assembly_id="A1",
            segment_id="S1",
            station_start=0,
            station_end=1000,
            segment_type=CompositeSegmentType.CROSS_CORE_WITH_FLANGES,
            confidence=0.91,
            evidence_codes=["STATION_REGIME_SEGMENT"],
            main_plates=[
                CompositeMainPlate(
                    part_id="p-flange",
                    part_position="P-FLANGE",
                    primary_role=CompositePrimaryRole.CROSS_FLANGE_MAIN_PLATE,
                    secondary_evidence=["parallel_to_cross_core_plate"],
                    evidence_codes=["CROSS_FLANGE_OUTER_PLATE"],
                )
            ],
        )

        self.assertEqual(
            {
                "assembly_id": "A1",
                "segment_id": "S1",
                "station_start": 0,
                "station_end": 1000,
                "segment_type": "CROSS_CORE_WITH_FLANGES",
                "confidence": 0.91,
                "evidence_codes": ["STATION_REGIME_SEGMENT"],
                "main_plates": [
                    {
                        "part_id": "p-flange",
                        "part_position": "P-FLANGE",
                        "primary_role": "CROSS_FLANGE_MAIN_PLATE",
                        "secondary_evidence": ["parallel_to_cross_core_plate"],
                        "evidence_codes": ["CROSS_FLANGE_OUTER_PLATE"],
                    }
                ],
            },
            segment.to_dict(),
        )

    def test_splits_cross_transition_and_box_station_regimes(self):
        assembly = _composite_fixture()

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual(
            [
                "CROSS_CORE_WITH_FLANGES",
                "CROSS_TO_BOX_TRANSITION",
                "BOX_CLOSED_SECTION",
            ],
            [segment.segment_type.value for segment in segments],
        )
        self.assertEqual([(0, 3000), (3000, 4500), (4500, 8000)], [
            (segment.station_start, segment.station_end) for segment in segments
        ])
        self.assertEqual([[], [], []], [segment.main_plates for segment in segments])

    def test_uses_member_axis_length_for_last_segment_end_when_terminal_station_missing(self):
        assembly = _composite_fixture(include_terminal_box_station=False)

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual((4500, 8000), (segments[-1].station_start, segments[-1].station_end))
        self.assertEqual("BOX_CLOSED_SECTION", segments[-1].segment_type.value)

    def test_transition_does_not_require_box_forming_parts_to_start_after_zero(self):
        assembly = _composite_fixture(box_parts_start=0)

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual("CROSS_TO_BOX_TRANSITION", segments[0].segment_type.value)

    def test_zero_station_can_be_transition_when_cross_and_box_forming_overlap(self):
        assembly = _composite_fixture(box_parts_start=0)
        assembly["metadata"]["boxSectionEvidence"]["stationLoops"] = [
            _station_loop(0, "transition"),
            _station_loop(4500, "box"),
        ]

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual("CROSS_TO_BOX_TRANSITION", segments[0].segment_type.value)
        self.assertEqual((0, 4500), (segments[0].station_start, segments[0].station_end))
        self.assertEqual([], segments[0].main_plates)


def _composite_fixture(include_terminal_box_station=True, box_parts_start=3000):
    station_loops = [
        _station_loop(0, "cross"),
        _station_loop(1500, "cross"),
        _station_loop(3000, "transition"),
        _station_loop(4500, "box"),
    ]
    if include_terminal_box_station:
        station_loops.append(_station_loop(8000, "box"))
    return {
        "assemblyId": "A-COMPOSITE",
        "metadata": {
            "memberAxisEvidence": {"length": 8000},
            "boxSectionEvidence": {
                "source": "teklaSolidFaceSectionSegments.v2",
                "stationLoops": station_loops,
            },
        },
        "parts": [
            _part("core-x", "P-CORE-X", 0, 4500, "X", 0, 0, 20, 300),
            _part("core-y", "P-CORE-Y", 0, 4500, "Y", 0, 0, 300, 20),
            _part("flange-l", "P-FLANGE-L", 0, 3000, "X", -220, 0, 20, 220),
            _part("flange-r", "P-FLANGE-R", 0, 3000, "X", 220, 0, 20, 220),
            _part("box-a", "P-BOX-A", box_parts_start, 8000, "X", -260, 0, 20, 520),
            _part("box-b", "P-BOX-B", box_parts_start, 8000, "X", 260, 0, 20, 520),
            _part("box-c", "P-BOX-C", 4500, 8000, "Y", 0, -260, 520, 20),
            _part("box-d", "P-BOX-D", 4500, 8000, "Y", 0, 260, 520, 20),
        ],
        "relationships": [],
    }


def _station_loop(station, regime_hint):
    closed_count = 1 if regime_hint == "box" else 0
    return {
        "station": station,
        "closedLoopCount": closed_count,
        "partLoops": [],
        "diagnostics": [f"compositeTestRegime={regime_hint}"],
    }


def _part(part_id, position, start, end, normal_axis, u, v, span_u, span_v):
    normal = {"u": 1.0, "v": 0.0} if normal_axis == "X" else {"u": 0.0, "v": 1.0}
    return {
        "partId": part_id,
        "partPosition": position,
        "mainMaterialEvidence": {
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "bodyFaceId": f"FACE-{part_id}",
            "isBodyWallPlateCandidate": True,
            "sectionProjectionEvidence": {
                "projectedCentroid": {"u": u, "v": v},
                "projectedBoundsMin": {"u": u - span_u / 2, "v": v - span_v / 2},
                "projectedBoundsMax": {"u": u + span_u / 2, "v": v + span_v / 2},
                "normalProjection": normal,
                "normalProjectionMagnitude": 1.0,
            },
        },
    }


if __name__ == "__main__":
    unittest.main()