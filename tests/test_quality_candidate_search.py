import unittest

from zijinhua_tekla.quality.candidates import (
    build_conflict_candidate_report,
    build_missing_candidate_report,
    flatten_conflict_candidate_report,
    flatten_missing_candidate_report,
    search_missing_part_candidates,
)


class QualityCandidateSearchTests(unittest.TestCase):
    def test_search_missing_part_candidates_ranks_exact_geometry_before_near_candidates(self):
        row = {
            "零件名称": "T3-P-3449",
            "规格": "PL10*200",
            "长度": 1000,
        }
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "A-1",
                    "parts": [
                        {
                            "partId": "10",
                            "partPosition": "A-P-1",
                            "name": "PLATE",
                            "profileString": "PL10",
                            "runtimeType": "ContourPlate",
                            "isPlateLike": True,
                            "thickness": 10,
                            "obbDims": {"x": 1000, "y": 200, "z": 10},
                        }
                    ],
                },
                {
                    "assemblyId": "A-2",
                    "parts": [
                        {
                            "partId": "20",
                            "partPosition": "A-P-2",
                            "name": "PLATE",
                            "profileString": "PL10",
                            "runtimeType": "ContourPlate",
                            "isPlateLike": True,
                            "thickness": 10,
                            "obbDims": {"x": 1080, "y": 205, "z": 10},
                        }
                    ],
                },
            ]
        }

        candidates = search_missing_part_candidates(row, bundle, limit=5)

        self.assertEqual(2, len(candidates))
        self.assertEqual("10", candidates[0].part_id)
        self.assertEqual("A-1", candidates[0].assembly_id)
        self.assertEqual("A-P-1", candidates[0].part_position)
        self.assertEqual("GEOMETRY_EXACT", candidates[0].match_level)
        self.assertEqual(0, candidates[0].length_delta)
        self.assertEqual(0, candidates[0].width_delta)
        self.assertEqual("20", candidates[1].part_id)
        self.assertEqual("GEOMETRY_NEAR", candidates[1].match_level)

    def test_build_missing_candidate_report_from_aligned_rows(self):
        aligned_rows = [
            {
                "零件名称": "A-P-1",
                "规格": "PL10*200",
                "长度": 1000,
                "prediction_status": "MATCH",
                "match_method": "partPosition",
            },
            {
                "零件名称": "A-P-2",
                "规格": "PL8*120",
                "长度": 300,
                "prediction_status": "DATA_MISSING",
                "match_method": "missing",
            },
            {
                "零件名称": "A-P-3",
                "规格": "PL6*100",
                "长度": 200,
                "prediction_status": "DATA_MISSING",
                "match_method": "missing",
            },
        ]
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "B-1",
                    "parts": [
                        {
                            "partId": "30",
                            "partPosition": "B-P-30",
                            "name": "PLATE",
                            "profileString": "PL8",
                            "runtimeType": "ContourPlate",
                            "isPlateLike": True,
                            "thickness": 8,
                            "obbDims": {"x": 300, "y": 120, "z": 8},
                        }
                    ],
                }
            ]
        }

        report = build_missing_candidate_report("A-GKZ-1", aligned_rows, bundle, limit=3)
        flat_rows = flatten_missing_candidate_report(report)

        self.assertEqual(2, len(report))
        self.assertEqual("A-GKZ-1:A-P-2:DATA_MISSING", report[0]["task_id"])
        self.assertEqual(1, report[0]["candidate_count"])
        self.assertEqual("30", report[0]["candidates"][0]["part_id"])
        self.assertEqual("A-GKZ-1:A-P-3:DATA_MISSING", report[1]["task_id"])
        self.assertEqual(0, report[1]["candidate_count"])
        self.assertEqual("30", flat_rows[0]["part_id"])
        self.assertEqual("", flat_rows[1]["part_id"])
        self.assertEqual(0, flat_rows[1]["candidate_count"])

    def test_build_conflict_candidate_report_keeps_conflict_and_geometry_review_evidence(self):
        aligned_rows = [
            {
                "零件名称": "A-P-9",
                "规格": "PL8*120",
                "长度": 300,
                "prediction_status": "MATCH_CONFLICT",
                "match_method": "partPositionConflict",
            }
        ]
        bundle = {
            "assemblies": [
                {
                    "assemblyId": "B-1",
                    "parts": [
                        {
                            "partId": "90",
                            "partPosition": "A-P-9",
                            "name": "CONFLICT_PLATE",
                            "profileString": "PL10",
                            "runtimeType": "ContourPlate",
                            "isPlateLike": True,
                            "thickness": 10,
                            "obbDims": {"x": 420, "y": 140, "z": 10},
                        },
                        {
                            "partId": "91",
                            "partPosition": "B-P-91",
                            "name": "GEOMETRY_REVIEW_CANDIDATE",
                            "profileString": "PL8",
                            "runtimeType": "ContourPlate",
                            "isPlateLike": True,
                            "thickness": 8,
                            "obbDims": {"x": 300, "y": 120, "z": 8},
                        },
                    ],
                }
            ]
        }

        report = build_conflict_candidate_report("A-GKZ-1", aligned_rows, bundle, limit=3)
        flat_rows = flatten_conflict_candidate_report(report)

        self.assertEqual(1, len(report))
        self.assertEqual("A-GKZ-1:A-P-9:MATCH_CONFLICT", report[0]["task_id"])
        self.assertEqual(1, report[0]["conflict_count"])
        self.assertEqual("90", report[0]["conflict_parts"][0]["part_id"])
        self.assertEqual("PART_POSITION_CONFLICT", report[0]["conflict_parts"][0]["match_level"])
        self.assertEqual(1, report[0]["geometry_review_candidate_count"])
        self.assertEqual("91", report[0]["geometry_review_candidates"][0]["part_id"])
        self.assertEqual("GEOMETRY_EXACT", report[0]["geometry_review_candidates"][0]["match_level"])
        self.assertEqual("conflict_part", flat_rows[0]["candidate_kind"])
        self.assertEqual("geometry_review_candidate", flat_rows[1]["candidate_kind"])


if __name__ == "__main__":
    unittest.main()
