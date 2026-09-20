"""Shapely behind a thin planar API. Classifiers import this, not shapely."""

from __future__ import annotations

from typing import Sequence

from shapely.geometry import LineString, Point, Polygon

from . import LINEAR_TOL_MM

Point2 = tuple[float, float]
_RIGHT_ANGLE_COS = 0.035


def as_polygon(ring: Sequence[Sequence[float]]) -> Polygon | None:
    if len(ring) < 3:
        return None
    coords = [(float(point[0]), float(point[1])) for point in ring]
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    polygon = Polygon(coords)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty or polygon.area <= LINEAR_TOL_MM:
        return None
    if polygon.geom_type == "MultiPolygon":
        polygon = max(polygon.geoms, key=lambda item: item.area)
    return polygon


def min_rectangle(polygon: Polygon) -> Polygon:
    return polygon.minimum_rotated_rectangle


def rectangle_corners(frame: Polygon) -> list[Point2]:
    coords = list(frame.exterior.coords)[:-1]
    return [(float(x), float(y)) for x, y in coords]


def covers_point(polygon: Polygon, point: Sequence[float], tol: float = LINEAR_TOL_MM) -> bool:
    target = Point(float(point[0]), float(point[1]))
    return bool(polygon.covers(target) or polygon.distance(target) <= tol)


def point_on_segment(
    point: Sequence[float],
    start: Sequence[float],
    end: Sequence[float],
    tol: float = LINEAR_TOL_MM,
) -> bool:
    return LineString(
        [(float(start[0]), float(start[1])), (float(end[0]), float(end[1]))]
    ).distance(Point(float(point[0]), float(point[1]))) <= tol


def is_convex(polygon: Polygon, tol: float = LINEAR_TOL_MM) -> bool:
    hull = polygon.convex_hull
    return abs(hull.area - polygon.area) <= max(tol, 0.001 * max(hull.area, 1.0))


def project_uv(points: Sequence[Sequence[float]]) -> list[Point2]:
    origin = tuple(float(component) for component in points[0][:3])
    axis_u = None
    for point in points[1:]:
        vec = _sub3(point, origin)
        if _length3(vec) > LINEAR_TOL_MM:
            axis_u = _norm3(vec)
            break
    if axis_u is None:
        return []
    axis_n = None
    for point in points[1:]:
        vec = _sub3(point, origin)
        crossed = _cross3(axis_u, vec)
        if _length3(crossed) > LINEAR_TOL_MM:
            axis_n = _norm3(crossed)
            break
    if axis_n is None:
        return [(_dot3(_sub3(point, origin), axis_u), 0.0) for point in points]
    axis_v = _norm3(_cross3(axis_n, axis_u))
    return [(_dot3(_sub3(point, origin), axis_u), _dot3(_sub3(point, origin), axis_v)) for point in points]


def clean_ring(uv: Sequence[Sequence[float]]) -> list[Point2]:
    points = [(float(item[0]), float(item[1])) for item in uv]
    if len(points) >= 2 and dist2(points[0], points[-1]) <= LINEAR_TOL_MM:
        points = points[:-1]
    compact: list[Point2] = []
    for point in points:
        if not compact or dist2(compact[-1], point) > LINEAR_TOL_MM:
            compact.append(point)
    if len(compact) >= 2 and dist2(compact[0], compact[-1]) <= LINEAR_TOL_MM:
        compact = compact[:-1]
    if len(compact) < 3:
        return compact
    ring: list[Point2] = []
    count = len(compact)
    for index, point in enumerate(compact):
        prev_pt = compact[(index - 1) % count]
        next_pt = compact[(index + 1) % count]
        if point_on_segment(point, prev_pt, next_pt):
            continue
        ring.append(point)
    return ring


def is_strict_rectangle(ring: Sequence[Sequence[float]]) -> bool:
    if len(ring) != 4:
        return False
    sides = [dist2(ring[index], ring[(index + 1) % 4]) for index in range(4)]
    if min(sides) <= LINEAR_TOL_MM:
        return False
    if abs(sides[0] - sides[2]) > _length_tol(sides[0], sides[2]):
        return False
    if abs(sides[1] - sides[3]) > _length_tol(sides[1], sides[3]):
        return False
    for index in range(4):
        incoming = norm2(sub2(ring[index], ring[(index - 1) % 4]))
        outgoing = norm2(sub2(ring[(index + 1) % 4], ring[index]))
        if incoming is None or outgoing is None:
            return False
        if abs(dot2(incoming, outgoing)) > _RIGHT_ANGLE_COS:
            return False
    diagonal_a = dist2(ring[0], ring[2])
    diagonal_b = dist2(ring[1], ring[3])
    return abs(diagonal_a - diagonal_b) <= _length_tol(diagonal_a, diagonal_b)


def dist2(a: Sequence[float], b: Sequence[float]) -> float:
    return length2(sub2(a, b))


def sub2(a: Sequence[float], b: Sequence[float]) -> Point2:
    return (float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def dot2(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1])


def cross2(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[1]) - float(a[1]) * float(b[0])


def length2(vec: Sequence[float]) -> float:
    return (dot2(vec, vec)) ** 0.5


def norm2(vec: Sequence[float]) -> Point2 | None:
    length = length2(vec)
    if length <= LINEAR_TOL_MM:
        return None
    return (float(vec[0]) / length, float(vec[1]) / length)


def _length_tol(a: float, b: float) -> float:
    return max(LINEAR_TOL_MM, 0.002 * max(a, b))


def _sub3(point: Sequence[float], origin: Sequence[float]) -> tuple[float, float, float]:
    return (float(point[0]) - float(origin[0]), float(point[1]) - float(origin[1]), float(point[2]) - float(origin[2]))


def _dot3(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])


def _cross3(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _length3(vec: Sequence[float]) -> float:
    return (_dot3(vec, vec)) ** 0.5


def _norm3(vec: Sequence[float]) -> tuple[float, float, float]:
    length = _length3(vec)
    if length <= 0:
        return (0.0, 0.0, 0.0)
    return (float(vec[0]) / length, float(vec[1]) / length, float(vec[2]) / length)
