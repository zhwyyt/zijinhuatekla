from __future__ import annotations

from dataclasses import dataclass

from .contracts import DrawingStatus


PAGE_WIDTH = 420.0
PAGE_HEIGHT = 297.0
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


@dataclass(frozen=True)
class PartDrawingLayout:
    page_width: float
    page_height: float
    scale: float
    view_rect: DrawingRect
    model_transform: ModelTransform
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
    lines, texts, unplaced = [], [], []
    counts = {"top": 0, "bottom": 0, "left": 0, "right": 0, "note": 0}
    limits = {"top": 6, "bottom": 6, "left": 6, "right": 6, "note": 8}
    for intent in sorted(intents, key=lambda item: (-item.priority, item.intent_id)):
        band = intent.preferred_band
        if counts.get(band, 0) >= limits.get(band, 0):
            unplaced.append(intent)
            continue
        line, text = _place(intent, view, counts.get(band, 0))
        if text.box.left < 12 or text.box.right > PAGE_WIDTH - 12 or text.box.top < 12 or text.box.bottom > PAGE_HEIGHT - 12:
            unplaced.append(intent)
            continue
        if any(text.box.intersects(existing.box, 1.0) for existing in texts):
            unplaced.append(intent)
            continue
        if line:
            lines.append(line)
        texts.append(text)
        counts[band] = counts.get(band, 0) + 1
    return PartDrawingLayout(
        PAGE_WIDTH, PAGE_HEIGHT, scale, view, transform, tuple(lines), tuple(texts),
        {"part_position": snapshot.part_position, "name": snapshot.name, "material": snapshot.material, "thickness": str(snapshot.thickness), "quantity": str(quantity), "scale": f"1:{1 / scale:g}"},
        DrawingStatus.REVIEW_REQUIRED if unplaced else DrawingStatus.OK,
        0, tuple(unplaced),
    )


def _fit_scale(width, height, view):
    available_width, available_height = view.right - view.left, view.bottom - view.top
    return next((scale for scale in STANDARD_SCALES if width * scale <= available_width and height * scale <= available_height), STANDARD_SCALES[-1])


def _place(intent, view, index):
    height = 3.5
    if intent.preferred_band == "top":
        x, y = (view.left + view.right) / 2, view.top - 8 - index * 7
        line = DrawingLine(view.left, y + 2, view.right, y + 2, "DIMENSION")
    elif intent.preferred_band == "right":
        x, y = view.right + 12 + index * 9, (view.top + view.bottom) / 2
        line = DrawingLine(x - 3, view.top, x - 3, view.bottom, "DIMENSION")
    elif intent.preferred_band == "bottom":
        x, y = (view.left + view.right) / 2, view.bottom + 10 + index * 7
        line = DrawingLine(view.left, y - 2, view.right, y - 2, "DIMENSION")
    elif intent.preferred_band == "left":
        x, y = view.left - 30 - index * 9, (view.top + view.bottom) / 2
        line = DrawingLine(x + 20, view.top, x + 20, view.bottom, "DIMENSION")
    else:
        x, y = view.left, 232 + index * 7
        line = None
    width = _text_width(intent.text, height)
    return line, DrawingText(x, y, intent.text, height, "ANNOTATION", DrawingRect(x - width / 2, y - height, x + width / 2, y + height))


def _text_width(text, height):
    ascii_count = sum(ord(char) < 128 for char in text)
    return max(height * 1.6, ascii_count * height * 0.52 + (len(text) - ascii_count) * height * 0.92)
