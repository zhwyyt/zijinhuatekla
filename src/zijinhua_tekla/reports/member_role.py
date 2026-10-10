"""Report the accepted structural role separately from section geometry."""

from __future__ import annotations

from typing import Any

from ..classifiers.member_structural_role import (
    StructuralRoleAssertion,
    classify_body_bracket_assembly,
)
from ..rules import text


ALIGNED_SPAN_AXIS_SOURCE = "assemblyParts.alignedSpanCentroid"
MEMBER_ROLE_COLUMNS = [
    "构件名称", "装配ID", "构件角色", "角色代码", "职能子类",
    "轴线姿态", "轴线形状", "折点数量", "主轴来源", "复核状态",
    "置信度", "规则", "证据",
]
_POSE_LABELS = {
    "vertical": "竖直", "horizontal": "水平", "inclined": "倾斜", "unknown": "未知",
}


def member_axis_review(assembly: dict[str, Any], member: dict[str, Any]) -> tuple[str, str]:
    source = text(((assembly.get("metadata") or {}).get("memberAxisEvidence") or {}).get("source"))
    member_source = text(member.get("LongitudinalAxisSource"))
    if source != ALIGNED_SPAN_AXIS_SOURCE or member_source != ALIGNED_SPAN_AXIS_SOURCE:
        return source or "未知", "旧主轴或来源不一致，需重新导出"
    return source, ""


def member_role_row(
    assembly: dict[str, Any],
    member: dict[str, Any],
    assertion: StructuralRoleAssertion | None = None,
) -> dict[str, Any]:
    result = assertion or classify_body_bracket_assembly(assembly, member)
    source, review = member_axis_review(assembly, member)
    if result.role == "UNKNOWN":
        review = ";".join(item for item in (review, "角色证据不足或冲突") if item)
    return {
        "构件名称": result.member_id,
        "装配ID": text(assembly.get("assemblyId")),
        "构件角色": result.role_label,
        "角色代码": result.role,
        "职能子类": result.subtype,
        "轴线姿态": _POSE_LABELS[result.pose],
        "轴线形状": result.axis_form,
        "折点数量": result.bend_count if result.axis_form != "未知" else "",
        "主轴来源": source,
        "复核状态": review,
        "置信度": result.confidence,
        "规则": result.rule_id,
        "证据": ";".join(result.evidence_codes),
    }
