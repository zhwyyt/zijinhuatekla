"""teklatest JSON -> PartFeatureSnapshot 纯格式转换."""
from __future__ import annotations

from typing import Any

from ..contracts.part import PartFeatureSnapshot


def adapt_snapshot(raw: dict[str, Any]) -> PartFeatureSnapshot:
    obb = {}
    obb_raw = raw.get("obb", {})
    if isinstance(obb_raw, dict):
        obb = {str(k): float(v) if v else 0.0 for k, v in obb_raw.items()}

    return PartFeatureSnapshot(
        part_id=str(raw.get("partId", "")),
        position=str(raw.get("partPosition", "")),
        name=str(raw.get("partName", "")),
        profile=str(raw.get("profile", "")),
        material=str(raw.get("material", "")),
        runtime_type=str(raw.get("runtimeType", "")),
        is_plate_like=bool(raw.get("isPlateLike", False)),
        is_special_shape=bool(raw.get("isSpecialShape", False)),
        thickness=float(raw.get("thickness") or 0),
        obb_dims=obb,
        contour_segment_lengths=[float(x) for x in raw.get("contourSegmentLengths", [])],
        contour_vertex_count=int(raw.get("contourVertexCount", 0)),
        concave_corner_count=int(raw.get("concaveCornerCount", 0)),
        hole_like_feature_count=int(raw.get("holeLikeFeatureCount", 0)),
        boolean_cut_count=int(raw.get("booleanCutCount", 0)),
        bolt_hole_count=int(raw.get("boltHoleCount", 0)),
        chamfer_count=int(raw.get("chamferCount", 0)),
        cutout_count=int(raw.get("cutoutCount", 0)),
        notch_count=int(raw.get("notchCount", 0)),
        bending_count=int(raw.get("bendingCount", 0)),
        weld_count=int(raw.get("weldCount", 0)),
        has_arc_contour=bool(raw.get("hasArcContour", False)),
        shape_type=str(raw.get("shapeType", "")),
        is_regular_shape=bool(raw.get("isRegularShape", True)),
    )


def adapt_snapshots(items: list[dict[str, Any]]) -> list[PartFeatureSnapshot]:
    return [adapt_snapshot(item) for item in items]