from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.ops import unary_union

from ..rules import as_float, text
from .box_main_material_segments import BoxMainMaterialSegmentGroup
from .box_part_spatial_relations import _parse_loop_points, _polygons_from_exported_section_loops, _polygons_from_exported_segments, _station_topology_from_part_loops


@dataclass(frozen=True)
class BoxStationTopologyDiagnostic:
    assembly_id: str
    station: float
    topology_status: str
    main_wall_loop_count: int
    usable_loop_count: int
    degenerate_loop_count: int
    union_geometry_type: str
    union_component_count: int
    inner_loop_count: int
    topology_area: float
    topology_bounds: str
    evidence_codes: list[str]
    station_scope: str = ""
    trigger_part_summaries: list[dict[str, object]] = field(default_factory=list)
    loop_summaries: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "station": round(self.station, 3),
            "topology_status": self.topology_status,
            "main_wall_loop_count": self.main_wall_loop_count,
            "usable_loop_count": self.usable_loop_count,
            "degenerate_loop_count": self.degenerate_loop_count,
            "union_geometry_type": self.union_geometry_type,
            "union_component_count": self.union_component_count,
            "inner_loop_count": self.inner_loop_count,
            "topology_area": round(self.topology_area, 3),
            "topology_bounds": self.topology_bounds,
            "evidence_codes": list(self.evidence_codes),
            "station_scope": self.station_scope,
            "trigger_part_summaries": list(self.trigger_part_summaries),
            "loop_summaries": list(self.loop_summaries),
        }


def diagnose_box_station_topology(
    assembly: dict[str, Any],
    main_wall_groups: list[BoxMainMaterialSegmentGroup],
) -> list[BoxStationTopologyDiagnostic]:
    main_wall_ids = {part_id for group in main_wall_groups for part_id in group.part_ids}
    if not main_wall_ids:
        return []
    part_index = {
        text(part.get("partId")): part
        for part in assembly.get("parts", [])
        if text(part.get("partId"))
    }
    part_positions = {part_id: text(part.get("partPosition")) for part_id, part in part_index.items()}
    metadata = assembly.get("metadata", {})
    evidence = metadata.get("boxSectionEvidence", {}) if isinstance(metadata, dict) else {}
    station_loops = evidence.get("stationLoops", []) if isinstance(evidence, dict) else []
    if not isinstance(station_loops, list):
        return []
    return [
        _diagnose_station_loop(text(assembly.get("assemblyId")), station, main_wall_ids, part_positions, part_index)
        for station in station_loops
        if isinstance(station, dict)
    ]


def _diagnose_station_loop(
    assembly_id: str,
    station: dict[str, Any],
    main_wall_ids: set[str],
    part_positions: dict[str, str],
    part_index: dict[str, dict[str, Any]],
) -> BoxStationTopologyDiagnostic:
    loop_summaries: list[dict[str, object]] = []
    usable_polygons = []
    main_wall_loop_count = 0
    degenerate_loop_count = 0
    for part_loop in station.get("partLoops", []) or []:
        if not isinstance(part_loop, dict):
            continue
        part_id = text(part_loop.get("partId"))
        if part_id not in main_wall_ids:
            continue
        main_wall_loop_count += 1
        exported_loop_polygons = _polygons_from_exported_section_loops(part_loop.get("sectionLoops"))
        exported_segment_polygons = _polygons_from_exported_segments(part_loop.get("segments"))
        points = _parse_loop_points(part_loop.get("points"))
        summary = _loop_summary(
            part_id,
            part_positions.get(part_id, ""),
            points,
            exported_loop_polygons,
            exported_segment_polygons,
        )
        loop_summaries.append(summary)
        if summary["is_degenerate"]:
            degenerate_loop_count += 1
        if exported_loop_polygons:
            usable_polygons.extend(exported_loop_polygons)
        elif exported_segment_polygons:
            usable_polygons.extend(exported_segment_polygons)
        else:
            polygon = _usable_polygon(points)
            if polygon is not None:
                usable_polygons.append(polygon)

    union_geometry = unary_union(usable_polygons) if usable_polygons else None
    topology = _station_topology_from_part_loops(station.get("partLoops", []), main_wall_ids)
    inner_loop_count = len(topology.get("inner_loops", [])) if topology else 0
    topology_geometry = topology.get("geometry") if topology else None
    station_value = as_float(station.get("station"))
    scope, trigger_summaries, scope_codes = _station_scope(station, station_value, main_wall_ids, part_index)
    status = _topology_status(main_wall_loop_count, len(usable_polygons), degenerate_loop_count, union_geometry, inner_loop_count, scope)
    evidence_codes = _evidence_codes(main_wall_loop_count, len(usable_polygons), degenerate_loop_count, union_geometry, inner_loop_count, status)
    evidence_codes.extend(scope_codes)
    return BoxStationTopologyDiagnostic(
        assembly_id=assembly_id,
        station=station_value,
        topology_status=status,
        main_wall_loop_count=main_wall_loop_count,
        usable_loop_count=len(usable_polygons),
        degenerate_loop_count=degenerate_loop_count,
        union_geometry_type=union_geometry.geom_type if union_geometry is not None else "",
        union_component_count=_component_count(union_geometry),
        inner_loop_count=inner_loop_count,
        topology_area=float(topology_geometry.area) if topology_geometry is not None else 0.0,
        topology_bounds=_bounds_text(topology_geometry),
        evidence_codes=_dedupe(evidence_codes),
        station_scope=scope,
        trigger_part_summaries=trigger_summaries,
        loop_summaries=loop_summaries,
    )


def _loop_summary(
    part_id: str,
    part_position: str,
    points: list[tuple[float, float]],
    exported_loop_polygons: list[Polygon] | None = None,
    exported_segment_polygons: list[Polygon] | None = None,
) -> dict[str, object]:
    polygon = Polygon(points) if len(points) >= 3 else None
    original_area = float(polygon.area) if polygon is not None else 0.0
    original_valid = bool(polygon.is_valid) if polygon is not None else False
    repaired = polygon if polygon is not None and polygon.is_valid else (polygon.buffer(0) if polygon is not None else None)
    repaired_area = float(repaired.area) if repaired is not None and not repaired.is_empty else 0.0
    exported_loop_polygons = exported_loop_polygons or []
    exported_segment_polygons = exported_segment_polygons or []
    has_exported_loop = bool(exported_loop_polygons)
    has_exported_segment_polygon = bool(exported_segment_polygons)
    is_degenerate = not (has_exported_loop or has_exported_segment_polygon) and (len(points) < 3 or original_area <= 1e-6 or not original_valid)
    return {
        "part_id": part_id,
        "part_position": part_position,
        "point_count": len(points),
        "area": round(original_area, 3),
        "is_valid": original_valid,
        "repaired_area": round(repaired_area, 3),
        "is_degenerate": is_degenerate,
        "has_exported_section_loop": has_exported_loop,
        "has_exported_segment_polygon": has_exported_segment_polygon,
        "exported_section_loop_area": round(sum(polygon.area for polygon in exported_loop_polygons), 3),
        "exported_segment_polygon_area": round(sum(polygon.area for polygon in exported_segment_polygons), 3),
        "bounds": _point_bounds_text(points),
    }


def _usable_polygon(points: list[tuple[float, float]]) -> Polygon | None:
    if len(points) < 3:
        return None
    polygon = Polygon(points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty or polygon.area <= 1e-6:
        return None
    return polygon


def _evidence_codes(
    main_wall_loop_count: int,
    usable_loop_count: int,
    degenerate_loop_count: int,
    union_geometry: Any,
    inner_loop_count: int,
    topology_status: str = "",
) -> list[str]:
    codes = []
    if main_wall_loop_count == 0:
        codes.append("MISSING_MAIN_WALL_STATION_LOOPS")
    if degenerate_loop_count:
        codes.append("DEGENERATE_OR_INVALID_MAIN_WALL_LOOP")
    if usable_loop_count == 0:
        codes.append("NO_USABLE_MAIN_WALL_POLYGON")
    if _component_count(union_geometry) > 1:
        codes.append("UNION_HAS_MULTIPLE_COMPONENTS")
    if inner_loop_count:
        codes.append("STATION_HAS_INNER_CAVITY_LOOP")
    elif topology_status == "END_TRANSITION_NOT_BODY_CORE":
        codes.append("END_TRANSITION_NOT_BODY_CORE")
    else:
        codes.append("STATION_TOPOLOGY_NOT_CLOSED")
    return codes


def _topology_status(
    main_wall_loop_count: int,
    usable_loop_count: int,
    degenerate_loop_count: int,
    union_geometry: Any,
    inner_loop_count: int,
    station_scope: str = "",
) -> str:
    if main_wall_loop_count == 0:
        return "MISSING_MAIN_WALL_LOOPS"
    if usable_loop_count == 0:
        return "NO_USABLE_MAIN_WALL_POLYGON"
    if inner_loop_count > 0:
        return "CLOSED_WITH_CAVITY"
    if degenerate_loop_count:
        return "STATION_TOPOLOGY_NOT_CLOSED"
    if _component_count(union_geometry) > 1:
        if station_scope == "END_TRANSITION_OR_ATTACHMENT_TRIGGERED":
            return "END_TRANSITION_NOT_BODY_CORE"
        return "STATION_TOPOLOGY_NOT_CLOSED"
    return "CLOSED_WITHOUT_CAVITY"


def _component_count(geometry: Any) -> int:
    if geometry is None:
        return 0
    if isinstance(geometry, Polygon):
        return 1
    if isinstance(geometry, MultiPolygon):
        return len(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        return sum(1 for item in geometry.geoms if isinstance(item, Polygon))
    return 0


def _bounds_text(geometry: Any) -> str:
    if geometry is None or geometry.is_empty:
        return ""
    return ";".join(f"{value:.1f}" for value in geometry.bounds)


def _point_bounds_text(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    us = [point[0] for point in points]
    vs = [point[1] for point in points]
    return f"{min(us):.1f};{min(vs):.1f};{max(us):.1f};{max(vs):.1f}"


def _station_scope(
    station: dict[str, Any],
    station_value: float,
    main_wall_ids: set[str],
    part_index: dict[str, dict[str, Any]],
) -> tuple[str, list[dict[str, object]], list[str]]:
    support_ids = [text(part_id) for part_id in station.get("supportPartIds", [])]
    main_support_ids = [part_id for part_id in support_ids if part_id in main_wall_ids]
    trigger_summaries = []
    for part_id in support_ids:
        if part_id in main_wall_ids:
            continue
        part = part_index.get(part_id, {})
        evidence = part.get("mainMaterialEvidence", {}) if isinstance(part, dict) else {}
        projection = evidence.get("sectionProjectionEvidence", {}) if isinstance(evidence, dict) else {}
        trigger_summaries.append({
            "part_id": part_id,
            "part_position": text(part.get("partPosition")),
            "axis_station_start": round(as_float(evidence.get("axisStationStart")), 3),
            "axis_station_end": round(as_float(evidence.get("axisStationEnd")), 3),
            "normal_projection_magnitude": round(as_float(projection.get("normalProjectionMagnitude")), 6),
        })
    if len(main_support_ids) >= 4:
        return "BODY_CORE", trigger_summaries, ["BODY_CORE_STATION"]
    if _near_any_main_wall_end(station_value, main_support_ids, part_index) or trigger_summaries:
        return "END_TRANSITION_OR_ATTACHMENT_TRIGGERED", trigger_summaries, ["END_TRANSITION_OR_ATTACHMENT_TRIGGERED_STATION"]
    return "INSUFFICIENT_SCOPE_EVIDENCE", trigger_summaries, ["STATION_SCOPE_INSUFFICIENT_EVIDENCE"]


def _near_any_main_wall_end(station_value: float, main_support_ids: list[str], part_index: dict[str, dict[str, Any]]) -> bool:
    for part_id in main_support_ids:
        part = part_index.get(part_id, {})
        evidence = part.get("mainMaterialEvidence", {}) if isinstance(part, dict) else {}
        start = as_float(evidence.get("axisStationStart"))
        end = as_float(evidence.get("axisStationEnd"))
        if min(abs(station_value - start), abs(station_value - end)) <= 50.0:
            return True
    return False


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


