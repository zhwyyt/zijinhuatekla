"""Factory workbook vs recognition rows. Never imported by classifiers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..quality.manufacturing_scope import apply_confirmed_segment_groups, apply_manufacturing_scope_hints
from ..rules import find_equivalent_parts, summarize_parts, text


def compare_recognition_to_truth(
    recognition_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    by_pos: dict[str, list[dict[str, Any]]],
    all_parts: list[dict[str, Any]],
    rel_by_part: Any,
    roles: dict[str, dict[str, Any]],
    member_id: str,
    bundle: dict[str, Any],
    case_bank: Any,
) -> list[dict[str, Any]]:
    rec_by_pos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in recognition_rows:
        rec_by_pos[text(row.get("零件名称"))].append(row)

    aligned: list[dict[str, Any]] = []
    for row in truth_rows:
        parts, match_method, match_note = find_equivalent_parts(row, by_pos, all_parts)
        summary = summarize_parts(parts, rel_by_part, roles, row)
        predicted = _predicted_from_recognition(rec_by_pos.get(row["零件名称"], []))
        status = _score_prediction(row, summary, predicted, match_method)
        aligned.append(
            {
                **row,
                **summary,
                **predicted,
                "match_method": match_method,
                "match_note": match_note,
                "prediction_status": status,
            }
        )
    aligned = apply_confirmed_segment_groups(aligned, member_id, case_bank)
    return apply_manufacturing_scope_hints(aligned, bundle)


def _predicted_from_recognition(recs: list[dict[str, Any]]) -> dict[str, Any]:
    if not recs:
        return {
            "predicted_role": "UNKNOWN",
            "predicted_process": "",
            "predicted_shape": "",
            "predicted_delivery": "",
            "evidence": "",
            "confidence": 0.0,
        }
    rec = recs[0]
    role = text(rec.get("predicted_role") or "UNKNOWN")
    process = text(rec.get("predicted_process") or rec.get("工序"))
    shape = rec.get("predicted_shape")
    if shape is None:
        shape = rec.get("形状分类", "")
    return {
        "predicted_role": role,
        "predicted_process": process,
        "predicted_shape": shape,
        "predicted_delivery": rec.get("predicted_delivery", ""),
        "evidence": rec.get("evidence", ""),
        "confidence": rec.get("confidence", 0.0),
    }


def _score_prediction(
    row: dict[str, Any],
    summary: dict[str, Any],
    predicted: dict[str, Any],
    match_method: str,
) -> str:
    if summary["tekla_count"] == 0:
        return "DATA_MISSING"
    if match_method == "partPositionConflict":
        return "MATCH_CONFLICT"
    process_match = predicted.get("predicted_process") == row["工序"]
    truth_shape = row.get("形状分类") or ""
    shape_match = (not truth_shape) or predicted.get("predicted_shape") == truth_shape
    if process_match and shape_match:
        return "MATCH"
    if process_match:
        return "PROCESS_MATCH"
    return "DIFF"
