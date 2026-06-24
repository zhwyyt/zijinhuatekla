from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..rules import text


class DataQualityIssueType(str, Enum):
    DATA_MISSING = "DATA_MISSING"
    MATCH_CONFLICT = "MATCH_CONFLICT"
    NUMBERING_DRIFT = "NUMBERING_DRIFT"
    MANUFACTURING_MODEL_SCOPE_MISMATCH = "MANUFACTURING_MODEL_SCOPE_MISMATCH"


@dataclass(frozen=True)
class DataQualityIssue:
    issue_type: DataQualityIssueType
    part_name: str
    status: str
    match_method: str
    evidence: str = ""


@dataclass(frozen=True)
class DataQualityReport:
    status_counts: Counter[str] = field(default_factory=Counter)
    method_counts: Counter[str] = field(default_factory=Counter)
    issues: list[DataQualityIssue] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.issues


def quality_report_from_aligned_rows(rows: list[dict[str, Any]]) -> DataQualityReport:
    status_counts = Counter(text(row.get("prediction_status")) for row in rows)
    method_counts = Counter(text(row.get("match_method")) for row in rows)
    issues = []
    for row in rows:
        status = text(row.get("prediction_status"))
        match_method = text(row.get("match_method"))
        issue_type = _issue_type(status, match_method, text(row.get("quality_issue_type_hint")))
        if issue_type is None:
            continue
        issues.append(
            DataQualityIssue(
                issue_type=issue_type,
                part_name=text(row.get("零件名称") or row.get("part_name")),
                status=status,
                match_method=match_method,
                evidence=text(row.get("match_note") or row.get("evidence")),
            )
        )
    return DataQualityReport(status_counts=status_counts, method_counts=method_counts, issues=issues)


def _issue_type(status: str, match_method: str, issue_type_hint: str = "") -> DataQualityIssueType | None:
    if issue_type_hint:
        try:
            return DataQualityIssueType(issue_type_hint)
        except ValueError:
            pass
    if status == "DATA_MISSING" or match_method == "missing":
        return DataQualityIssueType.DATA_MISSING
    if status == "MATCH_CONFLICT" or match_method == "partPositionConflict":
        return DataQualityIssueType.MATCH_CONFLICT
    return None
