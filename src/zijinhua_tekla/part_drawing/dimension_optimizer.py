from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import DrawingStatus
from .dimension_generator import DimensionKind
from .dimension_style import PART_CAD_DIMENSION_STYLE_V1


PAGE_WIDTH = 420.0
PAGE_HEIGHT = 297.0
TITLE_BLOCK_TOP = 242.0
STANDARD_SCALES = (1.0, 0.5, 0.2, 0.1, 0.05)


@dataclass(frozen=True)
class DrawingRect:
    left: float
    top: float
    right: float
    bottom: float

    def intersects(self, other, padding=0.0):
        return self.left - padding < other.right and self.right + padding > other.left and self.top - padding < other.bottom and self.bottom + padding > other.top


@dataclass(frozen=True)
class ModelTransform:
    scale: float
    offset_x: float
    offset_y: float

    def point(self, point):
        return self.offset_x + point.x * self.scale, self.offset_y - point.y * self.scale


@dataclass(frozen=True)
class DrawingLine:
    x1: float
    y1: float
    x2: float
    y2: float
    layer: str


@dataclass(frozen=True)
class DrawingArc:
    cx: float
    cy: float
    radius: float
    start_angle: float
    end_angle: float
    layer: str


@dataclass(frozen=True)
class DrawingCircle:
    cx: float
    cy: float
    radius: float
    layer: str


@dataclass(frozen=True)
class DrawingText:
    x: float
    y: float
    text: str
    height: float
    layer: str
    box: DrawingRect


class PlacedDimensionKind(str, Enum):
    LINEAR_HORIZONTAL = "LINEAR_HORIZONTAL"
    LINEAR_VERTICAL = "LINEAR_VERTICAL"
    RADIUS = "RADIUS"
    DIAMETER = "DIAMETER"


@dataclass(frozen=True)
class PlacedDimension:
    dimension_id: str
    kind: PlacedDimensionKind
    source_points: tuple[tuple[float, float], ...]
    dimension_line_point: tuple[float, float]
    measured_value_mm: float
    display_text: str
    text_rotation: float
    text_box: DrawingRect
    paper_radius: float = 0.0
    evidence_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PartDrawingLayout:
    page_width: float
    page_height: float
    scale: float
    view_rect: DrawingRect
    model_transform: ModelTransform
    placed_dimensions: tuple[PlacedDimension, ...]
    annotation_lines: tuple[DrawingLine, ...]
    annotation_texts: tuple[DrawingText, ...]
    title_fields: dict[str, str]
    status: DrawingStatus
    collision_count: int
    unplaced_intents: tuple


def optimize_dimension_layout(snapshot, geometry, intents, quantity):
    view = DrawingRect(47.0, 47.0, 343.0, 207.0)
    scale = _fit_scale(geometry.bounds[2], geometry.bounds[3], view)
    offset_x = view.left + ((view.right - view.left) - geometry.bounds[2] * scale) / 2.0
    offset_y = view.top + ((view.bottom - view.top) + geometry.bounds[3] * scale) / 2.0
    transform = ModelTransform(scale, offset_x, offset_y)
    dimensions, lines, texts, unplaced = [], [], [], []
    counts = {"top": 0, "bottom": 0, "left": 0, "right": 0, "note": 0}
    limits = {"top": 6, "bottom": 6, "left": 6, "right": 6, "note": 8}
    for intent in sorted(intents, key=lambda item: (-item.priority, item.intent_id)):
        band = intent.preferred_band
        if counts.get(band, 0) >= limits.get(band, 0):
            unplaced.append(intent)
            continue
        dimension, line, text = _place(intent, view, transform, counts.get(band, 0))
        obstacle = dimension.text_box if dimension else text.box
        if (
            obstacle.left < 12
            or obstacle.right > PAGE_WIDTH - 12
            or obstacle.top < 12
            or obstacle.bottom >= TITLE_BLOCK_TOP
        ):
            unplaced.append(intent)
            continue
        existing_boxes = [item.text_box for item in dimensions] + [item.box for item in texts]
        if any(obstacle.intersects(existing, 1.0) for existing in existing_boxes):
            unplaced.append(intent)
            continue
        if dimension:
            dimensions.append(dimension)
        if line:
            lines.append(line)
        if text:
            texts.append(text)
        counts[band] = counts.get(band, 0) + 1
    return PartDrawingLayout(
        PAGE_WIDTH, PAGE_HEIGHT, scale, view, transform, tuple(dimensions), tuple(lines), tuple(texts),
        {"part_position": snapshot.part_position, "name": snapshot.name, "material": snapshot.material, "thickness": str(snapshot.thickness), "quantity": str(quantity), "scale": f"1:{1 / scale:g}"},
        DrawingStatus.REVIEW_REQUIRED if unplaced else DrawingStatus.OK,
        0, tuple(unplaced),
    )


def _fit_scale(width, height, view):
    available_width, available_height = view.right - view.left, view.bottom - view.top
    return next((scale for scale in STANDARD_SCALES if width * scale <= available_width and height * scale <= available_height), STANDARD_SCALES[-1])


def _place(intent, view, transform, index):
    x, y = _band_position(intent.preferred_band, view, index)
    if _is_placeable_linear(intent):
        kind = (
            PlacedDimensionKind.LINEAR_VERTICAL
            if intent.preferred_band in {"left", "right"}
            else PlacedDimensionKind.LINEAR_HORIZONTAL
        )
        points = _linear_source_points(intent, transform, kind)
        rotation = 90.0 if kind == PlacedDimensionKind.LINEAR_VERTICAL else 0.0
        display_text = _dimension_display_text(intent)
        return (
            PlacedDimension(
                intent.intent_id,
                kind,
                points,
                (x, y),
                float(intent.model_value),
                display_text,
                rotation,
                _dimension_text_box(x, y, display_text, 2.5, rotation),
                evidence_codes=intent.evidence_codes,
            ),
            None,
            None,
        )
    if (
        intent.kind in {DimensionKind.DIAMETER, DimensionKind.RADIUS}
        and intent.anchors
        and intent.model_value is not None
    ):
        center = transform.point(intent.anchors[0])
        paper_radius = float(intent.model_value) * transform.scale
        if intent.kind == DimensionKind.DIAMETER:
            paper_radius /= 2.0
        x = center[0] + paper_radius + 12.0
        y = center[1] - paper_radius - 8.0
        kind = PlacedDimensionKind(intent.kind.value)
        display_text = _dimension_display_text(intent)
        return (
            PlacedDimension(
                intent.intent_id,
                kind,
                (center,),
                (x, y),
                float(intent.model_value),
                display_text,
                0.0,
                _dimension_text_box(x, y, display_text, 2.5, 0.0),
                paper_radius,
                intent.evidence_codes,
            ),
            None,
            None,
        )
    height = 3.5
    width = _text_width(intent.text, height)
    text = DrawingText(
        x,
        y,
        intent.text,
        height,
        "ANNOTATION",
        DrawingRect(x - width / 2, y - height, x + width / 2, y + height),
    )
    return None, None, text


def _is_placeable_linear(intent):
    return (
        len(intent.anchors) >= 2
        and intent.model_value is not None
        and intent.kind
        in {
            DimensionKind.OVERALL,
            DimensionKind.DATUM_X,
            DimensionKind.DATUM_Y,
            DimensionKind.LENGTH,
            DimensionKind.WIDTH,
        }
    )


def _linear_source_points(intent, transform, kind):
    points = tuple(transform.point(anchor) for anchor in intent.anchors)
    axis = 1 if kind == PlacedDimensionKind.LINEAR_VERTICAL else 0
    return min(points, key=lambda point: point[axis]), max(points, key=lambda point: point[axis])


def _band_position(band, view, index):
    if band == "top":
        return (view.left + view.right) / 2, view.top - 8 - index * 7
    if band == "right":
        return view.right + 12 + index * 9, (view.top + view.bottom) / 2
    if band == "bottom":
        return (view.left + view.right) / 2, view.bottom + 10 + index * 7
    if band == "left":
        return view.left - 30 - index * 9, (view.top + view.bottom) / 2
    return view.left, 232 + index * 7


def _dimension_text_box(x, y, text, height, rotation):
    width = _text_width(text, height)
    if rotation % 180 == 90:
        width, height = height * 2, width / 2
    return DrawingRect(x - width / 2, y - height, x + width / 2, y + height)


def _dimension_display_text(intent):
    text = PART_CAD_DIMENSION_STYLE_V1.format_measurement(intent.model_value)
    if intent.kind == DimensionKind.DIAMETER:
        return f"DIA{text}"
    if intent.kind == DimensionKind.RADIUS:
        return f"R{text}"
    return text


def _text_width(text, height):
    ascii_count = sum(ord(char) < 128 for char in text)
    return max(height * 1.6, ascii_count * height * 0.52 + (len(text) - ascii_count) * height * 0.92)
