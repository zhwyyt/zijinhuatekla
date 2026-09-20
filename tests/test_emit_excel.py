import inspect
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from zijinhua_tekla.contracts.normalized import NormalizedPart, PartSpatialHints
from zijinhua_tekla.part_roles import classify_part_role
from zijinhua_tekla.pipeline.offline import run_model_recognition
from zijinhua_tekla.reports.recognition import RECOGNITION_COLUMNS, write_recognition_workbook


class EmitExcelTests(unittest.TestCase):
    def test_part_role_classifier_does_not_read_factory_workbook(self):
        import zijinhua_tekla.part_roles as part_roles

        source = inspect.getsource(part_roles)
        self.assertNotIn("load_truth_rows", source)
        self.assertNotIn("excel_truth", source)
        self.assertNotIn("truth_root", source)

    def test_main_wall_hint_overrides_connection_plate_name(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="1",
                part_position="A-P-1",
                name="连接板",
                profile="PL10*100",
                length=200,
                width=100,
                thickness=10,
                is_plate_like=True,
                contour_vertex_count=4,
                contour_points=((0, 0, 0), (200, 0, 0), (200, 100, 0), (0, 100, 0)),
            ),
            PartSpatialHints(relation_to_box_body="MAIN_WALL"),
        )
        self.assertEqual("箱型柱主材壁板", result.role)
        self.assertEqual("下料", result.process)
        self.assertEqual("方块", result.shape)

    def test_box_main_wall_label_wins_over_composite_h_role(self):
        from zijinhua_tekla.part_roles import main_material_label

        label = main_material_label(
            PartSpatialHints(
                member_body_type="BOX",
                relation_to_box_body="MAIN_WALL",
                main_material_role="H_WEB_MAIN_PLATE",
            ),
            "箱型柱主材壁板",
        )
        self.assertEqual("BOX主壁板", label)
        h_label = main_material_label(
            PartSpatialHints(
                member_body_type="H",
                relation_to_box_body="MAIN_WALL",
                main_material_role="H_TOP_FLANGE_MAIN_PLATE",
            )
        )
        self.assertEqual("H上翼缘", h_label)

    def test_h_main_plate_is_not_classified_as_corbel_from_mark_series(self):
        result = classify_part_role(
            NormalizedPart(
                part_id="1",
                part_position="A-H-100",
                name="上翼缘",
                profile="PL14*200",
                length=1000,
                width=200,
                thickness=14,
            ),
            PartSpatialHints(main_material_role="H_TOP_FLANGE_MAIN_PLATE"),
        )
        self.assertEqual("板件", result.role)

    def test_emit_excel_from_model_without_truth_workbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_root = root / "cache"
            out_dir = root / "out"
            _write_box_cache(cache_root)

            result = run_model_recognition(cache_root, "A-GKZ-1")
            paths = write_recognition_workbook(result, out_dir, "A-GKZ-1")

            self.assertEqual([], result.aligned_rows)
            self.assertTrue(result.recognition_rows)
            sheet = pd.read_excel(paths.xlsx_path)
            sidecar = json.loads(paths.json_path.read_text(encoding="utf-8"))

        self.assertEqual(list(sheet.columns), RECOGNITION_COLUMNS)
        self.assertIn("A-P-1", set(sheet["零件名称"]))
        wall = next(row for row in result.recognition_rows if row["零件名称"] == "A-P-1")
        self.assertEqual("箱型柱主材壁板", wall["predicted_role"])
        self.assertEqual("BOX主壁板", wall["主材"])
        self.assertEqual(0, wall["牛腿实体个数"])
        self.assertEqual("下料", wall["工序"])
        self.assertEqual("方块", wall["形状分类"])
        self.assertEqual("model-recognition.v1", sidecar["source"])
        self.assertEqual(0, sidecar["corbel"]["unit_count"])
        self.assertEqual("A-GKZ-1", sidecar["member_id"])
        self.assertEqual("BOX主壁板", sheet.loc[sheet["零件名称"] == "A-P-1", "主材"].iloc[0])
        self.assertEqual(0, int(sheet["牛腿实体个数"].iloc[0]))


def _write_box_cache(cache_root: Path) -> None:
    (cache_root / "members").mkdir(parents=True)
    (cache_root / "members" / "member_A-GKZ-1.json").write_text(
        json.dumps(
            {
                "Member": {"Name": "A-GKZ-1", "AssemblyId": "100"},
                "Classification": {"KeyDimensionsDisplay": "BOX 500x500x20", "Confidence": 88, "PartRoles": []},
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
                            }
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
                            }
                        ],
                        "relationships": [],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
