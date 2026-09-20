"""Planar chamfer detection. Reconstructs in-plane cuts, does not detect 剖口."""

from __future__ import annotations

from typing import Sequence

from . import LINEAR_TOL_MM
from .planar import (
    as_polygon,
    clean_ring,
    covers_point,
    dist2,
    is_convex,
    is_strict_rectangle,
    length2,
    min_rectangle,
    point_on_segment,
    rectangle_corners,
    sub2,
)

Point2 = tuple[float, float]
Chamfer = tuple[str, float, float]

_APPLY_TYPES = {
    "CHAMFER_LINE",
    "LINE",
    "CHAMFER_ARC",
    "ARC",
    "CHAMFER_ARC_POINT",
    "ARC_POINT",
    "CHAMFER_ROUNDING",
    "ROUNDING",
    "CHAMFER_SQUARE",
    "SQUARE",
    "CHAMFER_LINE_AND_ARC",
}
_ARC_TYPES = {
    "CHAMFER_ARC",
    "ARC",
    "CHAMFER_ARC_POINT",
    "ARC_POINT",
    "CHAMFER_ROUNDING",
    "ROUNDING",
}


def classify_plan_outline(
    ring: Sequence[Sequence[float]],
    chamfers: Sequence[Sequence[object]] = (),
) -> tuple[str, list[str]]:
    cleaned = clean_ring(ring)
    specs = _normalize_chamfers(chamfers)
    applied = False
    if len(cleaned) == 4:
        rebuilt = apply_vertex_chamfers(cleaned, specs)
        applied = len(rebuilt) != len(cleaned)
        cleaned = clean_ring(rebuilt)
    if len(cleaned) == 4 and is_strict_rectangle(cleaned):
        return "RECTANGLE", ["标准矩形外轮廓"]
    polygon = as_polygon(cleaned)
    if polygon is None:
        return "IRREGULAR", ["外轮廓无法构成平面环"]
    if not is_convex(polygon):
        evidence = ["平面缺口"]
        if _has_positive_chamfer(specs):
            evidence.append("平面倒角")
        return "NOTCHED", evidence
    if _is_chamfered_rectangle(cleaned, polygon) or applied:
        return "CHAMFERED", ["平面倒角"]
    return "IRREGULAR", ["外轮廓不是标准矩形"]


def apply_vertex_chamfers(ring: Sequence[Point2], chamfers: Sequence[Chamfer]) -> list[Point2]:
    count = len(ring)
    if count < 3:
        return [(float(point[0]), float(point[1])) for point in ring]
    result: list[Point2] = []
    for index, vertex in enumerate(ring):
        kind, size_x, size_y = _chamfer_at(chamfers, index)
        cut = _corner_cut(ring[(index - 1) % count], vertex, ring[(index + 1) % count], kind, size_x, size_y)
        if cut is None:
            result.append((float(vertex[0]), float(vertex[1])))
            continue
        result.extend(cut)
    return result


def _is_chamfered_rectangle(ring: Sequence[Point2], polygon) -> bool:
    frame = min_rectangle(polygon)
    corners = rectangle_corners(frame)
    if len(corners) != 4:
        return False
    sides = [dist2(corners[index], corners[(index + 1) % 4]) for index in range(4)]
    min_side = min(sides) if sides else 0.0
    if min_side <= LINEAR_TOL_MM:
        return False
    search = max(8.0, 0.25 * min_side)
    chamfered = 0
    intact = 0
    for index, corner in enumerate(corners):
        if covers_point(polygon, corner):
            intact += 1
            continue
        near = [point for point in ring if dist2(point, corner) <= search]
        prev_corner = corners[(index - 1) % 4]
        next_corner = corners[(index + 1) % 4]
        if _is_corner_clip(near, corner, prev_corner, next_corner):
            chamfered += 1
            continue
        return False
    if chamfered < 1 or intact + chamfered != 4:
        return False
    return all(dist2(point, _nearest(point, corners)) <= search for point in ring)


def _is_corner_clip(
    near: Sequence[Point2],
    corner: Point2,
    prev_corner: Point2,
    next_corner: Point2,
) -> bool:
    if len(near) < 2:
        return False
    on_incoming = [point for point in near if point_on_segment(point, prev_corner, corner)]
    on_outgoing = [point for point in near if point_on_segment(point, corner, next_corner)]
    return bool(on_incoming) and bool(on_outgoing)


def _corner_cut(
    prev: Sequence[float],
    vertex: Sequence[float],
    nxt: Sequence[float],
    kind: str,
    size_x: float,
    size_y: float,
) -> list[Point2] | None:
    if kind not in _APPLY_TYPES:
        return None
    if size_x <= LINEAR_TOL_MM and size_y <= LINEAR_TOL_MM:
        return None
    incoming = sub2(prev, vertex)
    outgoing = sub2(nxt, vertex)
    len_in = length2(incoming)
    len_out = length2(outgoing)
    if len_in <= LINEAR_TOL_MM * 2 or len_out <= LINEAR_TOL_MM * 2:
        return None
    cut_x = size_x if size_x > LINEAR_TOL_MM else size_y
    cut_y = size_y if size_y > LINEAR_TOL_MM else size_x
    cut_x = min(cut_x, 0.98 * len_in)
    cut_y = min(cut_y, 0.98 * len_out)
    start = (float(vertex[0]) + incoming[0] / len_in * cut_x, float(vertex[1]) + incoming[1] / len_in * cut_x)
    end = (float(vertex[0]) + outgoing[0] / len_out * cut_y, float(vertex[1]) + outgoing[1] / len_out * cut_y)
    if dist2(start, end) <= LINEAR_TOL_MM:
        return None
    if kind in _ARC_TYPES:
        return [start, *_arc_samples(start, vertex, end), end]
    return [start, end]


def _arc_samples(start: Point2, corner: Sequence[float], end: Point2) -> list[Point2]:
    samples = []
    for step in (1, 2, 3):
        t = step / 4.0
        keep = (1.0 - t) * (1.0 - t)
        mix = 2.0 * (1.0 - t) * t
        far = t * t
        samples.append(
            (
                keep * start[0] + mix * float(corner[0]) + far * end[0],
                keep * start[1] + mix * float(corner[1]) + far * end[1],
            )
        )
    return samples


def _has_positive_chamfer(specs: Sequence[Chamfer]) -> bool:
    for kind, size_x, size_y in specs:
        if kind in _APPLY_TYPES and (size_x > LINEAR_TOL_MM or size_y > LINEAR_TOL_MM):
            return True
    return False


def _normalize_chamfers(chamfers: Sequence[Sequence[object]]) -> tuple[Chamfer, ...]:
    result = []
    for item in chamfers:
        if not item:
            continue
        kind = str(item[0] or "NONE").upper()
        size_x = float(item[1]) if len(item) > 1 else 0.0
        size_y = float(item[2]) if len(item) > 2 else 0.0
        result.append((kind, size_x, size_y))
    return tuple(result)


def _chamfer_at(chamfers: Sequence[Chamfer], index: int) -> Chamfer:
    if index >= len(chamfers):
        return ("NONE", 0.0, 0.0)
    return chamfers[index]


def _nearest(point: Point2, corners: Sequence[Point2]) -> Point2:
    return min(corners, key=lambda corner: dist2(point, corner))
