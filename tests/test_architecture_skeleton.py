import unittest
from collections import Counter

from zijinhua_tekla.architecture import ARCHITECTURE_LAYERS, layer_names
from zijinhua_tekla.quality.gate import (
    DataQualityIssueType,
    quality_report_from_aligned_rows,
)
from zijinhua_tekla.pipeline.offline import OfflinePipelineResult


class ArchitectureSkeletonTests(unittest.TestCase):
    def test_architecture_layers_are_explicit_and_ordered(self):
        self.assertEqual(
            [
                "adapters",
                "quality",
                "features",
                "spatial",
                "classifiers",
                "cases",
                "pipeline",
                "reports",
            ],
            layer_names(),
        )
        self.assertTrue(all(layer.responsibility for layer in ARCHITECTURE_LAYERS))
        self.assertTrue(all(layer.allowed_inputs for layer in ARCHITECTURE_LAYERS))

    def test_quality_gate_report_counts_statuses_and_issues(self):
        aligned = [
            {"零件名称": "A-P-1", "prediction_status": "MATCH", "match_method": "partPosition"},
            {"零件名称": "A-P-2", "prediction_status": "DATA_MISSING", "match_method": "missing"},
            {
                "零件名称": "A-P-3",
                "prediction_status": "MATCH_CONFLICT",
                "match_method": "partPositionConflict",
            },
        ]

        report = quality_report_from_aligned_rows(aligned)

        self.assertEqual(Counter({"MATCH": 1, "DATA_MISSING": 1, "MATCH_CONFLICT": 1}), report.status_counts)
        self.assertEqual(2, len(report.issues))
        self.assertEqual(DataQualityIssueType.DATA_MISSING, report.issues[0].issue_type)
        self.assertEqual(DataQualityIssueType.MATCH_CONFLICT, report.issues[1].issue_type)
        self.assertFalse(report.is_clean)

    def test_offline_pipeline_result_exposes_member_assembly_alignment_and_quality(self):
        report = quality_report_from_aligned_rows(
            [{"零件名称": "A-P-1", "prediction_status": "MATCH", "match_method": "partPosition"}]
        )

        result = OfflinePipelineResult(
            member={"Member": {"Name": "A-GKZ-1"}},
            bundle={"assemblies": []},
            assembly={"assemblyId": "100"},
            aligned_rows=[{"零件名称": "A-P-1"}],
            quality_report=report,
        )

        self.assertEqual("A-GKZ-1", result.member["Member"]["Name"])
        self.assertEqual([], result.bundle["assemblies"])
        self.assertEqual("100", result.assembly["assemblyId"])
        self.assertEqual(1, len(result.aligned_rows))
        self.assertTrue(result.quality_report.is_clean)


if __name__ == "__main__":
    unittest.main()
