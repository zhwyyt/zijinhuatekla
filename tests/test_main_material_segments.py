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
