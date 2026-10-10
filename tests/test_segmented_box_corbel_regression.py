import copy
import json
from pathlib import Path
import unittest

from zijinhua_tekla.classifiers.box_main_material_segments import classify_main_material_segment_groups
from zijinhua_tekla.classifiers.box_part_spatial_relations import classify_box_part_spatial_relations
from zijinhua_tekla.classifiers.corbel_units import classify_corbel_units
from zijinhua_tekla.reports.member_complexity import classify_member_complexity
from zijinhua_tekla.spatial_features import (
    classify_appendage_clusters_from_bundle, main_wall_part_ids_from_groups,
    outside_box_part_ids_from_relations,
)


class SegmentedBoxCorbelRegressionTests(unittest.TestCase):
    def test_frozen_segmented_body_preserves_support_units_in_formal_summary(self):
        for expected in [4, 2]:
            with self.subTest(expected=expected):
                path = Path(__file__).parent / "fixtures" / f"segmented_box_corbel_{expected}.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                assembly, member = data["assembly"], data["member"]
                axis_before = copy.deepcopy(assembly["metadata"]["memberAxisEvidence"])
                member_before = copy.deepcopy(member)
                result = classify_member_complexity(assembly, member)
                self.assertEqual(expected, result.corbel_count)
                self.assertEqual(axis_before, assembly["metadata"]["memberAxisEvidence"])
                self.assertEqual(member_before, member)

    def test_missing_external_connection_evidence_does_not_invent_supports(self):
        path = Path(__file__).parent / "fixtures" / "segmented_box_corbel_4.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for part in data["assembly"]["parts"]:
            part.pop("boltHoles", None)

        result = classify_member_complexity(data["assembly"], data["member"])

        self.assertEqual(0, result.corbel_count)

    def test_fabricated_and_rolled_supports_remain_distinct_units(self):
        path = Path(__file__).parent / "fixtures" / "segmented_box_corbel_4.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assembly, member = data["assembly"], data["member"]
        groups = classify_main_material_segment_groups(assembly, member)
        relations = classify_box_part_spatial_relations(assembly, member, groups)
        clusters = classify_appendage_clusters_from_bundle(
            assembly, member, body_part_ids=main_wall_part_ids_from_groups(groups),
            appendage_part_ids=outside_box_part_ids_from_relations(relations),
        )
        units = classify_corbel_units(assembly, clusters, member)
        self.assertEqual(2, sum(bool(unit.spine_part_ids) for unit in units))
        self.assertEqual(2, sum("FABRICATED_BRACKET_CLUSTER" in unit.evidence_codes for unit in units))


if __name__ == "__main__":
    unittest.main()
