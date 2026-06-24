import json
import tempfile
import unittest
from pathlib import Path

from zijinhua_tekla.quality.gate import quality_report_from_aligned_rows
from zijinhua_tekla.quality.review import (
    QualityReviewTask,
    build_review_tasks,
    load_review_tasks_csv,
    load_review_tasks_json,
    save_review_tasks_csv,
    save_review_tasks_json,
    summarize_review_tasks,
)


class QualityReviewTests(unittest.TestCase):
    def test_build_review_tasks_from_quality_report(self):
        report = quality_report_from_aligned_rows(
            [
                {
                    "零件名称": "T3-P-3449",
                    "prediction_status": "DATA_MISSING",
                    "match_method": "missing",
                    "match_note": "candidate A; candidate B",
                },
                {
                    "零件名称": "T3-P-4916",
                    "prediction_status": "MATCH_CONFLICT",
                    "match_method": "partPositionConflict",
                    "match_note": "Tekla PL30*100 conflicts Excel PL16*1000",
                },
            ]
        )

        tasks = build_review_tasks("T3-5GKZ-10", report)

        self.assertEqual(2, len(tasks))
        self.assertEqual("T3-5GKZ-10:T3-P-3449:DATA_MISSING", tasks[0].task_id)
        self.assertEqual("DATA", tasks[0].case_issue_type)
        self.assertEqual("全模型搜索候选零件并核对 Excel/模型编号", tasks[0].recommended_action)
        self.assertEqual(["part_name", "status", "match_method", "evidence"], tasks[0].evidence_fields)
        self.assertIn("candidate A", tasks[0].evidence)
        self.assertEqual("核对同名零件的规格/长度冲突；几何候选仅作复核证据", tasks[1].recommended_action)

    def test_review_tasks_round_trip_json(self):
        tasks = [
            QualityReviewTask(
                task_id="T3-5GKZ-10:T3-P-4916:MATCH_CONFLICT",
                member_id="T3-5GKZ-10",
                part_name="T3-P-4916",
                issue_type="MATCH_CONFLICT",
                case_issue_type="DATA",
                recommended_action="核对同名零件的规格/长度冲突；几何候选仅作复核证据",
                evidence="Tekla conflicts Excel",
                evidence_fields=["part_name", "status", "match_method", "evidence"],
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review-tasks.json"
            save_review_tasks_json(tasks, path)
            raw = json.loads(path.read_text(encoding="utf-8"))
            loaded = load_review_tasks_json(path)

        self.assertEqual("T3-5GKZ-10:T3-P-4916:MATCH_CONFLICT", raw["tasks"][0]["task_id"])
        self.assertEqual(tasks, loaded)

    def test_review_tasks_round_trip_csv_for_manual_review(self):
        tasks = [
            QualityReviewTask(
                task_id="T3-5GKZ-10:T3-P-3449:DATA_MISSING",
                member_id="T3-5GKZ-10",
                part_name="T3-P-3449",
                issue_type="DATA_MISSING",
                case_issue_type="DATA",
                recommended_action="全模型搜索候选零件并核对 Excel/模型编号",
                evidence="no partPosition candidate",
                evidence_fields=["part_name", "status", "match_method", "evidence"],
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review-tasks.csv"
            save_review_tasks_csv(tasks, path)
            raw = path.read_text(encoding="utf-8-sig")
            loaded = load_review_tasks_csv(path)

        self.assertIn("task_id,member_id,part_name,issue_type", raw)
        self.assertIn("T3-5GKZ-10:T3-P-3449:DATA_MISSING", raw)
        self.assertEqual(tasks, loaded)

    def test_summarize_review_tasks_groups_by_issue_type_and_action(self):
        tasks = [
            QualityReviewTask(
                task_id="T3-5GKZ-10:T3-P-3449:DATA_MISSING",
                member_id="T3-5GKZ-10",
                part_name="T3-P-3449",
                issue_type="DATA_MISSING",
                case_issue_type="DATA",
                recommended_action="全模型搜索候选零件并核对 Excel/模型编号",
            ),
            QualityReviewTask(
                task_id="T3-5GKZ-10:T3-P-4910:DATA_MISSING",
                member_id="T3-5GKZ-10",
                part_name="T3-P-4910",
                issue_type="DATA_MISSING",
                case_issue_type="DATA",
                recommended_action="全模型搜索候选零件并核对 Excel/模型编号",
            ),
            QualityReviewTask(
                task_id="T3-5GKZ-10:T3-P-4916:MATCH_CONFLICT",
                member_id="T3-5GKZ-10",
                part_name="T3-P-4916",
                issue_type="MATCH_CONFLICT",
                case_issue_type="DATA",
                recommended_action="核对同名零件的规格/长度冲突；几何候选仅作复核证据",
            ),
        ]

        summary = summarize_review_tasks(tasks)

        self.assertEqual(2, len(summary))
        self.assertEqual("DATA_MISSING", summary[0]["issue_type"])
        self.assertEqual("全模型搜索候选零件并核对 Excel/模型编号", summary[0]["recommended_action"])
        self.assertEqual(2, summary[0]["task_count"])
        self.assertEqual("T3-P-3449;T3-P-4910", summary[0]["part_names"])
        self.assertEqual("MATCH_CONFLICT", summary[1]["issue_type"])
        self.assertEqual(1, summary[1]["task_count"])


if __name__ == "__main__":
    unittest.main()
