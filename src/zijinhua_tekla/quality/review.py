from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from .gate import DataQualityIssue, DataQualityIssueType, DataQualityReport


DEFAULT_EVIDENCE_FIELDS = ["part_name", "status", "match_method", "evidence"]
CSV_FIELDS = [
    "task_id",
    "member_id",
    "part_name",
    "issue_type",
    "case_issue_type",
    "recommended_action",
    "evidence",
    "evidence_fields",
]


@dataclass(frozen=True)
class QualityReviewTask:
    task_id: str
    member_id: str
    part_name: str
    issue_type: str
    case_issue_type: str
    recommended_action: str
    evidence: str = ""
    evidence_fields: list[str] = field(default_factory=lambda: list(DEFAULT_EVIDENCE_FIELDS))

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "member_id": self.member_id,
            "part_name": self.part_name,
            "issue_type": self.issue_type,
            "case_issue_type": self.case_issue_type,
            "recommended_action": self.recommended_action,
            "evidence": self.evidence,
            "evidence_fields": list(self.evidence_fields),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "QualityReviewTask":
        return cls(
            task_id=str(data.get("task_id", "")),
            member_id=str(data.get("member_id", "")),
            part_name=str(data.get("part_name", "")),
            issue_type=str(data.get("issue_type", "")),
            case_issue_type=str(data.get("case_issue_type", "")),
            recommended_action=str(data.get("recommended_action", "")),
            evidence=str(data.get("evidence", "")),
            evidence_fields=[str(item) for item in data.get("evidence_fields", [])],
        )


def build_review_tasks(member_id: str, report: DataQualityReport) -> list[QualityReviewTask]:
    return [_task_from_issue(member_id, issue) for issue in report.issues]


def save_review_tasks_json(tasks: list[QualityReviewTask], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"tasks": [task.to_dict() for task in tasks]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_review_tasks_json(path: Path) -> list[QualityReviewTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [QualityReviewTask.from_dict(item) for item in payload.get("tasks", [])]


def save_review_tasks_csv(tasks: list[QualityReviewTask], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for task in tasks:
            row = task.to_dict()
            row["evidence_fields"] = ";".join(task.evidence_fields)
            writer.writerow(row)


def load_review_tasks_csv(path: Path) -> list[QualityReviewTask]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            QualityReviewTask.from_dict(
                {
                    **row,
                    "evidence_fields": [item for item in row.get("evidence_fields", "").split(";") if item],
                }
            )
            for row in csv.DictReader(handle)
        ]


def summarize_review_tasks(tasks: list[QualityReviewTask]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[QualityReviewTask]] = {}
    for task in tasks:
        key = (task.issue_type, task.recommended_action)
        grouped.setdefault(key, []).append(task)

    rows = []
    for issue_type, recommended_action in sorted(grouped):
        group_tasks = grouped[(issue_type, recommended_action)]
        rows.append(
            {
                "issue_type": issue_type,
                "recommended_action": recommended_action,
                "task_count": len(group_tasks),
                "part_names": ";".join(task.part_name for task in group_tasks),
            }
        )
    return rows


def _task_from_issue(member_id: str, issue: DataQualityIssue) -> QualityReviewTask:
    issue_type = issue.issue_type.value
    return QualityReviewTask(
        task_id=f"{member_id}:{issue.part_name}:{issue_type}",
        member_id=member_id,
        part_name=issue.part_name,
        issue_type=issue_type,
        case_issue_type="DATA",
        recommended_action=_recommended_action(issue.issue_type),
        evidence=issue.evidence,
        evidence_fields=list(DEFAULT_EVIDENCE_FIELDS),
    )


def _recommended_action(issue_type: DataQualityIssueType) -> str:
    if issue_type == DataQualityIssueType.DATA_MISSING:
        return "全模型搜索候选零件并核对 Excel/模型编号"
    if issue_type == DataQualityIssueType.MATCH_CONFLICT:
        return "核对同名零件的规格/长度冲突；几何候选仅作复核证据"
    if issue_type == DataQualityIssueType.MANUFACTURING_MODEL_SCOPE_MISMATCH:
        return "核对制造整板与 Tekla 分段口径映射"
    if issue_type == DataQualityIssueType.NUMBERING_DRIFT:
        return "核对编号漂移并记录候选映射"
    return "人工复核质量问题并记录归因"
