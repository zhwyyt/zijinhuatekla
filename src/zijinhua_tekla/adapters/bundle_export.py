"""Contract dataclass -> bundle JSON 反向导出(供后续 MCP)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..contracts.assembly import AssemblyRecord


def assembly_to_dict(assembly: AssemblyRecord) -> dict[str, Any]:
    return {
        "assemblyId": assembly.assembly_id,
        "memberId": assembly.member_id,
        "mainPartId": assembly.main_part_id,
        "partIds": list(assembly.part_ids),
        "relationships": [
            {
                "partIdA": r.part_id_a,
                "partIdB": r.part_id_b,
                "edgeType": r.edge_type.value,
                "evidence": list(r.evidence),
            }
            for r in assembly.relationships
        ],
    }


def export_bundle_json(
    assemblies: list[AssemblyRecord],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "assemblies": [assembly_to_dict(a) for a in assemblies],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )