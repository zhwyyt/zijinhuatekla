from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ezdxf
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from .contracts import DrawingIssue, DrawingStatus, PartDrawingSnapshot
from .dimension_optimizer import (
    DrawingArc,
    DrawingCircle,
    DrawingLine,
    DrawingText,
    ModelTransform,
    PartDrawingLayout,
)
from .feature_recognizer import FeatureType, RecognizedFeature
from .geometry_analyzer import NormalizedPlateGeometry, NormalizedSegment, Point2D
from .snapshot_input import safe_part_position


LAYERS = {
    "PART_CONTOUR": 7,
    "PART_INNER": 3,
    "PART_CENTER": 4,
    "DIMENSION": 2,
    "ANNOTATION": 6,
    "TITLE_BLOCK": 7,
    "REVIEW": 1,
}


@dataclass(frozen=True)
class PartDrawingDocument:
    schema_version: str
    rule_version: str
    part_position: str
    part_ids: tuple[str, ...]
    quantity: int
    status: DrawingStatus
    page_width: float
    page_height: float
    scale: float
    geometry_fingerprint: str
    source: dict[str, str]
    tolerances: dict[str, float]
    recognized_feature_ids: tuple[str, ...]
    contour_segments: tuple[DrawingLine | DrawingArc, ...]
    inner_segments: tuple[DrawingLine | DrawingArc | DrawingCircle, ...]
    annotation_lines: tuple[DrawingLine, ...]
    annotation_text_items: tuple[DrawingText, ...]
    title_fields: dict[str, str]
    issues: tuple[DrawingIssue, ...]

    def annotation_texts(self) -> list[str]:
        return [item.text for item in self.annotation_text_items]


@dataclass(frozen=True)
class PartDrawingPaths:
    dxf_path: Path
    pdf_path: Path
    json_path: Path


class PartDrawingRenderError(RuntimeError):
    pass


def build_part_drawing_document(
    snapshot: PartDrawingSnapshot,
    geometry: NormalizedPlateGeometry,
    features: tuple[RecognizedFeature, ...],
    layout: PartDrawingLayout,
    quantity: int,
    status: DrawingStatus | None = None,
    issues: tuple[DrawingIssue, ...] = (),
    part_ids: tuple[str, ...] = (),
) -> PartDrawingDocument:
    contour_segments = tuple(
        _transform_segment(segment, layout.model_transform, "PART_CONTOUR")
        for segment in geometry.outer_loop
    )
    inner_segments = tuple(
        _transform_segment(segment, layout.model_transform, "PART_INNER")
        for loop in geometry.inner_loops
        for segment in loop
    ) + tuple(
        primitive
        for feature in features
        if feature.feature_type in {FeatureType.ROUND_HOLE, FeatureType.SLOT}
        for primitive in _feature_primitives(feature, layout.model_transform)
    )
    return PartDrawingDocument(
        schema_version="partDrawingDocument.v1",
        rule_version="partDrawingRules.v1",
        part_position=snapshot.part_position,
        part_ids=part_ids or (snapshot.part_id,),
        quantity=quantity,
        status=status or layout.status,
        page_width=layout.page_width,
        page_height=layout.page_height,
        scale=layout.scale,
        geometry_fingerprint=geometry.fingerprint,
        source={
            "schema_version": snapshot.schema_version,
            "exporter_version": snapshot.exporter_version,
            "model_identifier": snapshot.model_identifier,
            "exported_at": snapshot.exported_at,
        },
        tolerances={
            "coordinate_noise_mm": 0.01,
            "geometry_match_mm": 0.1,
            "angle_match_deg": 0.05,
            "thickness_match_mm": 0.01,
        },
        recognized_feature_ids=tuple(feature.feature_id for feature in features),
        contour_segments=contour_segments,
        inner_segments=inner_segments,
        annotation_lines=layout.annotation_lines,
        annotation_text_items=layout.annotation_texts,
        title_fields=layout.title_fields,
        issues=issues,
    )


def render_part_drawing(
    document: PartDrawingDocument,
    output_directory: Path,
    cjk_font_path: Path | None = None,
) -> PartDrawingPaths:
    if document.status == DrawingStatus.REJECTED:
        raise ValueError("REJECTED document cannot be rendered")
    font_name = _resolve_pdf_font(document, cjk_font_path)
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = safe_part_position(document.part_position)
    paths = PartDrawingPaths(
        output_directory / f"{stem}.dxf",
        output_directory / f"{stem}.pdf",
        output_directory / f"{stem}.drawing.json",
    )
    temporary = PartDrawingPaths(
        paths.dxf_path.with_suffix(".dxf.tmp"),
        paths.pdf_path.with_suffix(".pdf.tmp"),
        paths.json_path.with_suffix(".json.tmp"),
    )
    try:
        _render_dxf(document, temporary.dxf_path)
        _render_pdf(document, temporary.pdf_path, font_name)
        temporary.json_path.write_text(
            json.dumps(_document_to_jsonable(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.dxf_path.replace(paths.dxf_path)
        temporary.pdf_path.replace(paths.pdf_path)
        temporary.json_path.replace(paths.json_path)
    except Exception as exc:
        for path in (temporary.dxf_path, temporary.pdf_path, temporary.json_path):
            if path.exists():
                path.unlink()
        if isinstance(exc, (ValueError, PartDrawingRenderError)):
            raise
        raise PartDrawingRenderError(str(exc)) from exc
    return paths


def _transform_segment(segment: NormalizedSegment, transform: ModelTransform, layer: str):
    start = transform.point(segment.start)
    end = transform.point(segment.end)
    if segment.kind == "LINE":
        return DrawingLine(*start, *end, layer)
    if segment.center is None:
        raise PartDrawingRenderError("ARC segment requires center")
    center = transform.point(segment.center)
    radius = math.hypot(start[0] - center[0], start[1] - center[1])
    start_angle = math.degrees(math.atan2(start[1] - center[1], start[0] - center[0])) % 360
    end_angle = math.degrees(math.atan2(end[1] - center[1], end[0] - center[0])) % 360
    if not segment.clockwise:
        start_angle, end_angle = end_angle, start_angle
    return DrawingArc(center[0], center[1], radius, start_angle, end_angle, layer)


def _feature_primitives(feature: RecognizedFeature, transform: ModelTransform):
    center = transform.point(feature.anchors[0])
    if feature.feature_type == FeatureType.ROUND_HOLE:
        return (DrawingCircle(center[0], center[1], float(feature.parameters["diameter"]) * transform.scale / 2.0, "PART_INNER"),)
    length = float(feature.parameters["length"]) * transform.scale
    width = float(feature.parameters["width"]) * transform.scale
    angle = math.radians(-float(feature.parameters.get("angle_deg", 0.0)))
    ux, uy = math.cos(angle), math.sin(angle)
    px, py = -uy, ux
    radius = width / 2.0
    half_straight = max(0.0, (length - width) / 2.0)
    first = (center[0] - ux * half_straight, center[1] - uy * half_straight)
    second = (center[0] + ux * half_straight, center[1] + uy * half_straight)
    direction_angle = math.degrees(angle)
    return (
        DrawingLine(first[0] + px * radius, first[1] + py * radius, second[0] + px * radius, second[1] + py * radius, "PART_INNER"),
        DrawingLine(first[0] - px * radius, first[1] - py * radius, second[0] - px * radius, second[1] - py * radius, "PART_INNER"),
        DrawingArc(first[0], first[1], radius, direction_angle + 90, direction_angle + 270, "PART_INNER"),
        DrawingArc(second[0], second[1], radius, direction_angle - 90, direction_angle + 90, "PART_INNER"),
    )


def _resolve_pdf_font(document: PartDrawingDocument, cjk_font_path: Path | None) -> str:
    texts = document.annotation_texts() + list(document.title_fields.values())
    if not any(any(ord(char) > 127 for char in text) for text in texts):
        return "Helvetica"
    if cjk_font_path is None or not cjk_font_path.is_file():
        raise PartDrawingRenderError("CJK font is required for non-ASCII PDF text")
    try:
        pdfmetrics.registerFont(TTFont("PartDrawingCJK", str(cjk_font_path)))
    except Exception as exc:
        raise PartDrawingRenderError(f"CJK font cannot be loaded: {exc}") from exc
    return "PartDrawingCJK"


def _render_dxf(document: PartDrawingDocument, path: Path) -> None:
    dxf = ezdxf.new("R2007", setup=True)
    for name, color in LAYERS.items():
        if name not in dxf.layers:
            dxf.layers.add(name, color=color)
    modelspace = dxf.modelspace()
    for primitive in document.contour_segments + document.inner_segments + document.annotation_lines:
        _add_dxf_primitive(modelspace, primitive)
    for item in document.annotation_text_items:
        modelspace.add_text(item.text, dxfattribs={"insert": (item.x, item.y), "height": item.height, "layer": item.layer})
    _add_dxf_title(modelspace, document)
    dxf.saveas(path)
    audit = ezdxf.readfile(path).audit()
    if audit.has_errors:
        raise PartDrawingRenderError(f"DXF audit failed with {len(audit.errors)} errors")


def _add_dxf_primitive(modelspace, primitive) -> None:
    if isinstance(primitive, DrawingLine):
        modelspace.add_line((primitive.x1, primitive.y1), (primitive.x2, primitive.y2), dxfattribs={"layer": primitive.layer})
    elif isinstance(primitive, DrawingCircle):
        modelspace.add_circle((primitive.cx, primitive.cy), primitive.radius, dxfattribs={"layer": primitive.layer})
    elif isinstance(primitive, DrawingArc):
        modelspace.add_arc((primitive.cx, primitive.cy), primitive.radius, primitive.start_angle, primitive.end_angle, dxfattribs={"layer": primitive.layer})


def _add_dxf_title(modelspace, document) -> None:
    modelspace.add_line((12, 242), (408, 242), dxfattribs={"layer": "TITLE_BLOCK"})
    for index, (key, value) in enumerate(document.title_fields.items()):
        modelspace.add_text(f"{key}: {value}", dxfattribs={"insert": (220, 250 + index * 6), "height": 3.5, "layer": "TITLE_BLOCK"})


def _render_pdf(document: PartDrawingDocument, path: Path, font_name: str) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(document.page_width * mm, document.page_height * mm), pageCompression=0)
    pdf.setLineWidth(0.25 * mm)
    for primitive in document.contour_segments + document.inner_segments + document.annotation_lines:
        _add_pdf_primitive(pdf, document, primitive)
    for item in document.annotation_text_items:
        _pdf_text(pdf, document, item.x, item.y, item.text, item.height, font_name)
    pdf.line(12 * mm, (document.page_height - 242) * mm, 408 * mm, (document.page_height - 242) * mm)
    for index, (key, value) in enumerate(document.title_fields.items()):
        _pdf_text(pdf, document, 220, 250 + index * 6, f"{key}: {value}", 3.5, font_name)
    pdf.showPage()
    pdf.save()
    if not path.exists() or path.stat().st_size <= 1000:
        raise PartDrawingRenderError("PDF output is empty")


def _add_pdf_primitive(pdf, document, primitive) -> None:
    if isinstance(primitive, DrawingLine):
        pdf.line(primitive.x1 * mm, (document.page_height - primitive.y1) * mm, primitive.x2 * mm, (document.page_height - primitive.y2) * mm)
    elif isinstance(primitive, DrawingCircle):
        pdf.circle(primitive.cx * mm, (document.page_height - primitive.cy) * mm, primitive.radius * mm, stroke=1, fill=0)
    elif isinstance(primitive, DrawingArc):
        left = (primitive.cx - primitive.radius) * mm
        bottom = (document.page_height - primitive.cy - primitive.radius) * mm
        right = (primitive.cx + primitive.radius) * mm
        top = (document.page_height - primitive.cy + primitive.radius) * mm
        extent = (primitive.end_angle - primitive.start_angle) % 360
        pdf.arc(left, bottom, right, top, startAng=-primitive.end_angle, extent=extent)


def _pdf_text(pdf, document, x, y, text, height, font_name) -> None:
    pdf.setFont(font_name, height * mm)
    pdf.drawString(x * mm, (document.page_height - y) * mm, text)


def _document_to_jsonable(document: PartDrawingDocument) -> dict[str, Any]:
    return {
        "schema_version": document.schema_version,
        "rule_version": document.rule_version,
        "part_position": document.part_position,
        "part_ids": list(document.part_ids),
        "quantity": document.quantity,
        "status": document.status.value,
        "page": {"width": document.page_width, "height": document.page_height, "scale": document.scale},
        "geometry_fingerprint": document.geometry_fingerprint,
        "source": document.source,
        "tolerances": document.tolerances,
        "recognized_feature_ids": list(document.recognized_feature_ids),
        "annotation_texts": document.annotation_texts(),
        "entity_counts": _entity_counts(document),
        "issues": [
            {"code": item.code.value, "message": item.message, "blocking": item.blocking, "part_ids": list(item.part_ids), "evidence": list(item.evidence)}
            for item in document.issues
        ],
    }


def _entity_counts(document: PartDrawingDocument) -> dict[str, int]:
    primitives = document.contour_segments + document.inner_segments + document.annotation_lines
    return {
        "lines": sum(isinstance(item, DrawingLine) for item in primitives),
        "arcs": sum(isinstance(item, DrawingArc) for item in primitives),
        "circles": sum(isinstance(item, DrawingCircle) for item in primitives),
        "texts": len(document.annotation_text_items) + len(document.title_fields),
    }
