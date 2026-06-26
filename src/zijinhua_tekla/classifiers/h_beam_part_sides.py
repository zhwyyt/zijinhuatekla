from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..rules import as_float, parse_pl, text


H_SIDE_TOP_FLANGE_OUTER = "TOP_FLANGE_OUTER"
H_SIDE_BOTTOM_FLANGE_OUTER = "BOTTOM_FLANGE_OUTER"
H_SIDE_WEB_LEFT = "WEB_LEFT"
H_SIDE_WEB_RIGHT = "WEB_RIGHT"
H_SIDE_BOUNDARY = "BOUNDARY_OR_AMBIGUOUS"
H_SIDE_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class HBeamPartSide:
    assembly_id: str
    part_id: str
    part_position: str
    part_name: str
    h_side: str
    confidence: float
    issue_category: str = ""
    evidence_codes: list[str] = field(default_factory=list)
    evidence_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "part_id": self.part_id,
            "part_position": self.part_position,
            "part_name": self.part_name,
            "h_side": self.h_side,
            "confidence": round(self.confidence, 3),
            "issue_category": self.issue_category,
            "evidence_codes": list(self.evidence_codes),
            "evidence_summary": dict(self.evidence_summary),
        }


@dataclass(frozen=True)
class _HBeamSectionFrame:
    web_center_u: float
    web_half_thickness: float
    top_outer_v: float
    bottom_outer_v: float
    web_top_v: float
    web_bottom_v: float
    evidence_codes: tuple[str, ...] = ()


def classify_h_beam_part_sides(
    assembly: dict[str, Any],
    member: dict[str, Any] | float | int | None = None,
    tol: float = 2.0,
) -> list[HBeamPartSide]:
    """Classify non-main-material parts onto four local H-beam faces.

    The classifier consumes exported section projection evidence instead of
    live Tekla API objects. Left/right are defined in the section U axis:
    values lower than the web center are left, higher values are right.
    """

    if isinstance(member, (int, float)):
        tol = float(member)
        member = None

    assembly_id = text(assembly.get("assemblyId"))
    parts = list(assembly.get("parts", []))
    roles = _main_material_parts(parts, member if isinstance(member, dict) else None)
    frame = _build_section_frame(roles)
    main_part_ids = {text(part.get("partId")) for values in roles.values() for part in values if text(part.get("partId"))}

    station_frames = _h_beam_station_frames(assembly)
    direct_profile_frame = _uses_direct_h_profile_frame(assembly)
    rows: list[HBeamPartSide] = []
    for part in parts:
        part_id = text(part.get("partId"))
        if part_id in main_part_ids:
            continue
        rows.append(_classify_part(assembly_id, part, _frame_for_part(part, frame, station_frames, direct_profile_frame), tol))
    return rows


def _uses_direct_h_profile_frame(assembly: dict[str, Any]) -> bool:
    metadata = assembly.get("metadata")
    if not isinstance(metadata, dict):
        return False
    evidence = metadata.get("hBeamSectionEvidence")
    return isinstance(evidence, dict) and text(evidence.get("source")) == "directHProfileSectionFrame.v1"


def _h_beam_station_frames(assembly: dict[str, Any]) -> list[tuple[float, _HBeamSectionFrame]]:
    metadata = assembly.get("metadata")
    if not isinstance(metadata, dict):
        return []
    evidence = metadata.get("hBeamSectionEvidence")
    if not isinstance(evidence, dict):
        return []
    frame_codes = ["H_BEAM_STATION_LOCAL_FRAME"]
    if text(evidence.get("source")) == "directHProfileSectionFrame.v1":
        frame_codes.append("DIRECT_H_PROFILE_FRAME")
    frames: list[tuple[float, _HBeamSectionFrame]] = []
    for item in evidence.get("stationFrames") or []:
        if not isinstance(item, dict):
            continue
        frames.append(
            (
                as_float(item.get("station")),
                _HBeamSectionFrame(
                    web_center_u=as_float(item.get("webCenterU")),
                    web_half_thickness=max(1.0, as_float(item.get("webHalfThickness"), 1.0)),
                    top_outer_v=as_float(item.get("topOuterV")),
                    bottom_outer_v=as_float(item.get("bottomOuterV")),
                    web_top_v=as_float(item.get("webTopV")),
                    web_bottom_v=as_float(item.get("webBottomV")),
                    evidence_codes=tuple(frame_codes),
                ),
            )
        )
    return sorted(frames, key=lambda value: value[0])


def _frame_for_part(
    part: dict[str, Any],
    fallback: _HBeamSectionFrame | None,
    station_frames: list[tuple[float, _HBeamSectionFrame]],
    direct_profile_frame: bool = False,
) -> _HBeamSectionFrame | None:
    if not station_frames:
        return fallback
    station = _part_station_midpoint(part)
    if station is None:
        return fallback
    nearest_station, nearest_frame = min(station_frames, key=lambda item: abs(item[0] - station))
    if direct_profile_frame:
        return nearest_frame
    max_distance = max(75.0, _part_station_length(part) * 0.75)
    if abs(nearest_station - station) > max_distance:
        return fallback
    return nearest_frame

def _part_station_midpoint(part: dict[str, Any]) -> float | None:
    evidence = part.get("mainMaterialEvidence")
    if not isinstance(evidence, dict):
        return None
    start = as_float(evidence.get("axisStationStart"))
    end = as_float(evidence.get("axisStationEnd"))
    if start == 0 and end == 0:
        return None
    return (start + end) / 2.0


def _part_station_length(part: dict[str, Any]) -> float:
    evidence = part.get("mainMaterialEvidence")
    if not isinstance(evidence, dict):
        return 0.0
    return abs(as_float(evidence.get("axisStationEnd")) - as_float(evidence.get("axisStationStart")))
def _main_material_parts(parts: list[dict[str, Any]], member: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    roles: dict[str, list[dict[str, Any]]] = {"TOP_FLANGE": [], "WEB": [], "BOTTOM_FLANGE": [], "_EVIDENCE": []}
    for part in parts:
        name = text(part.get("name"))
        if "上翼缘" in name:
            roles["TOP_FLANGE"].append(part)
        elif "下翼缘" in name:
            roles["BOTTOM_FLANGE"].append(part)
        elif "腹板" in name:
            roles["WEB"].append(part)
    if roles["TOP_FLANGE"] and roles["WEB"] and roles["BOTTOM_FLANGE"]:
        roles["_EVIDENCE"].append({"code": "PART_NAME_MAIN_MATERIAL"})
        return roles

    role_parts = _main_material_parts_from_member_roles(parts, member)
    if role_parts is not None:
        return role_parts
    return roles


def _main_material_parts_from_member_roles(
    parts: list[dict[str, Any]], member: dict[str, Any] | None
) -> dict[str, list[dict[str, Any]]] | None:
    if not member:
        return None
    by_id = {text(part.get("partId")): part for part in parts}
    web_parts: list[dict[str, Any]] = []
    flange_parts: list[dict[str, Any]] = []
    for role in member.get("Classification", {}).get("PartRoles", []) or []:
        part = by_id.get(text(role.get("PartId")))
        if part is None:
            continue
        role_name = text(role.get("Role")).lower()
        if role_name in {"wall_candidate", "web_candidate"}:
            web_parts.append(part)
        elif role_name == "flange_candidate":
            flange_parts.append(part)
    flange_parts = [part for part in flange_parts if _projection_bounds(part) is not None]
    web_parts = [part for part in web_parts if _projection_bounds(part) is not None]
    if not web_parts or len(flange_parts) < 2:
        return None

    sorted_flanges = sorted(flange_parts, key=_part_centroid_v)
    return {
        "TOP_FLANGE": [sorted_flanges[-1]],
        "WEB": web_parts,
        "BOTTOM_FLANGE": [sorted_flanges[0]],
        "_EVIDENCE": [{"code": "MEMBER_PART_ROLES_MAIN_MATERIAL"}],
    }


def _build_section_frame(roles: dict[str, list[dict[str, Any]]]) -> _HBeamSectionFrame | None:
    web_bounds = [_projection_bounds(part) for part in roles.get("WEB", [])]
    top_bounds = [_projection_bounds(part) for part in roles.get("TOP_FLANGE", [])]
    bottom_bounds = [_projection_bounds(part) for part in roles.get("BOTTOM_FLANGE", [])]
    web_bounds = [bounds for bounds in web_bounds if bounds is not None]
    top_bounds = [bounds for bounds in top_bounds if bounds is not None]
    bottom_bounds = [bounds for bounds in bottom_bounds if bounds is not None]
    if not web_bounds or not top_bounds or not bottom_bounds:
        return None

    web_min_u = min(bounds[0] for bounds in web_bounds)
    web_max_u = max(bounds[1] for bounds in web_bounds)
    web_min_v = min(bounds[2] for bounds in web_bounds)
    web_max_v = max(bounds[3] for bounds in web_bounds)
    top_outer_v = max(bounds[3] for bounds in top_bounds)
    bottom_outer_v = min(bounds[2] for bounds in bottom_bounds)
    web_center_u = _main_web_center_u(roles.get("WEB", []), web_min_u, web_max_u)
    swept_half_width = max(1.0, (web_max_u - web_min_u) / 2.0)
    web_half_thickness = _web_half_thickness(roles.get("WEB", []), swept_half_width)
    evidence_codes = tuple(text(item.get("code")) for item in roles.get("_EVIDENCE", []) if text(item.get("code")))
    if web_half_thickness < swept_half_width:
        evidence_codes = (*evidence_codes, "WEB_THICKNESS_ESTIMATE_SPLIT")
    return _HBeamSectionFrame(
        web_center_u=web_center_u,
        web_half_thickness=web_half_thickness,
        top_outer_v=top_outer_v,
        bottom_outer_v=bottom_outer_v,
        web_top_v=web_max_v,
        web_bottom_v=web_min_v,
        evidence_codes=evidence_codes,
    )


def _classify_part(
    assembly_id: str,
    part: dict[str, Any],
    frame: _HBeamSectionFrame | None,
    tol: float,
) -> HBeamPartSide:
    if frame is None:
        return _row(
            assembly_id,
            part,
            H_SIDE_INSUFFICIENT,
            0.0,
            "FEATURE",
            ["MISSING_H_BEAM_MAIN_MATERIAL_FRAME"],
            {},
        )

    points = _sample_section_points(part)
    if not points:
        return _row(
            assembly_id,
            part,
            H_SIDE_INSUFFICIENT,
            0.0,
            "FEATURE",
            ["MISSING_SECTION_PROJECTION_EVIDENCE"],
            {},
        )

    votes = Counter(_point_side(point, frame, tol) for point in points)
    votes.pop("", None)
    if not votes:
        return _row(
            assembly_id,
            part,
            H_SIDE_INSUFFICIENT,
            0.0,
            "FEATURE",
            ["SECTION_POINTS_OUTSIDE_CLASSIFIABLE_ZONE"],
            _summary(frame, points, votes),
        )

    winner, winner_count = votes.most_common(1)[0]
    centroid_side = _centroid_side(part, frame, tol)
    total = len(points)
    if _has_conflicting_non_web_votes(votes, total) or _has_conflicting_web_votes_without_centroid(winner, votes, centroid_side):
        return _row(
            assembly_id,
            part,
            H_SIDE_BOUNDARY,
            min(0.55, winner_count / total),
            "GEOMETRY",
            ["PROJECTED_CONTOUR_VOTE", "MULTI_SIDE_VOTES", *frame.evidence_codes],
            _summary(frame, points, votes),
        )

    evidence = ["PROJECTED_CONTOUR_VOTE" if len(points) > 1 else "PROJECTED_CENTROID_VOTE"]
    if winner in {H_SIDE_WEB_LEFT, H_SIDE_WEB_RIGHT}:
        evidence.append("WEB_CENTER_U_SPLIT")
    else:
        evidence.append("FLANGE_OUTER_V_BOUNDARY")
    evidence.extend(frame.evidence_codes)
    return _row(
        assembly_id,
        part,
        winner,
        max(0.55, winner_count / total),
        "",
        evidence,
        _summary(frame, points, votes),
    )


def _point_side(point: tuple[float, float], frame: _HBeamSectionFrame, tol: float) -> str:
    u, v = point
    if v > frame.top_outer_v + tol:
        return H_SIDE_TOP_FLANGE_OUTER
    if v < frame.bottom_outer_v - tol:
        return H_SIDE_BOTTOM_FLANGE_OUTER
    if frame.web_bottom_v - tol <= v <= frame.web_top_v + tol:
        if u < frame.web_center_u - frame.web_half_thickness - tol:
            return H_SIDE_WEB_LEFT
        if u > frame.web_center_u + frame.web_half_thickness + tol:
            return H_SIDE_WEB_RIGHT
    return ""


def _has_conflicting_non_web_votes(votes: Counter[str], total: int) -> bool:
    strong = {side: count for side, count in votes.items() if count / total >= 0.25}
    if len(strong) <= 1:
        return False
    return set(strong) - {H_SIDE_WEB_LEFT, H_SIDE_WEB_RIGHT} != set()


def _has_conflicting_web_votes_without_centroid(winner: str, votes: Counter[str], centroid_side: str) -> bool:
    web_sides = {H_SIDE_WEB_LEFT, H_SIDE_WEB_RIGHT}
    if winner not in web_sides or set(votes) - web_sides:
        return False
    if len([side for side in web_sides if votes.get(side, 0) > 0]) <= 1:
        return False
    return centroid_side not in web_sides


def _sample_section_points(part: dict[str, Any]) -> list[tuple[float, float]]:
    projection = _projection(part)
    if not projection:
        return []
    points = _projection_contour_points(projection)
    centroid = _point(projection.get("projectedCentroid"))
    if centroid is not None:
        points.extend([centroid, centroid])
    if points:
        return points
    bounds = _projection_bounds(part)
    if bounds is None:
        return []
    min_u, max_u, min_v, max_v = bounds
    return [
        ((min_u + max_u) / 2.0, (min_v + max_v) / 2.0),
        (min_u, min_v),
        (max_u, min_v),
        (max_u, max_v),
        (min_u, max_v),
    ]


def _projection_contour_points(projection: dict[str, Any]) -> list[tuple[float, float]]:
    points = []
    for item in projection.get("projectedContour") or []:
        point = _point(item)
        if point is not None:
            points.append(point)
    return points


def _projection_bounds(part: dict[str, Any]) -> tuple[float, float, float, float] | None:
    projection = _projection(part)
    if not projection:
        return None
    bounds_min = projection.get("projectedBoundsMin")
    bounds_max = projection.get("projectedBoundsMax")
    if isinstance(bounds_min, dict) and isinstance(bounds_max, dict):
        min_u = as_float(bounds_min.get("u"))
        max_u = as_float(bounds_max.get("u"))
        min_v = as_float(bounds_min.get("v"))
        max_v = as_float(bounds_max.get("v"))
        return min(min_u, max_u), max(min_u, max_u), min(min_v, max_v), max(min_v, max_v)
    points = _projection_contour_points(projection)
    if not points:
        centroid = _point(projection.get("projectedCentroid"))
        points = [centroid] if centroid is not None else []
    if not points:
        return None
    return (
        min(point[0] for point in points),
        max(point[0] for point in points),
        min(point[1] for point in points),
        max(point[1] for point in points),
    )


def _projection(part: dict[str, Any]) -> dict[str, Any] | None:
    evidence = part.get("mainMaterialEvidence")
    if not isinstance(evidence, dict):
        return None
    projection = evidence.get("sectionProjectionEvidence")
    return projection if isinstance(projection, dict) else None


def _point(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    if "u" not in value and "v" not in value:
        return None
    return as_float(value.get("u")), as_float(value.get("v"))


def _part_centroid_v(part: dict[str, Any]) -> float:
    projection = _projection(part) or {}
    centroid = _point(projection.get("projectedCentroid"))
    if centroid is not None:
        return centroid[1]
    bounds = _projection_bounds(part)
    if bounds is None:
        return 0.0
    return (bounds[2] + bounds[3]) / 2.0


def _main_web_center_u(web_parts: list[dict[str, Any]], fallback_min_u: float, fallback_max_u: float) -> float:
    centers = []
    for part in web_parts:
        projection = _projection(part) or {}
        centroid = _point(projection.get("projectedCentroid"))
        if centroid is not None:
            centers.append(centroid[0])
    if centers:
        return sum(centers) / len(centers)
    return (fallback_min_u + fallback_max_u) / 2.0


def _web_half_thickness(web_parts: list[dict[str, Any]], swept_half_width: float) -> float:
    estimates = []
    for part in web_parts:
        thickness = as_float(part.get("thickness"))
        if thickness > 0:
            estimates.append(thickness / 2.0)
            continue
        pl = parse_pl(part.get("profileString"))
        if pl:
            estimates.append(pl[0] / 2.0)
    estimates = [value for value in estimates if value > 0]
    if not estimates:
        return swept_half_width
    return max(1.0, min(swept_half_width, max(estimates)))


def _centroid_side(part: dict[str, Any], frame: _HBeamSectionFrame, tol: float) -> str:
    projection = _projection(part) or {}
    centroid = _point(projection.get("projectedCentroid"))
    return _point_side(centroid, frame, tol) if centroid is not None else ""


def _summary(
    frame: _HBeamSectionFrame,
    points: list[tuple[float, float]],
    votes: Counter[str],
) -> dict[str, str]:
    return {
        "web_center_u": f"{frame.web_center_u:.3f}",
        "web_half_thickness": f"{frame.web_half_thickness:.3f}",
        "top_outer_v": f"{frame.top_outer_v:.3f}",
        "bottom_outer_v": f"{frame.bottom_outer_v:.3f}",
        "point_count": str(len(points)),
        "vote_counts": ";".join(f"{side}={count}" for side, count in sorted(votes.items())),
    }


def _row(
    assembly_id: str,
    part: dict[str, Any],
    h_side: str,
    confidence: float,
    issue_category: str,
    evidence_codes: list[str],
    evidence_summary: dict[str, str],
) -> HBeamPartSide:
    return HBeamPartSide(
        assembly_id=assembly_id,
        part_id=text(part.get("partId")),
        part_position=text(part.get("partPosition")),
        part_name=text(part.get("name")),
        h_side=h_side,
        confidence=confidence,
        issue_category=issue_category,
        evidence_codes=evidence_codes,
        evidence_summary=evidence_summary,
    )


