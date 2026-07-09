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

    def test_merges_split_fixture_base_wall_into_one_stage(self):
        assembly = _assembly_with_split_base()
        steps = build_box_assembly_drawing_steps(
            assembly=assembly,
            member_id="A-GKZ-2",
            aligned_rows=[],
            main_wall_groups=[_main_wall_group_for(["base_1", "base_2", "side_a", "side_b", "cover"])],
            box_part_spatial_relations=[],
            spatial_classifications=[],
        )

        base_step = steps[0]
        self.assertEqual("BASE_MAIN_WALL", base_step.step_type)
        self.assertEqual(["base_1", "base_2"], base_step.new_part_ids)
        self.assertEqual("FACE_BOTTOM", base_step.evidence_summary["fixture_face"])
        self.assertEqual("fixture_base", base_step.evidence_summary["fixture_role"])
        self.assertIn("胎架", base_step.title)
        self.assertEqual(1, sum(1 for step in steps if "base_1" in step.new_part_ids or "base_2" in step.new_part_ids))

    def test_merges_side_weld_parts_into_same_flip_stage(self):
        assembly = _assembly_with_external_flip_work()
        steps = build_box_assembly_drawing_steps(
            assembly=assembly,
            member_id="A-GKZ-3",
            aligned_rows=[],
            main_wall_groups=[_main_wall_group_for(["base", "side_a", "side_b", "cover"])],
            box_part_spatial_relations=[
                _relation("ext_top", "A-P-ext-top", "OUTSIDE_ATTACHMENT", "1200.0-1320.0"),
                _relation("ext_side", "A-P-ext-side", "OUTSIDE_ATTACHMENT", "1400.0-1500.0"),
            ],
            spatial_classifications=[
                AppendageRoleClassification(
                    cluster_id="100:face-a",
                    role="Bracket",
                    confidence=0.9,
                    part_ids=["ext_top"],
                    evidence_codes=["ROOT_LOCAL_ATTACHMENT"],
                ),
                AppendageRoleClassification(
                    cluster_id="100:face-b",
                    role="Connector",
                    confidence=0.88,
                    part_ids=["ext_side"],
                    evidence_codes=["SIDE_WELD_ALLOWED"],
                ),
            ],
        )

        external_steps = [step for step in steps if step.step_type == "ADD_EXTERNAL_CLUSTER"]
        self.assertEqual(1, len(external_steps))
        external = external_steps[0]
        self.assertEqual(["ext_top", "ext_side"], external.new_part_ids)
        self.assertEqual("FACE_A", external.evidence_summary["up_face"])
        self.assertEqual("FACE_B", external.evidence_summary["side_work_faces"])
        self.assertIn("翻面", external.title)
        self.assertIn("侧焊", external.title)

    def test_infers_external_work_face_from_projected_centroid(self):
        assembly = _assembly_with_projected_external_work()
        steps = build_box_assembly_drawing_steps(
            assembly=assembly,
            member_id="A-GKZ-4",
            aligned_rows=[],
            main_wall_groups=[_main_wall_group_for(["base", "side_a", "side_b", "cover"])],
            box_part_spatial_relations=[
                _relation(
                    "ext_top",
                    "A-P-ext-top",
                    "OUTSIDE_ATTACHMENT",
                    "1200.0-1320.0",
                    {"projected_centroid_u": "20.0", "projected_centroid_v": "540.0"},
                ),
                _relation(
                    "ext_side",
                    "A-P-ext-side",
                    "OUTSIDE_ATTACHMENT",
                    "1400.0-1500.0",
                    {"projected_centroid_u": "530.0", "projected_centroid_v": "40.0"},
                ),
            ],
            spatial_classifications=[
                AppendageRoleClassification(
                    cluster_id="100:radial-y-pos",
                    role="Bracket",
                    confidence=0.9,
                    part_ids=["ext_top"],
                    evidence_codes=["ROOT_LOCAL_ATTACHMENT"],
                ),
                AppendageRoleClassification(
                    cluster_id="100:radial-x-pos",
                    role="Connector",
                    confidence=0.88,
                    part_ids=["ext_side"],
                    evidence_codes=["SIDE_WELD_ALLOWED"],
                ),
            ],
        )

        external_steps = [step for step in steps if step.step_type == "ADD_EXTERNAL_CLUSTER"]
        self.assertEqual(1, len(external_steps))
        external = external_steps[0]
        self.assertEqual(["ext_top", "ext_side"], external.new_part_ids)
        self.assertEqual("RADIAL_Y_POS", external.evidence_summary["up_face"])
        self.assertEqual("RADIAL_X_POS", external.evidence_summary["side_work_faces"])


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


def _assembly_with_split_base():
    return {
        "assemblyId": "100",
        "parts": [
            _part("base_1", "A-P-base-1", "PL20*500", 0, 3000, "FACE_BOTTOM"),
            _part("base_2", "A-P-base-2", "PL20*500", 3000, 6000, "FACE_BOTTOM"),
            _part("side_a", "A-P-side-a", "PL16*500", 0, 6000, "FACE_SIDE_A"),
            _part("side_b", "A-P-side-b", "PL16*500", 0, 6000, "FACE_SIDE_B"),
            _part("cover", "A-P-cover", "PL20*500", 0, 6000, "FACE_TOP"),
        ],
        "relationships": [
            {"partIdA": "base_1", "partIdB": "base_2", "edgeType": "Weld"},
            {"partIdA": "base_1", "partIdB": "side_a", "edgeType": "Contact"},
            {"partIdA": "base_2", "partIdB": "side_b", "edgeType": "Contact"},
        ],
    }


def _assembly_with_external_flip_work():
    return {
        "assemblyId": "100",
        "parts": [
            _part("base", "A-P-base", "PL20*500", 0, 6000, "FACE_BOTTOM"),
            _part("side_a", "A-P-side-a", "PL16*500", 0, 6000, "FACE_SIDE_A"),
            _part("side_b", "A-P-side-b", "PL16*500", 0, 6000, "FACE_SIDE_B"),
            _part("cover", "A-P-cover", "PL20*500", 0, 6000, "FACE_TOP"),
            _part_with_access("ext_top", "A-P-ext-top", "PL22*300", 1200, 1320, "FACE_A", "MUST_TOP"),
            _part_with_access("ext_side", "A-P-ext-side", "PL10*180", 1400, 1500, "FACE_B", "CAN_SIDE"),
        ],
        "relationships": [
            {"partIdA": "cover", "partIdB": "ext_top", "edgeType": "Weld"},
            {"partIdA": "side_a", "partIdB": "ext_side", "edgeType": "Weld"},
        ],
    }


def _assembly_with_projected_external_work():
    assembly = _assembly_with_external_flip_work()
    parts = []
    for part in assembly["parts"]:
        if part["partId"] in {"ext_top", "ext_side"}:
            part = dict(part)
            evidence = dict(part["mainMaterialEvidence"])
            evidence.pop("bodyFaceId", None)
            part["mainMaterialEvidence"] = evidence
        parts.append(part)
    return {**assembly, "parts": parts}


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


def _part_with_access(part_id, position, profile, start, end, face, access_level):
    part = _part(part_id, position, profile, start, end, face)
    part["weldingAccessLevel"] = access_level
    return part


def _main_wall_group():
    return _main_wall_group_for(["base", "side_a", "side_b", "cover"])


def _main_wall_group_for(part_ids):
    return BoxMainMaterialSegmentGroup(
        assembly_id="100",
        group_type="BOX_MAIN_WALL_CONFIRMED_SET",
        face_id="BOX_MAIN_WALL_CONFIRMED",
        part_ids=part_ids,
        part_positions=[f"A-P-{part_id}" for part_id in part_ids],
        station_ranges="",
        gap_summary="",
        continuity_level=SegmentContinuityLevel.CONTINUOUS,
        evidence_codes=["BOX_MAIN_WALL_CONFIRMED_SET"],
        confidence=0.96,
    )


def _relation(part_id, position, relation, station_range, evidence_summary=None):
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
        evidence_summary=evidence_summary or {},
    )


if __name__ == "__main__":
    unittest.main()
