from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..rules import as_float, text
from .box_main_material_segments import BoxMainMaterialSegmentGroup


@dataclass(frozen=True)
class BoxPartSpatialRelation:
    assembly_id: str
    part_id: str
    part_position: str
    relation_to_box_body: str
    station_range: str
    section_relation: str
    connected_main_wall_ids: list[str]
    evidence_codes: list[str]
    confidence: float
    issue_category: str = ""
    evidence_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "part_id": self.part_id,
            "part_position": self.part_position,
            "relation_to_box_body": self.relation_to_box_body,
            "station_range": self.station_range,
            "section_relation": self.section_relation,
            "connected_main_wall_ids": list(self.connected_main_wall_ids),
            "evidence_codes": list(self.evidence_codes),
            "confidence": round(self.confidence, 3),
            "issue_category": self.issue_category,
            "evidence_summary": dict(self.evidence_summary),
        }


def classify_box_part_spatial_relations(
    assembly: dict[str, Any],
    member: dict[str, Any] | None,
    main_wall_groups: list[BoxMainMaterialSegmentGroup],
    outside_part_ids: set[str] | None = None,
) -> list[BoxPartSpatialRelation]:
    assembly_id = text(assembly.get("assemblyId"))
    main_wall_ids = {part_id for group in main_wall_groups for part_id in group.part_ids}
    enclosure = _main_wall_projected_enclosure(assembly, member, main_wall_ids)
    section_index = _section_relation_index(member)
    member_parts = _member_part_index(member)
    relationship_edges = _relationship_edges(assembly)
    outside_ids = outside_part_ids or set()
    rows = []
    for part in assembly.get("parts", []):
        part_id = text(part.get("partId"))
        if not part_id:
            continue
        member_part = member_parts.get(part_id, {})
        connected_main_wall_ids = _connected_main_wall_ids(part_id, main_wall_ids, relationship_edges)
        rows.append(
            _classify_part(
                assembly_id,
                part,
                member_part,
                section_index.get(part_id),
                main_wall_ids,
                connected_main_wall_ids,
                part_id in outside_ids,
                enclosure,
            )
        )
    return rows


def _classify_part(
    assembly_id: str,
    part: dict[str, Any],
    member_part: dict[str, Any],
    section: dict[str, str] | None,
    main_wall_ids: set[str],
    connected_main_wall_ids: list[str],
    is_outside_part: bool = False,
    enclosure: dict[str, float] | None = None,
) -> BoxPartSpatialRelation:
    part_id = text(part.get("partId"))
    part_position = text(part.get("partPosition"))
    station_range = _station_range(part, member_part)
    evidence_summary = {
        "name": text(part.get("name") or member_part.get("Name")),
        "profile": text(part.get("profileString") or member_part.get("ProfileString")),
        "member_role": _member_role(member_part),
    }
    if section:
        evidence_summary.update(section)
    projection_relation = _projected_enclosure_relation(part, enclosure)
    if projection_relation:
        evidence_summary.update(_projection_summary(part))

    if part_id in main_wall_ids:
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "MAIN_WALL",
            station_range,
            "outer_wall_trace",
            connected_main_wall_ids,
            ["BOX_MAIN_WALL_CONFIRMED_SET"],
            0.98,
            evidence_summary=evidence_summary,
        )

    if projection_relation == "mixed":
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "BOUNDARY_OR_THROUGH",
            station_range,
            "projected_centroid_mixed_across_station_loops",
            connected_main_wall_ids,
            ["PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS"],
            0.78,
            evidence_summary=evidence_summary,
        )

    if projection_relation == "inside":
        codes = ["PROJECTED_CENTROID_INSIDE_MAIN_WALL_ENCLOSURE"]
        if enclosure and enclosure.get("source"):
            codes.append(text(enclosure.get("source")))
        if connected_main_wall_ids:
            codes.append("CONNECTED_TO_MAIN_WALL")
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "INSIDE_BODY",
            station_range,
            "projected_centroid_inside_enclosure",
            connected_main_wall_ids,
            codes,
            0.9,
            evidence_summary=evidence_summary,
        )

    if projection_relation == "outside":
        codes = ["PROJECTED_CENTROID_OUTSIDE_MAIN_WALL_ENCLOSURE"]
        if enclosure and enclosure.get("source"):
            codes.append(text(enclosure.get("source")))
        if is_outside_part:
            codes.append("OUTSIDE_APPENDAGE_CLUSTER")
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "OUTSIDE_ATTACHMENT",
            station_range,
            "projected_centroid_outside_enclosure",
            connected_main_wall_ids,
            codes,
            0.88,
            evidence_summary=evidence_summary,
        )
    if section and section.get("section_relation") == "boundary_or_through":
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "BOUNDARY_OR_THROUGH",
            station_range,
            "boundary_or_through",
            connected_main_wall_ids,
            ["SECTION_SPANS_BOX_BODY"],
            0.72,
            evidence_summary=evidence_summary,
        )

    if section and section.get("section_relation") == "inside_body":
        codes = ["SECTION_INSIDE_CAVITY_TRACE"]
        if connected_main_wall_ids:
            codes.append("CONNECTED_TO_MAIN_WALL")
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "INSIDE_BODY",
            station_range,
            "inside_body",
            connected_main_wall_ids,
            codes,
            0.86,
            evidence_summary=evidence_summary,
        )

    if is_outside_part:
        codes = ["OUTSIDE_APPENDAGE_CLUSTER"]
        if connected_main_wall_ids:
            codes.append("CONNECTED_TO_MAIN_WALL")
        return _relation(
            assembly_id,
            part_id,
            part_position,
            "OUTSIDE_ATTACHMENT",
            station_range,
            text(section.get("section_relation")) if section else "outside_geometry_hint",
            connected_main_wall_ids,
            codes,
            0.74,
            evidence_summary=evidence_summary,
        )

    return _relation(
        assembly_id,
        part_id,
        part_position,
        "INSUFFICIENT_EVIDENCE",
        station_range,
        text(section.get("section_relation")) if section else "not_sampled",
        connected_main_wall_ids,
        _insufficient_evidence_codes(member_part),
        0.2,
        issue_category="FEATURE",
        evidence_summary=evidence_summary,
    )


def _relation(
    assembly_id: str,
    part_id: str,
    part_position: str,
    relation_to_box_body: str,
    station_range: str,
    section_relation: str,
    connected_main_wall_ids: list[str],
    evidence_codes: list[str],
    confidence: float,
    issue_category: str = "",
    evidence_summary: dict[str, str] | None = None,
) -> BoxPartSpatialRelation:
    return BoxPartSpatialRelation(
        assembly_id=assembly_id,
        part_id=part_id,
        part_position=part_position,
        relation_to_box_body=relation_to_box_body,
        station_range=station_range,
        section_relation=section_relation,
        connected_main_wall_ids=connected_main_wall_ids,
        evidence_codes=_dedupe(evidence_codes),
        confidence=confidence,
        issue_category=issue_category,
        evidence_summary=evidence_summary or {},
    )



def _main_wall_projected_enclosure(assembly: dict[str, Any], member: dict[str, Any] | None, main_wall_ids: set[str]) -> dict[str, Any] | None:
    exported_loop = _exported_outer_loop(assembly, member, main_wall_ids)
    if len(exported_loop) >= 3:
        return {"kind": "polygon", "outer_loop": exported_loop, "station_loops": _exported_station_main_wall_loops(assembly, main_wall_ids), "source": "EXPORTED_BOX_OUTER_LOOP_POLYGON"}

    points: list[tuple[float, float]] = []
    for part in assembly.get("parts", []):
        if text(part.get("partId")) not in main_wall_ids:
            continue
        projection = _section_projection(part)
        bounds_min = projection.get("projectedBoundsMin", {}) if isinstance(projection, dict) else {}
        bounds_max = projection.get("projectedBoundsMax", {}) if isinstance(projection, dict) else {}
        if not bounds_min or not bounds_max:
            continue
        min_u = as_float(bounds_min.get("u"))
        max_u = as_float(bounds_max.get("u"))
        min_v = as_float(bounds_min.get("v"))
        max_v = as_float(bounds_max.get("v"))
        points.extend([(min_u, min_v), (max_u, max_v)])
    if len(points) < 4:
        return None
    return {
        "kind": "bounds_fallback",
        "source": "MAIN_WALL_PROJECTED_BOUNDS_FALLBACK",
        "outer_min_u": min(point[0] for point in points),
        "outer_max_u": max(point[0] for point in points),
        "outer_min_v": min(point[1] for point in points),
        "outer_max_v": max(point[1] for point in points),
    }


def _exported_outer_loop(assembly: dict[str, Any], member: dict[str, Any] | None, main_wall_ids: set[str]) -> list[tuple[float, float]]:
    metadata = assembly.get("metadata", {})
    evidence = metadata.get("boxSectionEvidence", {}) if isinstance(metadata, dict) else {}
    candidates = []
    if isinstance(evidence, dict):
        main_wall_loop = _outer_loop_from_station_part_loops(evidence, main_wall_ids)
        if len(main_wall_loop) >= 3:
            return main_wall_loop
        candidates.append(evidence.get("outerLoop"))
    for sample in (member or {}).get("Samples", []) or []:
        features = sample.get("SectionFeatures", {}) if isinstance(sample, dict) else {}
        if isinstance(features, dict):
            candidates.append(features.get("OuterLoop") or features.get("outerLoop"))
    for candidate in candidates:
        loop = _parse_loop_points(candidate)
        if len(loop) >= 3:
            return loop
    return []






def _exported_station_main_wall_loops(assembly: dict[str, Any], main_wall_ids: set[str]) -> list[dict[str, Any]]:
    metadata = assembly.get("metadata", {})
    evidence = metadata.get("boxSectionEvidence", {}) if isinstance(metadata, dict) else {}
    station_loops = evidence.get("stationLoops", []) if isinstance(evidence, dict) else []
    result = []
    if not isinstance(station_loops, list):
        return result
    for station in station_loops:
        if not isinstance(station, dict):
            continue
        points: list[tuple[float, float]] = []
        for part_loop in station.get("partLoops", []) or []:
            if not isinstance(part_loop, dict) or text(part_loop.get("partId")) not in main_wall_ids:
                continue
            points.extend(_parse_loop_points(part_loop.get("points")))
        loop = _convex_hull(points)
        if len(loop) >= 3:
            result.append({"station": as_float(station.get("station")), "outer_loop": loop})
    return result
def _outer_loop_from_station_part_loops(evidence: dict[str, Any], main_wall_ids: set[str]) -> list[tuple[float, float]]:
    station_loops = evidence.get("stationLoops", [])
    if not isinstance(station_loops, list):
        return []
    best_loop: list[tuple[float, float]] = []
    best_area = 0.0
    for station in station_loops:
        if not isinstance(station, dict):
            continue
        points: list[tuple[float, float]] = []
        for part_loop in station.get("partLoops", []) or []:
            if not isinstance(part_loop, dict) or text(part_loop.get("partId")) not in main_wall_ids:
                continue
            points.extend(_parse_loop_points(part_loop.get("points")))
        loop = _convex_hull(points)
        area = _polygon_area(loop)
        if len(loop) >= 3 and area > best_area:
            best_loop = loop
            best_area = area
    return best_loop


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    unique = sorted(set((round(u, 6), round(v, 6)) for u, v in points))
    if len(unique) <= 3:
        return unique

    def cross(origin: tuple[float, float], left: tuple[float, float], right: tuple[float, float]) -> float:
        return ((left[0] - origin[0]) * (right[1] - origin[1])) - ((left[1] - origin[1]) * (right[0] - origin[0]))

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) / 2.0
def _parse_loop_points(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, list):
        return []
    points = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if "u" in item or "v" in item:
            points.append((as_float(item.get("u")), as_float(item.get("v"))))
        elif "X" in item or "Y" in item:
            points.append((as_float(item.get("X")), as_float(item.get("Y"))))
        elif "x" in item or "y" in item:
            points.append((as_float(item.get("x")), as_float(item.get("y"))))
    return points


def _projected_enclosure_relation(part: dict[str, Any], enclosure: dict[str, Any] | None) -> str:
    if not enclosure:
        return ""
    projection = _section_projection(part)
    centroid = projection.get("projectedCentroid", {}) if isinstance(projection, dict) else {}
    if not centroid:
        return ""
    u = as_float(centroid.get("u"))
    v = as_float(centroid.get("v"))
    if enclosure.get("kind") == "polygon":
        station_relations = _station_loop_relations(part, enclosure, (u, v))
        if station_relations:
            unique = set(station_relations)
            if len(unique) > 1:
                return "mixed"
            return station_relations[0]
        loop = enclosure.get("outer_loop", [])
        return "inside" if _point_in_polygon((u, v), loop) else "outside"
    tolerance = 1.0
    inside_outer = (
        enclosure["outer_min_u"] - tolerance <= u <= enclosure["outer_max_u"] + tolerance
        and enclosure["outer_min_v"] - tolerance <= v <= enclosure["outer_max_v"] + tolerance
    )
    return "inside" if inside_outer else "outside"




def _station_loop_relations(part: dict[str, Any], enclosure: dict[str, Any], point: tuple[float, float]) -> list[str]:
    station_loops = enclosure.get("station_loops", [])
    if not isinstance(station_loops, list) or not station_loops:
        return []
    result = []
    for station in _part_probe_stations(part):
        nearest = min(station_loops, key=lambda item: abs(as_float(item.get("station")) - station))
        loop = nearest.get("outer_loop", []) if isinstance(nearest, dict) else []
        if isinstance(loop, list) and loop:
            result.append("inside" if _point_in_polygon(point, loop) else "outside")
    return result


def _part_probe_stations(part: dict[str, Any]) -> list[float]:
    evidence = part.get("mainMaterialEvidence", {})
    if not isinstance(evidence, dict):
        return []
    start = as_float(evidence.get("axisStationStart"))
    end = as_float(evidence.get("axisStationEnd"))
    if start == 0 and end == 0:
        return []
    if end < start:
        start, end = end, start
    length = max(0.0, end - start)
    offset = min(25.0, length * 0.1)
    probes = [start + offset, (start + end) / 2.0, end - offset]
    result = []
    for station in probes:
        if station not in result:
            result.append(station)
    return result
def _nearest_station_loop(part: dict[str, Any], enclosure: dict[str, Any]) -> list[tuple[float, float]]:
    station_loops = enclosure.get("station_loops", [])
    if not isinstance(station_loops, list) or not station_loops:
        return []
    evidence = part.get("mainMaterialEvidence", {})
    if not isinstance(evidence, dict):
        return []
    center_station = (as_float(evidence.get("axisStationStart")) + as_float(evidence.get("axisStationEnd"))) / 2.0
    nearest = min(station_loops, key=lambda item: abs(as_float(item.get("station")) - center_station))
    loop = nearest.get("outer_loop", []) if isinstance(nearest, dict) else []
    return loop if isinstance(loop, list) else []
def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    u, v = point
    inside = False
    count = len(polygon)
    for index in range(count):
        u1, v1 = polygon[index]
        u2, v2 = polygon[(index + 1) % count]
        if _point_on_segment(u, v, u1, v1, u2, v2):
            return True
        intersects = (v1 > v) != (v2 > v)
        if intersects:
            cross_u = ((u2 - u1) * (v - v1) / (v2 - v1)) + u1
            if u < cross_u:
                inside = not inside
    return inside


def _point_on_segment(u: float, v: float, u1: float, v1: float, u2: float, v2: float) -> bool:
    tolerance = 1e-6
    cross = ((u - u1) * (v2 - v1)) - ((v - v1) * (u2 - u1))
    if abs(cross) > tolerance:
        return False
    return min(u1, u2) - tolerance <= u <= max(u1, u2) + tolerance and min(v1, v2) - tolerance <= v <= max(v1, v2) + tolerance

def _projection_summary(part: dict[str, Any]) -> dict[str, str]:
    projection = _section_projection(part)
    centroid = projection.get("projectedCentroid", {}) if isinstance(projection, dict) else {}
    return {
        "projected_centroid_u": f"{as_float(centroid.get('u')):.1f}",
        "projected_centroid_v": f"{as_float(centroid.get('v')):.1f}",
    }


def _section_projection(part: dict[str, Any]) -> dict[str, Any]:
    evidence = part.get("mainMaterialEvidence", {})
    projection = evidence.get("sectionProjectionEvidence", {}) if isinstance(evidence, dict) else {}
    return projection if isinstance(projection, dict) else {}
def _section_relation_index(member: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    if not member:
        return {}
    result: dict[str, dict[str, str]] = {}
    for sample in member.get("Samples", []):
        features = sample.get("SectionFeatures", {})
        if sample.get("IsAbnormal") is True:
            continue
        if as_float(features.get("ClosedLoops")) < 1 or as_float(features.get("CavityCount")) < 1:
            continue
        outer_width = as_float(features.get("OuterWidth"))
        outer_height = as_float(features.get("OuterHeight"))
        for section_part in sample.get("SectionParts", []):
            part_id = text(section_part.get("PartId"))
            if not part_id:
                continue
            relation = _section_relation(section_part, outer_width, outer_height)
            previous = result.get(part_id)
            if previous and _section_priority(previous["section_relation"]) >= _section_priority(relation):
                continue
            result[part_id] = {
                "section_relation": relation,
                "section_sample_id": text(sample.get("SampleId")),
                "section_role_hint": text(section_part.get("RoleHint")),
                "section_center_x": f"{as_float(section_part.get('Center2D', {}).get('X')):.1f}",
                "section_center_y": f"{as_float(section_part.get('Center2D', {}).get('Y')):.1f}",
                "section_cut_span_x": f"{as_float(section_part.get('CutSpanX')):.1f}",
                "section_cut_span_y": f"{as_float(section_part.get('CutSpanY')):.1f}",
            }
    return result


def _section_relation(section_part: dict[str, Any], outer_width: float, outer_height: float) -> str:
    span_x = as_float(section_part.get("CutSpanX"))
    span_y = as_float(section_part.get("CutSpanY"))
    total = as_float(section_part.get("TotalCutLength"))
    max_span = max(span_x, span_y, total)
    if outer_width > 0 and outer_height > 0:
        if span_x >= outer_width * 0.75 and span_y >= outer_height * 0.75:
            return "boundary_or_through"
        if max_span >= max(outer_width, outer_height) * 0.65:
            return "outer_wall_trace"
    role = text(section_part.get("RoleHint"))
    if role in {"stiffener_candidate", "flange_candidate", "web_candidate"}:
        return "inside_body"
    return "sampled_unknown"


def _section_priority(relation: str) -> int:
    return {
        "boundary_or_through": 4,
        "outer_wall_trace": 3,
        "inside_body": 2,
        "sampled_unknown": 1,
    }.get(relation, 0)


def _member_part_index(member: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not member:
        return {}
    return {text(part.get("PartId")): part for part in member.get("Parts", []) if text(part.get("PartId"))}


def _relationship_edges(assembly: dict[str, Any]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for rel in assembly.get("relationships", []):
        edge_type = text(rel.get("edgeType")).lower()
        if edge_type not in {"weld", "contact"}:
            continue
        part_a = text(rel.get("partIdA"))
        part_b = text(rel.get("partIdB"))
        if part_a and part_b and part_a != part_b:
            edges.add(tuple(sorted((part_a, part_b))))
    return edges


def _connected_main_wall_ids(part_id: str, main_wall_ids: set[str], edges: set[tuple[str, str]]) -> list[str]:
    connected = []
    for edge in edges:
        if part_id not in edge:
            continue
        other = edge[0] if edge[1] == part_id else edge[1]
        if other in main_wall_ids and other not in connected:
            connected.append(other)
    return sorted(connected)


def _station_range(part: dict[str, Any], member_part: dict[str, Any]) -> str:
    evidence = part.get("mainMaterialEvidence", {})
    start = as_float(evidence.get("axisStationStart"))
    end = as_float(evidence.get("axisStationEnd"))
    projection = member_part.get("AxisProjection", {})
    if (start == 0 and end == 0) and isinstance(projection, dict):
        start = as_float(projection.get("Start"))
        end = as_float(projection.get("End"))
    if start == 0 and end == 0:
        return ""
    return f"{start:.1f}-{end:.1f}"


def _outer_side_candidate(member_part: dict[str, Any]) -> bool:
    hints = member_part.get("GeometryHints", {})
    return isinstance(hints, dict) and hints.get("OuterSideCandidate") is True


def _member_role(member_part: dict[str, Any]) -> str:
    return text(member_part.get("Role") or member_part.get("role"))


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

def _insufficient_evidence_codes(member_part: dict[str, Any]) -> list[str]:
    codes = ["MISSING_SECTION_OR_SIDE_EVIDENCE"]
    if _outer_side_candidate(member_part):
        codes.append("OUTER_SIDE_GEOMETRY_HINT_AUXILIARY")
    return codes







