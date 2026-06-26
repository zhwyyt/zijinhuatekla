import unittest

from zijinhua_tekla.classifiers.composite_main_material_segments import (
    CompositeMainMaterialSegment,
    CompositeMainPlate,
    CompositePrimaryRole,
    CompositeSegmentType,
)


class CompositeMainMaterialSegmentTests(unittest.TestCase):
    def test_segment_to_dict_uses_string_roles(self):
        segment = CompositeMainMaterialSegment(
            assembly_id="A1",
            segment_id="S1",
            station_start=0,
            station_end=1000,
            segment_type=CompositeSegmentType.CROSS_CORE_WITH_FLANGES,
            confidence=0.91,
            evidence_codes=["STATION_REGIME_SEGMENT"],
            main_plates=[
                CompositeMainPlate(
                    part_id="p-flange",
                    part_position="P-FLANGE",
                    primary_role=CompositePrimaryRole.CROSS_FLANGE_MAIN_PLATE,
                    secondary_evidence=["parallel_to_cross_core_plate"],
                    evidence_codes=["CROSS_FLANGE_OUTER_PLATE"],
                )
            ],
        )

        self.assertEqual(
            {
                "assembly_id": "A1",
                "segment_id": "S1",
                "station_start": 0,
                "station_end": 1000,
                "segment_type": "CROSS_CORE_WITH_FLANGES",
                "confidence": 0.91,
                "evidence_codes": ["STATION_REGIME_SEGMENT"],
                "main_plates": [
                    {
                        "part_id": "p-flange",
                        "part_position": "P-FLANGE",
                        "primary_role": "CROSS_FLANGE_MAIN_PLATE",
                        "secondary_evidence": ["parallel_to_cross_core_plate"],
                        "evidence_codes": ["CROSS_FLANGE_OUTER_PLATE"],
                    }
                ],
            },
            segment.to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
