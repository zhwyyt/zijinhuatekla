"""Shop process/shape from part geometry. Not from role or factory Excel."""

from __future__ import annotations

from typing import Sequence

from ..rules import norm_spec
from .chamfer import classify_plan_outline
from .planar import project_uv
from .plate_cuts import rectangle_from_obb

_ROLLED_PREFIXES = ("BH", "HN", "HM", "HW", "HI", "IPE", "HEA", "HEB", "UB", "UC")
_SECTION_PREFIXES = _ROLLED_PREFIXES + (
    "C",
    "U",
    "[",
    "L",
    "T",
    "PIPE",
    "CHS",
    "RHS",
    "SHS",
    "BO",
    "UNP",
    "UPN",
    "PFC",
    "EA",
    "UA",
    "TW",
    "TN",
    "TM",
)
_FOLD_THICKNESS_RATIO = 3.0


def is_rolled_profile(profile: str) -> bool:
    spec = norm_spec(profile)
    if not spec:
        return False
    if spec.startswith(_ROLLED_PREFIXES):
        return True
    return spec.startswith("H") and "*" in spec and not spec.startswith(("HP", "H-", "HS"))


def _is_channel_profile(spec: str) -> bool:
    if spec.startswith("CHS"):
        return False
    if spec.startswith(("C", "[", "UNP", "UPN", "PFC")):
        return True
    return spec.startswith("U") and not spec.startswith(("UB", "UC", "UA"))


def is_section_profile(profile: str) -> bool:
    spec = norm_spec(profile)
    if not spec or spec.startswith("PL") or spec.startswith("FLAT"):
        return False
    if is_rolled_profile(spec) or spec.startswith(_SECTION_PREFIXES):
        return True
    return spec.startswith("I") and "*" in spec


def is_folded_plate(obb_dims: Sequence[float], thickness: float) -> bool:
    if thickness <= 0:
        return False
    dims = sorted(float(value) for value in obb_dims if float(value) > 0)
    if len(dims) < 3:
        return False
    return dims[0] > thickness * _FOLD_THICKNESS_RATIO


def has_inner_opening(hole_like_feature_count: int, bolt_hole_count: int) -> bool:
    return max(0, int(hole_like_feature_count) - int(bolt_hole_count)) > 0


def remaining_cut_count(
    *,
    hole_like_feature_count: int,
    bolt_hole_count: int,
    boolean_cut_count: int = 0,
    edge_bevel_count: int = 0,
    end_chamfer_count: int = 0,
) -> int:
    if boolean_cut_count > 0:
        return max(0, int(boolean_cut_count) - int(edge_bevel_count) - int(end_chamfer_count))
    return max(0, int(hole_like_feature_count) - int(bolt_hole_count) - int(end_chamfer_count))


def classify_shop_process(
    *,
    profile: str,
    runtime_type: str,
    is_plate_like: bool,
    thickness: float,
    obb_dims: Sequence[float],
    bolt_hole_count: int,
    hole_like_feature_count: int,
    boolean_cut_count: int = 0,
    edge_bevel_count: int = 0,
    end_chamfer_count: int = 0,
) -> tuple[str, list[str]]:
    spec = norm_spec(profile)
    plate = is_plate_like or spec.startswith("PL")
    if not plate:
        if spec.startswith("D"):
            process, evidence = "挂钩", ["圆杆规格"]
        elif _is_channel_profile(spec):
            process, evidence = "成品槽", ["槽钢规格"]
        elif is_section_profile(spec):
            process, evidence = "不下", ["轧制型材"]
        else:
            process, evidence = "不下", ["非板件"]
        if bolt_hole_count > 0 or remaining_cut_count(
            hole_like_feature_count=hole_like_feature_count,
            bolt_hole_count=bolt_hole_count,
            boolean_cut_count=boolean_cut_count,
            edge_bevel_count=edge_bevel_count,
            end_chamfer_count=end_chamfer_count,
        ):
            evidence = evidence + ["洞口"]
        return process, evidence

    if is_folded_plate(obb_dims, thickness) or _runtime_bent(runtime_type):
        return "下料折弯", ["板件出平面/折弯体"]
    if bolt_hole_count > 0 or hole_like_feature_count > 0:
        return "下料割孔", ["洞口"]
    return "下料", ["平板无孔"]


def classify_shop_shape(
    *,
    profile: str,
    runtime_type: str,
    is_plate_like: bool,
    thickness: float,
    obb_dims: Sequence[float],
    contour_vertex_count: int,
    concave_corner_count: int,
    contour_points: Sequence[Sequence[float]] = (),
    contour_chamfers: Sequence[Sequence[object]] = (),
    contour_chamfer_types: Sequence[str] = (),
    hole_like_feature_count: int = 0,
    bolt_hole_count: int = 0,
    is_main_material: bool = False,
    has_edge_bevel: bool = False,
    has_end_chamfer: bool = False,
) -> tuple[str, list[str]]:
    spec = norm_spec(profile)
    plate = is_plate_like or spec.startswith("PL")
    if not plate:
        evidence = ["非板件不参与方块/异形"]
        if has_edge_bevel:
            evidence.append("板边剖口")
        if has_end_chamfer:
            evidence.append("倒角")
        return "", evidence

    outline, evidence = classify_outline(
        runtime_type=runtime_type,
        thickness=thickness,
        obb_dims=obb_dims,
        contour_vertex_count=contour_vertex_count,
        concave_corner_count=concave_corner_count,
        contour_points=contour_points,
        contour_chamfers=contour_chamfers or tuple((kind, 0.0, 0.0) for kind in contour_chamfer_types),
    )
    if has_end_chamfer and outline == "RECTANGLE":
        outline = "IRREGULAR"
        evidence = evidence + ["平面倒角"]
    if bolt_hole_count > 0 or has_inner_opening(hole_like_feature_count, bolt_hole_count):
        evidence = evidence + ["洞口"]
        outline = "IRREGULAR"
    if has_edge_bevel:
        evidence = evidence + ["板边剖口"]
    if outline == "RECTANGLE":
        return "方块", evidence
    if outline == "UNKNOWN":
        return "UNKNOWN", evidence
    if is_main_material:
        return "异形主材", evidence + ["主板非标准矩形"]
    return "异形", evidence


def classify_outline(
    *,
    runtime_type: str,
    thickness: float,
    obb_dims: Sequence[float],
    contour_vertex_count: int,
    concave_corner_count: int,
    contour_points: Sequence[Sequence[float]] = (),
    contour_chamfers: Sequence[Sequence[object]] = (),
) -> tuple[str, list[str]]:
    if is_folded_plate(obb_dims, thickness) or _runtime_bent(runtime_type):
        return "IRREGULAR", ["折弯/出平面"]
    if contour_points and len(contour_points) >= 3:
        kind, evidence = classify_plan_outline(project_uv(contour_points), contour_chamfers)
        if kind == "RECTANGLE":
            return "RECTANGLE", evidence
        return "IRREGULAR", evidence
    if concave_corner_count > 0 or contour_vertex_count > 4:
        return "IRREGULAR", ["轮廓非四边矩形"]
    if (runtime_type or "").upper() == "POLYBEAM":
        return "IRREGULAR", ["PolyBeam无矩形轮廓"]
    rebuilt = rectangle_from_obb(obb_dims, thickness)
    if len(rebuilt) >= 4:
        kind, evidence = classify_plan_outline(project_uv(rebuilt), contour_chamfers)
        if kind == "RECTANGLE":
            return "RECTANGLE", evidence
        return "IRREGULAR", evidence
    return "UNKNOWN", ["轮廓不足以证明标准矩形"]


def _runtime_bent(runtime_type: str) -> bool:
    text = (runtime_type or "").lower()
    return "bent" in text or "lofted" in text
