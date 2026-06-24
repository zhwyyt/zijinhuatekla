import json
import tempfile
import unittest
from pathlib import Path

from zijinhua_tekla.casebank import CaseBank, CaseFeedback, CaseIssueType


class CaseBankPersistenceTests(unittest.TestCase):
    def test_case_bank_round_trips_json(self):
        bank = CaseBank()
        bank.add(
            CaseFeedback(
                case_id="T3-5GKZ-10:cluster-72805757:0",
                issue_type=CaseIssueType.SCORING,
                expected_label="Bracket",
                human_note="人工确认该附属件簇为牛腿。",
                evidence_fields=["root_contact_ratio", "cantilever_ratio", "evidence_codes"],
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "casebank.json"
            bank.save_json(path)
            raw = json.loads(path.read_text(encoding="utf-8"))
            loaded = CaseBank.load_json(path)

        self.assertEqual(1, len(raw["cases"]))
        self.assertEqual("SCORING", raw["cases"][0]["issue_type"])
        self.assertEqual(bank.all(), loaded.all())
        self.assertEqual(CaseIssueType.SCORING, loaded.get("T3-5GKZ-10:cluster-72805757:0").issue_type)

    def test_case_bank_round_trips_csv(self):
        bank = CaseBank()
        bank.add(
            CaseFeedback(
                case_id="T3-5GKZ-10:T3-H-558f",
                issue_type=CaseIssueType.FEATURE,
                expected_label="DERIVED_FROM_PROFILE",
                human_note="BH 腹板拆板，需保留派生证据。",
                evidence_fields=["profile", "position_suffix", "derived_parent"],
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "casebank.csv"
            bank.save_csv(path)
            loaded = CaseBank.load_csv(path)

        feedback = loaded.get("T3-5GKZ-10:T3-H-558f")
        self.assertEqual(CaseIssueType.FEATURE, feedback.issue_type)
        self.assertEqual("DERIVED_FROM_PROFILE", feedback.expected_label)
        self.assertEqual(["profile", "position_suffix", "derived_parent"], feedback.evidence_fields)

    def test_case_bank_rejects_feedback_without_required_regression_evidence(self):
        bank = CaseBank()

        with self.assertRaisesRegex(ValueError, "evidence_fields"):
            bank.add(
                CaseFeedback(
                    case_id="T3-5GKZ-10:empty-evidence",
                    issue_type=CaseIssueType.DATA,
                    expected_label="DATA_MISSING",
                    human_note="缺少模型实体。",
                    evidence_fields=[],
                )
            )

    def test_project_seed_case_bank_loads_confirmed_feedback(self):
        seed_path = Path(__file__).resolve().parents[1] / "cases" / "seed.json"

        bank = CaseBank.load_json(seed_path)
        feedback = bank.get("T3-5GKZ-10:T3-H-558f")

        self.assertIsNotNone(feedback)
        self.assertEqual(CaseIssueType.SCORING, feedback.issue_type)
        self.assertEqual("DERIVED_FROM_PROFILE", feedback.expected_label)
        self.assertIn("derived_parent", feedback.evidence_fields)

    def test_project_seed_case_bank_records_confirmed_box_column_segment_group(self):
        seed_path = Path(__file__).resolve().parents[1] / "cases" / "seed.json"

        bank = CaseBank.load_json(seed_path)
        feedback = bank.get("T3-5GKZ-10:box-column-main-material-segments")

        self.assertIsNotNone(feedback)
        self.assertEqual(CaseIssueType.DATA, feedback.issue_type)
        self.assertEqual("BOX_COLUMN_MAIN_MATERIAL_SEGMENT_GROUP", feedback.expected_label)
        self.assertIn("confirmed_segment_positions", feedback.evidence_fields)
        for part_name in [
            "T3-P-4918",
            "T3-P-4917",
            "T3-P-4919",
            "T3-P-6272",
            "T3-P-5577",
            "T3-P-6269",
            "T3-P-6268",
            "T3-P-5571",
            "T3-P-6284",
            "T3-P-6271",
            "T3-P-5579",
            "T3-P-5576",
            "T3-P-6270",
        ]:
            self.assertIn(part_name, feedback.human_note)


if __name__ == "__main__":
    unittest.main()







