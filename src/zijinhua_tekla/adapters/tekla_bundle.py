"""bundle.json -> contracts 做纯格式转换."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..contracts.assembly import AssemblyRecord, Relationship, RelationshipType
from ..contracts.part import PartRecord


def adapt_assembly(raw: dict[str, Any]) -> tuple[AssemblyRecord, list[PartRecord]]:
    assembly_id = str(raw.get("assemblyId", ""))
    parts = []
    relationships = []
    rel_map: dict[str, Counter[str]] = defaultdict(Counter)

    for p in raw.get("parts", []):
        parts.append(_adapt_part(p))

    for r in raw.get("relationships", []):
        a = str(r.get("partIdA", ""))
        b = str(r.get("partIdB", ""))
        et = r.get("edgeType", "Unknown")
        rel = Relationship(
            part_id_a=a,
            part_id_b=b,
            edge_type=_edge_type(et),
            evidence=[f"edgeType={et}"],
        )
        relationships.append(rel)
        if a:
            rel_map[a][et] += 1
        if b:
            rel_map[b][et] += 1

    main_id = str(raw.get("mainPartId", ""))
    if not main_id and parts:
        max_rel = max(rel_map.items(), key=lambda kv: sum(kv[1].values()), default=None)
        if max_rel:
            main_id = max_rel[0]

    rec = AssemblyRecord(
        assembly_id=assembly_id,
        main_part_id=main_id,
        part_ids=[p.part_id for p in parts],
        relationships=relationships,
    )
    return rec, parts


def _adapt_part(p: dict[str, Any]) -> PartRecord:
    thickness = _float(p.get("thickness"))
    length = _float(p.get("length"))
    width = _float(p.get("width"))
    name = str(p.get("partName", ""))
    profile = str(p.get("profile", ""))
    is_plate = thickness > 0 and ("PLATE" in name.upper() or "板" in name)

    return PartRecord(
        part_id=str(p.get("partId", "")),
        position=str(p.get("partPosition", "")),
        name=name,
        profile=profile,
        material=str(p.get("material", "")),
        runtime_type=str(p.get("runtimeType", "")),
        is_plate_like=is_plate,
        thickness=thickness,
        length=length,
        width=width,
        bolt_hole_count=int(p.get("boltHoleCount", 0)),
        boolean_cut_count=int(p.get("booleanCutCount", 0)),
        weld_count=int(p.get("weldCount", 0)),
    )


def _edge_type(raw: str) -> RelationshipType:
    mapping = {
        "Weld": RelationshipType.WELD,
        "Bolt": RelationshipType.BOLT,
        "Contact": RelationshipType.CONTACT,
        "Boolean": RelationshipType.BOOLEAN,
    }
    return mapping.get(raw, RelationshipType.UNKNOWN)


def _float(v: Any) -> float:
    try:
        return float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0