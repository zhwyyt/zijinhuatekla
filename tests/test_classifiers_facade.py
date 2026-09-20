import unittest

from zijinhua_tekla.bracket_classifier import AppendageClusterFeatures
from zijinhua_tekla.classifiers import (
    ClassificationFacade,
    classify_appendage,
    classify_member,
    classify_part,
)
from zijinhua_tekla.contracts.normalized import NormalizedPart


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
            NormalizedPart(
                part_id="1",
                part_position="A-P-1",
                name="连接板",
                profile="PL12*160",
                length=280,
                width=160,
                thickness=12,
                bolt_hole_count=2,
                contour_vertex_count=4,
            )
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
                external_connection_count=1,
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
            NormalizedPart(
                part_id="2",
                part_position="A-PR-1",
                profile="PL10*100",
                length=200,
                width=100,
                thickness=10,
                bolt_hole_count=2,
                contour_vertex_count=4,
            )
        )
        appendage_result = classify_appendage(AppendageClusterFeatures(cluster_id="weak"))

        self.assertEqual("H", member_result.body_type)
        self.assertEqual("对接耳板/连接小板", part_result.role)
        self.assertEqual("Unknown", appendage_result.role)


if __name__ == "__main__":
    unittest.main()
