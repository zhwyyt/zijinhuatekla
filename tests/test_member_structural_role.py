import unittest

from zijinhua_tekla.classifiers.member_structural_role import (
    StructuralContext,
    axis_from_member,
    classify_body_bracket_assembly,
    classify_member_document,
    classify_structural_role,
    landing_checker_plate,
)


def _plate(part_id: int, center_x: float) -> dict:
    return {
        "partId": part_id,
        "isPlateLike": True,
        "thickness": 25,
        "centroid": {"x": center_x, "y": 0, "z": 0},
        "obbDims": {"x": 25, "y": 400, "z": 500},
        "plateNormal": {"x": 1, "y": 0, "z": 0},
        "plateLongDirection": {"x": 0, "y": 0, "z": 1},
    }


def _bar(part_id: int, center_x: float, long_axis: dict | None = None) -> dict:
    return {
        "partId": part_id,
        "isPlateLike": False,
        "thickness": 25,
        "centroid": {"x": center_x, "y": 0, "z": 0},
        "obbDims": {"x": 25, "y": 25, "z": 460},
        "plateNormal": {"x": 0, "y": 1, "z": 0},
        "plateLongDirection": long_axis or {"x": 1, "y": 0, "z": 0},
    }


def _axis(pose: str, bends: int = 0):
    direction = {"vertical": (0, 0, 1), "horizontal": (1, 0, 0), "inclined": (1, 0, 1)}[pose]
    axis = axis_from_member({"Member": {"MainAxis": {"Direction": {"X": direction[0], "Y": direction[1], "Z": direction[2]}}}})
    if bends:
        axis = axis.__class__(
            pose=axis.pose,
            axis_form="折线",
            bend_count=bends,
            chord=axis.chord,
            source=axis.source,
            evidence_codes=list(axis.evidence_codes),
        )
    return axis


class MemberStructuralRoleTests(unittest.TestCase):
    def test_each_primary_role_hits_from_synthetic_facts(self):
        cases = [
            ("COLUMN", "vertical", StructuralContext(lower_end_support="foundation", side_incoming=("beam",)), "框架柱"),
            ("INCLINED_COLUMN", "inclined", StructuralContext(lower_end_continues_down=True, side_incoming=("beam",)), ""),
            ("BEAM", "horizontal", StructuralContext(end_supports=("column", "column")), "框梁"),
            (
                "INCLINED_BEAM",
                "inclined",
                StructuralContext(lies_on_roof_plane=True, supports_purlins=True, end_supports=("column", "beam")),
                "",
            ),
            ("CRANE_BEAM", "horizontal", StructuralContext(ends_on_corbels=True, crane_rail_or_brake=True), ""),
            ("PURLIN", "horizontal", StructuralContext(repeated_on_roof_beams=True), ""),
            (
                "GIRT",
                "horizontal",
                StructuralContext(attached_to_column_side_for_wall=True, carries_floor_beams=False),
                "",
            ),
            (
                "BRACE",
                "inclined",
                StructuralContext(paired_with_brace=True, end_supports=("gusset", "gusset"), brace_arrangement="交叉"),
                "交叉",
            ),
            (
                "HORIZONTAL_BRACE",
                "horizontal",
                StructuralContext(crosses_bay_in_plan=True, end_supports=("gusset", "gusset"), carries_floor_beams=False),
                "",
            ),
            ("KNEE_BRACE", "inclined", StructuralContext(short_brace_between_flange_and_purlin=True), ""),
            (
                "TIE",
                "horizontal",
                StructuralContext(
                    connects_frames_longitudinally=True,
                    carries_floor_beams=False,
                    crosses_bay_in_plan=False,
                ),
                "",
            ),
            ("TRUSS", "horizontal", StructuralContext(has_chord_web_system=True, external_supports_only=True), ""),
            (
                "EMBED",
                "horizontal",
                StructuralContext(anchor_plate_with_same_side_bars=True, has_span_axis=False),
                "",
            ),
            ("STAIR", "inclined", StructuralContext(repeated_treads=True), ""),
            ("STAIR_LANDING", "horizontal", StructuralContext(landing_checker_deck=True), ""),
        ]

        for role, pose, context, subtype in cases:
            with self.subTest(role=role):
                result = classify_structural_role(_axis(pose), context, member_id="M-1")
                self.assertEqual(role, result.role)
                self.assertEqual(subtype, result.subtype)
                self.assertNotEqual("UNKNOWN", result.rule_id)

    def test_missing_context_and_conflicts_stay_unknown(self):
        self.assertEqual("UNKNOWN", classify_structural_role(_axis("vertical"), None).role)
        conflicts = [
            StructuralContext(crosses_bay_in_plan=True, carries_floor_beams=True, end_supports=("column", "column")),
            StructuralContext(crosses_bay_in_plan=True, connects_frames_longitudinally=True),
            StructuralContext(
                lies_on_roof_plane=True,
                supports_purlins=True,
                paired_with_brace=True,
                end_supports=("gusset", "gusset"),
            ),
        ]
        poses = ("horizontal", "horizontal", "inclined")
        for pose, context in zip(poses, conflicts):
            result = classify_structural_role(_axis(pose), context)
            self.assertEqual("UNKNOWN", result.role)
            self.assertTrue(result.rule_id.startswith("MR-CONFLICT"))

    def test_member_mark_without_context_does_not_assign_role(self):
        for mark in ("T3-5GKZ-10", "T3-6GL-1", "T3-MJ-1"):
            member = {
                "Member": {"MemberId": mark, "MainAxis": {"Direction": {"X": 0, "Y": 0, "Z": 1}}},
            }
            result = classify_member_document(member, None)
            self.assertEqual("UNKNOWN", result.role)
            self.assertEqual(mark, result.member_id)
            self.assertNotIn(mark, result.evidence_codes)

    def test_vertical_chord_with_bend_stays_column_and_polyline(self):
        member = {
            "Member": {"MemberId": "BENT-1"},
            "GuidePolyline": [
                {"X": 0, "Y": 0, "Z": 0},
                {"X": 400, "Y": 0, "Z": 3000},
                {"X": 0, "Y": 0, "Z": 6000},
            ],
            "AxisSegments": [
                {"Direction": {"X": 0.13, "Y": 0, "Z": 0.99}, "Start": {"X": 0, "Y": 0, "Z": 0}, "End": {"X": 400, "Y": 0, "Z": 3000}},
                {"Direction": {"X": -0.13, "Y": 0, "Z": 0.99}, "Start": {"X": 400, "Y": 0, "Z": 3000}, "End": {"X": 0, "Y": 0, "Z": 6000}},
            ],
        }
        context = StructuralContext(lower_end_support="column_splice", side_incoming=("beam",))
        result = classify_member_document(member, context)
        self.assertEqual("COLUMN", result.role)
        self.assertEqual("框架柱", result.subtype)
        self.assertEqual("折线", result.axis_form)
        self.assertEqual(1, result.bend_count)
        self.assertEqual("vertical", result.pose)

    def test_secondary_beam_and_cantilever_are_beam_subtypes(self):
        secondary = classify_structural_role(_axis("horizontal"), StructuralContext(end_supports=("beam", "beam")))
        cantilever = classify_structural_role(_axis("horizontal"), StructuralContext(end_supports=("column", "free")))
        self.assertEqual(("BEAM", "次梁"), (secondary.role, secondary.subtype))
        self.assertEqual(("BEAM", "悬挑梁"), (cantilever.role, cantilever.subtype))

    def test_exported_links_map_column_side_beam_and_beam_ends(self):
        column = {
            "assemblyId": "10",
            "metadata": {
                "assemblyPosition": "SAMPLE-A",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 0, "y": 0, "z": 1},
                    "length": 4000,
                },
                "externalConnectionEvidence": {
                    "links": [
                        {"axisLocation": "start", "otherAxisPose": "vertical"},
                        {"axisLocation": "end", "otherAxisPose": "vertical"},
                        {"axisLocation": "end", "otherAxisPose": "horizontal"},
                    ]
                },
            },
        }
        beam = {
            "assemblyId": "20",
            "metadata": {
                "assemblyPosition": "SAMPLE-B",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 3000},
                    "direction": {"x": 1, "y": 0, "z": 0},
                    "length": 8000,
                },
                "externalConnectionEvidence": {
                    "links": [
                        {"axisLocation": "start", "otherAxisPose": "vertical"},
                        {"axisLocation": "end", "otherAxisPose": "vertical"},
                        {"axisLocation": "middle", "otherAxisPose": "horizontal"},
                    ]
                },
            },
        }
        incomplete = {
            "assemblyId": "30",
            "metadata": {
                "assemblyPosition": "GKZ-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 0, "y": 0, "z": 1},
                    "length": 4000,
                },
                "externalConnectionEvidence": {"links": []},
            },
        }

        column_role = classify_body_bracket_assembly(column)
        beam_role = classify_body_bracket_assembly(beam)
        incomplete_role = classify_body_bracket_assembly(incomplete)
        self.assertEqual(("COLUMN", "框架柱"), (column_role.role, column_role.subtype))
        self.assertEqual(("BEAM", "框梁"), (beam_role.role, beam_role.subtype))
        self.assertEqual("UNKNOWN", incomplete_role.role)
        self.assertNotIn("GKZ-SAMPLE", incomplete_role.evidence_codes)

    def test_vertical_shaft_with_side_beam_and_no_lower_tier_is_column(self):
        def _assembly(mark: str, length: float, parts: list[dict], links: list[dict]) -> dict:
            return {
                "assemblyId": "40",
                "metadata": {
                    "assemblyPosition": mark,
                    "memberAxisEvidence": {
                        "origin": {"x": 0, "y": 0, "z": 0},
                        "direction": {"x": 0, "y": 0, "z": 1},
                        "length": length,
                    },
                    "externalConnectionEvidence": {"links": links},
                },
                "parts": parts,
            }

        shaft = {
            "partId": 1,
            "isPlateLike": True,
            "obbDims": {"x": 16, "y": 500, "z": 3800},
        }
        column = _assembly(
            "GZ-SAMPLE",
            3800,
            [shaft, {**shaft, "partId": 2}],
            [{"axisLocation": "end", "otherAxisPose": "horizontal"}],
        )
        plate = _assembly(
            "GZ-SAMPLE",
            430,
            [{"partId": 1, "isPlateLike": True, "obbDims": {"x": 10, "y": 300, "z": 430}}],
            [{"axisLocation": "end", "otherAxisPose": "horizontal"}],
        )
        bare = _assembly("GKZ-SAMPLE", 3800, [shaft, {**shaft, "partId": 2}], [])

        result = classify_body_bracket_assembly(column)
        self.assertEqual(("COLUMN", "框架柱", "MR-COL-003"), (result.role, result.subtype, result.rule_id))
        self.assertIn("end.lower.outside_model", result.evidence_codes)
        self.assertNotIn("GZ-SAMPLE", result.evidence_codes)
        self.assertEqual("UNKNOWN", classify_body_bracket_assembly(plate).role)
        self.assertEqual("UNKNOWN", classify_body_bracket_assembly(bare).role)

    def test_round_bars_welded_to_one_plate_side_are_embed(self):
        plate = _plate(1, 0)
        left = _bar(2, -200)
        right = _bar(3, -200)
        assembly = {
            "assemblyId": "40",
            "metadata": {
                "assemblyPosition": "MJ-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 0, "y": 0, "z": 1},
                    "length": 500,
                },
            },
            "parts": [plate, left, right],
            "relationships": [
                {"partIdA": 1, "partIdB": 2, "edgeType": "Weld"},
                {"partIdA": 1, "partIdB": 3, "edgeType": "Weld"},
            ],
        }
        opposite = {
            **assembly,
            "parts": [plate, left, _bar(3, 200)],
        }
        beam = {
            **assembly,
            "metadata": {
                "assemblyPosition": "GL-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 3000},
                    "direction": {"x": 1, "y": 0, "z": 0},
                    "length": 8000,
                },
                "externalConnectionEvidence": {
                    "links": [
                        {"axisLocation": "start", "otherAxisPose": "vertical"},
                        {"axisLocation": "end", "otherAxisPose": "vertical"},
                    ]
                },
            },
            "parts": [plate, _bar(2, -200, long_axis={"x": 0, "y": 1, "z": 0}), _bar(3, -200)],
        }

        result = classify_body_bracket_assembly(assembly)
        self.assertEqual("EMBED", result.role)
        self.assertEqual("UNKNOWN", classify_body_bracket_assembly(opposite).role)
        self.assertEqual("BEAM", classify_body_bracket_assembly(beam).role)
        self.assertNotIn("MJ-SAMPLE", result.evidence_codes)

    def test_single_inclined_compact_bar_is_brace(self):
        bar = {
            "partId": 1,
            "isPlateLike": False,
            "thickness": 200,
            "centroid": {"x": 0, "y": 0, "z": 0},
            "obbDims": {"x": 200, "y": 200, "z": 4800},
            "plateNormal": {"x": 1, "y": 0, "z": 0},
            "plateLongDirection": {"x": 0, "y": 0.756, "z": -0.655},
        }
        inclined = {
            "assemblyId": "50",
            "metadata": {
                "assemblyPosition": "BE-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 0, "y": 0.756, "z": -0.655},
                    "length": 4800,
                },
            },
            "parts": [bar],
            "relationships": [],
        }
        horizontal = {
            **inclined,
            "metadata": {
                "assemblyPosition": "BE-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 1, "y": 0, "z": 0},
                    "length": 4800,
                },
            },
        }
        plate = {**bar, "isPlateLike": True, "obbDims": {"x": 12, "y": 200, "z": 4800}}
        plated = {**inclined, "parts": [plate]}

        result = classify_body_bracket_assembly(inclined)
        self.assertEqual("BRACE", result.role)
        self.assertEqual("UNKNOWN", classify_body_bracket_assembly(horizontal).role)
        self.assertEqual("UNKNOWN", classify_body_bracket_assembly(plated).role)
        self.assertNotIn("BE-SAMPLE", result.evidence_codes)

    def test_two_inclined_stringers_and_repeated_plates_are_stair(self):
        def _stringer(part_id: int) -> dict:
            return {
                "partId": part_id,
                "isPlateLike": False,
                "thickness": 8,
                "centroid": {"x": 0, "y": 0, "z": 0},
                "obbDims": {"x": 80, "y": 250, "z": 6000},
                "plateNormal": {"x": 1, "y": 0, "z": 0},
                "plateLongDirection": {"x": 0, "y": 0.707, "z": 0.707},
            }

        def _tread(part_id: int) -> dict:
            return {
                "partId": part_id,
                "isPlateLike": True,
                "thickness": 4,
                "centroid": {"x": 0, "y": 0, "z": 0},
                "obbDims": {"x": 100, "y": 240, "z": 440},
                "plateNormal": {"x": 0, "y": 1, "z": 0},
                "plateLongDirection": {"x": 1, "y": 0, "z": 0},
            }

        assembly = {
            "assemblyId": "60",
            "metadata": {
                "assemblyPosition": "TL-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 0, "y": 0.707, "z": 0.707},
                    "length": 6000,
                },
            },
            "parts": [_stringer(1), _stringer(2), *[_tread(10 + index) for index in range(8)]],
            "relationships": [],
        }
        beam = {
            **assembly,
            "parts": [
                {**_stringer(1), "plateLongDirection": {"x": 1, "y": 0, "z": 0}},
                {**_stringer(2), "plateLongDirection": {"x": 1, "y": 0, "z": 0}},
                *[_tread(10 + index) for index in range(8)],
            ],
            "metadata": {
                "assemblyPosition": "TL-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 3000},
                    "direction": {"x": 1, "y": 0, "z": 0},
                    "length": 6000,
                },
                "externalConnectionEvidence": {
                    "links": [
                        {"axisLocation": "start", "otherAxisPose": "vertical"},
                        {"axisLocation": "end", "otherAxisPose": "vertical"},
                    ]
                },
            },
        }

        result = classify_body_bracket_assembly(assembly)
        self.assertEqual("STAIR", result.role)
        self.assertEqual("BEAM", classify_body_bracket_assembly(beam).role)
        self.assertNotIn("TL-SAMPLE", result.evidence_codes)

    def test_horizontal_checker_plate_on_one_side_angles_is_landing(self):
        def _deck() -> dict:
            return {
                "partId": 1,
                "isPlateLike": True,
                "material": "Q235花纹板",
                "thickness": 6,
                "centroid": {"x": 0, "y": 0, "z": 0},
                "obbDims": {"x": 6, "y": 1390, "z": 1890},
                "plateNormal": {"x": 0, "y": 0, "z": 1},
            }

        def _angle(part_id: int, z: float) -> dict:
            return {
                "partId": part_id,
                "isPlateLike": False,
                "centroid": {"x": 100.0 * part_id, "y": 0, "z": z},
                "obbDims": {"x": 50, "y": 50, "z": 424},
            }

        assembly = {
            "assemblyId": "70",
            "metadata": {
                "assemblyPosition": "LTHW-SAMPLE",
                "memberAxisEvidence": {
                    "origin": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 1, "y": 0, "z": 0},
                    "length": 1890,
                },
            },
            "parts": [_deck(), *[_angle(10 + index, -28) for index in range(6)]],
        }
        plain = {
            **assembly,
            "parts": [{**_deck(), "material": "Q235B"}, *[_angle(10 + index, -28) for index in range(6)]],
        }
        narrow = {
            **assembly,
            "parts": [
                {**_deck(), "obbDims": {"x": 5, "y": 600, "z": 3100}},
                *[_angle(10 + index, -28) for index in range(6)],
            ],
        }
        both_sides = {
            **assembly,
            "parts": [_deck(), *[_angle(10 + index, -28 if index < 3 else 28) for index in range(6)]],
        }
        flat_stiffener = {
            **assembly,
            "parts": [
                _deck(),
                *[_angle(10 + index, -28) for index in range(6)],
                {
                    "partId": 90,
                    "isPlateLike": True,
                    "material": "Q235B",
                    "centroid": {"x": 0, "y": 0, "z": -40},
                    "obbDims": {"x": 6, "y": 100, "z": 400},
                    "plateNormal": {"x": 0, "y": 1, "z": 0},
                },
            ],
        }

        result = classify_body_bracket_assembly(assembly)
        self.assertEqual("STAIR_LANDING", result.role)
        self.assertEqual("休息平台", result.role_label)
        self.assertEqual("MR-LANDING-001", result.rule_id)
        self.assertEqual(1, landing_checker_plate(assembly)["partId"])
        self.assertIsNone(landing_checker_plate(plain))
        self.assertIsNone(landing_checker_plate(narrow))
        self.assertIsNone(landing_checker_plate(both_sides))
        self.assertIsNone(landing_checker_plate(flat_stiffener))
        self.assertNotIn("LTHW-SAMPLE", result.evidence_codes)

    def test_wind_column_requires_only_girt_incoming(self):
        result = classify_structural_role(
            _axis("vertical"),
            StructuralContext(lower_end_support="foundation", side_incoming=("girt",)),
        )
        self.assertEqual(("COLUMN", "抗风柱"), (result.role, result.subtype))


if __name__ == "__main__":
    unittest.main()
