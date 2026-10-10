from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from ..rules import as_float, as_int, norm_spec, text


def load_truth_rows(truth_root: Path, member_id: str) -> list[dict[str, Any]]:
    xls = truth_root / "T3楼五节柱零构件清单(1).xls"
    df = pd.read_excel(xls, sheet_name="Θ零件清单Θ", header=None, dtype=object)
    rows = []
    for _, row in df.iterrows():
        if text(row.iloc[0]) != member_id:
            continue
        rows.append(
            {
                "构件名称": text(row.iloc[0]),
                "零件名称": text(row.iloc[1]),
                "规格": norm_spec(row.iloc[2]),
                "长度": as_int(row.iloc[3]),
                "数量": as_int(row.iloc[4]),
                "单重": as_float(row.iloc[5]),
                "总重": as_float(row.iloc[6]),
                "材质": text(row.iloc[7]),
                "备注": text(row.iloc[8]),
                "工序": text(row.iloc[9]),
                "形状分类": text(row.iloc[10]),
                "配送责任": text(row.iloc[11]),
                "配送线": text(row.iloc[12]),
                "配送用途": text(row.iloc[13]),
                "单面积": as_float(row.iloc[14]),
                "总面积": as_float(row.iloc[15]),
                "单数": as_int(row.iloc[21]),
            }
        )
    return rows


def load_member_snapshots(root: Path) -> dict[str, dict[str, Any]]:
    """Index the complete batch by physical assembly, never by position number."""
    path = root / "members" / "batch_summary.json"
    if not path.is_file():
        return {}
    batch = json.loads(path.read_text(encoding="utf-8"))
    members: dict[str, dict[str, Any]] = {}
    for member in batch.get("Members") or []:
        assembly_id = text((member.get("Member") or {}).get("AssemblyId"))
        if not assembly_id:
            continue
        if assembly_id in members:
            raise ValueError(f"batch_summary 中装配ID重复：{assembly_id}")
        members[assembly_id] = member
    return members


def load_member(
    root: Path,
    member_id: str,
    assembly_id: str | None = None,
    *,
    batch_members: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    expected_id = text(assembly_id)
    member = None
    if expected_id:
        snapshots = load_member_snapshots(root) if batch_members is None else batch_members
        member = snapshots.get(expected_id)
    if member is None:
        path = root / "members" / f"member_{member_id}.json"
        member = json.loads(path.read_text(encoding="utf-8"))
    identity = member.get("Member") or {}
    actual_id = text(identity.get("AssemblyId"))
    actual_position = text(identity.get("MemberId"))
    if expected_id and actual_id and actual_id != expected_id:
        raise ValueError(f"构件快照装配ID不一致：需要 {expected_id}，实际 {actual_id}；缺少该实例的 batch_summary 快照")
    if expected_id and actual_position and actual_position != member_id:
        raise ValueError(f"构件快照编号不一致：需要 {member_id}，实际 {actual_position}")
    return member


def load_member_assembly_id(root: Path, member_id: str) -> str:
    member = load_member(root, member_id)
    return text(member.get("Member", {}).get("AssemblyId"))


def load_bundle(
    root: Path, assembly_id: str
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, Counter[str]], dict[str, Any]]:
    bundle_path = root / "tekla-body-bracket-export.bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assembly = next(item for item in bundle["assemblies"] if text(item.get("assemblyId")) == text(assembly_id))
    rel_by_part: dict[str, Counter[str]] = defaultdict(Counter)
    for rel in assembly.get("relationships", []):
        edge_type = text(rel.get("edgeType"))
        part_a = text(rel.get("partIdA"))
        part_b = text(rel.get("partIdB"))
        for part_id in {part_a, part_b}:
            if part_id:
                rel_by_part[part_id][edge_type] += 1
    by_pos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for part in assembly.get("parts", []):
        by_pos[text(part.get("partPosition"))].append(part)
    return assembly, by_pos, rel_by_part, bundle


def load_roles(member: dict[str, Any]) -> dict[str, dict[str, Any]]:
    roles = {}
    for role in member.get("Classification", {}).get("PartRoles", []):
        roles[text(role.get("PartId"))] = role
    return roles
