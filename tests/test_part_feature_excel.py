import unittest

from zijinhua_tekla.reports.part_feature_excel import (
    FEATURE_COLUMNS,
    algorithm_body_type,
    build_part_feature_rows,
)


class PartFeatureExcelTests(unittest.TestCase):
    def test_numeric_main_class_one_is_h(self):
        self.assertEqual(
            "H",
            algorithm_body_type({"Classification": {"MainClass": 1, "KeyDimensionsDisplay": "BH950*400*16*30"}}),
        )

    def test_h_direct_profile_marks_section_not_plates(self):
        rows = {row["零件名称"]: row for row in build_part_feature_rows(_h_assembly(), _h_member(), "T3-6GKL-4")}
        beam = rows["T3-H-471"]
        pad = rows["T3-P-4462"]
        plate = rows["T3-P-5453"]
        self.assertEqual("H", beam["构件类型"])
        self.assertEqual("是", beam["主材"])
        self.assertEqual("型钢", beam["主材说明"])
        self.assertEqual("否", pad["主材"])
        self.assertEqual("", pad["主材说明"])
        self.assertEqual("否", plate["主材"])
        self.assertNotEqual("BOX主壁板", plate["主材说明"])
        self.assertNotEqual("十字翼缘", plate["主材说明"])
        self.assertEqual("是", pad["焊接垫板"])
        self.assertEqual("否", beam["焊接垫板"])
        self.assertEqual("否", beam["BOX内零件"])
        self.assertTrue("下料" in pad["工序"] or pad["工序"].startswith("工序1"))
        self.assertNotEqual("不下", pad["工序"])
        self.assertEqual(set(FEATURE_COLUMNS), set(beam.keys()))

    def test_same_mark_plates_ignore_missed_boolean_cut(self):
        rows = {
            row["零件名称"]: row
            for row in build_part_feature_rows(_same_mark_plate_assembly(), _h_member(), "T3-6GKL-4")
        }
        plate = rows["T3-PX-187"]
        self.assertEqual("否", plate["剖口"])
        self.assertEqual("否", plate["洞口"])
        self.assertEqual("否", plate["割孔"])
        self.assertEqual("工序1：下料；工序2：下料钻孔", plate["工序"])
        self.assertNotEqual("UNKNOWN", plate["工序"])
        self.assertEqual(2, plate["数量"])

    def test_box_wall_stays_main_material(self):
        rows = {row["零件名称"]: row for row in build_part_feature_rows(_box_assembly(), _box_member(), "A-GKZ-1")}
        wall = rows["A-P-1"]
        pad = rows["A-P-2"]
        self.assertEqual("BOX", wall["构件类型"])
        self.assertEqual("是", wall["主材"])
        self.assertEqual("BOX主壁板", wall["主材说明"])
        self.assertEqual("否", pad["主材"])
        self.assertEqual("是", pad["焊接垫板"])


def _same_mark_plate_assembly() -> dict:
    box_a = {
        "min": {"x": 7706.4, "y": 2016.2, "z": 30580.0},
        "max": {"x": 7893.1, "y": 2224.7, "z": 31070.0},
    }
    box_b = {
        "min": {"x": 1169.9, "y": 9451.2, "z": 30580.0},
        "max": {"x": 1356.6, "y": 9659.7, "z": 31070.0},
    }
    plate = {
        "profileString": "PL20*490",
        "name": "连接板",
        "material": "Q355B",
        "runtimeType": "Beam",
        "isPlateLike": True,
        "thickness": 20,
        "obbDims": {"x": 260.0, "y": 490.0, "z": 20.0},
        "boltHoleCount": 2,
        "holeLikeFeatureCount": 2,
        "contourVertexCount": 4,
        "concaveCornerCount": 0,
        "contourPoints": [
            {"x": 0.0, "y": 0.0, "z": 0.0},
            {"x": 260.0, "y": 0.0, "z": 0.0},
            {"x": 260.0, "y": 490.0, "z": 0.0},
            {"x": 0.0, "y": 490.0, "z": 0.0},
        ],
    }
    first = dict(plate)
    first.update({"partId": "70797667", "partPosition": "T3-PX-187", "boundingBox": box_a, "booleanCutCount": 0})
    second = dict(plate)
    second.update(
        {
            "partId": "70797915",
            "partPosition": "T3-PX-187",
            "boundingBox": box_b,
            "booleanCutCount": 1,
            "holeLikeFeatureCount": 3,
            "booleanCutDetails": [
                {
                    "operativePartId": 71002361,
                    "cutsFatherSolid": False,
                    "cutProof": "AABB_MISS",
                    "boundingBox": {
                        "min": {"x": 519.3, "y": 9449.5, "z": 31258.0},
                        "max": {"x": 1571.3, "y": 9479.5, "z": 31288.0},
                    },
                }
            ],
        }
    )
    return {
        "assemblyId": "67451167",
        "mainPartId": "67451164",
        "metadata": {"assemblyPosition": "T3-6GKL-4"},
        "parts": [first, second],
        "relationships": [],
    }


def _h_member() -> dict:
    return {
        "Member": {"Name": "GKL9540-4", "ProfileString": "BH950*400*16*30"},
        "Classification": {
            "MainClass": 1,
            "KeyDimensionsDisplay": "BH950*400*16*30",
            "Confidence": 99,
            "Labels": ["profile-direct-hint"],
        },
    }


def _h_assembly() -> dict:
    return {
        "assemblyId": "67451167",
        "mainPartId": "67451164",
        "metadata": {
            "assemblyPosition": "T3-6GKL-4",
            "hBeamSectionEvidence": {
                "source": "directHProfileSectionFrame.v1",
                "diagnostics": ["DIRECT_H_PROFILE_FRAME", "PROFILE=BH950*400*16*30"],
                "stationFrames": [
                    {
                        "station": 0,
                        "webCenterU": 0,
                        "webHalfThickness": 8,
                        "topOuterV": 475,
                        "bottomOuterV": -475,
                        "webTopV": 445,
                        "webBottomV": -445,
                        "topFlangePartId": "67451164",
                        "webPartId": "67451164",
                        "bottomFlangePartId": "67451164",
                        "partSlices": [],
                    }
                ],
            },
        },
        "parts": [
            {
                "partId": "67451164",
                "partPosition": "T3-H-471",
                "name": "GKL9540-4",
                "profileString": "BH950*400*16*30",
                "material": "Q355B",
                "runtimeType": "Beam",
                "isPlateLike": False,
                "length": 9910,
                "thickness": 16,
                "obbDims": {"x": 400.0, "y": 950.0, "z": 9910.0},
            },
            {
                "partId": "pad",
                "partPosition": "T3-P-4462",
                "name": "板",
                "profileString": "PL6*30",
                "material": "Q355B",
                "isPlateLike": True,
                "length": 460,
                "thickness": 6,
                "obbDims": {"x": 460.0, "y": 30.0, "z": 6.0},
                "boltHoleCount": 0,
                "weldDetails": [
                    {
                        "mainPartId": "67451164",
                        "secondaryPartId": "pad",
                        "weldType": "Weld",
                        "sizeAbove": 6,
                        "sizeBelow": 0,
                        "shopWeld": True,
                        "aroundWeld": True,
                    }
                ],
            },
            {
                "partId": "conn",
                "partPosition": "T3-P-5453",
                "name": "连接板",
                "profileString": "PL10*140",
                "material": "Q355B",
                "isPlateLike": True,
                "length": 192,
                "thickness": 10,
                "obbDims": {"x": 192.0, "y": 140.0, "z": 10.0},
            },
        ],
        "relationships": [
            {
                "partIdA": "pad",
                "partIdB": "67451164",
                "edgeType": "Weld",
                "meta": "Weld|shop=True|sizeAbove=6|sizeBelow=0|around=True",
            },
            {"partIdA": "pad", "partIdB": "67451164", "edgeType": "Contact"},
        ],
    }


def _box_member() -> dict:
    return {
        "Member": {"Name": "A-GKZ-1"},
        "Classification": {"MainClass": 2, "KeyDimensionsDisplay": "BOX 500x500x20", "Confidence": 88},
    }


def _box_assembly() -> dict:
    return {
        "assemblyId": "100",
        "mainPartId": "1",
        "metadata": {
            "assemblyPosition": "A-GKZ-1",
            "boxSectionEvidence": {
                "source": "teklaSolidFaceSectionSegments.v2",
                "stationLoops": [
                    {
                        "station": 100,
                        "closedLoopCount": 1,
                        "supportPartIds": ["1"],
                        "partLoops": [
                            {
                                "partId": "1",
                                "sectionLoops": [
                                    {
                                        "points": [
                                            {"u": 0, "v": 0},
                                            {"u": 500, "v": 0},
                                            {"u": 500, "v": 500},
                                            {"u": 0, "v": 500},
                                        ],
                                        "isClosed": True,
                                        "isValid": True,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        },
        "parts": [
            {
                "partId": "1",
                "partPosition": "A-P-1",
                "name": "连接板",
                "profileString": "PL10*100",
                "material": "Q355B",
                "length": 200,
                "thickness": 10,
                "isPlateLike": True,
                "obbDims": {"x": 200.0, "y": 100.0, "z": 10.0},
                "contourVertexCount": 4,
                "concaveCornerCount": 0,
                "contourPoints": [
                    {"x": 0.0, "y": 0.0, "z": 0.0},
                    {"x": 200.0, "y": 0.0, "z": 0.0},
                    {"x": 200.0, "y": 100.0, "z": 0.0},
                    {"x": 0.0, "y": 100.0, "z": 0.0},
                ],
                "contourSegments": [
                    {"chamferType": "CHAMFER_NONE"},
                    {"chamferType": "CHAMFER_NONE"},
                    {"chamferType": "CHAMFER_NONE"},
                    {"chamferType": "CHAMFER_NONE"},
                ],
                "centroid": {"x": 100.0, "y": 50.0, "z": 5.0},
                "boundingBox": {
                    "min": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "max": {"x": 1000.0, "y": 100.0, "z": 100.0},
                },
                "mainMaterialEvidence": {
                    "axisStationStart": 0,
                    "axisStationEnd": 1000,
                    "axisStationLength": 1000,
                    "bodyFaceId": "FACE_A",
                    "isBodyWallPlateCandidate": True,
                    "sectionProjectionEvidence": {
                        "projectedCentroid": {"u": 0, "v": 242},
                        "projectedBoundsMin": {"u": -240, "v": 234},
                        "projectedBoundsMax": {"u": 240, "v": 250},
                    },
                },
            },
            {
                "partId": "2",
                "partPosition": "A-P-2",
                "name": "板",
                "profileString": "PL8*25",
                "material": "Q355B",
                "length": 200,
                "thickness": 8,
                "isPlateLike": True,
                "obbDims": {"x": 200.0, "y": 25.0, "z": 8.0},
                "boltHoleCount": 0,
                "centroid": {"x": 100.0, "y": 12.5, "z": 4.0},
                "weldDetails": [
                    {
                        "mainPartId": "1",
                        "secondaryPartId": "2",
                        "weldType": "Weld",
                        "sizeAbove": 6,
                        "sizeBelow": 0,
                        "shopWeld": True,
                        "aroundWeld": True,
                    }
                ],
            },
        ],
        "relationships": [
            {
                "partIdA": "1",
                "partIdB": "2",
                "edgeType": "Weld",
                "meta": "Weld|shop=True|sizeAbove=6|sizeBelow=0|around=True",
            },
            {"partIdA": "1", "partIdB": "2", "edgeType": "Contact"},
        ],
    }


if __name__ == "__main__":
    unittest.main()
