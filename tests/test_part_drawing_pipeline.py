import json
import shutil
import tempfile
import unittest
from pathlib import Path

from zijinhua_tekla.cli import main
from zijinhua_tekla.part_drawing.pipeline import run_part_drawing_batch


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingPipelineTests(unittest.TestCase):
    def test_batch_writes_one_part_folder_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_root = root / "snapshots"
            snapshot_root.mkdir()
            shutil.copy2(FIXTURE, snapshot_root / FIXTURE.name)
            result = run_part_drawing_batch(snapshot_root, root / "out")
            self.assertEqual(1, result.ok_count)
            self.assertEqual(0, result.rejected_count)
            self.assertTrue((root / "out" / "parts" / "P-1001" / "P-1001.dxf").exists())
            summary = json.loads((root / "out" / "part-drawing-batch-summary.json").read_text(encoding="utf-8"))
            self.assertEqual({"OK": 1, "REVIEW_REQUIRED": 0, "REJECTED": 0}, summary["status_counts"])
            drawing_payload = json.loads(
                next((root / "out").rglob("*.drawing.json")).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                "partCadDimensionStyle.v1",
                drawing_payload["dimension_style"]["style_id"],
            )
            self.assertGreaterEqual(
                drawing_payload["entity_counts"]["dimensions"],
                2,
            )

    def test_cli_returns_nonzero_and_writes_only_conflict_evidence_for_rejected_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_root = root / "snapshots"
            snapshot_root.mkdir()
            data = json.loads(FIXTURE.read_text(encoding="utf-8"))
            (snapshot_root / "first.json").write_text(json.dumps(data), encoding="utf-8")
            data["part"]["thickness"] = 12.0
            data["part"]["partId"] = "1002"
            (snapshot_root / "conflict.json").write_text(json.dumps(data), encoding="utf-8")
            output = root / "out"
            self.assertEqual(1, main(["draw-parts", "--snapshot-root", str(snapshot_root), "--out", str(output)]))
            self.assertTrue((output / "conflicts" / "P-1001.conflict.json").exists())
            self.assertFalse((output / "parts" / "P-1001").exists())

    def test_invalid_snapshot_does_not_block_valid_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_root = root / "snapshots"
            snapshot_root.mkdir()
            shutil.copy2(FIXTURE, snapshot_root / "valid.json")
            (snapshot_root / "invalid.json").write_text("{not-json", encoding="utf-8")
            result = run_part_drawing_batch(snapshot_root, root / "out")
            self.assertEqual(1, result.ok_count)
            self.assertEqual(1, result.rejected_count)
            self.assertTrue((root / "out" / "parts" / "P-1001" / "P-1001.pdf").exists())


if __name__ == "__main__":
    unittest.main()
