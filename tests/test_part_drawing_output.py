from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ezdxf
from pypdf import PdfReader

from zijinhua_tekla.part_drawing import drawing_output
from zijinhua_tekla.part_drawing.contracts import (
    ContourSegmentSnapshot,
    DrawingStatus,
    HoleSnapshot,
    Point3D,
)
from zijinhua_tekla.part_drawing.dimension_generator import generate_dimension_intents
from zijinhua_tekla.part_drawing.dimension_optimizer import optimize_dimension_layout
from zijinhua_tekla.part_drawing.drawing_output import (
    PartDrawingRenderError,
    build_part_drawing_document,
    render_part_drawing,
)
from zijinhua_tekla.part_drawing.feature_recognizer import recognize_plate_features
from zijinhua_tekla.part_drawing.geometry_analyzer import analyze_plate_geometry
from zijinhua_tekla.part_drawing.snapshot_input import load_part_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "part_drawing" / "rectangular_plate.json"


class PartDrawingOutputTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_part_snapshot(FIXTURE)
        self.geometry = analyze_plate_geometry(self.snapshot).geometry
        self.features = ()
        intents = generate_dimension_intents(self.snapshot, self.geometry, self.features).intents
        self.layout = optimize_dimension_layout(self.snapshot, self.geometry, intents, quantity=2)
        self.document = build_part_drawing_document(
            self.snapshot,
            self.geometry,
            self.features,
            self.layout,
            quantity=2,
        )

    def test_writes_dxf_pdf_and_json_from_one_document(self):
        self.assertEqual(2, len(self.document.placed_dimensions))
        self.assertEqual(
            "partCadDimensionStyle.v1",
            self.document.dimension_style.style_id,
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = render_part_drawing(self.document, Path(directory))
            self.assertTrue(paths.dxf_path.exists())
            self.assertTrue(paths.pdf_path.exists())
            self.assertTrue(paths.json_path.exists())
            dxf = ezdxf.readfile(paths.dxf_path)
            self.assertFalse(dxf.audit().has_errors)
            dimensions = list(dxf.modelspace().query("DIMENSION"))
            self.assertEqual(2, len(dimensions))
            self.assertFalse(
                list(dxf.modelspace().query('LINE[layer=="DIMENSION"]'))
            )
            style = dxf.dimstyles.get("PART-CAD-V1")
            self.assertEqual(2.5, style.dxf.dimtxt)
            self.assertEqual(2.0, style.dxf.dimasz)
            self.assertEqual(2.5, style.dxf.dimexo)
            self.assertEqual(2.0, style.dxf.dimexe)
            self.assertEqual(1.0, style.dxf.dimgap)
            self.assertEqual(0, style.dxf.dimdec)
            self.assertEqual(8, style.dxf.dimzin)
            self.assertEqual("_OBLIQUE", style.dxf.dimblk)
            self.assertEqual(0.65, dxf.styles.get("TArial").dxf.width)
            raw_measurements = sorted(
                float(item.get_measurement()) for item in dimensions
            )
            self.assertEqual([100.0, 200.0], raw_measurements)
            for entity in dimensions:
                overrides = entity.get_acad_dstyle(
                    dxf.dimstyles.get(entity.dxf.dimstyle)
                )
                self.assertEqual(1.0, overrides["dimlfac"])
            payload = json.loads(paths.json_path.read_text(encoding="utf-8"))
            self.assertEqual(self.document.part_position, payload["part_position"])
            self.assertEqual(self.document.annotation_texts(), payload["annotation_texts"])
            self.assertEqual("partDrawingSnapshot.v1", payload["source"]["schema_version"])
            self.assertEqual("partDrawingRules.v1", payload["rule_version"])
            self.assertIn("geometry_match_mm", payload["tolerances"])
            self.assertEqual(
                [item.display_text for item in self.document.placed_dimensions],
                payload["placed_dimensions"],
            )
            self.assertEqual(
                "partCadDimensionStyle.v1",
                payload["dimension_style"]["style_id"],
            )
            self.assertEqual(2, payload["entity_counts"]["dimensions"])
            self.assertGreater(paths.pdf_path.stat().st_size, 1000)
            pdf = PdfReader(str(paths.pdf_path))
            self.assertEqual(1, len(pdf.pages))
            page_text = pdf.pages[0].extract_text()
            self.assertIn("P-1001", page_text)
            self.assertIn("200", page_text)
            self.assertIn("100", page_text)

    def test_pdf_renderer_consumes_each_shared_placed_dimension(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "zijinhua_tekla.part_drawing.drawing_output._draw_pdf_dimension",
            wraps=drawing_output._draw_pdf_dimension,
        ) as draw_dimension:
            render_part_drawing(self.document, Path(directory))
            self.assertEqual(
                len(self.document.placed_dimensions),
                draw_dimension.call_count,
            )

    def test_renderer_does_not_emit_files_for_rejected_document(self):
        document = replace(self.document, status=DrawingStatus.REJECTED)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "REJECTED"):
                render_part_drawing(document, Path(directory))
            self.assertFalse(list(Path(directory).iterdir()))

    def test_explicit_round_hole_is_present_in_shared_document_and_dxf(self):
        snapshot = replace(
            self.snapshot,
            holes=(HoleSnapshot("H1", "ROUND", Point3D(60.0, 70.0, 30.0), diameter=22.0),),
        )
        geometry = analyze_plate_geometry(snapshot).geometry
        features = recognize_plate_features(snapshot, geometry).features
        intents = generate_dimension_intents(snapshot, geometry, features).intents
        layout = optimize_dimension_layout(snapshot, geometry, intents, quantity=1)
        document = build_part_drawing_document(snapshot, geometry, features, layout, quantity=1)
        self.assertTrue(any(item.__class__.__name__ == "DrawingCircle" for item in document.inner_segments))
        with tempfile.TemporaryDirectory() as directory:
            paths = render_part_drawing(document, Path(directory))
            modelspace = ezdxf.readfile(paths.dxf_path).modelspace()
            entities = list(modelspace.query("CIRCLE"))
            self.assertEqual(1, len(entities))
            dimensions = list(modelspace.query("DIMENSION"))
            self.assertEqual(5, len(dimensions))
            self.assertIn("DIA22", {entity.dxf.text for entity in dimensions})

    def test_chinese_pdf_text_requires_explicit_cjk_font(self):
        document = replace(
            self.document,
            title_fields={**self.document.title_fields, "name": "连接板"},
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PartDrawingRenderError, "CJK"):
                render_part_drawing(document, Path(directory), cjk_font_path=None)
            self.assertFalse(list(Path(directory).iterdir()))

    def test_slot_is_rendered_as_two_lines_and_two_arcs(self):
        snapshot = replace(
            self.snapshot,
            holes=(HoleSnapshot("S1", "SLOT", Point3D(110, 70, 30), length=40, width=18),),
        )
        document = self._document_for(snapshot)
        slot_primitives = document.inner_segments
        self.assertEqual(2, sum(item.__class__.__name__ == "DrawingLine" for item in slot_primitives))
        self.assertEqual(2, sum(item.__class__.__name__ == "DrawingArc" for item in slot_primitives))

    def test_arc_inner_loop_remains_arc_entities_in_dxf(self):
        points = [Point3D(90, 70, 30), Point3D(110, 90, 30), Point3D(130, 70, 30), Point3D(110, 50, 30)]
        center = Point3D(110, 70, 30)
        loop = tuple(
            ContourSegmentSnapshot(
                "ARC",
                points[index],
                points[(index + 1) % 4],
                center=center,
                clockwise=True,
            )
            for index in range(4)
        )
        document = self._document_for(replace(self.snapshot, inner_loops=(loop,)))
        with tempfile.TemporaryDirectory() as directory:
            paths = render_part_drawing(document, Path(directory))
            self.assertEqual(4, len(list(ezdxf.readfile(paths.dxf_path).modelspace().query("ARC"))))

    def _document_for(self, snapshot):
        geometry = analyze_plate_geometry(snapshot).geometry
        features = recognize_plate_features(snapshot, geometry).features
        intents = generate_dimension_intents(snapshot, geometry, features).intents
        layout = optimize_dimension_layout(snapshot, geometry, intents, quantity=1)
        return build_part_drawing_document(snapshot, geometry, features, layout, quantity=1)


if __name__ == "__main__":
    unittest.main()
