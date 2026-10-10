"""Human-accepted structural-role assertions used by recognition reports.

Axis pose comes from a member document. Connection facts come from
StructuralContext. Missing connection facts stay UNKNOWN. Member marks are
not read.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

VERTICAL_TOLERANCE_DEG = 10.0
HORIZONTAL_TOLERANCE_DEG = 10.0
BEND_ANGLE_DEG = 5.0

ROLE_LABELS = {
    "COLUMN": "柱",
    "INCLINED_COLUMN": "斜柱",
    "BEAM": "梁",
    "INCLINED_BEAM": "斜梁",
    "CRANE_BEAM": "吊车梁",
    "PURLIN": "檩条",
    "GIRT": "墙梁",
    "BRACE": "支撑",
    "HORIZONTAL_BRACE": "水平支撑",
    "KNEE_BRACE": "隅撑",
    "TIE": "系杆",
    "TRUSS": "桁架",
    "EMBED": "埋件",
    "STAIR": "楼梯",
    "STAIR_LANDING": "休息平台",
    "UNKNOWN": "未知",
}

LANDING_PLAN_MIN_MM = 1000.0
LANDING_THICKNESS_MAX_MM = 16.0
LANDING_ANGLE_LEG_MIN_MM = 20.0
LANDING_ANGLE_LEG_MAX_MM = 100.0
LANDING_ANGLE_MIN_COUNT = 4
LANDING_ANGLE_OFFSET_MAX_MM = 80.0
COLUMN_SHAFT_SLENDERNESS = 4.0

_BEARING_ENDS = {"column", "beam", "corbel", "embed"}
_LOWER_SUPPORTS = {"foundation", "column_splice", "embed"}


@dataclass(frozen=True)
class AxisAssertion:
    pose: str
    axis_form: str
    bend_count: int
    chord: tuple[float, float, float] | None = None
    source: str = ""
    evidence_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StructuralContext:
    """Observed connection facts. None means not observed."""

    has_chord_web_system: bool | None = None
    external_supports_only: bool | None = None
    anchor_plate_with_same_side_bars: bool | None = None
    has_span_axis: bool | None = None
    lower_end_support: str | None = None
    side_incoming: tuple[str, ...] = ()
    end_supports: tuple[str, ...] = ()
    crosses_bay_in_plan: bool | None = None
    carries_floor_beams: bool | None = None
    connects_frames_longitudinally: bool | None = None
    repeated_on_roof_beams: bool | None = None
    attached_to_column_side_for_wall: bool | None = None
    ends_on_corbels: bool | None = None
    crane_rail_or_brake: bool | None = None
    lies_on_roof_plane: bool | None = None
    supports_purlins: bool | None = None
    paired_with_brace: bool | None = None
    short_brace_between_flange_and_purlin: bool | None = None
    lower_end_continues_down: bool | None = None
    brace_arrangement: str | None = None
    brace_plane: str | None = None
    repeated_treads: bool | None = None
    landing_checker_deck: bool | None = None


@dataclass(frozen=True)
class StructuralRoleAssertion:
    member_id: str
    role: str
    role_label: str
    subtype: str
    pose: str
    axis_form: str
    bend_count: int
    confidence: float
    evidence_codes: list[str]
    rule_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "member_id": self.member_id,
            "role": self.role,
            "role_label": self.role_label,
            "subtype": self.subtype,
            "pose": self.pose,
            "axis_form": self.axis_form,
            "bend_count": self.bend_count,
            "confidence": self.confidence,
            "evidence_codes": list(self.evidence_codes),
            "rule_id": self.rule_id,
        }


def _coord(point: Any) -> tuple[float, float, float] | None:
    if not isinstance(point, dict):
        return None
    try:
        return (
            float(point.get("X", point.get("x"))),
            float(point.get("Y", point.get("y"))),
            float(point.get("Z", point.get("z"))),
        )
    except (TypeError, ValueError):
        return None


def _unit(vector: tuple[float, float, float] | None) -> tuple[float, float, float] | None:
    if vector is None:
        return None
    length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    if length < 1e-9:
        return None
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _sub(end: tuple[float, float, float], start: tuple[float, float, float]) -> tuple[float, float, float]:
    return (end[0] - start[0], end[1] - start[1], end[2] - start[2])


def _angle_deg(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
    return math.degrees(math.acos(dot))


def pose_of(direction: tuple[float, float, float] | None) -> str:
    unit = _unit(direction)
    if unit is None:
        return "unknown"
    abs_z = abs(unit[2])
    if abs_z >= math.cos(math.radians(VERTICAL_TOLERANCE_DEG)):
        return "vertical"
    if abs_z <= math.sin(math.radians(HORIZONTAL_TOLERANCE_DEG)):
        return "horizontal"
    return "inclined"


def axis_from_member(member: dict[str, Any]) -> AxisAssertion:
    segments = [item for item in member.get("AxisSegments") or [] if isinstance(item, dict)]
    directions = [_unit(_coord(item.get("Direction"))) for item in segments]
    directions = [item for item in directions if item is not None]
    bends = 0
    for before, after in zip(directions, directions[1:]):
        if _angle_deg(before, after) > BEND_ANGLE_DEG:
            bends += 1
    axis_form = "未知" if not directions else "折线" if bends else "直线"

    guide = [_coord(point) for point in member.get("GuidePolyline") or []]
    guide = [point for point in guide if point is not None]
    if len(guide) >= 2:
        chord = _sub(guide[-1], guide[0])
        source = "guide_polyline"
    elif segments:
        start = _coord(segments[0].get("Start"))
        end = _coord(segments[-1].get("End"))
        chord = _sub(end, start) if start and end else None
        source = "axis_segments"
    else:
        main_axis = (member.get("Member") or {}).get("MainAxis") or {}
        chord = _coord(main_axis.get("Direction"))
        source = "main_axis" if chord else ""

    pose = pose_of(chord)
    evidence = [f"axis.pose.{pose}", f"axis.form.{axis_form}", f"axis.bends.{bends}"]
    if source:
        evidence.append(f"axis.source.{source}")
    return AxisAssertion(
        pose=pose,
        axis_form=axis_form,
        bend_count=bends,
        chord=chord,
        source=source,
        evidence_codes=evidence,
    )


def _result(
    member_id: str,
    axis: AxisAssertion,
    role: str,
    subtype: str,
    rule_id: str,
    evidence: list[str],
    confidence: float,
) -> StructuralRoleAssertion:
    return StructuralRoleAssertion(
        member_id=member_id,
        role=role,
        role_label=ROLE_LABELS[role],
        subtype=subtype,
        pose=axis.pose,
        axis_form=axis.axis_form,
        bend_count=axis.bend_count,
        confidence=confidence,
        evidence_codes=[*axis.evidence_codes, *evidence],
        rule_id=rule_id,
    )


def _unknown(member_id: str, axis: AxisAssertion, rule_id: str, evidence: list[str]) -> StructuralRoleAssertion:
    return _result(member_id, axis, "UNKNOWN", "", rule_id, evidence, 0.0)


def _ends(context: StructuralContext) -> tuple[str, str] | None:
    if len(context.end_supports) != 2:
        return None
    return context.end_supports[0], context.end_supports[1]


def _gusset_ends(context: StructuralContext) -> bool:
    ends = _ends(context)
    return bool(ends and ends[0] == "gusset" and ends[1] == "gusset")


def _both_bearing(context: StructuralContext) -> bool:
    ends = _ends(context)
    return bool(ends and ends[0] in _BEARING_ENDS and ends[1] in _BEARING_ENDS)


def _spanning_beam_ends(context: StructuralContext) -> bool:
    ends = _ends(context)
    if ends is None:
        return False
    bearing = sum(item in _BEARING_ENDS for item in ends)
    free = sum(item == "free" for item in ends)
    return bearing == 2 or (bearing == 1 and free == 1)


def _beam_subtype(context: StructuralContext) -> str:
    ends = _ends(context)
    if ends is None:
        return ""
    if "free" in ends and any(item in _BEARING_ENDS for item in ends):
        return "悬挑梁"
    if ends[0] == "column" and ends[1] == "column":
        return "框梁"
    if ends[0] == "beam" and ends[1] == "beam":
        return "次梁"
    return ""


def _brace_subtype(context: StructuralContext) -> str:
    parts = [item for item in (context.brace_arrangement, context.brace_plane) if item]
    return "/".join(parts)


def _column_rule(context: StructuralContext) -> tuple[str, str, list[str]] | None:
    incoming = set(context.side_incoming)
    if context.lower_end_support == "outside_model" and "beam" in incoming:
        return "MR-COL-003", "框架柱", ["end.lower.outside_model", "side.beam", "shaft.vertical"]
    if context.lower_end_support not in _LOWER_SUPPORTS:
        return None
    evidence = [f"end.lower.{context.lower_end_support}"]
    if "beam" in incoming:
        return "MR-COL-001", "框架柱", [*evidence, "side.beam"]
    if incoming == {"girt"}:
        return "MR-COL-002", "抗风柱", [*evidence, "side.girt"]
    return None


def _conflict(context: StructuralContext, pose: str) -> tuple[str, list[str]] | None:
    if pose == "horizontal" and context.crosses_bay_in_plan is True and context.carries_floor_beams is True:
        return "MR-CONFLICT-BAY-FLOOR", ["conflict.bay_and_floor"]
    if (
        pose == "horizontal"
        and context.crosses_bay_in_plan is True
        and context.connects_frames_longitudinally is True
    ):
        return "MR-CONFLICT-BAY-TIE", ["conflict.bay_and_tie"]
    if (
        pose == "inclined"
        and context.lies_on_roof_plane is True
        and context.supports_purlins is True
        and context.paired_with_brace is True
        and _gusset_ends(context)
    ):
        return "MR-CONFLICT-ROOF-BRACE", ["conflict.roof_and_brace"]
    return None


def _match_role(axis: AxisAssertion, context: StructuralContext) -> tuple[str, str, str, list[str]] | None:
    if context.has_chord_web_system is True and context.external_supports_only is True:
        return "TRUSS", "", "MR-TRUSS-001", ["assembly.chord_web", "support.external_only"]
    if context.anchor_plate_with_same_side_bars is True and context.has_span_axis is False:
        return "EMBED", "", "MR-EMBED-001", ["embed.anchor_plate", "embed.same_side_bars"]
    if context.repeated_treads is True:
        return "STAIR", "", "MR-STAIR-001", ["stringer.pair", "tread.repeated"]
    if context.landing_checker_deck is True:
        return "STAIR_LANDING", "", "MR-LANDING-001", [
            "deck.checker_plate",
            "deck.horizontal",
            "support.equal_angles_one_side",
        ]

    if axis.pose == "vertical":
        matched = _column_rule(context)
        if matched:
            rule_id, subtype, evidence = matched
            return "COLUMN", subtype, rule_id, evidence
        return None

    if axis.pose == "horizontal":
        if context.crosses_bay_in_plan is True and _gusset_ends(context) and context.carries_floor_beams is False:
            return "HORIZONTAL_BRACE", "", "MR-HBRACE-001", ["plan.crosses_bay", "end.gusset", "floor.none"]
        if (
            context.connects_frames_longitudinally is True
            and context.carries_floor_beams is False
            and context.crosses_bay_in_plan is False
        ):
            return "TIE", "", "MR-TIE-001", ["plan.longitudinal", "floor.none"]
        if context.repeated_on_roof_beams is True:
            return "PURLIN", "", "MR-PURLIN-001", ["layout.repeated_on_roof"]
        if context.attached_to_column_side_for_wall is True and context.carries_floor_beams is False:
            return "GIRT", "", "MR-GIRT-001", ["support.column_side", "use.wall", "floor.none"]
        if context.ends_on_corbels is True and context.crane_rail_or_brake is True:
            return "CRANE_BEAM", "", "MR-CRANE-001", ["end.corbel", "top.rail_or_brake"]
        if _spanning_beam_ends(context):
            subtype = _beam_subtype(context)
            return "BEAM", subtype, "MR-BEAM-001", ["end.bearing", f"subtype.{subtype or 'none'}"]
        return None

    if axis.pose == "inclined":
        if context.lies_on_roof_plane is True and context.supports_purlins is True and _both_bearing(context):
            return "INCLINED_BEAM", "", "MR-IBEAM-001", ["plane.roof", "supports.purlin", "end.bearing"]
        if context.paired_with_brace is True and _gusset_ends(context):
            return "BRACE", _brace_subtype(context), "MR-BRACE-001", ["end.gusset", "pair.brace"]
        if context.short_brace_between_flange_and_purlin is True:
            return "KNEE_BRACE", "", "MR-KNEE-001", ["end.flange", "end.purlin_or_horizontal_brace"]
        if context.lower_end_continues_down is True and "beam" in context.side_incoming:
            return "INCLINED_COLUMN", "", "MR-ICOL-001", ["end.lower.continues", "side.beam"]
    return None


def classify_structural_role(
    axis: AxisAssertion,
    context: StructuralContext | None = None,
    member_id: str = "",
) -> StructuralRoleAssertion:
    if context is None:
        return _unknown(member_id, axis, "MR-UNKNOWN-CONTEXT", ["context.missing"])
    if axis.pose == "unknown":
        return _unknown(member_id, axis, "MR-UNKNOWN-POSE", ["axis.pose.unknown"])
    conflict = _conflict(context, axis.pose)
    if conflict:
        rule_id, evidence = conflict
        return _unknown(member_id, axis, rule_id, evidence)
    matched = _match_role(axis, context)
    if matched is None:
        return _unknown(member_id, axis, "MR-UNKNOWN-EVIDENCE", ["context.incomplete"])
    role, subtype, rule_id, evidence = matched
    return _result(member_id, axis, role, subtype, rule_id, evidence, 0.86)


def classify_member_document(
    member: dict[str, Any],
    context: StructuralContext | None = None,
) -> StructuralRoleAssertion:
    info = member.get("Member") or {}
    member_id = str(info.get("MemberId") or info.get("Name") or "")
    return classify_structural_role(axis_from_member(member), context, member_id)


def _point_of(value: Any) -> tuple[float, float, float] | None:
    return _coord(value)


def context_from_external_links(
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    length: float,
    links: list[dict[str, Any]],
) -> StructuralContext:
    """Map exported cross-member bolts onto connection facts.

    A horizontal member at a column end is a beam framing into the side.
    A vertical member at a column end is a splice. Beam ends use only the
    start and end bands. Member marks are not read.
    """
    pose = pose_of(direction)
    by_location: dict[str, set[str]] = {"start": set(), "end": set(), "middle": set()}
    for link in links:
        location = str(link.get("axisLocation") or "")
        other_pose = str(link.get("otherAxisPose") or "")
        if location in by_location and other_pose:
            by_location[location].add(other_pose)

    if pose == "vertical":
        end_z = origin[2] + (direction[2] * length)
        lower_location = "start" if origin[2] <= end_z else "end"
        lower_support = "column_splice" if "vertical" in by_location[lower_location] else None
        incoming: list[str] = []
        observed = set().union(*by_location.values())
        if "horizontal" in observed:
            incoming.append("beam")
        if "inclined" in observed:
            incoming.append("inclined")
        return StructuralContext(lower_end_support=lower_support, side_incoming=tuple(incoming))

    if pose != "horizontal":
        return StructuralContext()

    def _end_kind(poses: set[str]) -> str | None:
        kinds = set()
        if "vertical" in poses:
            kinds.add("column")
        if "horizontal" in poses:
            kinds.add("beam")
        if len(kinds) == 1:
            return next(iter(kinds))
        return None

    start = _end_kind(by_location["start"])
    end = _end_kind(by_location["end"])
    if start is None or end is None:
        return StructuralContext()
    return StructuralContext(end_supports=(start, end))


def classify_body_bracket_assembly(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
) -> StructuralRoleAssertion:
    metadata = assembly.get("metadata") or {}
    axis = metadata.get("memberAxisEvidence") or {}
    origin = _point_of(axis.get("origin"))
    direction = _point_of(axis.get("direction"))
    try:
        length = float(axis.get("length") or 0.0)
    except (TypeError, ValueError):
        length = 0.0
    if origin is None or direction is None or length <= 0.0:
        return classify_structural_role(AxisAssertion("unknown", "未知", 0), None, _assembly_label(assembly))
    end = (
        origin[0] + (direction[0] * length),
        origin[1] + (direction[1] * length),
        origin[2] + (direction[2] * length),
    )
    axis_member = member or {
        "Member": {
            "MemberId": _assembly_label(assembly),
            "MainAxis": {"Direction": {"X": direction[0], "Y": direction[1], "Z": direction[2]}},
        },
        "GuidePolyline": [
            {"X": origin[0], "Y": origin[1], "Z": origin[2]},
            {"X": end[0], "Y": end[1], "Z": end[2]},
        ],
    }
    evidence = metadata.get("externalConnectionEvidence") or {}
    context = context_from_external_links(origin, direction, length, list(evidence.get("links") or []))
    if embed_anchor_bars(assembly):
        context = StructuralContext(
            anchor_plate_with_same_side_bars=True,
            has_span_axis=False,
            lower_end_support=context.lower_end_support,
            side_incoming=context.side_incoming,
            end_supports=context.end_supports,
        )
    elif stair_flight(assembly):
        context = StructuralContext(repeated_treads=True)
    elif landing_checker_plate(assembly) is not None:
        context = StructuralContext(landing_checker_deck=True)
    elif single_inclined_bar(assembly, pose_of(direction)):
        context = StructuralContext(
            paired_with_brace=True,
            end_supports=("gusset", "gusset"),
            lower_end_support=context.lower_end_support,
            side_incoming=context.side_incoming,
        )
    elif _open_lower_column(assembly, context, length):
        context = StructuralContext(
            lower_end_support="outside_model",
            side_incoming=context.side_incoming,
        )
    return classify_structural_role(axis_from_member(axis_member), context, _assembly_label(assembly))


def _open_lower_column(assembly: dict[str, Any], context: StructuralContext, axis_length: float) -> bool:
    """A vertical shaft whose next lower tier is outside this model.

    Side beams are real welds or bolts. A lone plate stays unknown.
    Member marks are not read.
    """
    if context.lower_end_support is not None or "beam" not in context.side_incoming:
        return False
    parts = [item for item in assembly.get("parts") or [] if isinstance(item, dict)]
    if len(parts) == 1 and parts[0].get("isPlateLike") is True:
        return False
    section = 0.0
    for part in parts:
        dims = _sorted_dims(part)
        if dims is None:
            continue
        section = max(section, dims[1])
    if section <= 1.0:
        return False
    return axis_length / section >= COLUMN_SHAFT_SLENDERNESS


def single_inclined_bar(assembly: dict[str, Any], pose: str) -> bool:
    """One compact bar whose axis is inclined.

    The cross-section's two smaller dimensions are nearly equal, so the
    member is a tube or solid bar rather than a plate. It has no plates,
    chords, or secondary bars inside the assembly. Member marks are not read.
    """
    if pose != "inclined":
        return False
    parts = [item for item in assembly.get("parts") or [] if isinstance(item, dict)]
    if len(parts) != 1 or parts[0].get("isPlateLike") is True:
        return False
    dims = _sorted_dims(parts[0])
    if dims is None or dims[1] <= 1.0:
        return False
    small, middle, large = dims
    return small / middle >= 0.85 and large / middle >= 4.0


def landing_checker_plate(assembly: dict[str, Any]) -> dict[str, Any] | None:
    """The horizontal checkered plate of a stair landing.

    The material grade contains 花纹. The plate normal is vertical and both
    plan dimensions are at least 1000 mm. Every other part is an equal-leg
    angle, and those angles all sit on one side of the plate within 80 mm.
    Part names and member marks are not read.
    """
    parts = [item for item in assembly.get("parts") or [] if isinstance(item, dict)]
    decks = [part for part in parts if _is_landing_deck(part)]
    if len(decks) != 1:
        return None
    deck = decks[0]
    normal = _unit(_vector_of(deck.get("plateNormal")))
    origin = _vector_of(deck.get("centroid"))
    if normal is None or origin is None or abs(normal[2]) < math.cos(math.radians(VERTICAL_TOLERANCE_DEG)):
        return None
    angles: list[float] = []
    for part in parts:
        if part is deck:
            continue
        if not _is_equal_leg_angle(part):
            return None
        center = _vector_of(part.get("centroid"))
        if center is None:
            return None
        offset = _dot(
            (center[0] - origin[0], center[1] - origin[1], center[2] - origin[2]),
            normal,
        )
        if abs(offset) < 1.0 or abs(offset) > LANDING_ANGLE_OFFSET_MAX_MM:
            return None
        angles.append(offset)
    if len(angles) < LANDING_ANGLE_MIN_COUNT:
        return None
    if not (all(item > 0.0 for item in angles) or all(item < 0.0 for item in angles)):
        return None
    return deck


def _is_landing_deck(part: dict[str, Any]) -> bool:
    material = str(part.get("material") or part.get("Material") or "")
    if "花纹" not in material or part.get("isPlateLike") is not True:
        return False
    dims = _sorted_dims(part)
    if dims is None:
        return False
    thickness, width, length = dims
    return (
        thickness <= LANDING_THICKNESS_MAX_MM
        and width >= LANDING_PLAN_MIN_MM
        and length >= LANDING_PLAN_MIN_MM
    )


def _is_equal_leg_angle(part: dict[str, Any]) -> bool:
    if part.get("isPlateLike") is True:
        return False
    dims = _sorted_dims(part)
    if dims is None or dims[1] <= 0.0:
        return False
    small, middle, large = dims
    return (
        LANDING_ANGLE_LEG_MIN_MM <= middle <= LANDING_ANGLE_LEG_MAX_MM
        and small / middle >= 0.85
        and large / middle >= 2.0
    )


def stair_flight(assembly: dict[str, Any]) -> bool:
    """Two inclined stringers with one repeated run of shorter plates.

    The stringers are the two longest non-plate parts, and they share an
    inclined direction. At least eight plates belong to one size. Part names
    and member marks are not read.
    """
    parts = [item for item in assembly.get("parts") or [] if isinstance(item, dict)]
    stringers: list[float] = []
    for part in parts:
        if part.get("isPlateLike") is True:
            continue
        dims = _sorted_dims(part)
        direction = _unit(_vector_of(part.get("plateLongDirection")))
        if dims is None or direction is None or dims[2] < 2000.0:
            continue
        if pose_of(direction) != "inclined":
            continue
        stringers.append(dims[2])
    if len(stringers) < 2:
        return False
    longest = max(stringers)
    if sum(item >= longest * 0.85 for item in stringers) != 2:
        return False
    clusters: dict[tuple[int, int, int], int] = {}
    for part in parts:
        if part.get("isPlateLike") is not True:
            continue
        dims = _sorted_dims(part)
        if dims is None or dims[2] < 150.0 or dims[2] >= longest * 0.5:
            continue
        key = tuple(int(round(item / 40.0) * 40.0) for item in dims)
        clusters[key] = clusters.get(key, 0) + 1
    return any(count >= 8 for count in clusters.values())


def embed_anchor_bars(assembly: dict[str, Any]) -> bool:
    """A plate with at least two round bars welded to it on one side.

    A bar is round when its two cross-section dimensions match the profile
    thickness. The bars share one plate-normal side and point along that
    normal. Part names and member marks are not read.
    """
    parts = [item for item in assembly.get("parts") or [] if isinstance(item, dict)]
    plates = [part for part in parts if part.get("isPlateLike") is True]
    bars = [part for part in parts if _is_round_bar(part)]
    if len(bars) < 2 or not plates:
        return False
    anchor = max(plates, key=_plate_area)
    normal = _unit(_vector_of(anchor.get("plateNormal")))
    if normal is None:
        return False
    welded = _welded_pairs(assembly.get("relationships") or [])
    sides: set[int] = set()
    for bar in bars:
        if frozenset((bar.get("partId"), anchor.get("partId"))) not in welded:
            return False
        long_axis = _unit(_vector_of(bar.get("plateLongDirection")))
        if long_axis is None or abs(_dot(long_axis, normal)) < 0.85:
            return False
        sides.add(_side_of(bar.get("centroid"), anchor.get("centroid"), normal))
    return len(sides) == 1


def _vector_of(value: Any) -> tuple[float, float, float] | None:
    return _coord(value)


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _sorted_dims(part: dict[str, Any]) -> tuple[float, float, float] | None:
    values = _vector_of(part.get("obbDims"))
    if values is None:
        return None
    return tuple(sorted(abs(item) for item in values))


def _is_round_bar(part: dict[str, Any]) -> bool:
    if part.get("isPlateLike") is True:
        return False
    dims = _sorted_dims(part)
    try:
        thickness = float(part.get("thickness") or 0.0)
    except (TypeError, ValueError):
        return False
    if dims is None or thickness <= 0.0 or dims[1] <= 0.0:
        return False
    small, middle, large = dims
    return (
        small / middle >= 0.85
        and large / middle >= 4.0
        and 0.6 * thickness <= small <= 1.5 * thickness
        and 0.6 * thickness <= middle <= 1.5 * thickness
    )


def _plate_area(part: dict[str, Any]) -> float:
    dims = _sorted_dims(part)
    if dims is None:
        return 0.0
    return dims[1] * dims[2]


def _side_of(point: Any, origin: Any, normal: tuple[float, float, float]) -> int:
    start = _vector_of(origin)
    end = _vector_of(point)
    if start is None or end is None:
        return 0
    offset = (end[0] - start[0], end[1] - start[1], end[2] - start[2])
    return 1 if _dot(offset, normal) >= 0.0 else -1


def _welded_pairs(relationships: list[Any]) -> set[frozenset[Any]]:
    pairs: set[frozenset[Any]] = set()
    for item in relationships:
        if not isinstance(item, dict) or item.get("edgeType") != "Weld":
            continue
        pairs.add(frozenset((item.get("partIdA"), item.get("partIdB"))))
    return pairs


def _assembly_label(assembly: dict[str, Any]) -> str:
    metadata = assembly.get("metadata") or {}
    return str(metadata.get("assemblyPosition") or assembly.get("assemblyId") or "")
