import unittest

from zijinhua_tekla.casebank import CaseFeedback, CaseIssueType, CaseBank
from zijinhua_tekla.features import feature_snapshots_from_bundle_parts
from zijinhua_tekla.member_classifier import classify_member_body
from zijinhua_tekla.part_roles import classify_part_role
from zijinhua_tekla.bracket_classifier import (
    AppendageClusterFeatures,
    classify_appendage_cluster,
)


class AlgorithmInterfaceTests(unittest.TestCase):
    def test_member_body_classifier_normalizes_existing_classification(self):
        member = {
            "Member": {"Name": "T3-5GKZ-10"},
            "Classification": {
                "MainClass": "BOX",
                "KeyDimensionsDisplay": "BOX 960x970x16/30x16/30",
                "Confidence": 99,
            },
        }

        result = classify_member_body(member, [])

        self.assertEqual("BOX", result.body_type)
        self.assertGreaterEqual(result.confidence, 0.99)
        self.assertIn("member.Classification.MainClass", result.evidence_codes)
        self.assertIn("BOX 960x970", result.description)

    def test_member_body_classifier_infers_bh_profile_from_snapshots(self):
        member = {"Member": {"Name": "A1-GKL-01"}, "Classification": {}}
        snapshots = feature_snapshots_from_bundle_parts(
            [
                {
                    "partId": 1001,
                    "runtimeType": "Beam",
                    "name": "钢梁",
                    "profileString": "BH400*200*7*10",
                    "partPosition": "A1-H-558",
                    "obbDims": {"x": 400.0, "y": 389.4, "z": 200.0},
                }
            ]
        )

        result = classify_member_body(member, snapshots)

        self.assertEqual("H", result.body_type)
        self.assertGreaterEqual(result.confidence, 0.75)
        self.assertIn("snapshot.profile.BH", result.evidence_codes)

    def test_part_role_classifier_returns_evidence_not_special_case(self):
        row = {"零件名称": "T3-P-4869", "规格": "PL14*243", "长度": 281, "备注": "激光"}
        summary = {
            "tekla_names": "连接板:1",
            "bolt_holes": 1,
            "boolean_cuts": 0,
            "contour_vertices": 4,
            "has_arc_contour": True,
            "is_special_shape": False,
        }

        result = classify_part_role(row, summary)

        self.assertEqual("连接板", result.role)
        self.assertEqual("下料割孔", result.process)
        self.assertEqual("异形", result.shape)
        self.assertGreater(result.confidence, 0.5)
        self.assertIn("Tekla名称=连接板", result.evidence)

    def test_part_role_classifier_uses_generic_pr_mark_not_project_prefix(self):
        row = {"零件名称": "A1-PR-42", "规格": "PL12*160", "长度": 280, "备注": ""}
        summary = {
            "tekla_names": "",
            "bolt_holes": 2,
            "boolean_cuts": 0,
            "contour_vertices": 4,
            "concave_corners": 0,
            "has_arc_contour": False,
            "is_special_shape": False,
        }

        result = classify_part_role(row, summary)

        self.assertEqual("对接耳板/连接小板", result.role)
        self.assertEqual("下料割孔", result.process)
        self.assertEqual("异形", result.shape)
        self.assertIn("编号系列=PR", result.evidence)

    def test_case_bank_records_feedback_with_issue_type(self):
        bank = CaseBank()
        feedback = CaseFeedback(
            case_id="T3-5GKZ-10:T3-H-558f",
            issue_type=CaseIssueType.SCORING,
            expected_label="DERIVED_FROM_PROFILE",
            human_note="BH400*200*7*10 腹板拆板",
            evidence_fields=["profile", "position_suffix", "derived_parent"],
        )

        bank.add(feedback)

        self.assertEqual([feedback], bank.by_issue_type(CaseIssueType.SCORING))
        self.assertEqual(feedback, bank.get("T3-5GKZ-10:T3-H-558f"))

    def test_bracket_classifier_uses_root_and_overhang_evidence(self):
        features = AppendageClusterFeatures(
            cluster_id="cluster-1",
            root_contact_ratio=0.25,
            cantilever_ratio=2.4,
            span_along_axis=180,
            assembly_span=1200,
            centroid_outside_body=True,
            has_end_connection_signal=False,
        )

        result = classify_appendage_cluster(features)

        self.assertEqual("Bracket", result.role)
        self.assertGreaterEqual(result.confidence, 0.9)
        self.assertIn("ROOT_LOCAL_ATTACHMENT", result.evidence_codes)
        self.assertIn("OVERHANG_DOMINANT", result.evidence_codes)
        self.assertIn("AXIS_SPAN_LIMITED", result.evidence_codes)
        self.assertIn("EXTERNAL_CENTROID", result.evidence_codes)
        self.assertIn("NOT_END_CONNECTION", result.evidence_codes)

    def test_bracket_classifier_keeps_weak_evidence_unknown(self):
        features = AppendageClusterFeatures(
            cluster_id="cluster-2",
            root_contact_ratio=0.95,
            cantilever_ratio=0.2,
            span_along_axis=900,
            assembly_span=1000,
            centroid_outside_body=False,
            has_end_connection_signal=True,
            bolt_count=0,
        )

        result = classify_appendage_cluster(features)

        self.assertEqual("Unknown", result.role)
        self.assertLess(result.confidence, 0.5)

    def test_bracket_classifier_rejects_end_connection_even_with_other_evidence(self):
        features = AppendageClusterFeatures(
            cluster_id="cluster-3",
            root_contact_ratio=0.0,
            cantilever_ratio=2.4,
            span_along_axis=180,
            assembly_span=1200,
            centroid_outside_body=True,
            has_end_connection_signal=True,
        )

        result = classify_appendage_cluster(features)

        self.assertEqual("Unknown", result.role)
        self.assertIn("NOT_END_CONNECTION", result.missing_codes)


if __name__ == "__main__":
    unittest.main()
