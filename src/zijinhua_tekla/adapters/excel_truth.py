"""Excel 清单 -> list[dict] 适配, 泛化列映射不硬编码."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..config import ColumnMapping


def load_truth_rows(
    truth_path: Path,
    member_id: str,
    member_col: str = "构件名称",
    column_mapping: ColumnMapping | None = None,
    sheet_name: str | None = None,
) -> list[dict[str, Any]]:
    """读取 Excel 并筛选指定构件的零件行.

    Args:
        truth_path: Excel 文件路径
        member_id: 目标构件编号
        member_col: 构件列名(默认 '构件名称')
        column_mapping: 可选列映射
        sheet_name: 可选工作表名
    """
    kwargs: dict[str, Any] = {"dtype": object}
    if sheet_name:
        kwargs["sheet_name"] = sheet_name
    df = pd.read_excel(truth_path, header=None, **kwargs)

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        val = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if val != member_id:
            continue
        rows.append(_row_to_dict(row, column_mapping))
    return rows


def _row_to_dict(
    row: pd.Series,
    mapping: ColumnMapping | None = None,
) -> dict[str, Any]:
    if mapping is None:
        mapping = ColumnMapping()
    return {
        "构件名称": _text(row.iloc[0]),
        "零件名称": _text(row.iloc[1]),
        "规格": _text(row.iloc[2]),
        "长度": _as_int(row.iloc[3]),
        "数量": _as_int(row.iloc[4]),
        "单重": _as_float(row.iloc[5]),
        "总重": _as_float(row.iloc[6]),
        "材质": _text(row.iloc[7]),
        "备注": _text(row.iloc[8]),
        "工序": _text(row.iloc[9]),
        "形状分类": _text(row.iloc[10]),
        "配送责任": _text(row.iloc[11]),
        "配送线": _text(row.iloc[12]),
        "配送用途": _text(row.iloc[13]),
    }


def _text(v: Any) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def _as_int(v: Any) -> int:
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return 0


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0