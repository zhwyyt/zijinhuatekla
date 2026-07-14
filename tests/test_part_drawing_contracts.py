import json
import unittest
from pathlib import Path

from zijinhua_tekla.part_drawing.snapshot_input import (
    load_part_snapshot,
    parse_part_snapshot,
    safe_part_position,
)


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingContractTests(unittest.TestCase):
    def test_loads_versioned_flat_plate_snapshot(self):
        snapshot = load_part_snapshot(FIXTURE)
        self.assertEqual("partDrawingSnapshot.v1", snapshot.schema_version)
        self.assertEqual("P-1001", snapshot.part_position)
        self.assertEqual(10.0, snapshot.thickness)
        self.assertEqual(4, len(snapshot.outer_loop))

    def test_rejects_missing_part_position(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["part"]["partPosition"] = ""
        with self.assertRaisesRegex(ValueError, "partPosition"):
            parse_part_snapshot(data)

    def test_rejects_unknown_schema(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["schemaVersion"] = "partDrawingSnapshot.v2"
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            parse_part_snapshot(data)

    def test_sanitizes_file_name_without_changing_business_position(self):
        self.assertEqual("P_1001_2", safe_part_position("P/1001:2"))


if __name__ == "__main__":
    unittest.main()
