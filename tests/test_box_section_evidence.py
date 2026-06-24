import unittest

from zijinhua_tekla.box_section import classify_box_section_evidence


class BoxSectionEvidenceTests(unittest.TestCase):
    def test_long_axis_plate_is_wall_core(self):
        assembly = {
            "metadata": {"memberAxisEvidence": {"length": 9000}},
            "relationships": [],
            "parts": [
                _part("1", "B-P-1", "COLUMN", "PL16*900", "FACE_A", offset=900, start=0, end=9000),
            ],
        }

        evidence = classify_box_section_evidence(assembly)

        self.assertEqual("WALL_CORE", evidence["1"].side)
        self.assertIn("AXIS_COVERAGE_LONG", evidence["1"].evidence_codes)
        self.assertEqual("FACE_A", evidence["1"].face_id)

    def test_short_part_outside_wall_offset_is_outer_attachment(self):
        assembly = {
            "metadata": {"memberAxisEvidence": {"length": 9000}},
            "relationships": [_rel("wall", "att", "Weld")],
            "parts": [
                _part("wall", "B-P-W", "COLUMN", "PL16*900", "FACE_A", offset=900, start=0, end=9000),
                _part("att", "B-P-A", "连接板", "PL10", "FACE_A", offset=1280, start=2000, end=2300),
            ],
        }

        evidence = classify_box_section_evidence(assembly)

        self.assertEqual("OUTER_ATTACHMENT", evidence["att"].side)
        self.assertIn("FACE_OFFSET_OUTSIDE_WALL_CORE", evidence["att"].evidence_codes)
        self.assertIn("SHORT_AXIS_PART", evidence["att"].evidence_codes)

    def test_short_part_near_wall_core_with_multiple_contacts_is_inner_stiffener_candidate(self):
        assembly = {
            "metadata": {"memberAxisEvidence": {"length": 9000}},
            "relationships": [_rel("wall-a", "inner", "Weld"), _rel("wall-b", "inner", "Contact")],
            "parts": [
                _part("wall-a", "B-P-W1", "COLUMN", "PL16*900", "FACE_A", offset=900, start=0, end=9000),
                _part("wall-b", "B-P-W2", "COLUMN", "PL16*900", "FACE_B", offset=910, start=0, end=9000),
                _part("inner", "B-P-I", "内隔板", "PL20", "FACE_A", offset=650, start=3000, end=3300),
            ],
        }

        evidence = classify_box_section_evidence(assembly)

        self.assertEqual("INNER_STIFFENER_OR_DIAPHRAGM", evidence["inner"].side)
        self.assertIn("MULTI_WALL_RELATIONSHIP", evidence["inner"].evidence_codes)
        self.assertIn("FACE_OFFSET_INSIDE_WALL_CORE", evidence["inner"].evidence_codes)


def _part(part_id, position, name, profile, face, offset, start, end):
    return {
        "partId": part_id,
        "partPosition": position,
        "name": name,
        "profileString": profile,
        "mainMaterialEvidence": {
            "bodyFaceId": face,
            "bodyFaceOffset": offset,
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "isBodyWallPlateCandidate": True,
        },
    }


def _rel(part_a, part_b, edge_type):
    return {"partIdA": part_a, "partIdB": part_b, "edgeType": edge_type}


if __name__ == "__main__":
    unittest.main()

