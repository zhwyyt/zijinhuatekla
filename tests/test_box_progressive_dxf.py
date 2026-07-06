import unittest

from zijinhua_tekla.reports.box_progressive_dxf import build_box_assembly_drawing_steps_dxf


class BoxProgressiveDxfTests(unittest.TestCase):
    def test_renders_steps_with_station_dimensions_and_part_marks(self):
        payload = {
            "assembly_id": "100",
            "member_id": "A-GKZ-1",
            "steps": [
                {
                    "step_no": 1,
                    "step_type": "BASE_MAIN_WALL",
                    "title": "基准主板",
                    "station_range": "0.0-3000.0",
                    "new_part_ids": ["401"],
                    "visible_part_ids": ["401"],
                    "part_mark_targets": [
                        {
                            "part_id": "401",
                            "part_position": "A-P-401",
                            "profile": "PL16*900",
                            "name": "COLUMN",
                        }
                    ],
                    "dimension_targets": [
                        {
                            "kind": "station_range",
                            "label": "基准主板 station 范围",
                        }
                    ],
                }
            ],
        }

        dxf = build_box_assembly_drawing_steps_dxf(payload)

        self.assertIn("SECTION", dxf)
        self.assertIn("A-GKZ-1 BOX progressive drawing steps", dxf)
        self.assertIn("Step 1 BASE_MAIN_WALL", dxf)
        self.assertIn("station 0.0-3000.0", dxf)
        self.assertIn("A-P-401", dxf)
        self.assertIn("PL16*900", dxf)
        self.assertIn("station_range", dxf)


if __name__ == "__main__":
    unittest.main()
