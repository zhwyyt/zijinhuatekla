import copy
import unittest

from zijinhua_tekla.classifiers.box_main_material_segments import (
    classify_box_main_material_segment_groups, classify_main_material_segment_groups,
)
from zijinhua_tekla.classifiers.composite_main_material_segments import classify_composite_main_material_segments
from zijinhua_tekla.classifiers.local_body_sections import local_box_wall_ids, local_h_plate_roles
from zijinhua_tekla.reports.member_complexity import classify_member_complexity
from zijinhua_tekla.reports.part_feature_excel import build_part_feature_rows


class LocalBodySectionTests(unittest.TestCase):
    def test_short_box_walls_are_confirmed_without_axis_length_or_cut_ratio_gate(self):
        for length in [100, 600, 3000]:
            for axis_length in [11000, 1000000]:
                with self.subTest(length=length, axis_length=axis_length):
                    assembly, member = box_fixture(length, axis_length)
                    original = copy.deepcopy((assembly, member))
                    groups = classify_box_main_material_segment_groups(assembly, member)
                    walls = {pid for group in groups if group.group_type == "BOX_MAIN_WALL_CONFIRMED_SET"
                             for pid in group.part_ids}
                    self.assertEqual({"a", "b", "c", "d"}, walls)
                    self.assertEqual("BOX", classify_member_complexity(assembly, member, corbel_units=[]).main_material_type)
                    self.assertEqual(original, (assembly, member))

    def test_box_splice_counts_do_not_override_same_wall_identity(self):
        assembly, member = box_fixture()
        member["Samples"].append({"IsAbnormal": True, "AbnormalReason": "dense_attachment_zone", "SectionFeatures": {
            "MajorPlateCount": 5, "CentralVerticalPlateCount": 2, "CentralHorizontalPlateCount": 3,
        }, "SectionParts": [{"PartId": pid, "RoleHint": "wall_candidate"} for pid in "abcd"]})
        result = classify_member_complexity(assembly, member, corbel_units=[])
        self.assertEqual("BOX", result.main_material_type)
        self.assertIn("section.same_core_partial_samples:1", result.evidence_codes)

    def test_valid_different_section_is_not_discarded_even_with_same_part_ids(self):
        assembly, member = box_fixture()
        member["Samples"].append({"IsAbnormal": False, "SectionFeatures": {
            "MajorPlateCount": 3, "CentralVerticalPlateCount": 1, "CentralHorizontalPlateCount": 2,
        }, "SectionParts": [{"PartId": pid, "RoleHint": "wall_candidate"} for pid in "abc"]})
        self.assertEqual("UNKNOWN", classify_member_complexity(assembly, member, corbel_units=[]).main_material_type)

    def test_independent_cross_core_is_still_a_type_conflict(self):
        assembly, member = box_fixture()
        assembly["parts"].append(plate("cross", 0, 300))
        member["Samples"].append({"SectionFeatures": {
            "MajorPlateCount": 5, "CentralVerticalPlateCount": 2, "CentralHorizontalPlateCount": 3,
        }, "SectionParts": [{"PartId": "cross", "RoleHint": "web_candidate"}]})
        self.assertEqual("UNKNOWN", classify_member_complexity(assembly, member, corbel_units=[]).main_material_type)

    def test_unknown_abnormal_reason_or_missing_cavity_does_not_prove_box_walls(self):
        assembly, member = box_fixture()
        member["Samples"][0]["AbnormalReason"] = "invalid_geometry"
        self.assertEqual(set(), local_box_wall_ids(assembly, member))
        member["Samples"][0]["IsAbnormal"] = False
        member["Samples"][0]["SectionFeatures"]["CavityCount"] = 0
        self.assertEqual(set(), local_box_wall_ids(assembly, member))

    def test_native_profile_main_part_cannot_be_replaced_by_plate_sections(self):
        assembly, member = box_fixture()
        assembly["parts"].append({"partId": "native", "profileString": "BH500*200*10*16", "isPlateLike": False})
        assembly["mainPartId"] = "native"
        self.assertEqual(set(), local_box_wall_ids(assembly, member))
        h = h_fixture()
        h["parts"].extend(assembly["parts"][-1:])
        h["mainPartId"] = "native"
        self.assertEqual({}, local_h_plate_roles(h))

    def test_short_h_parts_use_complete_local_frames_and_keep_attachments_out(self):
        for length in [100, 600, 3000]:
            assembly = h_fixture(length)
            for axis_length in [11000, 1000000]:
                with self.subTest(length=length, axis_length=axis_length):
                    assembly["metadata"]["memberAxisEvidence"]["length"] = axis_length
                    segments = classify_composite_main_material_segments(assembly)
                    self.assertEqual({"top", "web", "bottom"}, {p.part_id for s in segments for p in s.main_plates})
                    self.assertEqual(length, segments[0].station_end)
                    self.assertEqual("H钢", classify_member_complexity(assembly, {}, corbel_units=[]).main_material_type)

    def test_h_partial_end_is_same_body_and_excel_marks_only_core_parts(self):
        assembly = h_fixture()
        member = {"Samples": [{"SectionFeatures": {"MajorPlateCount": 1},
                               "SectionParts": [{"PartId": "top", "RoleHint": "flange_candidate"}]}]}
        self.assertEqual("H钢", classify_member_complexity(assembly, member, corbel_units=[]).main_material_type)
        rows = {row["零件名称"]: row for row in build_part_feature_rows(assembly, member, "SAMPLE")}
        self.assertEqual({"H"}, {row["构件类型"] for row in rows.values()})
        self.assertEqual({"P-top", "P-web", "P-bottom"}, {pid for pid, row in rows.items() if row["主材"] == "是"})

    def test_explicit_sections_route_without_member_number_or_plate_name_hints(self):
        assembly = h_fixture()
        for position in ["SAMPLE", "A-GKZ-1", "A-GL-1"]:
            assembly["metadata"]["assemblyPosition"] = position
            groups = classify_main_material_segment_groups(assembly, {})
            self.assertEqual({"top", "web", "bottom"}, {pid for group in groups for pid in group.part_ids})
            self.assertEqual({"TOP_FLANGE", "WEB", "BOTTOM_FLANGE"},
                             {group.evidence_summary["main_material_role"] for group in groups})

    def test_repeated_station_or_missing_third_slice_does_not_prove_h(self):
        assembly = h_fixture()
        frames = assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"]
        frames[1]["station"] = frames[0]["station"]
        self.assertEqual({}, local_h_plate_roles(assembly))
        frames[1]["station"] += 1
        for frame in frames:
            frame["partSlices"] = frame["partSlices"][:2]
        self.assertEqual({}, local_h_plate_roles(assembly))

    def test_conflicting_station_roles_do_not_choose_a_winner(self):
        assembly = h_fixture()
        frames = assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"]
        conflicts = copy.deepcopy(frames)
        for frame in conflicts:
            frame["topFlangePartId"] = "attachment"
        frames.extend(conflicts)
        self.assertEqual({}, local_h_plate_roles(assembly))

    def test_repeated_single_slot_does_not_prove_a_complete_h_core(self):
        assembly = h_fixture()
        frame = assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"][1]
        frame["bottomFlangePartId"] = "attachment"
        self.assertEqual({}, local_h_plate_roles(assembly))

    def test_explicit_h_slot_with_stiffener_evidence_remains_unconfirmed(self):
        assembly = h_fixture()
        for frame in assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"]:
            frame["partSlices"][1]["roleHint"] = "stiffener_candidate"
        self.assertEqual({}, local_h_plate_roles(assembly))

    def test_disconnected_local_h_frame_does_not_join_main_material(self):
        assembly = h_fixture()
        other = h_fixture()
        for part in other["parts"]:
            part["partId"] += "-other"
        frames = other["metadata"]["hBeamSectionEvidence"]["stationFrames"]
        for frame in frames:
            frame["station"] += 1000
            for slot in ["topFlangePartId", "webPartId", "bottomFlangePartId"]:
                frame[slot] += "-other"
            for item in frame["partSlices"]:
                item["partId"] += "-other"
        assembly["parts"].extend(other["parts"])
        assembly["metadata"]["hBeamSectionEvidence"]["stationFrames"].extend(frames)
        self.assertEqual({"top", "web", "bottom"}, set(local_h_plate_roles(assembly)))


def plate(pid, start, end):
    return {"partId": pid, "partPosition": "P-" + pid, "profileString": "PL10*200", "isPlateLike": True,
            "mainMaterialEvidence": {"isBodyWallPlateCandidate": True, "bodyFaceId": "FACE-" + pid,
                                     "axisStationStart": start, "axisStationEnd": end, "axisStationLength": end-start}}


def box_fixture(length=300, axis_length=11000):
    assembly = {"assemblyId": "SAMPLE", "mainPartId": "a", "parts": [plate(pid, 0, length) for pid in "abcd"],
                "relationships": [], "metadata": {"assemblyPosition": "SAMPLE", "memberAxisEvidence": {"length": axis_length}}}
    member = {"Samples": [{"IsAbnormal": True, "AbnormalReason": "dense_attachment_zone", "SectionFeatures": {
        "ClosedLoops": 1, "CavityCount": 1, "OuterWidth": 200, "OuterHeight": 200,
    }, "SectionParts": [{"PartId": pid, "RoleHint": "flange_candidate" if pid in "ab" else "web_candidate",
                         "TotalCutLength": 10} for pid in "abcd"]}]}
    return assembly, member


def h_fixture(length=300):
    parts = [plate(pid, 0, length) for pid in ["top", "web", "bottom", "attachment"]]
    slices = [{"partId": pid, "roleHint": "web_candidate" if pid == "web" else "flange_candidate",
               "sectionLoops": [{"isClosed": True, "isValid": True, "points": [
                   {"u": 0, "v": 0}, {"u": 100, "v": 0}, {"u": 100, "v": 10}, {"u": 0, "v": 10},
               ]}]} for pid in ["top", "web", "bottom", "attachment"]]
    frames = [{"station": station, "topFlangePartId": "top", "webPartId": "web", "bottomFlangePartId": "bottom",
               "partSlices": copy.deepcopy(slices)} for station in [length/3, 2*length/3]]
    return {"assemblyId": "SAMPLE", "mainPartId": "top", "parts": parts, "relationships": [],
            "metadata": {"assemblyPosition": "SAMPLE", "memberAxisEvidence": {"length": 11000},
                         "hBeamSectionEvidence": {"stationFrames": frames}}}


if __name__ == "__main__":
    unittest.main()
