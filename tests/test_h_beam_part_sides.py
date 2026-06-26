import unittest

from zijinhua_tekla.classifiers.h_beam_part_sides import classify_h_beam_part_sides


class HBeamPartSideTests(unittest.TestCase):
    def test_classifies_four_local_h_beam_sides(self):
        assembly = {
            "assemblyId": "H-1",
            "metadata": {"assemblyPosition": "T3-7GL-36"},
            "parts": [
                _part("top", "T3-P-top", "上翼缘", -100, 100, 0, 14),
                _part("web", "T3-P-web", "腹板", -6, 6, -500, 0),
                _part("bottom", "T3-P-bottom", "下翼缘", -100, 100, -514, -500),
                _part("top-attachment", "T3-P-top-a", "吊耳", -20, 20, 20, 90),
                _part("bottom-attachment", "T3-P-bottom-a", "连接板", -20, 20, -610, -540),
                _part("web-left-attachment", "T3-P-left-a", "加劲板", -90, -20, -430, -120),
                _part("web-right-attachment", "T3-P-right-a", "加劲板", 20, 90, -430, -120),
            ],
        }

        rows = classify_h_beam_part_sides(assembly)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("TOP_FLANGE_OUTER", by_position["T3-P-top-a"].h_side)
        self.assertEqual("BOTTOM_FLANGE_OUTER", by_position["T3-P-bottom-a"].h_side)
        self.assertEqual("WEB_LEFT", by_position["T3-P-left-a"].h_side)
        self.assertEqual("WEB_RIGHT", by_position["T3-P-right-a"].h_side)
        self.assertIn("PROJECTED_CONTOUR_VOTE", by_position["T3-P-left-a"].evidence_codes)

    def test_marks_boundary_when_part_votes_for_multiple_sides(self):
        assembly = {
            "assemblyId": "H-1",
            "metadata": {"assemblyPosition": "T3-7GL-36"},
            "parts": [
                _part("top", "T3-P-top", "上翼缘", -100, 100, 0, 14),
                _part("web", "T3-P-web", "腹板", -6, 6, -500, 0),
                _part("bottom", "T3-P-bottom", "下翼缘", -100, 100, -514, -500),
                _part("through", "T3-P-through", "贯通板", -90, 90, -530, 30),
            ],
        }

        rows = classify_h_beam_part_sides(assembly)

        self.assertEqual(1, len(rows))
        self.assertEqual("BOUNDARY_OR_AMBIGUOUS", rows[0].h_side)
        self.assertEqual("GEOMETRY", rows[0].issue_category)
        self.assertIn("MULTI_SIDE_VOTES", rows[0].evidence_codes)

    def test_reports_feature_gap_when_projection_evidence_is_missing(self):
        assembly = {
            "assemblyId": "H-1",
            "metadata": {"assemblyPosition": "T3-7GL-36"},
            "parts": [
                _part("top", "T3-P-top", "上翼缘", -100, 100, 0, 14),
                _part("web", "T3-P-web", "腹板", -6, 6, -500, 0),
                _part("bottom", "T3-P-bottom", "下翼缘", -100, 100, -514, -500),
                {"partId": "missing", "partPosition": "T3-P-missing", "name": "连接板"},
            ],
        }

        rows = classify_h_beam_part_sides(assembly)

        self.assertEqual(1, len(rows))
        self.assertEqual("INSUFFICIENT_EVIDENCE", rows[0].h_side)
        self.assertEqual("FEATURE", rows[0].issue_category)
        self.assertIn("MISSING_SECTION_PROJECTION_EVIDENCE", rows[0].evidence_codes)

    def test_uses_member_part_roles_when_main_material_names_are_generic(self):
        assembly = {
            "assemblyId": "H-1",
            "parts": [
                _part("top", "T3-P-5114", "GL4015-1", -100, 100, 0, 8, thickness=8),
                _part("web", "T3-P-5046", "GL4015-1", -4, 4, -392, 0, thickness=8),
                _part("bottom", "T3-P-5006", "GL4015-1", -100, 100, -400, -392, thickness=8),
                _part("right", "T3-P-right-a", "连接板", 24, 70, -350, -50),
            ],
        }
        member = {
            "Classification": {
                "PartRoles": [
                    {"PartId": "top", "Role": "flange_candidate"},
                    {"PartId": "web", "Role": "wall_candidate"},
                    {"PartId": "bottom", "Role": "flange_candidate"},
                ]
            }
        }

        rows = classify_h_beam_part_sides(assembly, member)

        self.assertEqual(1, len(rows))
        self.assertEqual("WEB_RIGHT", rows[0].h_side)
        self.assertIn("MEMBER_PART_ROLES_MAIN_MATERIAL", rows[0].evidence_codes)

    def test_curved_beam_web_side_uses_plate_thickness_not_global_swept_web_bounds(self):
        assembly = {
            "assemblyId": "H-curve",
            "parts": [
                _part("top", "T3-P-5114", "GL4015-1", -1649, 1649, -4, 4, thickness=8),
                _part("bottom", "T3-P-5006", "GL4015-1", -1649, 1649, -396, -388, thickness=8),
                _part("web", "T3-P-5046", "GL4015-1", -1589, 1574, -388, -4, thickness=8),
                _part("left-angle", "T3-L-301", "BEAM", -414, -73, -71, 4),
                _part("right-plate", "T3-P-3226", "连接板", -38, 270, -388, -4),
            ],
        }
        member = {
            "Classification": {
                "PartRoles": [
                    {"PartId": "top", "Role": "flange_candidate"},
                    {"PartId": "web", "Role": "wall_candidate"},
                    {"PartId": "bottom", "Role": "flange_candidate"},
                ]
            }
        }

        rows = classify_h_beam_part_sides(assembly, member)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("WEB_LEFT", by_position["T3-L-301"].h_side)
        self.assertEqual("WEB_RIGHT", by_position["T3-P-3226"].h_side)
        self.assertIn("WEB_THICKNESS_ESTIMATE_SPLIT", by_position["T3-P-3226"].evidence_codes)


    def test_direct_profile_station_frame_applies_between_sparse_profile_frames(self):
        assembly = {
            "assemblyId": "H-direct",
            "metadata": {
                "assemblyPosition": "T2-3GL-17",
                "hBeamSectionEvidence": {
                    "source": "directHProfileSectionFrame.v1",
                    "stationFrames": [
                        _frame(25),
                        _frame(1500),
                        _frame(2975),
                    ],
                },
            },
            "parts": [
                _part("main", "T2-3B-721", "GL3020-1", -100, 100, -150, 150, station_start=0, station_end=3000),
                _part("top", "T2-3B-926", "连接板", -20, 20, 165, 220, station_start=720, station_end=730),
                _part("left", "T2-3B-1129", "连接板", -120, -70, -80, 80, station_start=2200, station_end=2210),
            ],
        }

        rows = classify_h_beam_part_sides(assembly)

        by_position = {row.part_position: row for row in rows}
        self.assertEqual("TOP_FLANGE_OUTER", by_position["T2-3B-926"].h_side)
        self.assertEqual("WEB_LEFT", by_position["T2-3B-1129"].h_side)
        self.assertIn("DIRECT_H_PROFILE_FRAME", by_position["T2-3B-926"].evidence_codes)

def _part(part_id, position, name, min_u, max_u, min_v, max_v, thickness=None, station_start=None, station_end=None):
    part = {
        "partId": part_id,
        "partPosition": position,
        "name": name,
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
    if thickness is not None:
        part["thickness"] = thickness
    if station_start is not None and station_end is not None:
        part["mainMaterialEvidence"]["axisStationStart"] = station_start
        part["mainMaterialEvidence"]["axisStationEnd"] = station_end
    return part

def _frame(station):
    return {
        "station": station,
        "webCenterU": 0,
        "webHalfThickness": 3,
        "topOuterV": 150,
        "bottomOuterV": -150,
        "webTopV": 140,
        "webBottomV": -140,
        "diagnostics": ["DIRECT_H_PROFILE_FRAME"],
    }

if __name__ == "__main__":
    unittest.main()
