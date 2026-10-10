"""Consume part identities in local core sections, independent of whole-axis length."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..rules import as_float, text


CORE_ROLES = {"wall_candidate", "flange_candidate", "web_candidate"}
H_SLOTS = {
    "topFlangePartId": "H_TOP_FLANGE_MAIN_PLATE",
    "webPartId": "H_WEB_MAIN_PLATE",
    "bottomFlangePartId": "H_BOTTOM_FLANGE_MAIN_PLATE",
}


def section_core_part_ids(sample: dict[str, Any]) -> set[str]:
    return {
        text(part.get("PartId")) for part in sample.get("SectionParts") or []
        if text(part.get("RoleHint")).lower() in CORE_ROLES and text(part.get("PartId"))
    }


def local_box_wall_ids(assembly: dict[str, Any], member: dict[str, Any] | None) -> set[str]:
    parts = {text(part.get("partId")): part for part in assembly.get("parts") or []}
    main_id = text(assembly.get("mainPartId"))
    if not main_id or parts.get(main_id, {}).get("isPlateLike") is False:
        return set()
    wall_ids: set[str] = set()
    for sample in (member or {}).get("Samples") or []:
        if sample.get("IsAbnormal") and sample.get("AbnormalReason") != "dense_attachment_zone":
            continue
        features = sample.get("SectionFeatures") or {}
        if as_float(features.get("ClosedLoops")) <= 0 or as_float(features.get("CavityCount")) <= 0:
            continue
        core_ids = section_core_part_ids(sample)
        if len(core_ids) < 2 or not core_ids <= parts.keys():
            continue
        if any(parts[pid].get("isPlateLike") is False for pid in core_ids):
            continue
        wall_ids.update(core_ids)
    return wall_ids if main_id in wall_ids else set()


def local_h_plate_roles(assembly: dict[str, Any]) -> dict[str, str]:
    """A complete, repeated three-plate frame proves local H membership.

    Duplicate observations at one station are not longitudinal evidence. Conflicting
    slot identities at that station are excluded instead of choosing a winner.
    """
    parts = {text(part.get("partId")): part for part in assembly.get("parts") or []}
    main_id = text(assembly.get("mainPartId"))
    if main_id and parts.get(main_id, {}).get("isPlateLike") is False:
        return {}
    frames = (assembly.get("metadata", {}).get("hBeamSectionEvidence") or {}).get("stationFrames") or []
    by_station: dict[float, set[tuple[str, ...]]] = defaultdict(set)
    for frame in frames:
        ids = tuple(text(frame.get(slot)) for slot in H_SLOTS)
        if len(set(ids)) != 3 or not all(ids) or not set(ids) <= parts.keys():
            continue
        if any(parts[pid].get("isPlateLike") is False for pid in ids):
            continue
        slices = {text(item.get("partId")): item for item in frame.get("partSlices") or []}
        if not all(_has_section_polygon(slices.get(pid, {})) for pid in ids):
            continue
        expected_hints = ("flange_candidate", "web_candidate", "flange_candidate")
        if any(text(slices[pid].get("roleHint")) not in {"", hint}
               for pid, hint in zip(ids, expected_hints)):
            continue
        by_station[as_float(frame.get("station"))].add(ids)
    observations: dict[str, dict[str, set[float]]] = defaultdict(lambda: defaultdict(set))
    for station, choices in by_station.items():
        if len(choices) != 1:
            continue
        for pid, role in zip(next(iter(choices)), H_SLOTS.values()):
            observations[pid][role].add(station)
    roles = {
        pid: next(iter(votes)) for pid, votes in observations.items()
        if len(votes) == 1 and len(next(iter(votes.values()))) >= 2
    }
    complete = [next(iter(choices)) for choices in by_station.values()
                if len(choices) == 1 and all(pid in roles for pid in next(iter(choices)))]
    proven_ids = {pid for ids in complete for pid in ids}
    roles = {pid: role for pid, role in roles.items() if pid in proven_ids}
    if main_id and main_id not in roles:
        return {}
    if main_id:
        neighbors: dict[str, set[str]] = defaultdict(set)
        for ids in complete:
            for pid in ids:
                neighbors[pid].update(ids)
        for relation in assembly.get("relationships") or []:
            left, right = text(relation.get("partIdA")), text(relation.get("partIdB"))
            if left in roles and right in roles and text(relation.get("edgeType")).lower() in {"weld", "contact"}:
                neighbors[left].add(right)
                neighbors[right].add(left)
        connected = {main_id}
        pending = [main_id]
        while pending:
            for pid in neighbors[pending.pop()] - connected:
                connected.add(pid)
                pending.append(pid)
        roles = {pid: role for pid, role in roles.items() if pid in connected}
    return roles


def _has_section_polygon(part_slice: dict[str, Any]) -> bool:
    for loop in part_slice.get("sectionLoops") or []:
        if loop.get("isClosed") is False or loop.get("isValid") is False:
            continue
        if len(loop.get("points") or []) >= 3:
            return True
    return False
