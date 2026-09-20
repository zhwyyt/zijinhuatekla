import inspect
import unittest

from zijinhua_tekla.classifiers import weld_backing
from zijinhua_tekla.classifiers.weld_backing import classify_weld_backing_plates
from zijinhua_tekla.contracts.normalized import NormalizedPart, PartSpatialHints
from zijinhua_tekla.part_roles import classify_part_role


def _plate(part_id, position, profile, obb, **extra):
    part = {
        "partId": part_id,
        "partPosition": position,
        "name": extra.pop("name", "板"),
        "profileString": profile,
        "isPlateLike": extra.pop("isPlateLike", True),
        "thickness": extra.pop("thickness", obb[2] if len(obb) > 2 else 0),
        "obbDims": {"x": obb[0], "y": obb[1], "z": obb[2]},
        "boltHoleCount": extra.pop("boltHoleCount", 0),
        "weldDetails": extra.pop("weldDetails", []),
    }
    part.update(extra)
    return part


class WeldBackingTests(unittest.TestCase):
    def test_classifier_does_not_read_part_names(self):
        source = inspect.getsource(weld_backing)
        self.assertNotIn("衬垫板", source)
        self.assertNotIn("衬条", source)
        self.assertNotIn('get("name")', source)
        self.assertNotIn("part.get('name')", source)

    def test_strip_welded_to_section_host_is_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("host", "A-H-1", "HI780*200*10*16", (2000, 780, 200), isPlateLike=False, thickness=200),
                    _plate(
                        "strip",
                        "A-P-2",
                        "PL6*30",
                        (260, 30, 6),
                        thickness=6,
                        weldDetails=[
                            {
                                "mainPartId": "host",
                                "secondaryPartId": "strip",
                                "weldType": "Weld",
                                "sizeAbove": 6,
                                "sizeBelow": 0,
                                "shopWeld": True,
                                "aroundWeld": True,
                            }
                        ],
                    ),
                ],
                "relationships": [
                    {
                        "partIdA": "host",
                        "partIdB": "strip",
                        "edgeType": "Weld",
                        "meta": "Weld|shop=True|sizeAbove=6|sizeBelow=0|around=True",
                    },
                    {"partIdA": "host", "partIdB": "strip", "edgeType": "Contact"},
                ],
            }
        )
        self.assertIn("strip", hits)
        self.assertTrue(any("焊缝" in item for item in hits["strip"]))
        self.assertTrue(any("从件" in item or "环绕" in item or "角焊" in item for item in hits["strip"]))
        result = classify_part_role(
            NormalizedPart(part_id="strip", part_position="A-P-2", name="板", profile="PL6*30", is_plate_like=True),
            PartSpatialHints(weld_backing=True, weld_backing_evidence=hits["strip"]),
        )
        self.assertEqual("焊接垫板", result.role)

    def test_strip_contacting_two_wall_plates_without_weld_is_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("wall_a", "A-P-1", "PL16*968", (3000, 968, 16), thickness=16),
                    _plate("wall_b", "A-P-2", "PL16*1000", (3000, 1000, 16), thickness=16),
                    _plate("strip", "A-P-3", "PL16*30", (968, 30, 16), thickness=16, name="连接板"),
                ],
                "relationships": [
                    {"partIdA": "strip", "partIdB": "wall_a", "edgeType": "Contact"},
                    {"partIdA": "strip", "partIdB": "wall_b", "edgeType": "Contact"},
                ],
            }
        )
        self.assertIn("strip", hits)
        self.assertTrue(any("接缝" in item for item in hits["strip"]))

    def test_strip_contacting_bevelled_host_is_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("host", "A-P-1", "PL20*400", (2000, 400, 20), thickness=20, hasEdgeBevel=True, edgeBevelCount=1),
                    _plate("strip", "A-P-2", "PL8*25", (400, 25, 8), thickness=8),
                ],
                "relationships": [
                    {"partIdA": "strip", "partIdB": "host", "edgeType": "Contact"},
                ],
            }
        )
        self.assertIn("strip", hits)
        self.assertTrue(any("剖口" in item for item in hits["strip"]))

    def test_name_alone_is_not_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("strip", "A-P-9", "PL16*30", (968, 30, 16), thickness=16, name="衬垫板"),
                ],
                "relationships": [],
            }
        )
        self.assertEqual({}, hits)
        result = classify_part_role(
            NormalizedPart(
                part_id="strip",
                part_position="A-P-9",
                name="衬垫板",
                profile="PL16*30",
                is_plate_like=True,
                thickness=16,
                length=968,
                width=30,
            )
        )
        self.assertNotEqual("焊接垫板", result.role)
        self.assertNotEqual("衬垫板", result.role)

    def test_wide_named_plate_with_holes_is_not_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("host", "A-H-1", "BH400*200*8*12", (4000, 400, 200), isPlateLike=False, thickness=200),
                    _plate(
                        "plate",
                        "A-P-9",
                        "PL16*200",
                        (400, 200, 16),
                        thickness=16,
                        name="衬垫板",
                        boltHoleCount=2,
                    ),
                ],
                "relationships": [
                    {"partIdA": "plate", "partIdB": "host", "edgeType": "Weld"},
                ],
            }
        )
        self.assertNotIn("plate", hits)

    def test_electroslag_block_is_not_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("wall_a", "A-P-1", "PL16*968", (3000, 968, 16), thickness=16),
                    _plate("wall_b", "A-P-2", "PL16*1000", (3000, 1000, 16), thickness=16),
                    _plate("block", "A-DB-1", "PL25*50", (900, 50, 25), thickness=25, name="电渣焊块"),
                ],
                "relationships": [
                    {"partIdA": "block", "partIdB": "wall_a", "edgeType": "Weld"},
                    {"partIdA": "block", "partIdB": "wall_b", "edgeType": "Contact"},
                ],
            }
        )
        self.assertNotIn("block", hits)

    def test_round_bar_is_not_backing(self):
        hits = classify_weld_backing_plates(
            {
                "parts": [
                    _plate("wall", "A-P-1", "PL30*1000", (3000, 1000, 30), thickness=30),
                    _plate("rod", "A-GG-1", "D8", (199, 38, 8), isPlateLike=False, thickness=8, name="柱挂钩"),
                ],
                "relationships": [
                    {"partIdA": "rod", "partIdB": "wall", "edgeType": "Contact"},
                ],
            }
        )
        self.assertNotIn("rod", hits)


if __name__ == "__main__":
    unittest.main()
