"""Plate BOOLEAN_CUT roles: 剖口 is elsewhere; here is 洞口 / 倒角 / foreign."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from . import LINEAR_TOL_MM


@dataclass(frozen=True)
class PlateCutRoles:
    opening_count: int = 0
    chamfer_count: int = 0
    foreign_count: int = 0


def rectangle_from_obb(
    obb_dims: Sequence[float],
    thickness: float,
) -> tuple[tuple[float, float, float], ...]:
    dims = [abs(float(value)) for value in obb_dims]
    if len(dims) < 3:
        return ()
    positive = [value for value in dims if value > LINEAR_TOL_MM]
    if len(positive) < 2:
        return ()
    plate_t = thickness if thickness > LINEAR_TOL_MM else min(positive)
    t_axis = min(range(3), key=lambda index: abs(dims[index] - plate_t))
    in_plane = [dims[index] for index in range(3) if index != t_axis]
    if len(in_plane) != 2 or min(in_plane) <= LINEAR_TOL_MM:
        return ()
    along, across = in_plane[0], in_plane[1]
    return (
        (0.0, 0.0, 0.0),
        (along, 0.0, 0.0),
        (along, across, 0.0),
        (0.0, across, 0.0),
    )


def solid_cut_proof(cut: Mapping[str, object] | None) -> bool | None:
    """Tekla GetCutPart(RAW father, cutter) when dump has cutsFatherSolid; else None."""
    if not isinstance(cut, Mapping) or "cutsFatherSolid" not in cut:
        return None
    return cut.get("cutsFatherSolid") is True


def boolean_cut_hits_part(
    part_box: Mapping[str, object] | None,
    cut: Mapping[str, object] | None,
    *,
    min_overlap: float = 1.0,
) -> bool | None:
    """Whether a BOOLEAN_CUT actually modifies the part solid.

    cutsFatherSolid in the dump is authoritative (Tekla GetCutPart on RAW father).
    Missing field falls back to AABB: False means the cut cannot have modified the
    solid; overlap is not solid proof.
    """
    proven = solid_cut_proof(cut)
    if proven is not None:
        return proven
    nested = cut.get("boundingBox") if isinstance(cut, Mapping) else None
    cut_box = nested if isinstance(nested, Mapping) else cut
    part_min, part_max = _bb_minmax(part_box or {})
    cut_min, cut_max = _bb_minmax(cut_box or {})
    if part_min is None or cut_min is None:
        return None
    overlap = _overlap_sizes(part_min, part_max, cut_min, cut_max)
    return overlap[0] > min_overlap and overlap[1] > min_overlap and overlap[2] > min_overlap


def classify_plate_boolean_cuts(
    *,
    part_box: Mapping[str, object],
    thickness: float,
    cuts: Sequence[Mapping[str, object]],
    bevel_operative_ids: set[int] | None = None,
) -> PlateCutRoles:
    plate_min, plate_max = _bb_minmax(part_box)
    if plate_min is None or plate_max is None:
        return PlateCutRoles()
    plate_size = _sizes(plate_min, plate_max)
    plate_t = thickness if thickness > LINEAR_TOL_MM else min((value for value in plate_size if value > 0), default=0.0)
    if plate_t <= LINEAR_TOL_MM:
        return PlateCutRoles()
    t_axis = min(range(3), key=lambda index: abs(plate_size[index] - plate_t))
    bevel_ops = bevel_operative_ids or set()
    openings = 0
    chamfers = 0
    foreign = 0
    for cut in cuts:
        if not isinstance(cut, Mapping):
            continue
        if solid_cut_proof(cut) is False:
            continue
        op_id = cut.get("operativePartId")
        if op_id is not None and int(op_id) in bevel_ops:
            continue
        cut_min, cut_max = _bb_minmax(cut.get("boundingBox") or cut)
        if cut_min is None or cut_max is None:
            continue
        role = _cut_role(plate_min, plate_max, plate_size, plate_t, t_axis, cut_min, cut_max)
        if role == "opening":
            openings += 1
        elif role == "chamfer":
            chamfers += 1
        else:
            foreign += 1
    return PlateCutRoles(opening_count=openings, chamfer_count=chamfers, foreign_count=foreign)


def _cut_role(
    plate_min: tuple[float, float, float],
    plate_max: tuple[float, float, float],
    plate_size: tuple[float, float, float],
    plate_t: float,
    t_axis: int,
    cut_min: tuple[float, float, float],
    cut_max: tuple[float, float, float],
) -> str:
    overlap = _overlap_sizes(plate_min, plate_max, cut_min, cut_max)
    if overlap[0] <= 0 or overlap[1] <= 0 or overlap[2] <= 0:
        return "foreign"
    cut_size = _sizes(cut_min, cut_max)
    through = overlap[t_axis] >= 0.45 * min(plate_t, plate_size[t_axis], max(cut_size[t_axis], plate_t))
    if not through:
        return "foreign"
    inplane = [index for index in range(3) if index != t_axis]
    overflow = max(cut_size[index] - overlap[index] for index in inplane)
    contained = overflow <= max(plate_t * 2.5, 20.0)
    if not contained:
        return "foreign"
    edge_tol = max(plate_t * 1.5, 12.0)
    n_edges = 0
    for index in inplane:
        if max(cut_min[index], plate_min[index]) <= plate_min[index] + edge_tol:
            n_edges += 1
        if min(cut_max[index], plate_max[index]) >= plate_max[index] - edge_tol:
            n_edges += 1
    if n_edges == 0:
        return "opening"
    return "chamfer"


def _bb_minmax(box: Mapping[str, object]) -> tuple[tuple[float, float, float] | None, tuple[float, float, float] | None]:
    if not isinstance(box, Mapping):
        return None, None
    minimum = box.get("min")
    maximum = box.get("max")
    if not isinstance(minimum, Mapping) or not isinstance(maximum, Mapping):
        return None, None
    part_min = (float(minimum.get("x") or 0.0), float(minimum.get("y") or 0.0), float(minimum.get("z") or 0.0))
    part_max = (float(maximum.get("x") or 0.0), float(maximum.get("y") or 0.0), float(maximum.get("z") or 0.0))
    return part_min, part_max


def _sizes(minimum: tuple[float, float, float], maximum: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        abs(maximum[0] - minimum[0]),
        abs(maximum[1] - minimum[1]),
        abs(maximum[2] - minimum[2]),
    )


def _overlap_sizes(
    a_min: tuple[float, float, float],
    a_max: tuple[float, float, float],
    b_min: tuple[float, float, float],
    b_max: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(max(0.0, min(a_max[i], b_max[i]) - max(a_min[i], b_min[i])) for i in range(3))
