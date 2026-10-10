"""Build one Excel workbook from a Tekla export root."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from ..rules import text
from ..classifiers.connection_review import connection_review_candidates
from .member_complexity import MEMBER_COMPLEXITY_COLUMNS, classify_member_complexity
from .member_role import MEMBER_ROLE_COLUMNS, member_axis_review, member_role_row
from .part_feature_excel import FEATURE_COLUMNS, build_part_feature_rows


BUNDLE_FILENAME = "tekla-body-bracket-export.bundle.json"
FEATURE_SHEET_NAME = "零件特征"
COMPLEXITY_SHEET_NAME = "构件复杂度"
ROLE_SHEET_NAME = "构件角色"
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n]+')


@dataclass(frozen=True)
class CombinedExcelResult:
    path: Path
    assembly_count: int
    feature_row_count: int
    complexity_row_count: int
    errors: list[dict[str, str]] = field(default_factory=list)
    role_row_count: int = 0
    axis_review_count: int = 0
    connection_review_count: int = 0

    @property
    def error_count(self) -> int:
        return len(self.errors)


def inspect_export_root(root: Path | str) -> dict[str, Any]:
    export_root = Path(root)
    bundle_path = export_root / BUNDLE_FILENAME
    members_dir = export_root / "members"
    member_count = (
        len(list(members_dir.glob("member_*.json")))
        if members_dir.is_dir()
        else 0
    )
    return {
        "root": export_root,
        "bundle_path": bundle_path,
        "bundle_found": bundle_path.is_file(),
        "member_count": member_count,
        "valid": bundle_path.is_file() and member_count > 0,
    }


def export_combined_excel(
    export_root: Path | str,
    project_name: str,
    project_area: str,
    output_dir: Path | str | None = None,
) -> CombinedExcelResult:
    source = inspect_export_root(export_root)
    if not source["bundle_found"]:
        raise FileNotFoundError(f"未找到 Tekla 导出包：{source['bundle_path']}")
    if not project_name.strip():
        raise ValueError("项目名称不能为空")
    if not project_area.strip():
        raise ValueError("工程区域不能为空")

    bundle_path: Path = source["bundle_path"]
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assemblies = bundle.get("assemblies") or []
    if not assemblies:
        raise ValueError("Tekla 导出包中没有 assemblies")

    member_cache: dict[str, dict[str, Any]] = {}
    feature_rows: list[dict[str, Any]] = []
    complexity_rows: list[dict[str, Any]] = []
    role_rows: list[dict[str, Any]] = []
    successful_assemblies: list[dict[str, Any]] = []
    axis_review_count = 0
    errors: list[dict[str, str]] = []
    for assembly in assemblies:
        member_id = text((assembly.get("metadata") or {}).get("assemblyPosition"))
        try:
            if member_id not in member_cache:
                member_cache[member_id] = _load_member(
                    Path(source["root"]),
                    member_id,
                )
            member = member_cache[member_id]
            features = build_part_feature_rows(assembly, member, member_id)
            complexity = classify_member_complexity(assembly, member).to_row()
            role = member_role_row(assembly, member)
            feature_rows.extend(features)
            complexity_rows.append(complexity)
            role_rows.append(role)
            successful_assemblies.append(assembly)
            axis_review_count += bool(member_axis_review(assembly, member)[1])
        except Exception as exc:
            errors.append(
                {
                    "member_id": member_id,
                    "assembly_id": text(assembly.get("assemblyId")),
                    "error": str(exc),
                }
            )

    if not complexity_rows:
        raise ValueError(f"没有可导出的构件复杂度数据；失败 {len(errors)} 个")

    target_dir = Path(output_dir) if output_dir else Path(source["root"])
    target_dir.mkdir(parents=True, exist_ok=True)
    path = _unique_path(target_dir / _report_filename(project_name, project_area))
    feature_frame = pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)
    complexity_frame = pd.DataFrame(
        complexity_rows,
        columns=MEMBER_COMPLEXITY_COLUMNS,
    )
    reviews = connection_review_candidates(successful_assemblies)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(role_rows, columns=MEMBER_ROLE_COLUMNS).to_excel(
            writer, index=False, sheet_name=ROLE_SHEET_NAME,
        )
        complexity_frame.to_excel(
            writer, index=False, sheet_name=COMPLEXITY_SHEET_NAME,
        )
        feature_frame.to_excel(
            writer,
            index=False,
            sheet_name=FEATURE_SHEET_NAME,
        )
        if reviews:
            pd.DataFrame([item.to_dict() for item in reviews]).rename(columns={
                "assembly_id": "装配ID", "assembly_position": "构件名称",
                "other_assembly_id": "候选装配ID", "other_assembly_position": "候选构件名称",
                "gap_mm": "间隙mm", "issue_type": "复核类型", "note": "复核说明",
            }).to_excel(writer, index=False, sheet_name="连接复核")
        if errors:
            pd.DataFrame(errors).rename(columns={
                "member_id": "构件名称", "assembly_id": "装配ID", "error": "失败原因",
            }).to_excel(writer, index=False, sheet_name="识别失败")

    return CombinedExcelResult(
        path=path,
        assembly_count=len(assemblies),
        feature_row_count=len(feature_rows),
        complexity_row_count=len(complexity_rows),
        errors=errors,
        role_row_count=len(role_rows),
        axis_review_count=axis_review_count,
        connection_review_count=len(reviews),
    )


def _load_member(root: Path, member_id: str) -> dict[str, Any]:
    path = root / "members" / f"member_{member_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"缺少构件导出文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _report_filename(project_name: str, project_area: str) -> str:
    clean_name = _INVALID_FILENAME_CHARS.sub("_", project_name.strip())
    clean_area = _INVALID_FILENAME_CHARS.sub("_", project_area.strip())
    return f"{clean_name}_{clean_area}.xlsx"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
