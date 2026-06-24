"""归因流程 -- 失败案例归因建议."""
from __future__ import annotations

from dataclasses import dataclass
from .bank import CaseFeedback, CaseIssueType


REASON_TARGETS: dict[CaseIssueType, str] = {
    CaseIssueType.DATA: "Data Quality Gate -- 更新检测规则",
    CaseIssueType.FEATURE: "Feature Snapshot -- 补字段",
    CaseIssueType.SCORING: "Scoring -- 调权重/阈值",
    CaseIssueType.NEW_TYPE: "类别定义 -- 补验收样例",
}


@dataclass(frozen=True)
class AttributionResult:
    case_id: str
    issue_type: CaseIssueType
    target_layer: str
    suggestion: str


def suggest_attribution(feedback: CaseFeedback) -> AttributionResult:
    """根据归因类型给出修改目标."""
    return AttributionResult(
        case_id=feedback.case_id,
        issue_type=feedback.issue_type,
        target_layer=feedback.layer or REASON_TARGETS.get(feedback.issue_type, "unknown"),
        suggestion=REASON_TARGETS.get(feedback.issue_type, "未知归因"),
    )


def batch_attribute(feedbacks: list[CaseFeedback]) -> list[AttributionResult]:
    return [suggest_attribution(f) for f in feedbacks]