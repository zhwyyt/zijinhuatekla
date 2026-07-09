from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class AnnotationKind(str, Enum):
    OVERALL_DIMENSION = "OVERALL_DIMENSION"
    SECTION_DIMENSION = "SECTION_DIMENSION"
    LOCAL_DIMENSION = "LOCAL_DIMENSION"
    THICKNESS_CALLOUT = "THICKNESS_CALLOUT"
    PART_MARK = "PART_MARK"
    FIXTURE_NOTE = "FIXTURE_NOTE"
    STAGE_NOTE = "STAGE_NOTE"
    ORIENTATION_MARK = "ORIENTATION_MARK"
    WARNING = "WARNING"
    DETAIL_REQUEST = "DETAIL_REQUEST"


class LayoutStatus(str, Enum):
    OK = "OK"
    OVERFLOW = "OVERFLOW"
    NEEDS_DETAIL_VIEW = "NEEDS_DETAIL_VIEW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class Rect:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def left(self) -> float:
        return min(self.x1, self.x2)

    @property
    def right(self) -> float:
        return max(self.x1, self.x2)

    @property
    def top(self) -> float:
        return min(self.y1, self.y2)

    @property
    def bottom(self) -> float:
        return max(self.y1, self.y2)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0

    def intersects(self, other: "Rect", padding: float = 0.0) -> bool:
        return (
            self.left - padding < other.right
            and self.right + padding > other.left
            and self.top - padding < other.bottom
            and self.bottom + padding > other.top
        )

    def to_list(self) -> list[float]:
        return [self.left, self.top, self.right, self.bottom]


@dataclass(frozen=True)
class PartAnchor:
    part_id: str
    x: float
    y: float
    label: str = ""


@dataclass(frozen=True)
class ProjectionScene:
    view_id: str
    drawing_bounds: Rect
    main_view_bounds: Rect
    model_length: float
    model_width: float
    model_thickness: float
    source_part_id: str
    source_part_position: str
    source_profile: str
    source_name: str
    fixture_face: str = ""
    anchors: dict[str, PartAnchor] = field(default_factory=dict)


@dataclass(frozen=True)
class AnnotationIntent:
    id: str
    kind: AnnotationKind
    priority: int
    text: str
    target_anchor: str = ""
    model_value: float | None = None
    source_part_ids: tuple[str, ...] = ()
    evidence_codes: tuple[str, ...] = ()
    allow_merge: bool = False
    fallback_policy: str = "review_required"

    def copy_with(self, **changes: Any) -> "AnnotationIntent":
        return replace(self, **changes)


@dataclass(frozen=True)
class LayoutLine:
    id: str
    intent_id: str
    annotation_kind: AnnotationKind
    x1: float
    y1: float
    x2: float
    y2: float
    role: str = "annotation"


@dataclass(frozen=True)
class LayoutText:
    id: str
    intent_id: str
    annotation_kind: AnnotationKind
    text: str
    x: float
    y: float
    box: Rect
    height: float = 7.2
    align: str = "left"


@dataclass(frozen=True)
class AnnotationLayout:
    status: LayoutStatus
    lines: list[LayoutLine]
    texts: list[LayoutText]
    unplaced_items: list[AnnotationIntent]
    collision_count: int = 0
    debug_boxes: list[Rect] = field(default_factory=list)


def build_u_stage_annotation_intents(scene: ProjectionScene) -> list[AnnotationIntent]:
    source_part_ids = (scene.source_part_id,) if scene.source_part_id else ()
    part_label = _source_part_label(scene)
    return [
        AnnotationIntent(
            id="overall-length",
            kind=AnnotationKind.OVERALL_DIMENSION,
            priority=100,
            text=_format_model_number(scene.model_length),
            target_anchor="main_view.length",
            model_value=scene.model_length,
            source_part_ids=source_part_ids,
            evidence_codes=("TEKLA_SOLID_EXTENT_LENGTH",),
            fallback_policy="review_required",
        ),
        AnnotationIntent(
            id="section-width",
            kind=AnnotationKind.SECTION_DIMENSION,
            priority=95,
            text=_format_model_number(scene.model_width),
            target_anchor="main_view.section_width",
            model_value=scene.model_width,
            source_part_ids=source_part_ids,
            evidence_codes=("TEKLA_SOLID_EXTENT_WIDTH",),
            fallback_policy="review_required",
        ),
        AnnotationIntent(
            id="thickness-callout",
            kind=AnnotationKind.THICKNESS_CALLOUT,
            priority=90,
            text=f"t={_format_model_number(scene.model_thickness)}",
            target_anchor="main_view.wall_thickness",
            model_value=scene.model_thickness,
            source_part_ids=source_part_ids,
            evidence_codes=("BOX_PROFILE_THICKNESS",),
            fallback_policy="review_required",
        ),
        AnnotationIntent(
            id="source-part-mark",
            kind=AnnotationKind.PART_MARK,
            priority=85,
            text=part_label,
            target_anchor="source_part",
            source_part_ids=source_part_ids,
            evidence_codes=("TEKLA_PART_POSITION", "TEKLA_PROFILE", "TEKLA_NAME"),
            allow_merge=True,
            fallback_policy="detail_view",
        ),
        AnnotationIntent(
            id="fixture-note",
            kind=AnnotationKind.FIXTURE_NOTE,
            priority=80,
            text=f"胎架基准：{scene.fixture_face or '未指定'}",
            target_anchor="fixture_face",
            source_part_ids=source_part_ids,
            evidence_codes=("FIXTURE_FACE",),
            fallback_policy="review_required",
        ),
        AnnotationIntent(
            id="stage-note",
            kind=AnnotationKind.STAGE_NOTE,
            priority=75,
            text="阶段：虚拟U形组立（底板+两侧板，盖板未装）",
            target_anchor="stage_note",
            source_part_ids=source_part_ids,
            evidence_codes=("BOX_PROFILE_VIRTUAL_U_STAGE",),
            fallback_policy="review_required",
        ),
    ]


def layout_annotation_intents(scene: ProjectionScene, intents: list[AnnotationIntent]) -> AnnotationLayout:
    lines: list[LayoutLine] = []
    texts: list[LayoutText] = []
    unplaced_items: list[AnnotationIntent] = []
    ordered = sorted(enumerate(intents), key=lambda item: (-item[1].priority, item[0]))
    part_mark_count = sum(1 for _, intent in ordered if intent.kind == AnnotationKind.PART_MARK)
    placed_part_marks = 0
    max_part_marks = 6

    for _, intent in ordered:
        if intent.kind == AnnotationKind.OVERALL_DIMENSION:
            _place_overall_dimension(scene, intent, lines, texts)
        elif intent.kind == AnnotationKind.SECTION_DIMENSION:
            _place_section_dimension(scene, intent, lines, texts)
        elif intent.kind == AnnotationKind.THICKNESS_CALLOUT:
            _place_thickness_callout(scene, intent, lines, texts)
        elif intent.kind == AnnotationKind.PART_MARK:
            if placed_part_marks >= max_part_marks:
                unplaced_items.append(intent)
                continue
            _place_part_mark(scene, intent, placed_part_marks, lines, texts)
            placed_part_marks += 1
        elif intent.kind == AnnotationKind.FIXTURE_NOTE:
            _place_fixture_note(scene, intent, lines, texts)
        elif intent.kind == AnnotationKind.STAGE_NOTE:
            _place_stage_note(scene, intent, texts)
        else:
            if not _place_generic_note(scene, intent, len(texts), texts):
                unplaced_items.append(intent)

    collision_count = _count_text_collisions(scene, texts)
    overflow_count = sum(1 for text in texts if not _contains(scene.drawing_bounds, text.box))
    if unplaced_items and part_mark_count > max_part_marks:
        status = LayoutStatus.NEEDS_DETAIL_VIEW
    elif overflow_count:
        status = LayoutStatus.OVERFLOW
    elif collision_count:
        status = LayoutStatus.REVIEW_REQUIRED
    else:
        status = LayoutStatus.OK
    return AnnotationLayout(
        status=status,
        lines=lines,
        texts=texts,
        unplaced_items=unplaced_items,
        collision_count=collision_count,
        debug_boxes=[text.box for text in texts],
    )


def layout_to_jsonable(layout: AnnotationLayout) -> dict[str, Any]:
    placed_items: list[dict[str, Any]] = []
    for line in layout.lines:
        placed_items.append(
            {
                "kind": "LINE",
                "id": line.id,
                "intent_id": line.intent_id,
                "annotation_kind": line.annotation_kind.value,
                "start": [line.x1, line.y1],
                "end": [line.x2, line.y2],
                "role": line.role,
            }
        )
    for text in layout.texts:
        placed_items.append(
            {
                "kind": "TEXT",
                "id": text.id,
                "intent_id": text.intent_id,
                "annotation_kind": text.annotation_kind.value,
                "text": text.text,
                "position": [text.x, text.y],
                "box": text.box.to_list(),
                "height": text.height,
                "align": text.align,
            }
        )
    return {
        "layout_status": layout.status.value,
        "collision_count": layout.collision_count,
        "placed_items": placed_items,
        "unplaced_items": [_intent_to_jsonable(intent) for intent in layout.unplaced_items],
        "debug_boxes": [box.to_list() for box in layout.debug_boxes],
    }


def _place_overall_dimension(
    scene: ProjectionScene,
    intent: AnnotationIntent,
    lines: list[LayoutLine],
    texts: list[LayoutText],
) -> None:
    bounds = scene.main_view_bounds
    y = max(scene.drawing_bounds.top + 48.0, bounds.top - 24.0)
    tick = 4.0
    _add_line(lines, intent, bounds.left, y, bounds.right, y, "overall_dimension")
    _add_line(lines, intent, bounds.left, bounds.top, bounds.left, y + tick, "extension")
    _add_line(lines, intent, bounds.right, bounds.top, bounds.right, y + tick, "extension")
    _add_line(lines, intent, bounds.left - tick, y - tick, bounds.left + tick, y + tick, "tick")
    _add_line(lines, intent, bounds.right - tick, y - tick, bounds.right + tick, y + tick, "tick")
    _add_text(texts, intent, intent.text, bounds.center_x, y - 11.0, height=7.2, align="center")


def _place_section_dimension(
    scene: ProjectionScene,
    intent: AnnotationIntent,
    lines: list[LayoutLine],
    texts: list[LayoutText],
) -> None:
    bounds = scene.main_view_bounds
    x = min(scene.drawing_bounds.right - 38.0, bounds.right + 22.0)
    tick = 4.0
    _add_line(lines, intent, x, bounds.top, x, bounds.bottom, "section_dimension")
    _add_line(lines, intent, bounds.right, bounds.top, x - tick, bounds.top, "extension")
    _add_line(lines, intent, bounds.right, bounds.bottom, x - tick, bounds.bottom, "extension")
    _add_line(lines, intent, x - tick, bounds.top - tick, x + tick, bounds.top + tick, "tick")
    _add_line(lines, intent, x - tick, bounds.bottom + tick, x + tick, bounds.bottom - tick, "tick")
    _add_text(texts, intent, intent.text, x + 12.0, bounds.center_y, height=7.2, align="left")


def _place_thickness_callout(
    scene: ProjectionScene,
    intent: AnnotationIntent,
    lines: list[LayoutLine],
    texts: list[LayoutText],
) -> None:
    bounds = scene.main_view_bounds
    label_x = min(scene.drawing_bounds.right - 36.0, bounds.right + 30.0)
    label_y = bounds.top + 28.0
    target_x = bounds.right - min(16.0, bounds.width / 8.0)
    target_y = bounds.top + 15.0
    elbow_x = min(scene.drawing_bounds.right - 46.0, bounds.right + 14.0)
    _add_line(lines, intent, target_x, target_y, elbow_x, label_y, "leader")
    _add_line(lines, intent, elbow_x, label_y, label_x - 3.0, label_y, "leader")
    _add_text(texts, intent, intent.text, label_x, label_y, height=7.2, align="left")


def _place_part_mark(
    scene: ProjectionScene,
    intent: AnnotationIntent,
    index: int,
    lines: list[LayoutLine],
    texts: list[LayoutText],
) -> None:
    bounds = scene.main_view_bounds
    anchor = scene.anchors.get(intent.target_anchor) or scene.anchors.get("source_part")
    anchor_x = anchor.x if anchor else bounds.center_x
    anchor_y = anchor.y if anchor else bounds.center_y
    row = index // 2
    side = index % 2
    label_y = bounds.bottom + 24.0 + row * 13.0
    label_x = bounds.left if side == 0 else max(bounds.center_x + 14.0, bounds.right - 185.0)
    line_end_x = label_x + min(_estimate_text_width(intent.text, 7.2), 150.0)
    _add_line(lines, intent, anchor_x, anchor_y, line_end_x, label_y, "leader")
    _add_text(texts, intent, intent.text, label_x, label_y, height=7.2, align="left")


def _place_fixture_note(
    scene: ProjectionScene,
    intent: AnnotationIntent,
    lines: list[LayoutLine],
    texts: list[LayoutText],
) -> None:
    bounds = scene.main_view_bounds
    x = bounds.left
    y = bounds.top - 11.0
    _add_line(lines, intent, bounds.left, bounds.top, bounds.left + 26.0, y, "fixture_note")
    _add_text(texts, intent, intent.text, x, y, height=7.2, align="left")


def _place_stage_note(scene: ProjectionScene, intent: AnnotationIntent, texts: list[LayoutText]) -> None:
    bounds = scene.main_view_bounds
    x = bounds.left
    y = max(scene.drawing_bounds.top + 24.0, bounds.top - 52.0)
    _add_text(texts, intent, intent.text, x, y, height=7.2, align="left")


def _place_generic_note(
    scene: ProjectionScene,
    intent: AnnotationIntent,
    index: int,
    texts: list[LayoutText],
) -> bool:
    y = scene.main_view_bounds.bottom + 28.0 + index * 11.0
    if y > scene.drawing_bounds.bottom - 12.0:
        return False
    _add_text(texts, intent, intent.text, scene.main_view_bounds.left, y, height=7.2, align="left")
    return True


def _add_line(
    lines: list[LayoutLine],
    intent: AnnotationIntent,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    role: str,
) -> None:
    lines.append(
        LayoutLine(
            id=f"{intent.id}-line-{len(lines) + 1}",
            intent_id=intent.id,
            annotation_kind=intent.kind,
            x1=float(x1),
            y1=float(y1),
            x2=float(x2),
            y2=float(y2),
            role=role,
        )
    )


def _add_text(
    texts: list[LayoutText],
    intent: AnnotationIntent,
    text: str,
    x: float,
    y: float,
    height: float,
    align: str,
) -> None:
    width = _estimate_text_width(text, height)
    if align == "center":
        left = x - width / 2.0
    elif align == "right":
        left = x - width
    else:
        left = x
    box = Rect(left, y - height / 2.0, left + width, y + height / 2.0)
    texts.append(
        LayoutText(
            id=f"{intent.id}-text-{len(texts) + 1}",
            intent_id=intent.id,
            annotation_kind=intent.kind,
            text=text,
            x=float(x),
            y=float(y),
            box=box,
            height=height,
            align=align,
        )
    )


def _count_text_collisions(scene: ProjectionScene, texts: list[LayoutText]) -> int:
    count = 0
    for text in texts:
        if text.box.intersects(scene.main_view_bounds):
            count += 1
    for index, left in enumerate(texts):
        for right in texts[index + 1 :]:
            if left.box.intersects(right.box, padding=1.0):
                count += 1
    return count


def _contains(container: Rect, item: Rect) -> bool:
    return (
        item.left >= container.left
        and item.right <= container.right
        and item.top >= container.top
        and item.bottom <= container.bottom
    )


def _intent_to_jsonable(intent: AnnotationIntent) -> dict[str, Any]:
    return {
        "id": intent.id,
        "kind": intent.kind.value,
        "priority": intent.priority,
        "text": intent.text,
        "target_anchor": intent.target_anchor,
        "model_value": intent.model_value,
        "source_part_ids": list(intent.source_part_ids),
        "evidence_codes": list(intent.evidence_codes),
        "allow_merge": intent.allow_merge,
        "fallback_policy": intent.fallback_policy,
    }


def _source_part_label(scene: ProjectionScene) -> str:
    anchor = scene.anchors.get("source_part")
    if anchor and anchor.label:
        return anchor.label
    return " / ".join(
        value
        for value in (scene.source_part_position, scene.source_profile, scene.source_name)
        if value
    )


def _format_model_number(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def _estimate_text_width(text: str, height: float) -> float:
    ascii_count = sum(1 for char in text if ord(char) < 128)
    wide_count = len(text) - ascii_count
    return max(height * 1.6, ascii_count * height * 0.52 + wide_count * height * 0.92)
