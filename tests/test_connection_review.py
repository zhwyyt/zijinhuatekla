import unittest

from zijinhua_tekla.classifiers.connection_review import connection_review_candidates
from zijinhua_tekla.classifiers.member_structural_role import classify_body_bracket_assembly


def _assembly(assembly_id, position, origin, direction, length, parts, links=()):
    return {
        "assemblyId": assembly_id,
        "metadata": {
            "assemblyPosition": position,
            "memberAxisEvidence": {
                "origin": {"x": origin[0], "y": origin[1], "z": origin[2]},
                "direction": {"x": direction[0], "y": direction[1], "z": direction[2]},
                "length": length,
            },
            "externalConnectionEvidence": {"links": list(links)},
        },
        "parts": parts,
        "relationships": [],
    }


def _brace():
    return _assembly(
        "1",
        "BRACE-SAMPLE",
        (0, 0, 0),
        (0, 0.756, -0.655),
        4800,
        [{
            "partId": 1,
            "isPlateLike": False,
            "thickness": 200,
            "centroid": {"x": 0, "y": 0, "z": 0},
            "obbDims": {"x": 200, "y": 200, "z": 4800},
            "plateNormal": {"x": 1, "y": 0, "z": 0},
            "plateLongDirection": {"x": 0, "y": 0.756, "z": -0.655},
        }],
    )


def _node(origin):
    return _assembly(
        "2",
        "NODE-SAMPLE",
        origin,
        (1, 0, 0),
        588,
        [{
            "partId": 2,
            "isPlateLike": True,
            "thickness": 20,
            "centroid": {"x": origin[0], "y": origin[1], "z": origin[2]},
            "obbDims": {"x": 20, "y": 150, "z": 588},
            "plateNormal": {"x": 0, "y": 0, "z": 1},
            "plateLongDirection": {"x": 1, "y": 0, "z": 0},
        }],
    )


class ConnectionReviewTests(unittest.TestCase):
    def test_near_unconnected_node_is_only_a_candidate(self):
        brace = _brace()
        node = _node((0, 180, 0))
        candidates = connection_review_candidates([brace, node])

        self.assertEqual(1, len(candidates))
        self.assertEqual("MODEL_CONNECTION_MISSING", candidates[0].issue_type)
        self.assertEqual("模型中没有焊缝或螺栓", candidates[0].note)
        self.assertLessEqual(candidates[0].gap_mm, 250)
        self.assertEqual("BRACE", classify_body_bracket_assembly(brace).role)
        self.assertEqual("UNKNOWN", classify_body_bracket_assembly(node).role)

    def test_modeled_bolt_or_large_gap_emits_nothing(self):
        brace = _brace()
        linked = _node((0, 180, 0))
        linked["metadata"]["externalConnectionEvidence"] = {
            "links": [{"otherAssemblyId": "1", "relation": "Bolt"}]
        }
        far = _node((0, 4000, 0))
        long_member = _node((0, 180, 0))
        long_member["assemblyId"] = "3"
        long_member["metadata"]["memberAxisEvidence"]["length"] = 8000

        self.assertEqual([], connection_review_candidates([brace, linked]))
        self.assertEqual([], connection_review_candidates([brace, far]))
        self.assertEqual([], connection_review_candidates([brace, long_member]))


if __name__ == "__main__":
    unittest.main()
