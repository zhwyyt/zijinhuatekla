from types import SimpleNamespace
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

    def test_adapts_h_gl_main_material_groups_into_composite_roles(self):
        from zijinhua_tekla.classifiers.box_main_material_segments import classify_main_material_segment_groups

        assembly = _h_gl_fixture()
        groups = classify_main_material_segment_groups(assembly)

        segments = classify_composite_main_material_segments(assembly, main_material_groups=groups)

        self.assertEqual(1, len(segments))
        self.assertEqual("H_OR_BH_SECTION", segments[0].segment_type.value)
        self.assertEqual((0.0, 13114.9), (segments[0].station_start, segments[0].station_end))
        roles = {plate.part_position: plate.primary_role.value for plate in segments[0].main_plates}
        self.assertEqual("H_TOP_FLANGE_MAIN_PLATE", roles["T3-P-4866"])
        self.assertEqual("H_WEB_MAIN_PLATE", roles["T3-P-4753"])
        self.assertEqual("H_BOTTOM_FLANGE_MAIN_PLATE", roles["T3-P-4863"])
        self.assertEqual("H_BOTTOM_FLANGE_MAIN_PLATE", roles["T3-P-5555"])
        self.assertEqual("H_BOTTOM_FLANGE_MAIN_PLATE", roles["T3-P-4862"])
        self.assertIn("adapted_from_main_material_segment_groups", segments[0].evidence_codes)

    def test_prefers_native_h_station_frames_over_adapted_main_material_groups(self):
        from zijinhua_tekla.classifiers.box_main_material_segments import classify_main_material_segment_groups

        assembly = _h_station_frame_fixture()
        groups = classify_main_material_segment_groups(assembly)

        segments = classify_composite_main_material_segments(assembly, main_material_groups=groups)

        self.assertEqual(1, len(segments))
        self.assertEqual("H_OR_BH_SECTION", segments[0].segment_type.value)
        self.assertEqual((0, 4750), (segments[0].station_start, segments[0].station_end))
        self.assertIn("H_GL_STATION_FRAME_NATIVE_COMPOSITE", segments[0].evidence_codes)
        self.assertNotIn("adapted_from_main_material_segment_groups", segments[0].evidence_codes)
        roles = {plate.part_position: plate.primary_role.value for plate in segments[0].main_plates}
        self.assertEqual("H_TOP_FLANGE_MAIN_PLATE", roles["T2-3B-top"])
        self.assertEqual("H_WEB_MAIN_PLATE", roles["T2-3B-web"])
        self.assertEqual("H_BOTTOM_FLANGE_MAIN_PLATE", roles["T2-3B-bottom"])
        self.assertNotIn("T2-3B-local", roles)
        self.assertTrue(
            all("h_beam_station_frame" in plate.secondary_evidence for plate in segments[0].main_plates)
        )
    def test_native_h_station_frames_expand_main_plate_chain_by_axis_continuity(self):
        assembly = _h_station_frame_fixture()
        assembly["metadata"]["memberAxisEvidence"]["length"] = 6200
        assembly["parts"].extend(
            [
                _part("top-tail", "T2-3B-top-tail", 4750, 6200, "Y", 0, 180, 240, 20, name="乱码"),
                _part("bottom-tail", "T2-3B-bottom-tail", 4750, 6200, "Y", 0, -180, 240, 20, name="乱码"),
                _part("top-short", "T2-3B-top-short", 4500, 5000, "Y", 0, 180, 240, 20, name="乱码"),
            ]
        )
        assembly["relationships"].extend([_rel("top", "top-tail", "Contact"), _rel("bottom", "bottom-tail", "Contact")])
        for station in range(5000, 6500, 250):
            assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].append(
                {
                    "station": station,
                    "topFlangePartId": "top-tail",
                    "webPartId": "web",
                    "bottomFlangePartId": "bottom-tail",
                    "partSlices": [
                        _h_slice("top-tail", "T2-3B-top-tail", "flange_candidate"),
                        _h_slice("web", "T2-3B-web", "web_candidate"),
                        _h_slice("bottom-tail", "T2-3B-bottom-tail", "flange_candidate"),
                    ],
                }
            )
        for station in range(4500, 5000, 250):
            assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].append(
                {
                    "station": station,
                    "topFlangePartId": "top-short",
                    "webPartId": "web",
                    "bottomFlangePartId": "bottom",
                    "partSlices": [
                        _h_slice("top-short", "T2-3B-top-short", "flange_candidate"),
                        _h_slice("web", "T2-3B-web", "web_candidate"),
                        _h_slice("bottom", "T2-3B-bottom", "flange_candidate"),
                    ],
                }
            )

        segments = classify_composite_main_material_segments(assembly)

        roles = {plate.part_position: plate.primary_role.value for plate in segments[0].main_plates}
        self.assertEqual("H_TOP_FLANGE_MAIN_PLATE", roles["T2-3B-top-tail"])
        self.assertEqual("H_BOTTOM_FLANGE_MAIN_PLATE", roles["T2-3B-bottom-tail"])
        self.assertNotIn("T2-3B-top-short", roles)
        tail_plate = next(plate for plate in segments[0].main_plates if plate.part_position == "T2-3B-top-tail")
        self.assertIn("h_beam_axis_continuity_expanded", tail_plate.secondary_evidence)
        self.assertIn("H_GL_AXIS_CONTINUITY_EXPANDED", tail_plate.evidence_codes)
    def test_native_h_continuity_updates_segment_range_for_expanded_plates(self):
        assembly = _h_station_frame_fixture()
        assembly["metadata"]["memberAxisEvidence"]["length"] = 6200
        assembly["parts"].append(_part("top-tail", "T2-3B-top-tail", 4750, 6250, "Y", 0, 180, 240, 20, name="乱码"))
        assembly["relationships"].append(_rel("top", "top-tail", "Contact"))
        for station in range(5000, 6500, 250):
            assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].append(
                {
                    "station": station,
                    "topFlangePartId": "top-tail",
                    "webPartId": "web",
                    "bottomFlangePartId": "bottom",
                    "partSlices": [
                        _h_slice("top-tail", "T2-3B-top-tail", "flange_candidate"),
                        _h_slice("web", "T2-3B-web", "web_candidate"),
                        _h_slice("bottom", "T2-3B-bottom", "flange_candidate"),
                    ],
                }
            )

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual(6250, segments[0].station_end)

    def test_native_h_continuity_expands_multiple_hops(self):
        assembly = _h_station_frame_fixture()
        assembly["metadata"]["memberAxisEvidence"]["length"] = 8200
        assembly["parts"].extend(
            [
                _part("top-tail-1", "T2-3B-top-tail-1", 4750, 6200, "Y", 0, 180, 240, 20, name="乱码"),
                _part("top-tail-2", "T2-3B-top-tail-2", 6200, 8200, "Y", 0, 180, 240, 20, name="乱码"),
            ]
        )
        assembly["relationships"].extend([_rel("top", "top-tail-1", "Contact"), _rel("top-tail-1", "top-tail-2", "Contact")])
        for station in range(5000, 6500, 250):
            assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].append(
                {
                    "station": station,
                    "topFlangePartId": "top-tail-1",
                    "webPartId": "web",
                    "bottomFlangePartId": "bottom",
                    "partSlices": [_h_slice("top-tail-1", "T2-3B-top-tail-1", "flange_candidate")],
                }
            )
        for station in range(6500, 8500, 250):
            assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].append(
                {
                    "station": station,
                    "topFlangePartId": "top-tail-2",
                    "webPartId": "web",
                    "bottomFlangePartId": "bottom",
                    "partSlices": [_h_slice("top-tail-2", "T2-3B-top-tail-2", "flange_candidate")],
                }
            )

        segments = classify_composite_main_material_segments(assembly)

        positions = _plate_positions(segments[0])
        self.assertIn("T2-3B-top-tail-1", positions)
        self.assertIn("T2-3B-top-tail-2", positions)

    def test_native_h_continuity_allows_thickness_change_in_same_plate_chain(self):
        assembly = _h_station_frame_fixture()
        assembly["metadata"]["memberAxisEvidence"]["length"] = 6200
        assembly["parts"].append(_part("top-tail", "T2-3B-top-tail", 4750, 6200, "Y", 0, 180, 240, 28, name="乱码"))
        assembly["parts"][-1]["profileString"] = "PL28*240"
        assembly["relationships"].append(_rel("top", "top-tail", "Contact"))
        for station in range(5000, 6500, 250):
            assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].append(
                {
                    "station": station,
                    "topFlangePartId": "top-tail",
                    "webPartId": "web",
                    "bottomFlangePartId": "bottom",
                    "partSlices": [_h_slice("top-tail", "T2-3B-top-tail", "flange_candidate")],
                }
            )

        segments = classify_composite_main_material_segments(assembly)

        roles = {plate.part_position: plate.primary_role.value for plate in segments[0].main_plates}
        self.assertEqual("H_TOP_FLANGE_MAIN_PLATE", roles["T2-3B-top-tail"])
    def test_adapter_parses_negative_zero_station_ranges(self):
        groups = [
            SimpleNamespace(
                evidence_summary={"main_material_role": "BOTTOM_FLANGE"},
                evidence_codes=["PROFILE_FAMILY_H_OR_GL"],
                part_ids=["bottom-1", "bottom-2", "bottom-3"],
                part_positions=["T3-P-4863", "T3-P-5555", "T3-P-4862"],
                station_ranges="T3-P-4863:-0.0-1775.0;T3-P-5555:1775.0-11324.9;T3-P-4862:11324.8-13114.9",
            )
        ]

        segments = classify_composite_main_material_segments(
            {"assemblyId": "GL-NEG-ZERO", "metadata": {"memberAxisEvidence": {"length": 13114.9}}},
            main_material_groups=groups,
        )

        self.assertEqual((0.0, 13114.9), (segments[0].station_start, segments[0].station_end))
    def test_closed_part_loops_do_not_force_cross_section_to_box(self):
        assembly = _composite_fixture()
        for station_loop in assembly["metadata"]["boxSectionEvidence"]["stationLoops"][:2]:
            station_loop["closedLoopCount"] = 7

        segments = classify_composite_main_material_segments(assembly)

        self.assertEqual("CROSS_CORE_WITH_FLANGES", segments[0].segment_type.value)
        self.assertIn("P-FLANGE-L", _plate_positions(segments[0]))

    def test_assigns_cross_flange_and_box_main_wall_roles(self):
        segments = classify_composite_main_material_segments(_composite_fixture())

        lower = segments[0]
        transition = segments[1]
        upper = segments[2]

        self.assertEqual({"P-CORE-X", "P-CORE-Y", "P-FLANGE-L", "P-FLANGE-R"}, _plate_positions(lower))
        lower_roles = {plate.part_position: plate.primary_role.value for plate in lower.main_plates}
        self.assertEqual("CROSS_FLANGE_MAIN_PLATE", lower_roles["P-FLANGE-L"])
        self.assertEqual("CROSS_FLANGE_MAIN_PLATE", lower_roles["P-FLANGE-R"])
        self.assertEqual("CROSS_CORE_MAIN_PLATE", lower_roles["P-CORE-X"])
        self.assertEqual("CROSS_CORE_MAIN_PLATE", lower_roles["P-CORE-Y"])

        self.assertEqual({"P-BOX-A", "P-BOX-B", "P-CORE-X", "P-CORE-Y"}, _plate_positions(transition))
        transition_roles = {plate.part_position: plate.primary_role.value for plate in transition.main_plates}
        self.assertEqual("TRANSITION_MAIN_PLATE", transition_roles["P-CORE-X"])
        self.assertEqual("TRANSITION_MAIN_PLATE", transition_roles["P-CORE-Y"])
        self.assertEqual("BOX_FORMING_MAIN_PLATE", transition_roles["P-BOX-A"])
        self.assertEqual("BOX_FORMING_MAIN_PLATE", transition_roles["P-BOX-B"])
        self.assertIn(
            "continues_from_lower_cross_column",
            next(plate for plate in transition.main_plates if plate.part_position == "P-CORE-X").secondary_evidence,
        )

        self.assertEqual({"P-BOX-A", "P-BOX-B", "P-BOX-C", "P-BOX-D"}, _plate_positions(upper))
        upper_roles = {plate.part_position: plate.primary_role.value for plate in upper.main_plates}
        self.assertEqual(
            {
                "P-BOX-A": "BOX_MAIN_WALL_PLATE",
                "P-BOX-B": "BOX_MAIN_WALL_PLATE",
                "P-BOX-C": "BOX_MAIN_WALL_PLATE",
                "P-BOX-D": "BOX_MAIN_WALL_PLATE",
            },
            upper_roles,
        )
    def test_skips_center_candidate_without_cross_core_span_evidence(self):
        assembly = _composite_fixture()
        assembly["parts"].append(_part("center-short", "P-CENTER-SHORT", 0, 3000, "X", 0, 0, 20, 80))

        lower = classify_composite_main_material_segments(assembly)[0]

        self.assertNotIn("P-CENTER-SHORT", _plate_positions(lower))
def _plate_positions(segment):
    return {plate.part_position for plate in segment.main_plates}


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
    inner_loop_count = 1 if regime_hint == "box" else 0
    return {
        "station": station,
        "closedLoopCount": closed_count,
        "innerLoopCount": inner_loop_count,
        "partLoops": [],
        "diagnostics": [f"compositeTestRegime={regime_hint}"],
    }


def _part(part_id, position, start, end, normal_axis, u, v, span_u, span_v, name="PLATE"):
    normal = {"u": 1.0, "v": 0.0} if normal_axis == "X" else {"u": 0.0, "v": 1.0}
    return {
        "partId": part_id,
        "partPosition": position,
        "name": name,
        "profileString": f"PL{span_v}*{span_u}" if span_u >= span_v else f"PL{span_u}",
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


def _h_gl_fixture():
    return {
        "assemblyId": "GL-1",
        "metadata": {"assemblyPosition": "T3-6GL-110", "memberAxisEvidence": {"length": 13114.9}},
        "relationships": [
            _rel("top", "web", "Contact"),
            _rel("web", "bottom-1", "Weld"),
            _rel("web", "bottom-2", "Weld"),
            _rel("web", "bottom-3", "Weld"),
            _rel("bottom-1", "bottom-2", "Contact"),
            _rel("bottom-2", "bottom-3", "Contact"),
        ],
        "parts": [
            _part("top", "T3-P-4866", 0, 13114.9, "Y", 0, 150, 200, 14, name="上翼缘"),
            _part("web", "T3-P-4753", 0, 13114.9, "X", 0, 0, 12, 380, name="腹板"),
            _part("bottom-1", "T3-P-4863", 0, 1775.0, "Y", 0, -150, 200, 14, name="下翼缘"),
            _part("bottom-2", "T3-P-5555", 1775.0, 11324.9, "Y", 0, -150, 200, 22, name="下翼缘"),
            _part("bottom-3", "T3-P-4862", 11324.8, 13114.9, "Y", 0, -150, 200, 14, name="下翼缘"),
            _part("stiffener", "T3-P-4653", 1966.6, 1978.6, "X", 0, 0, 12, 160, name="加劲板"),
        ],
    }


def _h_station_frame_fixture():
    frames = []
    for station in range(0, 5000, 250):
        slices = [
            _h_slice("top", "T2-3B-top", "flange_candidate"),
            _h_slice("web", "T2-3B-web", "web_candidate"),
            _h_slice("bottom", "T2-3B-bottom", "flange_candidate"),
        ]
        if 1000 <= station <= 1500:
            slices.append(_h_slice("local", "T2-3B-local", "flange_candidate"))
        frames.append(
            {
                "station": station,
                "topFlangePartId": "top",
                "webPartId": "web",
                "bottomFlangePartId": "bottom",
                "partSlices": slices,
            }
        )
    return {
        "assemblyId": "H-NATIVE-1",
        "metadata": {
            "assemblyPosition": "T2-3GL-55",
            "memberAxisEvidence": {"length": 4750},
            "hBeamSectionEvidence": {
                "source": "hBeamStationLocalSolidSection.v1",
                "stationFrames": frames,
            },
        },
        "relationships": [],
        "parts": [
            _part("top", "T2-3B-top", 0, 4750, "Y", 0, 180, 240, 20, name="乱码"),
            _part("web", "T2-3B-web", 0, 4750, "X", 0, 0, 18, 360, name="乱码"),
            _part("bottom", "T2-3B-bottom", 0, 4750, "Y", 0, -180, 240, 20, name="乱码"),
            _part("local", "T2-3B-local", 1000, 1500, "Y", 0, 180, 240, 20, name="乱码"),
        ],
    }

def _h_slice(part_id, position, role_hint):
    return {
        "partId": part_id,
        "partPosition": position,
        "roleHint": role_hint,
        "segments": [
            {"start": {"u": 0, "v": 0}, "end": {"u": 100, "v": 0}},
            {"start": {"u": 100, "v": 0}, "end": {"u": 100, "v": 20}},
            {"start": {"u": 100, "v": 20}, "end": {"u": 0, "v": 20}},
            {"start": {"u": 0, "v": 20}, "end": {"u": 0, "v": 0}},
        ],
        "sectionLoops": [
            {
                "isClosed": True,
                "isValid": True,
                "points": [
                    {"u": 0, "v": 0},
                    {"u": 100, "v": 0},
                    {"u": 100, "v": 20},
                    {"u": 0, "v": 20},
                ],
            }
        ],
    }

def _rel(part_a, part_b, edge_type):
    return {"partIdA": part_a, "partIdB": part_b, "edgeType": edge_type}


if __name__ == "__main__":
    unittest.main()












