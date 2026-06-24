from __future__ import annotations

import csv
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

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "issue_type": self.issue_type.value,
            "expected_label": self.expected_label,
            "human_note": self.human_note,
            "evidence_fields": list(self.evidence_fields),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CaseFeedback":
        return cls(
            case_id=str(data.get("case_id", "")),
            issue_type=CaseIssueType(str(data.get("issue_type", ""))),
            expected_label=str(data.get("expected_label", "")),
            human_note=str(data.get("human_note", "")),
            evidence_fields=[str(item) for item in data.get("evidence_fields", [])],
        )


class CaseBank:
    def __init__(self) -> None:
        self._items: dict[str, CaseFeedback] = {}

    def add(self, feedback: CaseFeedback) -> None:
        _validate_feedback(feedback)
        self._items[feedback.case_id] = feedback

    def get(self, case_id: str) -> CaseFeedback | None:
        return self._items.get(case_id)

    def by_issue_type(self, issue_type: CaseIssueType) -> list[CaseFeedback]:
        return [item for item in self._items.values() if item.issue_type == issue_type]

    def all(self) -> list[CaseFeedback]:
        return list(self._items.values())

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cases": [item.to_dict() for item in self.all()]}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path) -> "CaseBank":
        payload = json.loads(path.read_text(encoding="utf-8"))
        bank = cls()
        for item in payload.get("cases", []):
            bank.add(CaseFeedback.from_dict(item))
        return bank

    def save_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["case_id", "issue_type", "expected_label", "human_note", "evidence_fields"],
            )
            writer.writeheader()
            for item in self.all():
                row = item.to_dict()
                row["evidence_fields"] = ";".join(item.evidence_fields)
                writer.writerow(row)

    @classmethod
    def load_csv(cls, path: Path) -> "CaseBank":
        bank = cls()
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                bank.add(
                    CaseFeedback(
                        case_id=row.get("case_id", ""),
                        issue_type=CaseIssueType(row.get("issue_type", "")),
                        expected_label=row.get("expected_label", ""),
                        human_note=row.get("human_note", ""),
                        evidence_fields=[item for item in row.get("evidence_fields", "").split(";") if item],
                    )
                )
        return bank


def _validate_feedback(feedback: CaseFeedback) -> None:
    if not feedback.case_id:
        raise ValueError("case_id is required")
    if not feedback.expected_label:
        raise ValueError("expected_label is required")
    if not feedback.human_note:
        raise ValueError("human_note is required")
    if not feedback.evidence_fields:
        raise ValueError("evidence_fields is required")
