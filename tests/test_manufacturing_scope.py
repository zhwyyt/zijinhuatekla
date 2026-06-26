import unittest

from zijinhua_tekla.casebank import CaseBank, CaseFeedback, CaseIssueType

from zijinhua_tekla.quality.gate import DataQualityIssueType, quality_report_from_aligned_rows
from zijinhua_tekla.quality.manufacturing_scope import (
    apply_confirmed_segment_groups,
    build_manufacturing_scope_report,
    find_manufacturing_scope_candidates,
    flatten_manufacturing_scope_report,
)


class ManufacturingScopeTests(unittest.TestCase):
    def test_applies_confirmed_segment_group_from_case_bank_to_matching_rows(self):
        bank = CaseBank()
        bank.add(
            CaseFeedback(
                case_id="T3-5GKZ-10:box-column-main-material-segments",
                issue_type=CaseIssueType.DATA,
                expected_label="BOX_COLUMN_MAIN_MATERIAL_SEGMENT_GROUP",
                human_note="人工确认 T3-P-6272、T3-P-5577 都是同一类柱主材分段模型。",
                evidence_fields=["confirmed_segment_positions"],
            )
        )
        rows = [
            {"零件名称": "T3-P-6272", "prediction_status": "MATCH"},
            {"零件名称": "T3-P-5577", "prediction_status": "DATA_MISSING"},
            {"零件名称": "T3-P-4914", "prediction_status": "DATA_MISSING"},
            {"零件名称": "T3-P-9999", "prediction_status": "MATCH"},
        ]

        updated = apply_confirmed_segment_groups(rows, "T3-5GKZ-10", bank)

        self.assertEqual("T3-P-6272;T3-P-5577", updated[0]["confirmed_segment_positions"])
        self.assertEqual("HUMAN_CONFIRMED_SEGMENT_GROUP", updated[0]["confirmation_level"])
        self.assertEqual("T3-P-6272;T3-P-5577", updated[1]["confirmed_segment_positions"])
        self.assertNotIn("confirmed_segment_positions", updated[2])
        self.assertNotIn("confirmed_segment_positions", updated[3])
    def test_finds_long_manufacturing_plate_with_segmented_tekla_wall_parts(self):
        row = {
            "零件名称": "T3-P-4914",
            "规格": "PL16*968",
            "长度": 10534,
            "prediction_status": "DATA_MISSING",
            "match_method": "missing",
            "predicted_role": "箱型柱主材壁板",
            "形状分类": "异形主材",
        }
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "72805757",
                    "parts": [
                        _plate("72805753", "T3-P-6284", "COLUMN", "PL16*968", 3088, 968, 16),
                        _plate("72806584", "T3-P-6270", "COLUMN", "PL16*968", 3088, 968, 16),
                        _plate("72806770", "T3-P-4916", "环形劲板", "PL30*100", 412, 100, 30),
                    ],
                }
            ]
        }

        candidates = find_manufacturing_scope_candidates(row, bundle)

        self.assertEqual(1, len(candidates))
        self.assertEqual("BOX_WALL_LONG_PLATE_SEGMENTS", candidates[0].evidence_code)
        self.assertEqual("SEGMENTED_MODEL_REVIEW", candidates[0].match_level)
        self.assertEqual(["72805753", "72806584"], candidates[0].segment_part_ids)
        self.assertEqual(2, candidates[0].segment_count)
        self.assertAlmostEqual(6176, candidates[0].segment_total_length)
        self.assertLess(candidates[0].coverage_ratio, 1.0)


    def test_candidate_exports_station_continuity_evidence(self):
        row = {
            "零件名称": "T3-P-4914",
            "规格": "PL16*968",
            "长度": 6200,
            "prediction_status": "DATA_MISSING",
            "match_method": "missing",
            "predicted_role": "箱型柱主材壁板",
            "形状分类": "异形主材",
        }
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "72805757",
                    "parts": [
                        _plate_at("72805753", "T3-P-6284", 1500, 3000),
                        _plate_at("72806584", "T3-P-6270", 4550, 3000),
                    ],
                }
            ]
        }

        report = build_manufacturing_scope_report("T3-5GKZ-10", [row], bundle)
        flat_rows = flatten_manufacturing_scope_report(report)

        candidate = report[0]["candidates"][0]
        self.assertEqual("T3-P-6284:0.0-3000.0;T3-P-6270:3050.0-6050.0", candidate["station_ranges"])
        self.assertEqual("50.0", candidate["continuity_gaps"])
        self.assertEqual("NEAR_CONTINUOUS", candidate["continuity_level"])
        self.assertEqual("T3-P-6284:0.0-3000.0;T3-P-6270:3050.0-6050.0", flat_rows[0]["station_ranges"])
        self.assertEqual("50.0", flat_rows[0]["continuity_gaps"])
        self.assertEqual("NEAR_CONTINUOUS", flat_rows[0]["continuity_level"])

    def test_station_continuity_prefers_exported_main_material_station_ranges(self):
        row = {
            "零件名称": "T3-P-4914",
            "规格": "PL16*968",
            "长度": 6200,
            "prediction_status": "DATA_MISSING",
            "match_method": "missing",
            "predicted_role": "箱型柱主材壁板",
            "形状分类": "异形主材",
        }
        first = _plate_at("72805753", "T3-P-6284", 9000, 3000)
        second = _plate_at("72806584", "T3-P-6270", 1000, 3000)
        first["mainMaterialEvidence"] = {"axisStationStart": 0, "axisStationEnd": 3000}
        second["mainMaterialEvidence"] = {"axisStationStart": 3005, "axisStationEnd": 6005}
        bundle = {"assemblies": [{"assemblyId": "72805757", "parts": [first, second]}]}

        report = build_manufacturing_scope_report("T3-5GKZ-10", [row], bundle)

        candidate = report[0]["candidates"][0]
        self.assertEqual("T3-P-6284:0.0-3000.0;T3-P-6270:3005.0-6005.0", candidate["station_ranges"])
        self.assertEqual("5.0", candidate["continuity_gaps"])
        self.assertEqual("CONTINUOUS", candidate["continuity_level"])
    def test_overlapping_station_ranges_require_face_grouping(self):
        row = {
            "零件名称": "T3-P-4914",
            "规格": "PL16*968",
            "长度": 6200,
            "prediction_status": "DATA_MISSING",
            "match_method": "missing",
            "predicted_role": "箱型柱主材壁板",
            "形状分类": "异形主材",
        }
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "72805757",
                    "parts": [
                        _plate_at("72805753", "T3-P-6284", 1500, 3000),
                        _plate_at("72806584", "T3-P-6270", 1600, 3000),
                    ],
                }
            ]
        }

        report = build_manufacturing_scope_report("T3-5GKZ-10", [row], bundle)

        candidate = report[0]["candidates"][0]
        self.assertEqual("AXIS_OVERLAP_NEEDS_FACE_GROUPING", candidate["continuity_level"])
    def test_confirmed_segment_positions_are_retained_as_group_evidence(self):
        row = {
            "零件名称": "T3-P-4914",
            "规格": "PL16*968",
            "长度": 10534,
            "prediction_status": "DATA_MISSING",
            "match_method": "missing",
            "predicted_role": "箱型柱主材壁板",
            "形状分类": "异形主材",
            "confirmed_segment_positions": "T3-P-4916;T3-P-4917;T3-P-4919;T3-P-6272;T3-P-5577;T3-P-6269;T3-P-6268;T3-P-5571;T3-P-6284;T3-P-6271;T3-P-5579;T3-P-5576;T3-P-6270",
        }
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "72805757",
                    "parts": [
                        _plate("72805753", "T3-P-6284", "COLUMN", "PL16*968", 3088, 968, 16),
                        _plate("72806584", "T3-P-6270", "COLUMN", "PL16*968", 3088, 968, 16),
                    ],
                }
            ]
        }

        report = build_manufacturing_scope_report("T3-5GKZ-10", [row], bundle)

        candidate = report[0]["candidates"][0]
        self.assertEqual("T3-P-4916;T3-P-4917;T3-P-4919;T3-P-6272;T3-P-5577;T3-P-6269;T3-P-6268;T3-P-5571;T3-P-6284;T3-P-6271;T3-P-5579;T3-P-5576;T3-P-6270", candidate["confirmed_segment_positions"])
        self.assertEqual("HUMAN_CONFIRMED_SEGMENT_GROUP", candidate["confirmation_level"])

    def test_build_report_marks_scope_issue_without_auto_matching_numbers(self):
        aligned_rows = [
            {
                "零件名称": "T3-P-4914",
                "规格": "PL16*968",
                "长度": 10534,
                "prediction_status": "DATA_MISSING",
                "match_method": "missing",
                "predicted_role": "箱型柱主材壁板",
                "形状分类": "异形主材",
            },
            {
                "零件名称": "T3-H-558s",
                "规格": "PL10*200",
                "长度": 320,
                "prediction_status": "MATCH",
                "match_method": "derivedFromProfilePart",
                "predicted_role": "牛腿/钢梁相关件",
            },
        ]
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "72805757",
                    "parts": [
                        _plate("72805753", "T3-P-6284", "COLUMN", "PL16*968", 3088, 968, 16),
                        _plate("72806584", "T3-P-6270", "COLUMN", "PL16*968", 3088, 968, 16),
                    ],
                }
            ]
        }

        report = build_manufacturing_scope_report("T3-5GKZ-10", aligned_rows, bundle)
        flat_rows = flatten_manufacturing_scope_report(report)

        self.assertEqual(1, len(report))
        self.assertEqual("T3-5GKZ-10:T3-P-4914:MANUFACTURING_MODEL_SCOPE_MISMATCH", report[0]["task_id"])
        self.assertEqual("MANUFACTURING_MODEL_SCOPE_MISMATCH", report[0]["issue_type_hint"])
        self.assertEqual(1, report[0]["candidate_count"])
        self.assertEqual("scope_segment", flat_rows[0]["candidate_kind"])
        self.assertEqual("72805753", flat_rows[0]["part_id"])
        self.assertEqual("T3-P-6284", flat_rows[0]["part_position"])

    def test_quality_gate_uses_scope_hint_instead_of_generic_missing(self):
        report = quality_report_from_aligned_rows(
            [
                {
                    "零件名称": "T3-P-4914",
                    "prediction_status": "DATA_MISSING",
                    "match_method": "missing",
                    "quality_issue_type_hint": "MANUFACTURING_MODEL_SCOPE_MISMATCH",
                    "match_note": "segmented wall candidates",
                }
            ]
        )

        self.assertEqual(1, len(report.issues))
        self.assertEqual(DataQualityIssueType.MANUFACTURING_MODEL_SCOPE_MISMATCH, report.issues[0].issue_type)
        self.assertEqual("DATA_MISSING", report.issues[0].status)
        self.assertIn("segmented wall", report.issues[0].evidence)


def _plate(part_id, position, name, profile, length, width, thickness):
    return {
        "partId": part_id,
        "partPosition": position,
        "name": name,
        "profileString": profile,
        "runtimeType": "ContourPlate",
        "isPlateLike": True,
        "thickness": thickness,
        "obbDims": {"x": length, "y": width, "z": thickness},
    }




def _plate_at(part_id, position, station_center, length):
    part = _plate(part_id, position, "COLUMN", "PL16*968", length, 968, 16)
    part["centroid"] = {"x": station_center, "y": 0, "z": 0}
    part["plateLongDirection"] = {"x": 1, "y": 0, "z": 0}
    return part
if __name__ == "__main__":
    unittest.main()
