import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from zijinhua_tekla.pipeline.offline import run_offline_analysis


class OfflinePipelineTests(unittest.TestCase):
    def test_run_offline_analysis_coordinates_adapters_features_classifiers_and_quality(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_root = root / "cache"
            truth_root = root / "truth"
            (cache_root / "members").mkdir(parents=True)
            truth_root.mkdir()
            (cache_root / "members" / "member_A-GKZ-1.json").write_text(
                json.dumps(
                    {
                        "Member": {"Name": "A-GKZ-1", "AssemblyId": "100"},
                        "Classification": {
                            "KeyDimensionsDisplay": "BOX 500x500x20",
                            "Confidence": 88,
                            "PartRoles": [{"PartId": "1", "Role": "wall_candidate"}],
                        },
                        "Samples": [
                            {
                                "SampleId": "S01",
                                "IsAbnormal": False,
                                "Station": 100,
                                "SectionFeatures": {"ClosedLoops": 1, "CavityCount": 1, "OuterWidth": 500, "OuterHeight": 500},
                                "SectionParts": [
                                    {"PartId": "1", "RoleHint": "flange_candidate", "Center2D": {"X": 0, "Y": 242}, "CutSpanX": 480, "CutSpanY": 16, "TotalCutLength": 480},
                                    {"PartId": "10", "RoleHint": "stiffener_candidate", "Center2D": {"X": 20, "Y": 100}, "CutSpanX": 100, "CutSpanY": 16, "TotalCutLength": 100}
                                ],
                            }
                        ],
                        "Parts": [
                            {"PartId": "1", "AxisProjection": {"Start": 0, "End": 1000}},
                            {"PartId": "10", "AxisProjection": {"Start": 80, "End": 160}},
                            {"PartId": "11", "AxisProjection": {"Start": 80, "End": 160}, "GeometryHints": {"OuterSideCandidate": True}}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (cache_root / "tekla-body-bracket-export.bundle.json").write_text(
                json.dumps(
                    {
                        "assemblies": [
                            {
                                "assemblyId": "100",
                                "mainPartId": "1",
                                "metadata": {
                                    "boxSectionEvidence": {
                                        "source": "teklaSolidFaceSectionSegments.v2",
                                        "stationLoops": [
                                            {
                                                "station": 100,
                                                "supportPartIds": ["1", "10"],
                                                "partLoops": [
                                                    {
                                                        "partId": "1",
                                                        "sectionLoops": [
                                                            {
                                                                "points": [
                                                                    {"u": 0, "v": 0},
                                                                    {"u": 500, "v": 0},
                                                                    {"u": 500, "v": 500},
                                                                    {"u": 0, "v": 500}
                                                                ],
                                                                "isClosed": True,
                                                                "isValid": True,
                                                            }
                                                        ],
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                },
                                "parts": [
                                    {
                                        "partId": "1",
                                        "partPosition": "A-P-1",
                                        "name": "连接板",
                                        "profileString": "PL10*100",
                                        "mainMaterialEvidence": {
                                            "axisStationStart": 0,
                                            "axisStationEnd": 1000,
                                            "axisStationLength": 1000,
                                            "bodyFaceId": "FACE_A",
                                            "isBodyWallPlateCandidate": True,
                                        },
                                        "length": 200,
                                        "thickness": 10,
                                        "centroid": {"x": 100.0, "y": 50.0, "z": 5.0},
                                        "boundingBox": {
                                            "min": {"x": 0.0, "y": 0.0, "z": 0.0},
                                            "max": {"x": 1000.0, "y": 100.0, "z": 100.0},
                                        },
                                        "volume": 10000000.0,
                                        "obbDims": {"x": 200.0, "y": 100.0, "z": 10.0},
                                    },
                                    {
                                        "partId": "10",
                                        "partPosition": "A-BR-ROOT",
                                        "name": "牛腿根部板",
                                        "profileString": "PL20*100",
                                        "length": 120,
                                        "thickness": 20,
                                        "centroid": {"x": 415.0, "y": 115.0, "z": 50.0},
                                        "boundingBox": {
                                            "min": {"x": 400.0, "y": 100.0, "z": 30.0},
                                            "max": {"x": 430.0, "y": 130.0, "z": 70.0},
                                        },
                                        "volume": 36000.0,
                                        "obbDims": {"x": 120.0, "y": 100.0, "z": 20.0},
                                    },
                                    {
                                        "partId": "11",
                                        "partPosition": "A-BR-RIB",
                                        "name": "牛腿肋板",
                                        "profileString": "PL16*230",
                                        "length": 230,
                                        "thickness": 16,
                                        "centroid": {"x": 475.0, "y": 245.0, "z": 40.0},
                                        "boundingBox": {
                                            "min": {"x": 430.0, "y": 130.0, "z": 30.0},
                                            "max": {"x": 520.0, "y": 360.0, "z": 50.0},
                                        },
                                        "volume": 414000.0,
                                        "obbDims": {"x": 230.0, "y": 90.0, "z": 16.0},
                                    }
                                ],
                                "relationships": [
                                    {"partIdA": "1", "partIdB": "10", "edgeType": "Contact"},
                                    {"partIdA": "10", "partIdB": "11", "edgeType": "Weld"},
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    [
                        "A-GKZ-1",
                        "A-P-1",
                        "PL10*100",
                        200,
                        1,
                        1.0,
                        1.0,
                        "Q355B",
                        "",
                        "下料",
                        "异形",
                        "",
                        "",
                        "",
                        1.0,
                        1.0,
                        "",
                        "",
                        "",
                        "",
                        "",
                        1,
                    ]
                ]
            ).to_excel(truth_root / "T3楼五节柱零构件清单(1).xls", sheet_name="Θ零件清单Θ", header=False, index=False)

            result = run_offline_analysis(cache_root, truth_root, "A-GKZ-1")

        self.assertEqual("A-GKZ-1", result.member["Member"]["Name"])
        self.assertEqual(1, len(result.bundle["assemblies"]))
        self.assertEqual("100", result.assembly["assemblyId"])
        self.assertEqual(1, len(result.aligned_rows))
        self.assertEqual("A-P-1", result.aligned_rows[0]["零件名称"])
        self.assertEqual("MATCH", result.aligned_rows[0]["prediction_status"])
        self.assertEqual("连接板", result.aligned_rows[0]["predicted_role"])
        self.assertTrue(result.quality_report.is_clean)
        self.assertEqual(1, len(result.spatial_classifications))
        self.assertEqual("Bracket", result.spatial_classifications[0].role)
        relation_by_position = {row.part_position: row for row in result.box_part_spatial_relations}
        self.assertEqual("MAIN_WALL", relation_by_position["A-P-1"].relation_to_box_body)
        self.assertEqual("INSIDE_BODY", relation_by_position["A-BR-ROOT"].relation_to_box_body)
        self.assertEqual("OUTSIDE_ATTACHMENT", relation_by_position["A-BR-RIB"].relation_to_box_body)
        self.assertEqual(1, len(result.box_station_topology_diagnostics))
        self.assertEqual("CLOSED_WITHOUT_CAVITY", result.box_station_topology_diagnostics[0].topology_status)

    def test_run_offline_analysis_outputs_h_beam_part_sides_for_gl_member(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_root = root / "cache"
            truth_root = root / "truth"
            (cache_root / "members").mkdir(parents=True)
            truth_root.mkdir()
            (cache_root / "members" / "member_A-GL-1.json").write_text(
                json.dumps(
                    {
                        "Member": {"Name": "A-GL-1", "AssemblyId": "200"},
                        "Classification": {
                            "KeyDimensionsDisplay": "BH500*200*10*14",
                            "Confidence": 90,
                            "PartRoles": [],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (cache_root / "tekla-body-bracket-export.bundle.json").write_text(
                json.dumps(
                    {
                        "assemblies": [
                            {
                                "assemblyId": "200",
                                "mainPartId": "top",
                                "metadata": {"assemblyPosition": "A-GL-1"},
                                "parts": [
                                    _projected_part("top", "A-P-top", "上翼缘", -100, 100, 0, 14),
                                    _projected_part("web", "A-P-web", "腹板", -6, 6, -500, 0),
                                    _projected_part("bottom", "A-P-bottom", "下翼缘", -100, 100, -514, -500),
                                    _projected_part("lift", "A-P-lift", "吊耳", -20, 20, 20, 90),
                                    _projected_part("left", "A-P-left", "加劲板", -90, -20, -430, -120),
                                ],
                                "relationships": [],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    [
                        "A-GL-1",
                        "A-P-top",
                        "PL14*200",
                        1000,
                        1,
                        1.0,
                        1.0,
                        "Q355B",
                        "",
                        "下料",
                        "方块",
                        "",
                        "",
                        "",
                        1.0,
                        1.0,
                        "",
                        "",
                        "",
                        "",
                        "",
                        1,
                    ]
                ]
            ).to_excel(truth_root / "T3楼五节柱零构件清单(1).xls", sheet_name="Θ零件清单Θ", header=False, index=False)

            result = run_offline_analysis(cache_root, truth_root, "A-GL-1")

        by_position = {row.part_position: row for row in result.h_beam_part_sides}
        self.assertEqual("TOP_FLANGE_OUTER", by_position["A-P-lift"].h_side)
        self.assertEqual("WEB_LEFT", by_position["A-P-left"].h_side)


if __name__ == "__main__":
    unittest.main()


def _projected_part(part_id, position, name, min_u, max_u, min_v, max_v):
    return {
        "partId": part_id,
        "partPosition": position,
        "name": name,
        "profileString": "PL10",
        "length": 100,
        "thickness": 10,
        "centroid": {"x": 0.0, "y": 0.0, "z": 0.0},
        "boundingBox": {
            "min": {"x": 0.0, "y": 0.0, "z": 0.0},
            "max": {"x": 100.0, "y": 100.0, "z": 10.0},
        },
        "obbDims": {"x": 100.0, "y": 100.0, "z": 10.0},
        "mainMaterialEvidence": {
            "axisStationStart": 0,
            "axisStationEnd": 1000,
            "axisStationLength": 1000,
            "bodyFaceId": "H_FACE",
            "isBodyWallPlateCandidate": True,
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
            },
        },
    }
