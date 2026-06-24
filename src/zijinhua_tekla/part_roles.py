from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .rules import parse_pl, text


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


def infer_role(row: dict[str, Any], summary: dict[str, Any]) -> tuple[str, list[str]]:
    spec = row["规格"]
    name = row["零件名称"]
    length = row["长度"]
    pl = parse_pl(spec)
    tekla_names = summary["tekla_names"]
    series = number_series(name)
    evidence = []

    if name == "CP-1" or ("C" in spec and not spec.startswith("PL")):
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
    if "衬垫板" in tekla_names or (pl and pl[1] <= 35 and length >= 800):
        evidence.append("衬垫板名称/窄长垫板")
        return "衬垫板", evidence
    if series == "PR":
        evidence.append("编号系列=PR")
        return "对接耳板/连接小板", evidence
    if contains_any(tekla_names, ["隔板"]):
        evidence.append("Tekla名称=隔板")
        return "内隔板", evidence
    if contains_any(tekla_names, ["柱内竖向劲板"]):
        evidence.append("Tekla名称=柱内竖向劲板")
        return "柱内竖向劲板", evidence
    if contains_any(tekla_names, ["幕墙埋件"]):
        evidence.append("Tekla名称=幕墙埋件")
        return "幕墙埋件", evidence
    if contains_any(tekla_names, ["连接板"]):
        evidence.append("Tekla名称=连接板")
        return "连接板", evidence
    if contains_any(tekla_names, ["PLATE"]):
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
        if summary["bolt_holes"] >= 2:
            evidence.append("孔类连接证据")
            return "带孔/切割板", evidence
        if width <= 300 and length <= 1300:
            evidence.append("中小PL板")
            return "小板/加劲板/连接板", evidence
        evidence.append("PL板默认")
        return "板件", evidence
    return "未分类", evidence


def infer_process(row: dict[str, Any], summary: dict[str, Any], role: str) -> tuple[str, list[str]]:
    spec = row["规格"]
    length = row["长度"]
    pl = parse_pl(spec)
    evidence = []

    if role == "成品槽钢/外购件":
        evidence.append("成品型材角色")
        return "成品槽", evidence
    if role == "挂钩/圆杆件":
        evidence.append("圆杆挂钩角色")
        return "挂钩", evidence
    if role in {"电渣焊块", "现场件/封板类", "衬垫板"}:
        evidence.append("组立/现场/垫板不下料口径")
        return "不下", evidence
    if role == "牛腿/钢梁相关件":
        evidence.append("H编号牛腿零件")
        return "不下" if "BH" in spec else "下料", evidence
    if role == "箱型柱主材壁板":
        evidence.append("箱型柱主壁板折弯")
        return "下料折弯", evidence
    if role == "内隔板":
        evidence.append("内隔板通常割孔")
        return "下料割孔", evidence
    if role in {"对接耳板/连接小板", "带孔/切割板"}:
        evidence.append("连接/孔类板")
        return "下料割孔", evidence
    if role == "连接板" and summary["bolt_holes"] >= 1:
        evidence.append("连接板带孔")
        return "下料割孔", evidence
    if pl and pl[1] >= 500 and summary["bolt_holes"] >= 1:
        evidence.append("宽板带孔")
        return "下料割孔", evidence
    if summary["bolt_holes"] >= 2 and role not in {"箱型柱主材壁板"}:
        evidence.append("多孔证据")
        return "下料割孔", evidence
    if length > 9000 and pl and pl[1] >= 900:
        evidence.append("超长宽板兜底")
        return "下料折弯", evidence
    return "下料", evidence


def infer_shape(row: dict[str, Any], summary: dict[str, Any], role: str, process: str) -> tuple[str, list[str]]:
    name = row["零件名称"]
    length = row["长度"]
    pl = parse_pl(row["规格"])
    evidence = []

    if role == "箱型柱主材壁板":
        evidence.append("主壁板")
        return "异形主材", evidence
    if process in {"不下", "成品槽", "挂钩"}:
        evidence.append("非下料形状不参与方块/异形")
        return "", evidence
    if role in {"内隔板", "对接耳板/连接小板", "连接板", "带孔/切割板"}:
        evidence.append("隔板/连接孔类")
        return "异形", evidence
    if role == "厚板/牛腿板":
        evidence.append("厚板/牛腿板口径")
        return "异形", evidence
    if role == "牛腿/钢梁相关件":
        evidence.append("H编号板形")
        return "异形" if name.endswith("f") else "方块", evidence
    if role == "幕墙埋件":
        if summary["bolt_holes"] or summary["boolean_cuts"] or (summary["contour_vertices"] > 4 and length < 500):
            evidence.append("幕墙埋件短异形/切割")
            return "异形", evidence
        evidence.append("幕墙埋件长矩形")
        return "方块", evidence
    if role == "柱内竖向劲板":
        if summary["boolean_cuts"] >= 2:
            evidence.append("劲板多切割")
            return "异形", evidence
        if pl and pl[1] == 200 and 180 <= length <= 1250 and not name.endswith("7"):
            evidence.append("柱内竖向劲板批次口径")
            return "异形", evidence
        evidence.append("柱内竖向劲板矩形口径")
        return "方块", evidence
    if summary["bolt_holes"] or summary["boolean_cuts"] >= 2 or summary["concave_corners"]:
        evidence.append("孔/cut/凹角")
        return "异形", evidence
    if summary["has_arc_contour"] and summary["contour_vertices"] > 5 and length <= 500:
        evidence.append("短板多边/弧边")
        return "异形", evidence
    if summary["is_special_shape"]:
        evidence.append("导出特殊形状")
        return "异形", evidence
    return "方块", evidence


def _confidence_from_evidence(summary: dict[str, Any], evidence: list[str]) -> float:
    score = 0.35
    if summary.get("tekla_count", 1) == 0:
        score -= 0.2
    if summary.get("bolt_holes", 0):
        score += 0.15
    if summary.get("boolean_cuts", 0):
        score += 0.1
    if summary.get("tekla_names"):
        score += 0.15
    if evidence:
        score += min(0.25, len(evidence) * 0.06)
    return max(0.0, min(1.0, score))


def classify_part_role(row: dict[str, Any], summary: dict[str, Any]) -> PartRoleResult:
    role, role_evidence = infer_role(row, summary)
    process, process_evidence = infer_process(row, summary, role)
    shape, shape_evidence = infer_shape(row, summary, role, process)
    evidence = role_evidence + process_evidence + shape_evidence
    return PartRoleResult(
        role=role,
        process=process,
        shape=shape,
        confidence=_confidence_from_evidence(summary, evidence),
        evidence=evidence,
    )
