from __future__ import annotations

from dataclasses import dataclass, field
import io
import math
import re
from typing import Any

import ezdxf

from zijinhua_tekla.reports.annotation_layout import AnnotationKind, AnnotationLayout


def build_box_assembly_drawing_steps_dxf(payload: dict[str, Any]) -> str:
    member_id = str(payload.get("member_id") or "")
    steps = [step for step in payload.get("steps", []) if isinstance(step, dict)]
    part_catalog = _build_part_catalog(payload, steps)
    layout = _build_layout(payload, steps, part_catalog)
    state = _AssemblyState()
    writer = _DxfWriter()
    writer.start()

    requested_step_no = str(payload.get("render_step_no") or "")
    page_index = 0
    for index, step in enumerate(steps):
        state.apply_step(step, part_catalog)
        if requested_step_no and str(step.get("step_no") or "") != requested_step_no:
            continue
        new_ids = set(_ids(step.get("new_part_ids")))
        detail_count = len(_detail_parts_for_step(step, state, part_catalog, new_ids))
        sheet_height = layout.sheet_height_for(len(state.installed_part_ids), detail_count)
        page_column = page_index % layout.sheet_columns
        page_row = page_index // layout.sheet_columns
        origin_x = page_column * (layout.sheet_width + layout.sheet_gap)
        origin_y = -page_row * (sheet_height + layout.sheet_gap)
        writer.push_offset(origin_x, origin_y)
        _draw_step(writer, step, member_id, state, part_catalog, layout, sheet_height, sheet_height, detail_count)
        writer.pop_offset()
        page_index += 1
        if requested_step_no:
            break

    if requested_step_no and page_index == 0 and steps:
        fallback_state = _AssemblyState()
        for step in steps:
            fallback_state.apply_step(step, part_catalog)
        step = steps[-1]
        new_ids = set(_ids(step.get("new_part_ids")))
        detail_count = len(_detail_parts_for_step(step, fallback_state, part_catalog, new_ids))
        sheet_height = layout.sheet_height_for(len(fallback_state.installed_part_ids), detail_count)
        _draw_step(writer, step, member_id, fallback_state, part_catalog, layout, sheet_height, sheet_height, detail_count)

    writer.finish()
    return writer.content()


@dataclass(frozen=True)
class _ProjectionArc:
    center_x: float
    center_y: float
    radius: float
    start_angle: float
    end_angle: float


@dataclass(frozen=True)
class _PartSnapshot:
    part_id: str
    part_position: str
    profile: str
    name: str
    material: str = ""
    station_start: float = 0.0
    station_end: float = 0.0
    face: str = ""
    requires_detail: bool = False
    bolt_hole_count: int = 0
    bolt_diameter: float = 0.0
    welds: list[dict[str, Any]] = field(default_factory=list)
    projection_edges: tuple[tuple[float, float, float, float], ...] = ()
    projection_arcs: tuple[_ProjectionArc, ...] = ()

    @property
    def quantity_key(self) -> tuple[str, str, str, str]:
        return (self.part_position, self.profile, self.name, self.material)


@dataclass(frozen=True)
class _BomRow:
    part_position: str
    profile: str
    name: str
    material: str
    quantity: int
    part_ids: tuple[str, ...]

    @property
    def label(self) -> str:
        values = [self.part_position, self.profile]
        return " / ".join(value for value in values if value)


class _AssemblyState:
    def __init__(self) -> None:
        self.installed_part_ids: list[str] = []

    def apply_step(self, step: dict[str, Any], part_catalog: dict[str, _PartSnapshot]) -> None:
        for part_id in _ids(step.get("visible_part_ids")) + _ids(step.get("new_part_ids")):
            if part_id in part_catalog and part_id not in self.installed_part_ids:
                self.installed_part_ids.append(part_id)


class _Layout:
    sheet_width = 599.0
    base_sheet_height = 420.0
    sheet_gap = 28.0
    sheet_columns = 3
    header_height = 0.0
    view_left = 145.0
    view_top_offset = 64.0
    view_height = 285.0
    view_width = 92.0
    body_width = 34.0
    part_mark_left = 225.0
    detail_left = 330.0
    bom_left = 390.0
    row_height = 7.0

    def __init__(
        self,
        station_start: float,
        station_end: float,
        segments: list[dict[str, Any]],
        bend_joints: list[dict[str, Any]],
        projection_bounds: tuple[float, float, float, float] | None,
    ) -> None:
        self.station_start = station_start
        self.station_end = station_end
        self.segments = segments
        self.bend_joints = bend_joints
        self.projection_bounds = projection_bounds

    def sheet_height_for(self, installed_count: int, detail_count: int) -> float:
        return self.base_sheet_height


@dataclass(frozen=True)
class _ProjectionTransform:
    scale: float
    mid_x: float
    mid_y: float
    draw_mid_x: float
    draw_mid_y: float

    def point(self, x: float, y: float) -> tuple[float, float]:
        return self.draw_mid_x + (x - self.mid_x) * self.scale, self.draw_mid_y + (y - self.mid_y) * self.scale


def _draw_annotation_layout(writer: "_DxfWriter", layout: AnnotationLayout) -> None:
    for line in layout.lines:
        layer = _annotation_layout_layer(line.annotation_kind, line.role)
        writer.line(line.x1, line.y1, line.x2, line.y2, layer, color=_annotation_layout_color(layer))
    for text in layout.texts:
        layer = _annotation_layout_layer(text.annotation_kind, "TEXT")
        writer.text(_annotation_layout_text_x(text), text.y, text.height, text.text, layer, color=_annotation_layout_color(layer))


def _annotation_layout_text_x(text: Any) -> float:
    box = getattr(text, "box", None)
    if box is not None and str(getattr(text, "align", "left") or "left").lower() in {"center", "right"}:
        return float(box.left)
    return float(text.x)

def _annotation_layout_layer(kind: AnnotationKind, role: str) -> str:
    role_text = str(role or "").upper()
    if kind in {
        AnnotationKind.OVERALL_DIMENSION,
        AnnotationKind.SECTION_DIMENSION,
        AnnotationKind.LOCAL_DIMENSION,
        AnnotationKind.THICKNESS_CALLOUT,
    } or "DIMENSION" in role_text:
        return "Z-DIMENSIONS"
    if kind == AnnotationKind.PART_MARK:
        return "PartMark"
    return "文本"


def _annotation_layout_color(layer: str) -> int:
    if layer == "Z-DIMENSIONS":
        return 1
    if layer == "PartMark":
        return 3
    return 7


def _draw_step(
    writer: "_DxfWriter",
    step: dict[str, Any],
    member_id: str,
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    sheet_height: float,
    detail_count: int,
) -> None:
    writer.rectangle(0, top_y, layout.sheet_width, top_y - sheet_height, "DrawingSheet", color=5)
    writer.rectangle(18, top_y - 18, layout.sheet_width - 18, top_y - sheet_height + 18, "DrawingSheet", color=7)

    step_no = step.get("step_no", "")
    step_type = str(step.get("step_type") or "")
    title = str(step.get("title") or "")
    writer.text(28, top_y - 13, 4.0, f"{member_id} BOX 工序图", "文本", color=3)
    writer.text(28, top_y - 24, 3.0, f"STEP {step_no} {step_type} {title}", "文本", color=3)
    writer.text(28, top_y - 33, 2.2, f"MEMBER {member_id}", "文本", color=3)
    writer.text(layout.sheet_width - 118, top_y - sheet_height + 38, 2.6, "BOX PROCESS DRAWING", "文本", color=3)
    writer.text(layout.sheet_width - 118, top_y - sheet_height + 27, 2.2, f"{member_id}-{step_no}", "文本", color=7)

    if layout.bend_joints:
        writer.text(layout.sheet_width - 210, top_y - 30, 2.0, f"BEND STRATEGY {_bend_strategy(layout.bend_joints)}", "文本", color=3)

    new_ids = set(_ids(step.get("new_part_ids")))
    _draw_main_view(writer, step, state, part_catalog, layout, top_y, new_ids)
    _draw_dimension_chains(writer, step, state, part_catalog, layout, top_y, sheet_height, new_ids)
    _draw_part_marks(writer, state, part_catalog, layout, top_y, new_ids)
    _draw_weld_notes(writer, state, part_catalog, layout, top_y, new_ids)
    _draw_detail_views(writer, step, state, part_catalog, layout, top_y, new_ids)
    _draw_bom_table(writer, step, state, part_catalog, layout, top_y, sheet_height, new_ids, detail_count)
    _draw_stage_note(writer, step, state, layout, top_y, sheet_height)


def _draw_main_view(
    writer: "_DxfWriter",
    step: dict[str, Any],
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    new_ids: set[str],
) -> None:
    view_top = top_y - layout.view_top_offset
    view_bottom = view_top - layout.view_height
    writer.text(layout.view_left - 24, view_top + 12, 2.0, "MAIN VIEW", "文本", color=3)

    installed = _installed_parts(state, part_catalog)
    projection_transform = _projection_transform(layout, top_y)
    if projection_transform and any(part.projection_edges or part.projection_arcs for part in installed):
        writer.text(layout.view_left - 24, view_top + 5, 1.8, "TRUE PROJECTION", "文本", color=3)
        for part in installed:
            color = 1 if part.part_id in new_ids else 7
            _draw_part_true_projection(writer, part, projection_transform, color)
        return

    if layout.segments:
        _draw_true_segment_projection(writer, layout, view_top)
    else:
        left = layout.view_left
        right = layout.view_left + layout.body_width
        writer.line(left, view_top, left, view_bottom, "Part", color=7)
        writer.line(right, view_top, right, view_bottom, "Part", color=7)

    for part in installed:
        color = 1 if part.part_id in new_ids else 7
        if layout.segments:
            _draw_part_projection(writer, part, layout, view_top, color)
        else:
            y1 = _station_to_y(part.station_start, layout, view_top)
            y2 = _station_to_y(part.station_end, layout, view_top)
            if abs(y1 - y2) < 2.5:
                y2 = y1 - 2.5
            x1, x2 = _part_lane(part, layout)
            writer.rectangle(x1, y1, x2, y2, "Part", color=color)


def _projection_transform(layout: _Layout, top_y: float) -> _ProjectionTransform | None:
    if layout.projection_bounds is None:
        return None
    min_x, min_y, max_x, max_y = layout.projection_bounds
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min(layout.view_width / span_x, layout.view_height / span_y) * 0.96
    view_top = top_y - layout.view_top_offset
    view_bottom = view_top - layout.view_height
    return _ProjectionTransform(
        scale=scale,
        mid_x=(min_x + max_x) / 2.0,
        mid_y=(min_y + max_y) / 2.0,
        draw_mid_x=layout.view_left + layout.view_width / 2.0,
        draw_mid_y=(view_top + view_bottom) / 2.0,
    )


def _draw_part_true_projection(writer: "_DxfWriter", part: _PartSnapshot, transform: _ProjectionTransform, color: int) -> None:
    for x1, y1, x2, y2 in part.projection_edges:
        sx, sy = transform.point(x1, y1)
        ex, ey = transform.point(x2, y2)
        writer.line(sx, sy, ex, ey, "Part", color=color)
    for arc in part.projection_arcs:
        cx, cy = transform.point(arc.center_x, arc.center_y)
        radius = arc.radius * transform.scale
        writer.arc(cx, cy, radius, arc.start_angle, arc.end_angle, "Part", color=color)
        writer.text(cx + radius + 3.0, cy, 1.8, f"R{_format_length(arc.radius)}", "Z-DIMENSIONS", color=1)


def _draw_true_segment_projection(writer: "_DxfWriter", layout: _Layout, view_top: float) -> None:
    half_width = layout.body_width / 2.0
    center_x = layout.view_left + half_width
    start_offsets = _segment_offsets(layout)
    for segment in layout.segments:
        start = _float(segment.get("station_start"))
        end = _float(segment.get("station_end"))
        angle = math.radians(_float(segment.get("angle_deg")))
        x_start = center_x + start_offsets.get(id(segment), 0.0)
        x_end = x_start + math.tan(angle) * (end - start) * _station_scale(layout)
        y_start = _station_to_y(start, layout, view_top)
        y_end = _station_to_y(end, layout, view_top)
        writer.line(x_start - half_width, y_start, x_end - half_width, y_end, "Part", color=7)
        writer.line(x_start + half_width, y_start, x_end + half_width, y_end, "Part", color=7)

    for joint in layout.bend_joints:
        station = _float(joint.get("station"))
        label = str(joint.get("label") or "")
        y = _station_to_y(station, layout, view_top)
        center_x = _segment_center_x_at_station(layout, station)
        half_width = layout.body_width / 2.0
        writer.line(center_x - half_width - 6, y + 1.4, center_x + half_width + 6, y + 1.4, "Part", color=7)
        writer.line(center_x - half_width - 6, y - 1.4, center_x + half_width + 6, y - 1.4, "Part", color=7)
        _draw_section_marker(writer, center_x + half_width + 17, y, label)
        bend_angle = _float(joint.get("bend_angle_deg"))
        if bend_angle:
            writer.text(center_x + half_width + 28, y + 6, 1.9, f"BEND {_format_length(bend_angle)}°", "Section", color=6)


def _draw_part_projection(writer: "_DxfWriter", part: _PartSnapshot, layout: _Layout, view_top: float, color: int) -> None:
    left_offset, right_offset = _part_lane_offsets(part, layout)
    for segment in layout.segments:
        segment_start = _float(segment.get("station_start"))
        segment_end = _float(segment.get("station_end"))
        start = max(part.station_start, segment_start)
        end = min(part.station_end, segment_end)
        if end <= start:
            continue
        y1 = _station_to_y(start, layout, view_top)
        y2 = _station_to_y(end, layout, view_top)
        if abs(y1 - y2) < 2.5:
            y2 = y1 - 2.5
        x1 = _segment_center_x_at_station(layout, start)
        x2 = _segment_center_x_at_station(layout, end)
        writer.line(x1 + left_offset, y1, x2 + left_offset, y2, "Part", color=color)
        writer.line(x1 + right_offset, y1, x2 + right_offset, y2, "Part", color=color)
        writer.line(x1 + left_offset, y1, x1 + right_offset, y1, "Part", color=color)
        writer.line(x2 + left_offset, y2, x2 + right_offset, y2, "Part", color=color)


def _segment_center_x_at_station(layout: _Layout, station: float) -> float:
    center_x = layout.view_left + layout.body_width / 2.0
    offsets = _segment_offsets(layout)
    segment = _segment_for_station(layout, station)
    if segment is None:
        return center_x
    start = _float(segment.get("station_start"))
    angle = math.radians(_float(segment.get("angle_deg")))
    return center_x + offsets.get(id(segment), 0.0) + math.tan(angle) * (station - start) * _station_scale(layout)


def _segment_for_station(layout: _Layout, station: float) -> dict[str, Any] | None:
    for segment in layout.segments:
        start = _float(segment.get("station_start"))
        end = _float(segment.get("station_end"))
        if start - 0.001 <= station <= end + 0.001:
            return segment
    return None


def _segment_offsets(layout: _Layout) -> dict[int, float]:
    offsets: dict[int, float] = {}
    current_x = 0.0
    previous_end = layout.station_start
    for segment in layout.segments:
        start = _float(segment.get("station_start"))
        if start > previous_end:
            previous_end = start
        offsets[id(segment)] = current_x
        angle = math.radians(_float(segment.get("angle_deg")))
        end = _float(segment.get("station_end"))
        current_x += math.tan(angle) * (end - start) * _station_scale(layout)
        previous_end = end
    return offsets


def _draw_section_marker(writer: "_DxfWriter", x: float, y: float, label: str) -> None:
    writer.line(x - 8, y + 5, x, y, "Section", color=6)
    writer.line(x - 8, y - 5, x, y, "Section", color=6)
    writer.line(x + 8, y + 5, x, y, "Section", color=6)
    writer.line(x + 8, y - 5, x, y, "Section", color=6)
    writer.text(x + 10, y - 2, 2.2, label, "Section", color=6)


def _draw_dimension_chains(
    writer: "_DxfWriter",
    step: dict[str, Any],
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    sheet_height: float,
    new_ids: set[str],
) -> None:
    view_top = top_y - layout.view_top_offset
    view_bottom = view_top - layout.view_height
    outer_x = layout.view_left - 55.0
    detail_x = layout.view_left - 30.0

    total_height = layout.station_end - layout.station_start
    writer.line(outer_x, view_top, outer_x, view_bottom, "Z-DIMENSIONS", color=1)
    writer.line(outer_x - 5, view_top, outer_x + 5, view_top, "Z-DIMENSIONS", color=1)
    writer.line(outer_x - 5, view_bottom, outer_x + 5, view_bottom, "Z-DIMENSIONS", color=1)
    writer.text(outer_x - 34, (view_top + view_bottom) / 2.0, 2.5, f"全部通高 {_format_length(total_height)}", "Z-DIMENSIONS", color=1)
    writer.text(outer_x - 30, view_bottom - 10, 1.8, f"OVERALL {_format_length(total_height)}", "Z-DIMENSIONS", color=1)

    marks = _height_marks(state, part_catalog, layout, new_ids)
    writer.text(detail_x - 22, view_top + 8, 1.8, "CONTINUOUS HEIGHT CHAIN", "Z-DIMENSIONS", color=1)
    writer.text(detail_x - 12, view_top + 2, 1.8, "DETAIL CHAIN", "Z-DIMENSIONS", color=1)
    for start, end, highlighted in marks:
        y1 = _station_to_y(start, layout, view_top)
        y2 = _station_to_y(end, layout, view_top)
        color = 1 if highlighted else 7
        writer.line(detail_x, y1, detail_x, y2, "Z-DIMENSIONS", color=color)
        writer.line(detail_x - 4, y1, detail_x + 4, y1, "Z-DIMENSIONS", color=color)
        writer.line(detail_x - 4, y2, detail_x + 4, y2, "Z-DIMENSIONS", color=color)
        if abs(end - start) > 0.01:
            writer.text(detail_x - 20, (y1 + y2) / 2.0, 1.8, _format_length(abs(end - start)), "Z-DIMENSIONS", color=color)

    for joint in layout.bend_joints:
        y = _station_to_y(_float(joint.get("station")), layout, view_top)
        writer.line(detail_x - 6, y, detail_x + 6, y, "Section", color=6)

    labels = []
    for target in step.get("dimension_targets", []):
        if not isinstance(target, dict):
            continue
        label = str(target.get("label") or target.get("kind") or "")
        if label:
            labels.append(label)
    if labels:
        writer.text(detail_x - 22, top_y - sheet_height + 28.0, 1.8, "DIM: " + "; ".join(labels), "Z-DIMENSIONS", color=1)


def _height_marks(
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    new_ids: set[str],
) -> list[tuple[float, float, bool]]:
    points = {layout.station_start, layout.station_end}
    for part in _installed_parts(state, part_catalog):
        points.add(part.station_start)
        points.add(part.station_end)
    sorted_points = sorted(points)
    if len(sorted_points) < 2:
        return []
    result = []
    new_parts = [part_catalog[part_id] for part_id in new_ids if part_id in part_catalog]
    for start, end in zip(sorted_points, sorted_points[1:]):
        highlighted = any(start >= part.station_start - 0.001 and end <= part.station_end + 0.001 for part in new_parts)
        result.append((start, end, highlighted))
    return result


def _draw_part_marks(
    writer: "_DxfWriter",
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    new_ids: set[str],
) -> None:
    view_top = top_y - layout.view_top_offset
    rows = _bom_rows(_installed_parts(state, part_catalog))
    rows_to_draw = _part_mark_rows(rows, new_ids, 8)
    used_label_y: list[float] = []
    for index, row in enumerate(rows_to_draw):
        part = part_catalog[row.part_ids[0]]
        anchor_x, anchor_y = _part_anchor(part, layout, top_y, view_top)
        y = _part_mark_label_y(anchor_y, top_y, layout, used_label_y)
        used_label_y.append(y)
        label_x = layout.part_mark_left + (index % 2) * 8.0
        color = 1 if any(part_id in new_ids for part_id in row.part_ids) else 3
        _draw_part_mark(writer, label_x, y, anchor_x, anchor_y, row.label, "PartMark", color)
    if len(rows) > len(rows_to_draw):
        writer.text(layout.part_mark_left, top_y - 78.0, 1.8, f"... {len(rows) - len(rows_to_draw)} more PartMarks in BOM", "PartMark", color=3)


def _draw_part_mark(writer: "_DxfWriter", label_x: float, label_y: float, anchor_x: float, anchor_y: float, label: str, layer: str, color: int) -> None:
    width = max(42.0, min(95.0, len(label) * 2.3))
    height = 6.0
    writer.rectangle(label_x, label_y + height / 2.0, label_x + width, label_y - height / 2.0, layer, color=color)
    writer.text(label_x + 2.0, label_y - 1.7, 2.0, label, layer, color=color)
    writer.line(label_x, label_y - height / 2.0, anchor_x, anchor_y, layer, color=color)


def _part_mark_rows(rows: list[_BomRow], new_ids: set[str], limit: int) -> list[_BomRow]:
    new_rows = [row for row in rows if any(part_id in new_ids for part_id in row.part_ids)]
    old_rows = [row for row in rows if not any(part_id in new_ids for part_id in row.part_ids)]
    if not new_rows:
        return old_rows[:limit]
    old_limit = max(0, min(2, limit - len(new_rows)))
    return (new_rows + old_rows[:old_limit])[:limit]


def _part_mark_label_y(anchor_y: float, top_y: float, layout: _Layout, used_label_y: list[float]) -> float:
    min_y = top_y - layout.base_sheet_height + 58.0
    max_y = top_y - 72.0
    label_y = max(min_y, min(max_y, anchor_y + 4.0))
    for _ in range(20):
        if all(abs(label_y - used) >= 8.0 for used in used_label_y):
            return label_y
        label_y -= 8.0
        if label_y < min_y:
            label_y = max_y
    return label_y


def _draw_weld_notes(
    writer: "_DxfWriter",
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    new_ids: set[str],
) -> None:
    view_top = top_y - layout.view_top_offset
    y_offset = 0.0
    ordered_ids = [part_id for part_id in state.installed_part_ids if part_id in new_ids]
    note_count = 0
    max_notes = 8
    for part_id in ordered_ids:
        part = part_catalog[part_id]
        for weld in part.welds[:2]:
            if note_count >= max_notes:
                writer.text(layout.view_left + layout.body_width + 28.0, top_y - 210.0, 1.8, "... more stage weld notes in BOM/detail", "文本", color=3)
                return
            text = _weld_text(weld)
            if not text:
                continue
            anchor_x, anchor_y = _part_anchor(part, layout, top_y, view_top)
            y = anchor_y - y_offset
            x1 = anchor_x + 3.0
            x2 = x1 + 18.0
            color = 1 if part_id in new_ids else 3
            writer.line(x1, y, x2, y + 10.0, "文本", color=color)
            writer.text(x2 + 2.0, y + 8.0, 2.0, text, "文本", color=color)
            y_offset += 7.0
            note_count += 1


def _part_anchor(part: _PartSnapshot, layout: _Layout, top_y: float, view_top: float) -> tuple[float, float]:
    transform = _projection_transform(layout, top_y)
    bounds = _part_projection_bounds(part)
    if transform is not None and bounds is not None:
        min_x, min_y, max_x, max_y = bounds
        return transform.point((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    return layout.view_left + layout.body_width + 5.0, _station_to_y((part.station_start + part.station_end) / 2.0, layout, view_top)


def _part_projection_bounds(part: _PartSnapshot) -> tuple[float, float, float, float] | None:
    xs = []
    ys = []
    for x1, y1, x2, y2 in part.projection_edges:
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    for arc in part.projection_arcs:
        xs.extend([arc.center_x - arc.radius, arc.center_x + arc.radius])
        ys.extend([arc.center_y - arc.radius, arc.center_y + arc.radius])
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _draw_detail_views(
    writer: "_DxfWriter",
    step: dict[str, Any],
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    new_ids: set[str],
) -> None:
    detail_parts = _detail_parts_for_step(step, state, part_catalog, new_ids)
    if not detail_parts:
        return
    detail_top = top_y - 150.0
    for index, part in enumerate(detail_parts[:4]):
        x = layout.detail_left
        y = detail_top - index * 54.0
        color = 1 if part.part_id in new_ids else 7
        writer.rectangle(x, y, x + 104, y - 42, "Part", color=color)
        writer.text(x + 3, y - 5, 2.0, "LOCAL DETAIL", "文本", color=3)
        writer.rectangle(x + 12, y - 14, x + 50, y - 32, "Part", color=color)
        _draw_part_mark(writer, x + 54, y - 18, x + 50, y - 23, f"{part.part_position} / {part.profile}", "PartMark", 3)
        if part.bolt_hole_count:
            diameter = int(part.bolt_diameter or 25)
            for bolt_index in range(part.bolt_hole_count):
                cx = x + 20 + bolt_index * 14
                cy = y - 23
                writer.circle(cx, cy, 2.3, "Bolt", color=7)
            writer.text(x + 54, y - 33, 1.9, f"{part.bolt_hole_count}Φ{diameter}", "BoltMark", color=3)
    total_detail_count = _installed_detail_count(step, state, part_catalog, new_ids)
    if total_detail_count > len(detail_parts):
        writer.text(layout.detail_left + 3, detail_top - len(detail_parts) * 54.0 - 5.0, 1.8, f"... {total_detail_count - len(detail_parts)} more LOCAL DETAILS", "文本", color=3)


def _draw_bom_table(
    writer: "_DxfWriter",
    step: dict[str, Any],
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    layout: _Layout,
    top_y: float,
    sheet_height: float,
    new_ids: set[str],
    detail_count: int,
) -> None:
    rows = _bom_rows(_installed_parts(state, part_catalog))
    rows_to_draw = _prioritize_rows(rows, new_ids, 9)
    step_no = step.get("step_no", "")
    total_qty = sum(row.quantity for row in rows)
    left = layout.bom_left
    right = layout.sheet_width - 12.0
    top = top_y - 20.0
    row_h = layout.row_height
    bottom = top - row_h * (len(rows_to_draw) + 3)
    writer.text(left, top + 7.0, 2.0, f"BOM STEP {step_no} CUMULATIVE PARTS {total_qty}", "文本", color=3)
    writer.rectangle(left, top, right, bottom, "DrawingSheet", color=5)
    headers = [("零件号", 3), ("规格", 54), ("名称", 104), ("数量", 150), ("材质", 174)]
    writer.line(left, top - row_h, right, top - row_h, "DrawingSheet", color=5)
    for header, offset in headers:
        writer.text(left + offset, top - 5.0, 1.8, header, "文本", color=3)
    for index, row in enumerate(rows_to_draw):
        y = top - row_h * (index + 1)
        color = 1 if any(part_id in new_ids for part_id in row.part_ids) else 7
        writer.line(left, y - row_h, right, y - row_h, "DrawingSheet", color=5)
        writer.text(left + 3, y - 5.0, 1.65, row.part_position, "文本", color=color)
        writer.text(left + 54, y - 5.0, 1.65, row.profile, "文本", color=color)
        writer.text(left + 104, y - 5.0, 1.65, row.name, "文本", color=color)
        writer.text(left + 154, y - 5.0, 1.65, str(row.quantity), "文本", color=color)
        writer.text(left + 174, y - 5.0, 1.65, row.material, "文本", color=color)
    if len(rows) > len(rows_to_draw):
        writer.text(left + 3, bottom - 5.0, 1.65, f"... {len(rows) - len(rows_to_draw)} more rows", "文本", color=3)


def _draw_stage_note(writer: "_DxfWriter", step: dict[str, Any], state: _AssemblyState, layout: _Layout, top_y: float, sheet_height: float) -> None:
    new_count = len(_ids(step.get("new_part_ids")))
    notes = [
        f"NOTE installed={len(state.installed_part_ids)} new={new_count} station={step.get('station_range') or 'member range'}"
    ]
    summary = step.get("evidence_summary") if isinstance(step.get("evidence_summary"), dict) else {}
    fixture_face = _non_empty_text(summary.get("fixture_face"))
    if fixture_face:
        notes.append(f"FIXTURE {fixture_face}")
    up_face = _non_empty_text(summary.get("up_face"))
    if up_face:
        notes.append(f"UP FACE {up_face}")
    side_work_faces = _note_list_text(summary.get("side_work_faces"))
    if side_work_faces:
        notes.append(f"SIDE WELD {side_work_faces}")
    flip_from_previous = _non_empty_text(summary.get("flip_from_previous"))
    if flip_from_previous:
        notes.append(f"FLIP {flip_from_previous}")
    for index, note in enumerate(notes):
        writer.text(12, top_y - sheet_height + 14.0 + index * 4.2, 2.0, note, "文本", color=3)


def _note_list_text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ";".join(text for item in value if (text := _non_empty_text(item)))
    return _non_empty_text(value)


def _non_empty_text(value: Any) -> str:
    text = str(value or "").strip()
    return text


def _build_part_catalog(payload: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, _PartSnapshot]:
    catalog: dict[str, _PartSnapshot] = {}
    for raw in payload.get("parts", []):
        if isinstance(raw, dict):
            part = _part_from_dict(raw)
            if part.part_id:
                catalog[part.part_id] = part
    for step in steps:
        step_start, step_end = _station_range(step)
        for target in step.get("part_mark_targets", []):
            if not isinstance(target, dict):
                continue
            part_id = str(target.get("part_id") or "")
            if part_id and part_id not in catalog:
                catalog[part_id] = _PartSnapshot(
                    part_id=part_id,
                    part_position=str(target.get("part_position") or ""),
                    profile=str(target.get("profile") or ""),
                    name=str(target.get("name") or ""),
                    station_start=step_start,
                    station_end=step_end,
                    requires_detail=str(step.get("step_type") or "") == "ADD_EXTERNAL_CLUSTER",
                )
    return catalog


def _default_render_step_no(steps: list[dict[str, Any]]) -> str:
    for step in steps:
        if str(step.get("step_type") or "") == "ADD_INTERNAL_GROUP":
            return str(step.get("step_no") or "")
    if steps:
        return str(steps[-1].get("step_no") or "")
    return ""


def _part_from_dict(raw: dict[str, Any]) -> _PartSnapshot:
    evidence = raw.get("mainMaterialEvidence") if isinstance(raw.get("mainMaterialEvidence"), dict) else {}
    station_start = _first_float(raw.get("station_start"), raw.get("axisStationStart"), evidence.get("axisStationStart"))
    station_end = _first_float(raw.get("station_end"), raw.get("axisStationEnd"), evidence.get("axisStationEnd"))
    welds = raw.get("welds")
    if not isinstance(welds, list):
        welds = raw.get("weldDetails") if isinstance(raw.get("weldDetails"), list) else []
    bolt_hole_count = int(_first_float(raw.get("bolt_hole_count"), raw.get("boltHoleCount"), 0.0))
    bolt_diameter = _first_float(raw.get("bolt_diameter"), raw.get("boltDiameter"), 0.0)
    if not bolt_diameter:
        holes = raw.get("boltHoles") if isinstance(raw.get("boltHoles"), list) else []
        if holes and isinstance(holes[0], dict):
            bolt_diameter = _float(holes[0].get("diameter"))
    return _PartSnapshot(
        part_id=str(raw.get("part_id") or raw.get("partId") or ""),
        part_position=str(raw.get("part_position") or raw.get("partPosition") or ""),
        profile=str(raw.get("profile") or raw.get("profileString") or ""),
        name=str(raw.get("name") or ""),
        material=str(raw.get("material") or ""),
        station_start=station_start,
        station_end=station_end,
        face=str(raw.get("face") or evidence.get("bodyFaceId") or ""),
        requires_detail=bool(raw.get("requires_detail") or raw.get("requiresDetail")),
        bolt_hole_count=bolt_hole_count,
        bolt_diameter=bolt_diameter,
        welds=[weld for weld in welds if isinstance(weld, dict)],
        projection_edges=_projection_edges_from_dict(raw),
        projection_arcs=_projection_arcs_from_dict(raw),
    )


def _build_layout(payload: dict[str, Any], steps: list[dict[str, Any]], part_catalog: dict[str, _PartSnapshot]) -> _Layout:
    ranges = [_station_range(step) for step in steps]
    for part in part_catalog.values():
        ranges.append((part.station_start, part.station_end))
    segments = [segment for segment in payload.get("segments", []) if isinstance(segment, dict)]
    bend_joints = [joint for joint in payload.get("bend_joints", []) if isinstance(joint, dict)]
    if not bend_joints:
        bend_joints = _infer_bend_joints(segments)
    for segment in segments:
        ranges.append((_float(segment.get("station_start")), _float(segment.get("station_end"))))
    starts = [start for start, end in ranges if end > start]
    ends = [end for start, end in ranges if end > start]
    if not starts or not ends:
        return _Layout(0.0, 1000.0, segments, bend_joints, _projection_bounds(part_catalog.values()))
    start = min(0.0, min(starts))
    end = max(ends)
    if end <= start:
        end = start + 1000.0
    return _Layout(start, end, segments, bend_joints, _projection_bounds(part_catalog.values()))


def _projection_edges_from_dict(raw: dict[str, Any]) -> tuple[tuple[float, float, float, float], ...]:
    raw_edges = raw.get("projectionEdges") or raw.get("projection_edges") or []
    if not isinstance(raw_edges, list):
        return ()
    edges = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            continue
        start = _point_2d(raw_edge.get("start") or raw_edge.get("Start"))
        end = _point_2d(raw_edge.get("end") or raw_edge.get("End"))
        if start is None or end is None:
            continue
        if start == end:
            continue
        edges.append((start[0], start[1], end[0], end[1]))
    return tuple(edges)


def _projection_arcs_from_dict(raw: dict[str, Any]) -> tuple[_ProjectionArc, ...]:
    raw_arcs = raw.get("projectionArcs") or raw.get("projection_arcs") or []
    if not isinstance(raw_arcs, list):
        return ()
    arcs = []
    for raw_arc in raw_arcs:
        if not isinstance(raw_arc, dict):
            continue
        center = _point_2d(raw_arc.get("center") or raw_arc.get("Center"))
        radius = _float(raw_arc.get("radius") or raw_arc.get("Radius"))
        if center is None or radius <= 0:
            continue
        arcs.append(
            _ProjectionArc(
                center_x=center[0],
                center_y=center[1],
                radius=radius,
                start_angle=_float(raw_arc.get("start_angle") or raw_arc.get("startAngle") or raw_arc.get("StartAngle")),
                end_angle=_float(raw_arc.get("end_angle") or raw_arc.get("endAngle") or raw_arc.get("EndAngle")),
            )
        )
    return tuple(arcs)


def _point_2d(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    return _float(value.get("x") or value.get("X") or value.get("u") or value.get("U")), _float(
        value.get("y") or value.get("Y") or value.get("v") or value.get("V")
    )


def _projection_bounds(parts: Any) -> tuple[float, float, float, float] | None:
    xs = []
    ys = []
    for part in parts:
        for x1, y1, x2, y2 in part.projection_edges:
            xs.extend([x1, x2])
            ys.extend([y1, y2])
        for arc in part.projection_arcs:
            xs.extend([arc.center_x - arc.radius, arc.center_x + arc.radius])
            ys.extend([arc.center_y - arc.radius, arc.center_y + arc.radius])
    if not xs or not ys:
        return None
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    if max_x <= min_x:
        max_x = min_x + 1.0
    if max_y <= min_y:
        max_y = min_y + 1.0
    return min_x, min_y, max_x, max_y


def _station_range(step: dict[str, Any]) -> tuple[float, float]:
    value = str(step.get("station_range") or "")
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", value)
    if match is None:
        return 0.0, 0.0
    return float(match.group(1)), float(match.group(2))


def _installed_parts(state: _AssemblyState, part_catalog: dict[str, _PartSnapshot]) -> list[_PartSnapshot]:
    return [part_catalog[part_id] for part_id in state.installed_part_ids if part_id in part_catalog]


def _bom_rows(parts: list[_PartSnapshot]) -> list[_BomRow]:
    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for part in parts:
        grouped.setdefault(part.quantity_key, []).append(part.part_id)
    rows = [
        _BomRow(position, profile, name, material, len(part_ids), tuple(part_ids))
        for (position, profile, name, material), part_ids in grouped.items()
    ]
    rows.sort(key=lambda row: (row.part_position, row.profile, row.name))
    return rows


def _prioritize_rows(rows: list[_BomRow], new_ids: set[str], limit: int) -> list[_BomRow]:
    new_rows = [row for row in rows if any(part_id in new_ids for part_id in row.part_ids)]
    old_rows = [row for row in rows if not any(part_id in new_ids for part_id in row.part_ids)]
    return (new_rows + old_rows)[:limit]


def _part_lane(part: _PartSnapshot, layout: _Layout) -> tuple[float, float]:
    left = layout.view_left
    right = layout.view_left + layout.body_width
    left_offset, right_offset = _part_lane_offsets(part, layout)
    center = layout.view_left + layout.body_width / 2.0
    return center + left_offset, center + right_offset


def _part_lane_offsets(part: _PartSnapshot, layout: _Layout) -> tuple[float, float]:
    half_width = layout.body_width / 2.0
    face = part.face.upper()
    if part.requires_detail:
        return half_width + 7.0, half_width + 16.0
    if "X_NEG" in face or "LEFT" in face:
        return -half_width - 8.0, -half_width + 2.0
    if "X_POS" in face or "RIGHT" in face:
        return half_width - 2.0, half_width + 8.0
    if "Y_NEG" in face or "BOTTOM" in face:
        return -half_width + 3.0, half_width - 3.0
    if "Y_POS" in face or "TOP" in face:
        return -half_width + 7.0, half_width - 7.0
    return -half_width + 4.0, half_width - 4.0


def _detail_parts_for_step(
    step: dict[str, Any],
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    new_ids: set[str],
) -> list[_PartSnapshot]:
    detail_parts = [
        part
        for part in _installed_parts(state, part_catalog)
        if part.requires_detail or (part.part_id in new_ids and str(step.get("step_type") or "") == "ADD_EXTERNAL_CLUSTER")
    ]
    new_parts = [part for part in detail_parts if part.part_id in new_ids]
    old_parts = [part for part in detail_parts if part.part_id not in new_ids]
    return (new_parts + old_parts)[0:4]


def _installed_detail_count(
    step: dict[str, Any],
    state: _AssemblyState,
    part_catalog: dict[str, _PartSnapshot],
    new_ids: set[str],
) -> int:
    return len(
        [
            part
            for part in _installed_parts(state, part_catalog)
            if part.requires_detail or (part.part_id in new_ids and str(step.get("step_type") or "") == "ADD_EXTERNAL_CLUSTER")
        ]
    )


def _detail_count(step: dict[str, Any], part_catalog: dict[str, _PartSnapshot]) -> int:
    if str(step.get("step_type") or "") == "ADD_EXTERNAL_CLUSTER":
        return max(1, len(_ids(step.get("new_part_ids"))))
    return sum(1 for part_id in _ids(step.get("new_part_ids")) if part_catalog.get(part_id, _EMPTY_PART).requires_detail)


def _weld_text(weld: dict[str, Any]) -> str:
    explicit = str(weld.get("text") or "").strip()
    if explicit:
        return explicit
    weld_type = str(weld.get("weldType") or weld.get("type") or "")
    size = _first_float(weld.get("size"), weld.get("sizeAbove"), weld.get("leg_size"), 0.0)
    if "full" in weld_type.lower() or "熔透" in weld_type:
        return "全熔透"
    if size:
        return f"角焊缝 {_format_length(size)}mm"
    if weld_type:
        return weld_type
    return ""


def _bend_strategy(bend_joints: list[dict[str, Any]]) -> str:
    max_angle = max((_float(joint.get("bend_angle_deg")) for joint in bend_joints), default=0.0)
    if max_angle <= 15:
        return "single_view_true_rotation"
    if max_angle <= 45:
        return "single_view_true_rotation_with_local_length_dim"
    return "split_view_with_schematic_overall_plus_detail"


def _infer_bend_joints(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    joints: list[dict[str, Any]] = []
    sorted_segments = sorted(segments, key=lambda segment: _float(segment.get("station_start")))
    for previous, current in zip(sorted_segments, sorted_segments[1:]):
        previous_end = _float(previous.get("station_end"))
        current_start = _float(current.get("station_start"))
        previous_angle = _float(previous.get("angle_deg"))
        current_angle = _float(current.get("angle_deg"))
        angle_delta = abs(current_angle - previous_angle)
        if angle_delta <= 0.1:
            continue
        if abs(previous_end - current_start) > max(1.0, abs(previous_end) * 0.001):
            continue
        letter = chr(min(ord("Z"), ord("B") + len(joints)))
        joints.append({"station": current_start, "label": f"{letter}-{letter}", "bend_angle_deg": angle_delta})
    return joints


def _station_to_y(station: float, layout: _Layout, view_top: float) -> float:
    span = max(layout.station_end - layout.station_start, 1.0)
    ratio = (station - layout.station_start) / span
    ratio = max(0.0, min(1.0, ratio))
    return view_top - (1.0 - ratio) * layout.view_height


def _station_scale(layout: _Layout) -> float:
    return layout.view_height / max(layout.station_end - layout.station_start, 1.0)


def _ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _first_float(*values: Any) -> float:
    for value in values:
        result = _float(value)
        if result:
            return result
    return 0.0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_length(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


class _DxfWriter:
    def __init__(self) -> None:
        self._doc: Any | None = None
        self._msp: Any | None = None
        self._offset_stack: list[tuple[float, float]] = [(0.0, 0.0)]
        self._layers: set[str] = set()

    def start(self) -> None:
        self._doc = ezdxf.new("R2007", setup=True)
        self._msp = self._doc.modelspace()

    def finish(self) -> None:
        return None

    def content(self) -> str:
        if self._doc is None:
            return ""
        stream = io.StringIO()
        self._doc.write(stream)
        return stream.getvalue()

    def push_offset(self, x: float, y: float) -> None:
        current_x, current_y = self._offset_stack[-1]
        self._offset_stack.append((current_x + x, current_y + y))

    def pop_offset(self) -> None:
        if len(self._offset_stack) > 1:
            self._offset_stack.pop()

    def line(self, x1: float, y1: float, x2: float, y2: float, layer: str, color: int | None = None) -> None:
        if self._msp is None:
            return
        ox, oy = self._offset_stack[-1]
        self._msp.add_line((x1 + ox, y1 + oy), (x2 + ox, y2 + oy), dxfattribs=self._dxfattribs(layer, color))

    def rectangle(self, x1: float, y1: float, x2: float, y2: float, layer: str, color: int | None = None) -> None:
        self.line(x1, y1, x2, y1, layer, color=color)
        self.line(x2, y1, x2, y2, layer, color=color)
        self.line(x2, y2, x1, y2, layer, color=color)
        self.line(x1, y2, x1, y1, layer, color=color)

    def circle(self, x: float, y: float, radius: float, layer: str, color: int | None = None) -> None:
        if self._msp is None:
            return
        ox, oy = self._offset_stack[-1]
        self._msp.add_circle((x + ox, y + oy), radius, dxfattribs=self._dxfattribs(layer, color))

    def arc(
        self,
        x: float,
        y: float,
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str,
        color: int | None = None,
    ) -> None:
        if self._msp is None:
            return
        ox, oy = self._offset_stack[-1]
        self._msp.add_arc(
            (x + ox, y + oy),
            radius,
            start_angle,
            end_angle,
            dxfattribs=self._dxfattribs(layer, color),
        )

    def text(self, x: float, y: float, height: float, value: str, layer: str, color: int | None = None) -> None:
        if self._msp is None:
            return
        ox, oy = self._offset_stack[-1]
        self._msp.add_text(
            _clean_text(value),
            dxfattribs={**self._dxfattribs(layer, color), "height": height, "insert": (x + ox, y + oy)},
        )

    def _dxfattribs(self, layer: str, color: int | None) -> dict[str, Any]:
        if self._doc is not None and layer not in self._layers:
            if layer not in self._doc.layers:
                self._doc.layers.add(layer)
            self._layers.add(layer)
        attribs: dict[str, Any] = {"layer": layer}
        if color is not None:
            attribs["color"] = color
        return attribs


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _clean_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ").strip()


_EMPTY_PART = _PartSnapshot("", "", "", "")
