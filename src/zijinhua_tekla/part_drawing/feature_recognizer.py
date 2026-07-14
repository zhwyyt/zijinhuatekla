from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import DrawingIssue, DrawingStatus, IssueCode, PartDrawingSnapshot
from .geometry_analyzer import NormalizedPlateGeometry, Point2D, project_point


class FeatureType(str, Enum):
    ROUND_HOLE = "ROUND_HOLE"
    HOLE_GROUP = "HOLE_GROUP"
    SLOT = "SLOT"
    POLYGON_CUTOUT = "POLYGON_CUTOUT"
    CHAMFER = "CHAMFER"
    NOTCH = "NOTCH"
    ARC_CUTOUT = "ARC_CUTOUT"
    BEVEL = "BEVEL"


@dataclass(frozen=True)
class RecognizedFeature:
    feature_id: str
    feature_type: FeatureType
    anchors: tuple[Point2D, ...]
    parameters: dict[str, Any]
    source_ids: tuple[str, ...]
    evidence_codes: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class FeatureRecognitionResult:
    features: tuple[RecognizedFeature, ...]
    status: DrawingStatus
    issues: tuple[DrawingIssue, ...]


def recognize_plate_features(
    snapshot: PartDrawingSnapshot,
    geometry: NormalizedPlateGeometry,
) -> FeatureRecognitionResult:
    features = [_explicit_hole_feature(snapshot, geometry, hole) for hole in snapshot.holes]
    features.extend(_hole_groups(features))
    issues: list[DrawingIssue] = []
    for index, loop in enumerate(geometry.inner_loops, 1):
        if all(segment.kind == "LINE" for segment in loop):
            features.append(_loop_feature(index, FeatureType.POLYGON_CUTOUT, loop, {}))
        elif all(segment.kind == "ARC" for segment in loop) and _consistent_arc_loop(loop):
            radius = _distance(loop[0].start, loop[0].center)
            features.append(_loop_feature(index, FeatureType.ARC_CUTOUT, loop, {"radius": radius}))
        else:
            issues.append(DrawingIssue(
                IssueCode.FEATURE_AMBIGUOUS,
                f"inner loop {index} cannot be classified reliably",
                False,
                (snapshot.part_id,),
                ("INNER_LOOP_ARC_CONFLICT",),
            ))
    features.extend(_outer_features(geometry))
    features.extend(_explicit_bevels(snapshot))
    return FeatureRecognitionResult(
        tuple(features),
        DrawingStatus.REVIEW_REQUIRED if issues else DrawingStatus.OK,
        tuple(issues),
    )


def _explicit_hole_feature(snapshot, geometry, hole) -> RecognizedFeature:
    projected = project_point(hole.center, snapshot.local_frame)
    anchor = Point2D(
        projected.x - geometry.normalization_offset.x,
        projected.y - geometry.normalization_offset.y,
    )
    if hole.kind == "ROUND":
        feature_type = FeatureType.ROUND_HOLE
        parameters = {"diameter": hole.diameter}
        evidence = ("TEKLA_HOLE_OPERATION",)
    else:
        feature_type = FeatureType.SLOT
        parameters = {"length": hole.length, "width": hole.width, "angle_deg": hole.angle_deg}
        evidence = ("TEKLA_SLOT_OPERATION",)
    return RecognizedFeature(hole.hole_id, feature_type, (anchor,), parameters, (hole.hole_id,), evidence, 1.0)


def _hole_groups(features: list[RecognizedFeature]) -> list[RecognizedFeature]:
    rounds = [item for item in features if item.feature_type == FeatureType.ROUND_HOLE]
    groups = []
    by_diameter: dict[float, list[RecognizedFeature]] = {}
    for item in rounds:
        by_diameter.setdefault(round(float(item.parameters["diameter"]), 2), []).append(item)
    for diameter, items in by_diameter.items():
        if len(items) < 3:
            continue
        for axis in ("x", "y"):
            ordered = sorted(items, key=lambda item: getattr(item.anchors[0], axis))
            fixed_axis = "y" if axis == "x" else "x"
            if max(getattr(item.anchors[0], fixed_axis) for item in ordered) - min(getattr(item.anchors[0], fixed_axis) for item in ordered) > 0.1:
                continue
            values = [getattr(item.anchors[0], axis) for item in ordered]
            spacings = [round(right - left, 2) for left, right in zip(values, values[1:])]
            if spacings and max(spacings) - min(spacings) <= 0.1:
                groups.append(RecognizedFeature(
                    f"hole-group-{len(groups) + 1}", FeatureType.HOLE_GROUP,
                    tuple(item.anchors[0] for item in ordered),
                    {"diameter": diameter, "count": len(ordered), "spacing": spacings[0], "axis": axis},
                    tuple(item.feature_id for item in ordered),
                    ("EQUAL_DIAMETER", "COLLINEAR", "EQUAL_SPACING"), 1.0,
                ))
                break
    return groups


def _loop_feature(index, feature_type, loop, parameters):
    return RecognizedFeature(
        f"inner-{index}", feature_type, tuple(segment.start for segment in loop), parameters,
        (f"inner-loop-{index}",), ("CLOSED_INNER_LOOP",), 1.0,
    )


def _consistent_arc_loop(loop) -> bool:
    centers = [segment.center for segment in loop if segment.center is not None]
    if len(centers) != len(loop):
        return False
    first = centers[0]
    radii = [_distance(segment.start, segment.center) for segment in loop]
    return max(_distance(first, center) for center in centers) <= 0.1 and max(radii) - min(radii) <= 0.1


def _outer_features(geometry) -> list[RecognizedFeature]:
    loop = geometry.outer_loop
    diagonal = [item for item in loop if abs(item.end.x - item.start.x) > 0.1 and abs(item.end.y - item.start.y) > 0.1]
    if diagonal:
        item = diagonal[0]
        return [RecognizedFeature("outer-chamfer-1", FeatureType.CHAMFER, (item.start, item.end), {}, ("outer-loop",), ("DIAGONAL_BOUNDARY_EDGE",), 0.95)]
    width, height = geometry.bounds[2], geometry.bounds[3]
    if len(loop) > 4 and geometry.area < width * height - 0.1:
        return [RecognizedFeature("outer-notch-1", FeatureType.NOTCH, tuple(item.start for item in loop), {}, ("outer-loop",), ("BOUNDING_RECTANGLE_DEFICIT",), 0.95)]
    return []


def _explicit_bevels(snapshot) -> list[RecognizedFeature]:
    return [
        RecognizedFeature(
            f"bevel-{index}", FeatureType.BEVEL, (), dict(cut),
            (str(cut.get("operationId") or index),), ("TEKLA_EXPLICIT_BEVEL",), 1.0,
        )
        for index, cut in enumerate(snapshot.cuts, 1)
        if str(cut.get("operationType") or "").upper() == "BEVEL"
    ]


def _distance(first, second) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)
