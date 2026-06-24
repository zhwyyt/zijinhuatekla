import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from zijinhua_tekla.adapters.offline import (
    load_bundle,
    load_member,
    load_member_assembly_id,
    load_roles,
    load_truth_rows,
)


class OfflineAdapterTests(unittest.TestCase):
    def test_load_truth_rows_normalizes_excel_rows_for_member(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                ["A-GKZ-1", "A-P-1", "PL14×243", 281.2, 2, 1.2, 2.4, "Q355B", "激光", "下料割孔", "异形", "车间", "L1", "组立用", 0.5, 1.0, "", "", "", "", "", 2],
                ["B-GKZ-1", "B-P-1", "PL10*100", 100, 1, 0.1, 0.1, "Q235B", "", "下料", "方块", "", "", "", 0.1, 0.1, "", "", "", "", "", 1],
            ]
            pd.DataFrame(rows).to_excel(root / "T3楼五节柱零构件清单(1).xls", sheet_name="Θ零件清单Θ", header=False, index=False)

            result = load_truth_rows(root, "A-GKZ-1")

        self.assertEqual(1, len(result))
        self.assertEqual("A-P-1", result[0]["零件名称"])
        self.assertEqual("PL14*243", result[0]["规格"])
        self.assertEqual(281, result[0]["长度"])
        self.assertEqual(2, result[0]["单数"])

    def test_load_member_and_roles_from_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "members").mkdir()
            (root / "members" / "member_A-GKZ-1.json").write_text(
                json.dumps(
                    {
                        "Member": {"AssemblyId": "100", "Name": "A-GKZ-1"},
                        "Classification": {"PartRoles": [{"PartId": "1", "Role": "wall_candidate"}]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            member = load_member(root, "A-GKZ-1")
            assembly_id = load_member_assembly_id(root, "A-GKZ-1")
            roles = load_roles(member)

        self.assertEqual("A-GKZ-1", member["Member"]["Name"])
        self.assertEqual("100", assembly_id)
        self.assertEqual({"1": {"PartId": "1", "Role": "wall_candidate"}}, roles)

    def test_load_bundle_indexes_relationship_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = {
                "assemblies": [
                    {
                        "assemblyId": "100",
                        "parts": [
                            {"partId": 1, "partPosition": "A-P-1"},
                            {"partId": 2, "partPosition": "A-P-2"},
                        ],
                        "relationships": [
                            {"partIdA": 1, "partIdB": 2, "edgeType": "Weld"},
                            {"partIdA": 1, "partIdB": 2, "edgeType": "Contact"},
                        ],
                    }
                ]
            }
            (root / "tekla-body-bracket-export.bundle.json").write_text(json.dumps(bundle), encoding="utf-8")

            assembly, by_pos, rel_by_part, loaded_bundle = load_bundle(root, "100")

        self.assertEqual("100", assembly["assemblyId"])
        self.assertEqual(bundle, loaded_bundle)
        self.assertEqual([{"partId": 1, "partPosition": "A-P-1"}], by_pos["A-P-1"])
        self.assertEqual(1, rel_by_part["1"]["Weld"])
        self.assertEqual(1, rel_by_part["2"]["Contact"])


if __name__ == "__main__":
    unittest.main()
