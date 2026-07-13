from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .contracts import (
    ContourSegmentSnapshot,
    HoleSnapshot,
    LocalFrame,
    PartDrawingSnapshot,
    Point3D,
    Vector3D,
)


SCHEMA_VERSION = "partDrawingSnapshot.v1"


def load_part_snapshot(path: Path) -> PartDrawingSnapshot:
    return parse_part_snapshot(json.loads(path.read_text(encoding="utf-8")))


def parse_part_snapshot(data: dict[str, Any]) -> PartDrawingSnapshot:
    if data.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schemaVersion: {data.get('schemaVersion')!r}")

    part = data.get("part") or {}
    part_position = str(part.get("partPosition") or "").strip()
    if not part_position:
        raise ValueError("partPosition is required")

    thickness = float(part.get("thickness") or 0.0)
    if thickness <= 0.0:
        raise ValueError("thickness must be positive")

    frame = part.get("localFrame") or {}
    outer_loop = tuple(_segment(item) for item in part.get("outerLoop") or [])
    if len(outer_loop) < 3:
        raise ValueError("outerLoop requires at least three segments")

    return PartDrawingSnapshot(
        schema_version=SCHEMA_VERSION,
        exporter_version=str(data.get("exporterVersion") or ""),
        model_identifier=str(data.get("modelIdentifier") or ""),
        exported_at=str(data.get("exportedAt") or ""),
        part_id=str(part.get("partId") or ""),
        part_position=part_position,
        assembly_id=str(part.get("assemblyId") or ""),
        name=str(part.get("name") or ""),
        profile=str(part.get("profile") or ""),
        material=str(part.get("material") or ""),
        quantity=max(1, int(part.get("quantity") or 1)),
        thickness=thickness,
        local_frame=LocalFrame(
            origin=_point(frame.get("origin")),
            x_axis=_vector(frame.get("xAxis")),
            y_axis=_vector(frame.get("yAxis")),
            normal=_vector(frame.get("normal")),
        ),
        outer_loop=outer_loop,
        inner_loops=tuple(
            tuple(_segment(segment) for segment in loop)
            for loop in part.get("innerLoops") or []
        ),
        holes=tuple(_hole(item) for item in part.get("holes") or []),
        cuts=tuple(part.get("cuts") or []),
        source_evidence=tuple(str(item) for item in part.get("sourceEvidence") or []),
    )


def safe_part_position(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" .")
    return safe or "unnamed-part"


def _point(value: Any) -> Point3D:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("3D point requires three coordinates")
    return Point3D(*(float(item) for item in value))


def _vector(value: Any) -> Vector3D:
    point = _point(value)
    return Vector3D(point.x, point.y, point.z)


def _segment(data: dict[str, Any]) -> ContourSegmentSnapshot:
    kind = str(data.get("kind") or "").upper()
    if kind not in {"LINE", "ARC"}:
        raise ValueError(f"unsupported contour segment kind: {kind!r}")
    return ContourSegmentSnapshot(
        kind=kind,
        start=_point(data.get("start")),
        end=_point(data.get("end")),
        center=_point(data["center"]) if data.get("center") is not None else None,
        clockwise=bool(data.get("clockwise", False)),
    )


def _hole(data: dict[str, Any]) -> HoleSnapshot:
    return HoleSnapshot(
        hole_id=str(data.get("holeId") or ""),
        kind=str(data.get("kind") or "ROUND").upper(),
        center=_point(data.get("center")),
        diameter=float(data.get("diameter") or 0.0),
        length=float(data.get("length") or 0.0),
        width=float(data.get("width") or 0.0),
        angle_deg=float(data.get("angleDeg") or 0.0),
    )
