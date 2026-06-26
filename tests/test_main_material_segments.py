import unittest

from zijinhua_tekla.classifiers.box_main_material_segments import (
    SegmentContinuityLevel,
    classify_main_material_segment_groups,
)


class MainMaterialSegmentTests(unittest.TestCase):
    def test_classifies_gl_member_top_web_and_bottom_flange_segments(self):
        assembly = {
            "assemblyId": "GL-1",
            "metadata": {"assemblyPosition": "T3-6GL-110", "memberAxisEvidence": {"length": 13114.9}},
            "relationships": [
                _rel("top", "web", "Contact"),
                _rel("web", "bottom-1", "Weld"),
                _rel("web", "bottom-2", "Weld"),
                _rel("web", "bottom-3", "Weld"),
                _rel("web", "stiffener", "Weld"),
            ],
            "parts": [
                _part("top", "T3-P-4866", "上翼缘", "PL14.0*200.0", "RADIAL_Y_NEG", 0, 13114.9),
                _part("web", "T3-P-4753", "腹板", "PL12.0", "RADIAL_Z_NEG", 0, 13114.9),
                _part("bottom-1", "T3-P-4863", "下翼缘", "PL14*200", "RADIAL_Z_NEG", 0, 1775.0),
                _part("bottom-2", "T3-P-5555", "下翼缘", "PL22.0*200.0", "RADIAL_Z_NEG", 1775.0, 11324.9),
                _part("bottom-3", "T3-P-4862", "下翼缘", "PL14*200", "RADIAL_Z_NEG", 11324.8, 13114.9),
                _part("stiffener", "T3-P-4653", "加劲板", "PL12.0", "RADIAL_Z_NEG", 1966.6, 1978.6),
            ],
        }

        groups = classify_main_material_segment_groups(assembly)

        by_role = {group.evidence_summary["main_material_role"]: group for group in groups}
        self.assertEqual({"TOP_FLANGE", "WEB", "BOTTOM_FLANGE"}, set(by_role))
        self.assertEqual(["T3-P-4866"], by_role["TOP_FLANGE"].part_positions)
        self.assertEqual(["T3-P-4753"], by_role["WEB"].part_positions)
        self.assertEqual(["T3-P-4863", "T3-P-5555", "T3-P-4862"], by_role["BOTTOM_FLANGE"].part_positions)
        self.assertEqual(SegmentContinuityLevel.CONTINUOUS, by_role["BOTTOM_FLANGE"].continuity_level)
        self.assertIn("PROFILE_FAMILY_H_OR_GL", by_role["BOTTOM_FLANGE"].evidence_codes)
        self.assertNotIn("T3-P-4653", ";".join(part for group in groups for part in group.part_positions))

    def test_falls_back_to_box_strategy_for_box_member(self):
        assembly = {
            "assemblyId": "BOX-1",
            "metadata": {"assemblyPosition": "T3-5GKZ-10", "memberAxisEvidence": {"length": 9000}},
            "relationships": [_rel("1", "2", "Weld")],
            "parts": [
                _part("1", "B-P-1", "COLUMN", "PL16*900", "FACE_A", 0, 3000),
                _part("2", "B-P-2", "COLUMN", "PL16*900", "FACE_A", 3000, 6000),
            ],
        }

        groups = classify_main_material_segment_groups(assembly)

        self.assertEqual(1, len(groups))
        self.assertEqual("BOX_WALL_FACE", groups[0].evidence_summary["main_material_role"])
        self.assertEqual(["B-P-1", "B-P-2"], groups[0].part_positions)

    def test_ignores_part_roles_when_h_gl_lacks_explicit_section_evidence(self):
        assembly = {
            "assemblyId": "GL-2",
            "metadata": {
                "assemblyPosition": "T2-3GL-55",
                "memberAxisEvidence": {"length": 4750},
            },
            "relationships": [_rel("wall", "flange", "Weld")],
            "parts": [
                _part("web", "T2-3B-526", "乱码", "PL30*400", "RADIAL_Z_NEG", 0, 4750),
                _part("flange", "T2-3B-797", "XZJJ", "PL14", "RADIAL_Z_NEG", 30, 4720),
                _part("wall", "T2-3B-508", "乱码", "PL30*400", "RADIAL_Z_POS", 1056, 3911),
            ],
        }
        member = {
            "Classification": {
                "PartRoles": [
                    {"PartId": "web", "Role": "web_candidate"},
                    {"PartId": "flange", "Role": "flange_candidate"},
                    {"PartId": "wall", "Role": "wall_candidate"},
                ]
            }
        }

        groups = classify_main_material_segment_groups(assembly, member)

        self.assertEqual([], groups)

    def test_classifies_h_gl_main_plates_from_station_slice_loops(self):
        frames = []
        for station in range(0, 5000, 250):
            slices = [
                _slice("web", "T2-3B-526", "flange_candidate"),
                _slice("flange", "T2-3B-797", "web_candidate"),
            ]
            if 1000 <= station <= 4000:
                slices.append(_slice("confirmed", "T2-3B-508", "flange_candidate"))
            if 3500 <= station <= 4750:
                slices.append(_slice("tail-local", "T2-3B-502", "flange_candidate"))
            if 1200 <= station <= 1500:
                slices.append(_slice("short", "T2-3B-LOCAL", "flange_candidate"))
            frames.append({"station": station, "partSlices": slices})
        assembly = {
            "assemblyId": "GL-3",
            "metadata": {
                "assemblyPosition": "T2-3GL-55",
                "memberAxisEvidence": {"length": 4750},
                "hBeamSectionEvidence": {"source": "hBeamStationLocalSolidSection.v1", "stationFrames": frames},
            },
            "relationships": [],
            "parts": [
                _part("web", "T2-3B-526", "乱码", "PL30*400", "RADIAL_Z_NEG", 0, 4750),
                _part("flange", "T2-3B-797", "XZJJ", "PL14", "RADIAL_Z_NEG", 30, 4720),
                _part("confirmed", "T2-3B-508", "乱码", "PL30*400", "RADIAL_Z_POS", 1056, 3911),
                _part("tail-local", "T2-3B-502", "乱码", "PL30*400", "RADIAL_Z_POS", 3500, 4750),
                _part("short", "T2-3B-LOCAL", "乱码", "PL16", "RADIAL_Z_POS", 1200, 1500),
            ],
        }
        member = {
            "Classification": {
                "PartRoles": [
                    {"PartId": "web", "Role": "other"},
                    {"PartId": "flange", "Role": "other"},
                    {"PartId": "confirmed", "Role": "other"},
                ]
            }
        }

        groups = classify_main_material_segment_groups(assembly, member)

        positions = {position for group in groups for position in group.part_positions}
        self.assertEqual({"T2-3B-526", "T2-3B-797", "T2-3B-508"}, positions)
        self.assertNotIn("T2-3B-502", positions)
        self.assertNotIn("T2-3B-LOCAL", positions)
        self.assertTrue(all("H_GL_STATION_SLICE_MAIN_PLATE" in group.evidence_codes for group in groups))
        self.assertTrue(all(group.evidence_summary["main_material_source"] == "hBeamSectionEvidence.stationFrames" for group in groups))


def _slice(part_id, position, role_hint):
    return {
        "partId": part_id,
        "partPosition": position,
        "roleHint": role_hint,
        "spanU": 100,
        "spanV": 20,
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
def _part(part_id, position, name, profile, face, start, end):
    return {
        "partId": part_id,
        "partPosition": position,
        "name": name,
        "profileString": profile,
        "thickness": 12,
        "mainMaterialEvidence": {
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "bodyFaceId": face,
            "isBodyWallPlateCandidate": True,
            "evidenceSource": "axisProjection+radialFaceBucket",
        },
    }


def _rel(part_a, part_b, edge_type):
    return {"partIdA": part_a, "partIdB": part_b, "edgeType": edge_type}


if __name__ == "__main__":
    unittest.main()


