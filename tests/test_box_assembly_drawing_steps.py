import unittest

from zijinhua_tekla.bracket_classifier import AppendageRoleClassification
from zijinhua_tekla.classifiers.box_assembly_drawing_steps import build_box_assembly_drawing_steps
from zijinhua_tekla.classifiers.box_main_material_segments import BoxMainMaterialSegmentGroup, SegmentContinuityLevel
from zijinhua_tekla.classifiers.box_part_spatial_relations import BoxPartSpatialRelation


class BoxAssemblyDrawingStepTests(unittest.TestCase):
    def test_builds_stage_steps_without_single_part_page_explosion(self):
        assembly = _assembly()
        steps = build_box_assembly_drawing_steps(
            assembly=assembly,
            member_id="A-GKZ-1",
            aligned_rows=[],
            main_wall_groups=[_main_wall_group()],
            box_part_spatial_relations=[
                _relation("base", "A-P-base", "MAIN_WALL", "0.0-6000.0"),
                _relation("side_a", "A-P-side-a", "MAIN_WALL", "0.0-6000.0"),
                _relation("side_b", "A-P-side-b", "MAIN_WALL", "0.0-6000.0"),
                _relation("cover", "A-P-cover", "MAIN_WALL", "0.0-6000.0"),
                _relation("int_a", "A-P-int-a", "INSIDE_BODY", "900.0-980.0"),
                _relation("int_b", "A-P-int-b", "INSIDE_BODY", "940.0-1010.0"),
                _relation("ext_root", "A-P-ext-root", "OUTSIDE_ATTACHMENT", "1200.0-1320.0"),
                _relation("ext_rib", "A-P-ext-rib", "OUTSIDE_ATTACHMENT", "1200.0-1320.0"),
            ],
            spatial_classifications=[
                AppendageRoleClassification(
                    cluster_id="100:0",
                    role="Bracket",
                    confidence=0.91,
                    part_ids=["ext_root", "ext_rib"],
                    evidence_codes=["ROOT_LOCAL_ATTACHMENT"],
                )
            ],
        )

        self.assertEqual(
            ["BASE_MAIN_WALL", "ADD_SIDE_WALLS", "ADD_INTERNAL_GROUP", "ADD_COVER_WALL", "ADD_EXTERNAL_CLUSTER"],
            [step.step_type for step in steps],
        )
        internal = steps[2]
        self.assertEqual(["int_a", "int_b"], internal.new_part_ids)
        self.assertIn("station_position", [target.kind for target in internal.dimension_targets])
        self.assertLess(len(steps), len(assembly["parts"]))
        external = steps[-1]
        self.assertEqual(["ext_root", "ext_rib"], external.new_part_ids)
        self.assertIn("appendage_cluster_root_station", [target.kind for target in external.dimension_targets])


def _assembly():
    return {
        "assemblyId": "100",
        "parts": [
            _part("base", "A-P-base", "PL20*500", 0, 6000, "FACE_BOTTOM"),
            _part("side_a", "A-P-side-a", "PL16*500", 0, 6000, "FACE_SIDE_A"),
            _part("side_b", "A-P-side-b", "PL16*500", 0, 6000, "FACE_SIDE_B"),
            _part("cover", "A-P-cover", "PL20*500", 0, 6000, "FACE_TOP"),
            _part("int_a", "A-P-int-a", "PL12*420", 900, 980, "INNER"),
            _part("int_b", "A-P-int-b", "PL12*420", 940, 1010, "INNER"),
            _part("ext_root", "A-P-ext-root", "PL18*260", 1200, 1320, "OUTER"),
            _part("ext_rib", "A-P-ext-rib", "PL12*180", 1200, 1320, "OUTER"),
        ],
        "relationships": [
            {"partIdA": "base", "partIdB": "side_a", "edgeType": "Contact"},
            {"partIdA": "base", "partIdB": "side_b", "edgeType": "Contact"},
            {"partIdA": "side_a", "partIdB": "cover", "edgeType": "Contact"},
            {"partIdA": "int_a", "partIdB": "int_b", "edgeType": "Weld"},
            {"partIdA": "ext_root", "partIdB": "ext_rib", "edgeType": "Weld"},
            {"partIdA": "side_a", "partIdB": "ext_root", "edgeType": "Weld"},
        ],
    }


def _part(part_id, position, profile, start, end, face):
    return {
        "partId": part_id,
        "partPosition": position,
        "name": "PLATE",
        "profileString": profile,
        "mainMaterialEvidence": {
            "axisStationStart": start,
            "axisStationEnd": end,
            "axisStationLength": end - start,
            "bodyFaceId": face,
        },
    }


def _main_wall_group():
    return BoxMainMaterialSegmentGroup(
        assembly_id="100",
        group_type="BOX_MAIN_WALL_CONFIRMED_SET",
        face_id="BOX_MAIN_WALL_CONFIRMED",
        part_ids=["base", "side_a", "side_b", "cover"],
        part_positions=["A-P-base", "A-P-side-a", "A-P-side-b", "A-P-cover"],
        station_ranges="",
        gap_summary="",
        continuity_level=SegmentContinuityLevel.CONTINUOUS,
        evidence_codes=["BOX_MAIN_WALL_CONFIRMED_SET"],
        confidence=0.96,
    )


def _relation(part_id, position, relation, station_range):
    return BoxPartSpatialRelation(
        assembly_id="100",
        part_id=part_id,
        part_position=position,
        relation_to_box_body=relation,
        station_range=station_range,
        section_relation="",
        connected_main_wall_ids=["base"] if relation != "MAIN_WALL" else [],
        evidence_codes=[relation],
        confidence=0.9,
    )


if __name__ == "__main__":
    unittest.main()
