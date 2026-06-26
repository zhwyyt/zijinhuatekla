from __future__ import annotations

from collections import defaultdict, deque
import math
from typing import Any

from .bracket_classifier import (
    AppendageClusterFeatures,
    AppendageRoleClassification,
    classify_appendage_cluster,
)
from .rules import as_float, text


BODY_ROLE_NAMES = {
    "web_candidate",
    "flange_candidate",
    "wall_candidate",
}


def body_part_ids_from_member_roles(member: dict[str, Any]) -> set[str]:
    roles = member.get("Classification", {}).get("PartRoles", [])
    return {
        text(role.get("PartId"))
        for role in roles
        if text(role.get("Role")).lower() in BODY_ROLE_NAMES and text(role.get("PartId"))
    }


def appendage_cluster_features_from_bundle(
    assembly: dict[str, Any],
    member: dict[str, Any],
    body_part_ids: set[str] | None = None,
) -> list[AppendageClusterFeatures]:
    parts = {text(part.get("partId")): part for part in assembly.get("parts", [])}
    body_ids = {text(part_id) for part_id in (body_part_ids or set()) if text(part_id)}
    if not body_ids:
        body_ids = body_part_ids_from_member_roles(member)
    if not body_ids and assembly.get("mainPartId"):
        body_ids = {text(assembly.get("mainPartId"))}

    appendage_ids = set(parts) - body_ids
    if not appendage_ids:
        return []

    graph, root_edges, bolt_counts = _build_graph(assembly, body_ids, appendage_ids)
    clusters = _collect_appendage_clusters(appendage_ids, graph)
    body_box = _union_box([parts[part_id] for part_id in body_ids if part_id in parts])
    axis = _member_axis(member)
    assembly_span = _assembly_span(member, body_box)
    result = []
    for index, cluster_ids in enumerate(clusters):
        cluster_parts = [parts[part_id] for part_id in cluster_ids if part_id in parts]
        if not cluster_parts:
            continue
        result.append(
            _cluster_to_features(
                assembly_id=text(assembly.get("assemblyId")),
                index=index,
                cluster_ids=cluster_ids,
                cluster_parts=cluster_parts,
                root_edges=root_edges,
                bolt_counts=bolt_counts,
                body_box=body_box,
                axis=axis,
                assembly_span=assembly_span,
            )
        )
    return result


def classify_appendage_clusters_from_bundle(
    assembly: dict[str, Any],
    member: dict[str, Any],
    body_part_ids: set[str] | None = None,
) -> list[AppendageRoleClassification]:
    return [
        classify_appendage_cluster(features)
        for features in appendage_cluster_features_from_bundle(assembly, member, body_part_ids=body_part_ids)
    ]


def _build_graph(
    assembly: dict[str, Any],
    body_ids: set[str],
    appendage_ids: set[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, int]]:
    graph: dict[str, set[str]] = defaultdict(set)
    root_edges: dict[str, set[str]] = defaultdict(set)
    bolt_counts: dict[str, int] = defaultdict(int)
    for rel in assembly.get("relationships", []):
        left = text(rel.get("partIdA"))
        right = text(rel.get("partIdB"))
        edge_type = text(rel.get("edgeType"))
        if not left or not right:
            continue

        if left in appendage_ids and right in appendage_ids and edge_type in {"Weld", "Contact", "Boolean"}:
            graph[left].add(right)
            graph[right].add(left)

        if left in appendage_ids and right in body_ids and edge_type in {"Weld", "Contact"}:
            root_edges[left].add(right)
        if right in appendage_ids and left in body_ids and edge_type in {"Weld", "Contact"}:
            root_edges[right].add(left)

        if edge_type == "Bolt":
            if left in appendage_ids:
                bolt_counts[left] += 1
            if right in appendage_ids:
                bolt_counts[right] += 1

    return graph, root_edges, bolt_counts


def _collect_appendage_clusters(appendage_ids: set[str], graph: dict[str, set[str]]) -> list[list[str]]:
    clusters = []
    visited = set()
    for part_id in sorted(appendage_ids):
        if part_id in visited:
            continue
        visited.add(part_id)
        cluster = [part_id]
        queue = deque([part_id])
        while queue:
            current = queue.popleft()
            for neighbor in graph.get(current, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                cluster.append(neighbor)
                queue.append(neighbor)
        clusters.append(sorted(cluster))
    return clusters


def _cluster_to_features(
    assembly_id: str,
    index: int,
    cluster_ids: list[str],
    cluster_parts: list[dict[str, Any]],
    root_edges: dict[str, set[str]],
    bolt_counts: dict[str, int],
    body_box: dict[str, dict[str, float]],
    axis: tuple[float, float, float],
    assembly_span: float,
) -> AppendageClusterFeatures:
    cluster_box = _union_box(cluster_parts)
    root_part_count = sum(1 for part_id in cluster_ids if root_edges.get(part_id))
    root_contact_ratio = root_part_count / len(cluster_ids) if cluster_ids else 0.0
    span_along_axis = _box_span_along_axis(cluster_box, axis)
    span_perp = _box_max_perp_span(cluster_box, axis)
    root_contact_width = max(1.0, root_part_count)
    cantilever_ratio = span_perp / root_contact_width
    centroid = _weighted_centroid(cluster_parts)
    return AppendageClusterFeatures(
        cluster_id=f"{assembly_id}:{index}",
        part_ids=sorted(cluster_ids),
        root_contact_ratio=round(root_contact_ratio, 4),
        cantilever_ratio=round(cantilever_ratio, 4),
        span_along_axis=round(span_along_axis, 4),
        assembly_span=round(assembly_span, 4),
        centroid_outside_body=not _point_inside_box(centroid, body_box, margin=50.0),
        has_end_connection_signal=any(_part_near_body_axis_end(part, body_box, axis) for part in cluster_parts),
        bolt_count=sum(bolt_counts.get(part_id, 0) for part_id in cluster_ids),
        cluster_volume=sum(as_float(part.get("volume"), 1.0) or 1.0 for part in cluster_parts),
        max_thickness=max((as_float(part.get("thickness")) for part in cluster_parts), default=0.0),
    )


def _member_axis(member: dict[str, Any]) -> tuple[float, float, float]:
    segments = member.get("AxisSegments") or []
    if segments:
        direction = segments[0].get("Direction") or {}
        return _normalize((as_float(direction.get("X")), as_float(direction.get("Y")), as_float(direction.get("Z"))))
    return (1.0, 0.0, 0.0)


def _assembly_span(member: dict[str, Any], body_box: dict[str, dict[str, float]]) -> float:
    segments = member.get("AxisSegments") or []
    length = sum(as_float(segment.get("Length")) for segment in segments)
    if length > 0:
        return length
    return _box_span_along_axis(body_box, _member_axis(member))


def _union_box(parts: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    mins = []
    maxs = []
    for part in parts:
        box = part.get("boundingBox") or {}
        box_min = box.get("min") or {}
        box_max = box.get("max") or {}
        mins.append((as_float(box_min.get("x")), as_float(box_min.get("y")), as_float(box_min.get("z"))))
        maxs.append((as_float(box_max.get("x")), as_float(box_max.get("y")), as_float(box_max.get("z"))))
    if not mins:
        return {"min": {"x": 0.0, "y": 0.0, "z": 0.0}, "max": {"x": 0.0, "y": 0.0, "z": 0.0}}
    return {
        "min": {"x": min(p[0] for p in mins), "y": min(p[1] for p in mins), "z": min(p[2] for p in mins)},
        "max": {"x": max(p[0] for p in maxs), "y": max(p[1] for p in maxs), "z": max(p[2] for p in maxs)},
    }


def _weighted_centroid(parts: list[dict[str, Any]]) -> tuple[float, float, float]:
    total = sum(as_float(part.get("volume"), 1.0) or 1.0 for part in parts)
    if total <= 0:
        total = float(len(parts) or 1)
    x = y = z = 0.0
    for part in parts:
        weight = as_float(part.get("volume"), 1.0) or 1.0
        centroid = part.get("centroid") or {}
        x += as_float(centroid.get("x")) * weight
        y += as_float(centroid.get("y")) * weight
        z += as_float(centroid.get("z")) * weight
    return x / total, y / total, z / total


def _box_corners(box: dict[str, dict[str, float]]) -> list[tuple[float, float, float]]:
    box_min = box.get("min") or {}
    box_max = box.get("max") or {}
    xs = [as_float(box_min.get("x")), as_float(box_max.get("x"))]
    ys = [as_float(box_min.get("y")), as_float(box_max.get("y"))]
    zs = [as_float(box_min.get("z")), as_float(box_max.get("z"))]
    return [(x, y, z) for x in xs for y in ys for z in zs]


def _box_span_along_axis(box: dict[str, dict[str, float]], axis: tuple[float, float, float]) -> float:
    projections = [_dot(corner, axis) for corner in _box_corners(box)]
    return max(projections) - min(projections) if projections else 0.0


def _box_max_perp_span(box: dict[str, dict[str, float]], axis: tuple[float, float, float]) -> float:
    corners = _box_corners(box)
    max_distance = 0.0
    for left in corners:
        for right in corners:
            delta = (left[0] - right[0], left[1] - right[1], left[2] - right[2])
            along = _dot(delta, axis)
            perp_sq = max(0.0, _dot(delta, delta) - (along * along))
            max_distance = max(max_distance, math.sqrt(perp_sq))
    return max_distance


def _point_inside_box(
    point: tuple[float, float, float],
    box: dict[str, dict[str, float]],
    margin: float = 0.0,
) -> bool:
    box_min = box.get("min") or {}
    box_max = box.get("max") or {}
    return (
        as_float(box_min.get("x")) - margin <= point[0] <= as_float(box_max.get("x")) + margin
        and as_float(box_min.get("y")) - margin <= point[1] <= as_float(box_max.get("y")) + margin
        and as_float(box_min.get("z")) - margin <= point[2] <= as_float(box_max.get("z")) + margin
    )


def _part_near_body_axis_end(
    part: dict[str, Any],
    body_box: dict[str, dict[str, float]],
    axis: tuple[float, float, float],
) -> bool:
    body_projections = [_dot(corner, axis) for corner in _box_corners(body_box)]
    part_box = _union_box([part])
    part_projections = [_dot(corner, axis) for corner in _box_corners(part_box)]
    if not body_projections or not part_projections:
        return False
    span = max(body_projections) - min(body_projections)
    if span <= 1e-6:
        return False
    part_center = (max(part_projections) + min(part_projections)) / 2.0
    return (
        abs(part_center - min(body_projections)) <= span * 0.08
        or abs(part_center - max(body_projections)) <= span * 0.08
    )


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(_dot(vector, vector))
    if length <= 1e-9:
        return (1.0, 0.0, 0.0)
    return vector[0] / length, vector[1] / length, vector[2] / length
