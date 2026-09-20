"""Write model-origin recognition Excel. Does not read factory truth."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import pandas as pd

from ..pipeline.offline import OfflinePipelineResult
from ..rules import text


FACTORY_COLUMNS = ["构件名称", "零件名称", "规格", "长度", "数量", "材质", "工序", "形状分类"]
RECOGNITION_COLUMNS = FACTORY_COLUMNS + ["主材", "牛腿实体个数"]


@dataclass(frozen=True)
class RecognitionReportPaths:
    xlsx_path: Path
    json_path: Path


def write_recognition_workbook(result: OfflinePipelineResult, out_dir: Path, member_id: str) -> RecognitionReportPaths:
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_dir / f"{member_id}-recognition.xlsx"
    json_path = out_dir / f"{member_id}-recognition.json"
    rows = [{column: row.get(column, "") for column in RECOGNITION_COLUMNS} for row in result.recognition_rows]
    pd.DataFrame(rows, columns=RECOGNITION_COLUMNS).to_excel(xlsx_path, index=False, sheet_name="零件清单")
    sidecar = {
        "member_id": member_id,
        "assembly_id": text(result.assembly.get("assemblyId")),
        "source": "model-recognition.v1",
        "member_body_type": result.member_body_type,
        "main_material_segments": [segment.to_dict() for segment in result.composite_main_material_segments],
        "box_main_material_groups": [group.to_dict() for group in result.box_main_material_segment_groups],
        "corbel": {
            "unit_count": len(result.corbel_units),
            "units": [unit.to_dict() for unit in result.corbel_units],
            "candidate_clusters": [
                {
                    "cluster_id": getattr(item, "cluster_id", ""),
                    "role": getattr(item, "role", ""),
                    "confidence": getattr(item, "confidence", 0.0),
                    "part_ids": list(getattr(item, "part_ids", [])),
                }
                for item in result.spatial_classifications
                if text(getattr(item, "role", "")) == "Bracket"
            ],
        },
        "parts": result.recognition_rows,
        "box_part_spatial_relations": [item.to_dict() for item in result.box_part_spatial_relations],
        "h_beam_part_sides": [item.to_dict() for item in result.h_beam_part_sides],
    }
    json_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    return RecognitionReportPaths(xlsx_path=xlsx_path, json_path=json_path)
