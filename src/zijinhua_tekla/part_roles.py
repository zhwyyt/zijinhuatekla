from __future__ import annotations

from dataclasses import dataclass, field
import re

from .contracts.normalized import NormalizedPart, PartSpatialHints
from .geom.shop import classify_shop_process, classify_shop_shape
from .rules import parse_pl, text


_BOX_MAIN_ROLES = {
    "BOX_MAIN_WALL_PLATE",
    "BOX_FORMING_MAIN_PLATE",
}
_H_MAIN_ROLES = {
    "H_TOP_FLANGE_MAIN_PLATE",
    "H_BOTTOM_FLANGE_MAIN_PLATE",
    "H_WEB_MAIN_PLATE",
    "H_FLANGE_MAIN_PLATE",
}
_CROSS_MAIN_ROLES = {
    "CROSS_CORE_MAIN_PLATE",
    "CROSS_FLANGE_MAIN_PLATE",
    "TRANSITION_MAIN_PLATE",
}
MAIN_MATERIAL_LABELS = {
    "BOX_MAIN_WALL_PLATE": "BOX主壁板",
    "BOX_FORMING_MAIN_PLATE": "BOX主壁板",
    "H_TOP_FLANGE_MAIN_PLATE": "H上翼缘",
    "H_BOTTOM_FLANGE_MAIN_PLATE": "H下翼缘",
    "H_WEB_MAIN_PLATE": "H腹板",
    "H_FLANGE_MAIN_PLATE": "H翼缘",
    "CROSS_CORE_MAIN_PLATE": "十字核心",
    "CROSS_FLANGE_MAIN_PLATE": "十字翼缘",
    "TRANSITION_MAIN_PLATE": "过渡主板",
    "END_NODE_MAIN_PLATE_CANDIDATE": "端部主板候选",
}


def main_material_label(hints: PartSpatialHints | None, role: str = "") -> str:
    hints = hints or PartSpatialHints()
    body = (hints.member_body_type or "").upper()
    mapped = MAIN_MATERIAL_LABELS.get(hints.main_material_role or "")
    if body == "BOX":
        if (
            hints.relation_to_box_body == "MAIN_WALL"
            or role == "箱型柱主材壁板"
            or hints.main_material_role in _BOX_MAIN_ROLES
        ):
            return "BOX主壁板"
        return "否"
    if mapped:
        return mapped
    if role == "箱型柱主材壁板":
        return "BOX主壁板"
    return "否"


@dataclass(frozen=True)
class PartRoleResult:
    role: str
    process: str
    shape: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


def contains_any(value: str, keywords: list[str]) -> bool:
    return any(keyword in value for keyword in keywords)


def number_series(name: str) -> str:
    match = re.match(r"^[A-Za-z0-9]+-([A-Za-z]+)-", text(name))
    if match:
        return match.group(1).upper()
    match = re.match(r"^[A-Za-z]+-", text(name))
    return match.group(0).rstrip("-").upper() if match else ""


def infer_role(part: NormalizedPart, hints: PartSpatialHints | None = None) -> tuple[str, list[str]]:
    hints = hints or PartSpatialHints()
    spec = part.profile
    name = part.name
    position = part.part_position
    length = part.length
    pl = parse_pl(spec)
    series = number_series(position)
    evidence: list[str] = []

    if hints.relation_to_box_body == "MAIN_WALL" or hints.main_material_role in _BOX_MAIN_ROLES:
        evidence.append("截面主壁板")
        return "箱型柱主材壁板", evidence
    if hints.main_material_role in _H_MAIN_ROLES:
        evidence.append("H截面主板")
        return "板件", evidence
    if hints.main_material_role in _CROSS_MAIN_ROLES:
        evidence.append("组合截面主板")
        return "板件", evidence
    if hints.appendage_role == "Bracket":
        evidence.append("外侧附属件簇=Bracket")
        return "牛腿/钢梁相关件", evidence
    if hints.appendage_role == "ConnectionPlate":
        evidence.append("外侧单板连接")
        return "连接板", evidence
    if hints.relation_to_box_body == "INSIDE_BODY" and contains_any(name, ["隔板"]):
        evidence.append("内腔+隔板名称")
        return "内隔板", evidence

    if position == "CP-1" or name == "CP-1" or ("C" in spec and not spec.startswith("PL")):
        evidence.append("非PL型材")
        return "成品槽钢/外购件", evidence
    if spec.startswith("D"):
        evidence.append("D类圆杆规格")
        return "挂钩/圆杆件", evidence
    if series == "DB":
        evidence.append("编号系列=DB")
        return "电渣焊块", evidence
    if series == "H":
        evidence.append("编号系列=H")
        return "牛腿/钢梁相关件", evidence
    if series == "PX":
        evidence.append("编号系列=PX")
        return "现场件/封板类", evidence
    if "衬垫板" in name or (pl and pl[1] <= 35 and length >= 800):
        evidence.append("衬垫板名称/窄长垫板")
        return "衬垫板", evidence
    if series == "PR":
        evidence.append("编号系列=PR")
        return "对接耳板/连接小板", evidence
    if contains_any(name, ["隔板"]):
        evidence.append("Tekla名称=隔板")
        return "内隔板", evidence
    if contains_any(name, ["柱内竖向劲板"]):
        evidence.append("Tekla名称=柱内竖向劲板")
        return "柱内竖向劲板", evidence
    if contains_any(name, ["幕墙埋件"]):
        evidence.append("Tekla名称=幕墙埋件")
        return "幕墙埋件", evidence
    if contains_any(name, ["连接板"]):
        evidence.append("Tekla名称=连接板")
        return "连接板", evidence
    if contains_any(name, ["PLATE"]):
        evidence.append("Tekla名称=PLATE")
        return "厚板/牛腿板", evidence
    if pl:
        thickness, width = pl
        if length > 9000 and width >= 900 and thickness <= 20:
            evidence.append("超长宽板")
            return "箱型柱主材壁板", evidence
        if width >= 800 and 800 <= length <= 1000 and thickness >= 10:
            evidence.append("大宽板/内隔板口径")
            return "内隔板", evidence
        if part.bolt_hole_count >= 2:
            evidence.append("孔类连接证据")
            return "带孔/切割板", evidence
        if width <= 300 and length <= 1300:
            evidence.append("中小PL板")
            return "小板/加劲板/连接板", evidence
        evidence.append("PL板默认")
        return "板件", evidence
    return "UNKNOWN", evidence


def infer_process(part: NormalizedPart, role: str = "") -> tuple[str, list[str]]:
    _ = role
    return classify_shop_process(
        profile=part.profile,
        runtime_type=part.runtime_type,
        is_plate_like=part.is_plate_like,
        thickness=part.thickness,
        obb_dims=part.obb_dims,
        bolt_hole_count=part.bolt_hole_count,
        hole_like_feature_count=part.hole_like_feature_count,
        boolean_cut_count=part.boolean_cut_count,
        edge_bevel_count=part.edge_bevel_count,
        end_chamfer_count=part.end_chamfer_count,
    )


def infer_shape(part: NormalizedPart, role: str = "", process: str = "", hints: PartSpatialHints | None = None) -> tuple[str, list[str]]:
    _ = process
    hints = hints or PartSpatialHints()
    is_main = (
        hints.relation_to_box_body == "MAIN_WALL"
        or hints.main_material_role in _BOX_MAIN_ROLES
        or hints.main_material_role in _H_MAIN_ROLES
        or hints.main_material_role in _CROSS_MAIN_ROLES
        or role == "箱型柱主材壁板"
    )
    return classify_shop_shape(
        profile=part.profile,
        runtime_type=part.runtime_type,
        is_plate_like=part.is_plate_like,
        thickness=part.thickness,
        obb_dims=part.obb_dims,
        contour_vertex_count=part.contour_vertex_count,
        concave_corner_count=part.concave_corner_count,
        contour_points=part.contour_points,
        contour_chamfers=part.contour_chamfers,
        hole_like_feature_count=part.hole_like_feature_count,
        bolt_hole_count=part.bolt_hole_count,
        is_main_material=is_main,
        has_edge_bevel=part.has_edge_bevel,
        has_end_chamfer=part.has_end_chamfer,
    )


def _confidence_from_evidence(part: NormalizedPart, evidence: list[str], hints: PartSpatialHints | None) -> float:
    score = 0.35
    if hints and (hints.main_material_role or hints.relation_to_box_body or hints.appendage_role):
        score += 0.2
    if part.bolt_hole_count:
        score += 0.15
    if part.boolean_cut_count:
        score += 0.1
    if part.name:
        score += 0.15
    if evidence:
        score += min(0.25, len(evidence) * 0.06)
    return max(0.0, min(1.0, score))


def classify_part_role(part: NormalizedPart, hints: PartSpatialHints | None = None) -> PartRoleResult:
    role, role_evidence = infer_role(part, hints)
    process, process_evidence = infer_process(part)
    shape, shape_evidence = infer_shape(part, role=role, hints=hints)
    evidence = []
    for item in role_evidence + process_evidence + shape_evidence:
        if item not in evidence:
            evidence.append(item)
    return PartRoleResult(
        role=role,
        process=process,
        shape=shape,
        confidence=_confidence_from_evidence(part, evidence, hints),
        evidence=evidence,
    )
