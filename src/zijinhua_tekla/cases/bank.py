"""Case Bank CRUD + 持久化 -- S1 骨架.

增强字段: layer, actual_label, regression_command.
兼容已有 casebank.py 的 CaseBank 实例。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class CaseIssueType(str, Enum):
    DATA = "DATA"
    FEATURE = "FEATURE"
    SCORING = "SCORING"
    NEW_TYPE = "NEW_TYPE"


@dataclass(frozen=True)
class CaseFeedback:
    case_id: str
    issue_type: CaseIssueType
    expected_label: str
    human_note: str
    evidence_fields: list[str] = field(default_factory=list)
    layer: str = ""
    actual_label: str = ""
    regression_command: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "issue_type": self.issue_type.value,
            "expected_label": self.expected_label,
            "human_note": self.human_note,
            "evidence_fields": list(self.evidence_fields),
            "layer": self.layer,
            "actual_label": self.actual_label,
            "regression_command": self.regression_command,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CaseFeedback:
        return cls(
            case_id=str(data.get("case_id", "")),
            issue_type=CaseIssueType(str(data.get("issue_type", ""))),
            expected_label=str(data.get("expected_label", "")),
            human_note=str(data.get("human_note", "")),
            evidence_fields=[str(i) for i in data.get("evidence_fields", [])],
            layer=str(data.get("layer", "")),
            actual_label=str(data.get("actual_label", "")),
            regression_command=str(data.get("regression_command", "")),
        )


class CaseBank:
    def __init__(self) -> None:
        self._items: dict[str, CaseFeedback] = {}

    def add(self, feedback: CaseFeedback) -> None:
        if not feedback.case_id:
            raise ValueError("case_id is required")
        self._items[feedback.case_id] = feedback

    def get(self, case_id: str) -> CaseFeedback | None:
        return self._items.get(case_id)

    def by_issue_type(self, issue_type: CaseIssueType) -> list[CaseFeedback]:
        return [f for f in self._items.values() if f.issue_type == issue_type]

    def all(self) -> list[CaseFeedback]:
        return list(self._items.values())

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cases": [f.to_dict() for f in self.all()]}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path) -> CaseBank:
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        bank = cls()
        for item in payload.get("cases", []):
            bank.add(CaseFeedback.from_dict(item))
        return bank