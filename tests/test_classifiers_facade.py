import unittest

from zijinhua_tekla.bracket_classifier import AppendageClusterFeatures
from zijinhua_tekla.classifiers import (
    ClassificationFacade,
    classify_appendage,
    classify_member,
    classify_part,
)


class ClassifiersFacadeTests(unittest.TestCase):
    def test_facade_exposes_member_part_and_appendage_classifiers(self):
        facade = ClassificationFacade()

        member_result = facade.classify_member(
            {
                "Member": {"Name": "A-GKZ-1"},
                "Classification": {"KeyDimensionsDisplay": "BOX 500x500x20", "Confidence": 88},
            },
            [],
        )
        part_result = facade.classify_part(
            {"零件名称": "A-P-1", "规格": "PL12*160", "长度": 280, "备注": ""},
            {
                "tekla_names": "连接板:1",
                "bolt_holes": 2,
                "boolean_cuts": 0,
                "contour_vertices": 4,
                "concave_corners": 0,
                "has_arc_contour": False,
                "is_special_shape": False,
            },
        )
        appendage_result = facade.classify_appendage(
            AppendageClusterFeatures(
                cluster_id="cluster-1",
                root_contact_ratio=0.2,
                cantilever_ratio=2.0,
                span_along_axis=100,
                assembly_span=1000,
                centroid_outside_body=True,
                has_end_connection_signal=False,
            )
        )

        self.assertEqual("BOX", member_result.body_type)
        self.assertEqual("连接板", part_result.role)
        self.assertEqual("Bracket", appendage_result.role)

    def test_module_functions_use_default_facade(self):
        member_result = classify_member(
            {"Member": {"Name": "A-GKL-1"}, "Classification": {}},
            [{"profile": "BH400*200*7*10"}],
        )
        part_result = classify_part(
            {"零件名称": "A-PR-1", "规格": "PL10*100", "长度": 200, "备注": ""},
            {
                "tekla_names": "",
                "bolt_holes": 2,
                "boolean_cuts": 0,
                "contour_vertices": 4,
                "concave_corners": 0,
                "has_arc_contour": False,
                "is_special_shape": False,
            },
        )
        appendage_result = classify_appendage(AppendageClusterFeatures(cluster_id="weak"))

        self.assertEqual("H", member_result.body_type)
        self.assertEqual("对接耳板/连接小板", part_result.role)
        self.assertEqual("Unknown", appendage_result.role)


if __name__ == "__main__":
    unittest.main()
