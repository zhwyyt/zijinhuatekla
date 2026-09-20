"""Weld backing plates from strip geometry, welds, and host bevels. Not from names."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from ..geom.shop import is_section_profile
from ..rules import as_float, as_int, parse_pl, text

_MAX_STRIP_WIDTH = 45.0
_MAX_STRIP_THICKNESS = 25.0
_MIN_ASPECT = 4.0
_MIN_HOST_WIDTH = 80.0
_HOST_WIDTH_RATIO = 3.0


def classify_weld_backing_plates(assembly: Mapping[str, Any] | None) -> dict[str, tuple[str, ...]]:
    parts = {
        text(part.get("partId")): part
        for part in (assembly or {}).get("parts") or []
        if text(part.get("partId"))
    }
    welds, contacts, weld_geom = _adjacency(assembly or {})
    hits: dict[str, tuple[str, ...]] = {}
    for part_id, part in parts.items():
        evidence = _backing_evidence(
            part_id,
            part,
            parts,
            welds.get(part_id, ()),
            contacts.get(part_id, ()),
            weld_geom,
        )
        if evidence:
            hits[part_id] = evidence
    return hits


def _backing_evidence(
    part_id: str,
    part: Mapping[str, Any],
    parts: Mapping[str, Mapping[str, Any]],
    weld_ids: tuple[str, ...],
    contact_ids: tuple[str, ...],
    weld_geom: Mapping[frozenset[str], Mapping[str, Any]],
) -> tuple[str, ...]:
    if not _is_strip(part):
        return ()
    if as_int(part.get("boltHoleCount")) > 0:
        return ()
    weld_hosts = [host_id for host_id in weld_ids if _is_host(parts.get(host_id), _strip_width(part))]
    contact_hosts = [host_id for host_id in contact_ids if _is_host(parts.get(host_id), _strip_width(part))]
    if not weld_hosts and len(contact_hosts) < 2 and not any(_has_edge_bevel(parts.get(host_id)) for host_id in contact_hosts):
        return ()
    evidence = ["窄长垫板几何"]
    if weld_hosts:
        evidence.append("焊缝连到主板/型钢")
        evidence.extend(_weld_geometry_evidence(part_id, weld_hosts, weld_geom))
    if contact_hosts:
        evidence.append("与主板接触")
    if len(contact_hosts) >= 2 or len(set(weld_hosts + contact_hosts)) >= 2:
        evidence.append("贴在两块主板接缝")
    if any(_has_edge_bevel(parts.get(host_id)) for host_id in set(weld_hosts + contact_hosts)):
        evidence.append("主板有板边剖口")
    return tuple(dict.fromkeys(evidence))


def _weld_geometry_evidence(
    part_id: str,
    host_ids: list[str],
    weld_geom: Mapping[frozenset[str], Mapping[str, Any]],
) -> list[str]:
    evidence: list[str] = []
    for host_id in host_ids:
        info = weld_geom.get(frozenset({part_id, host_id})) or {}
        if info.get("around"):
            evidence.append("焊缝环绕接缝")
        if as_float(info.get("size_above")) > 0 or as_float(info.get("size_below")) > 0:
            evidence.append("角焊缝尺寸")
        if info.get("shop"):
            evidence.append("车间焊")
        if text(info.get("secondary")) == part_id:
            evidence.append("作为焊缝从件")
    return evidence


def _is_strip(part: Mapping[str, Any] | None) -> bool:
    if part is None:
        return False
    profile = text(part.get("profileString") or part.get("profile"))
    plate = bool(part.get("isPlateLike")) or profile.startswith("PL")
    if not plate:
        return False
    width = _strip_width(part)
    length = _strip_length(part)
    thickness = _thickness(part)
    if width <= 0 or length <= 0:
        return False
    if width > _MAX_STRIP_WIDTH or thickness > _MAX_STRIP_THICKNESS:
        return False
    return length >= width * _MIN_ASPECT


def _is_host(part: Mapping[str, Any] | None, strip_width: float) -> bool:
    if part is None or _is_strip(part):
        return False
    profile = text(part.get("profileString") or part.get("profile"))
    if is_section_profile(profile):
        return True
    width = _inplane_width(part)
    return width >= max(_MIN_HOST_WIDTH, strip_width * _HOST_WIDTH_RATIO)


def _has_edge_bevel(part: Mapping[str, Any] | None) -> bool:
    if part is None:
        return False
    return bool(part.get("hasEdgeBevel")) or as_int(part.get("edgeBevelCount")) > 0


def _strip_width(part: Mapping[str, Any]) -> float:
    parsed = parse_pl(text(part.get("profileString") or part.get("profile")))
    if parsed:
        return parsed[1]
    return _inplane_width(part)


def _inplane_width(part: Mapping[str, Any]) -> float:
    dims = _obb_dims(part)
    if len(dims) >= 2:
        return dims[-2]
    return as_float(part.get("width"))


def _strip_length(part: Mapping[str, Any]) -> float:
    dims = _obb_dims(part)
    if dims:
        return dims[-1]
    return as_float(part.get("length"))


def _thickness(part: Mapping[str, Any]) -> float:
    thickness = as_float(part.get("thickness"))
    if thickness > 0:
        return thickness
    parsed = parse_pl(text(part.get("profileString") or part.get("profile")))
    if parsed:
        return parsed[0]
    dims = _obb_dims(part)
    return dims[0] if dims else 0.0


def _obb_dims(part: Mapping[str, Any]) -> list[float]:
    obb = part.get("obbDims") or {}
    if isinstance(obb, Mapping):
        values = [abs(as_float(obb.get(key))) for key in ("x", "y", "z")]
    else:
        values = [abs(as_float(value)) for value in obb]
    return sorted(value for value in values if value > 0)


def _adjacency(
    assembly: Mapping[str, Any],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], dict[frozenset[str], dict[str, Any]]]:
    welds: dict[str, set[str]] = defaultdict(set)
    contacts: dict[str, set[str]] = defaultdict(set)
    weld_geom: dict[frozenset[str], dict[str, Any]] = {}
    for rel in assembly.get("relationships") or []:
        left = text(rel.get("partIdA"))
        right = text(rel.get("partIdB"))
        if not left or not right or left == right:
            continue
        edge = text(rel.get("edgeType"))
        if edge.lower() == "weld":
            welds[left].add(right)
            welds[right].add(left)
            weld_geom[frozenset({left, right})] = _merge_weld_info(
                weld_geom.get(frozenset({left, right})),
                _weld_info_from_relationship(rel),
            )
        elif edge.lower() == "contact":
            contacts[left].add(right)
            contacts[right].add(left)
    for part in assembly.get("parts") or []:
        for weld in part.get("weldDetails") or []:
            main_id = text(weld.get("mainPartId"))
            secondary_id = text(weld.get("secondaryPartId"))
            if not main_id or not secondary_id or main_id == secondary_id:
                continue
            welds[main_id].add(secondary_id)
            welds[secondary_id].add(main_id)
            info = {
                "around": bool(weld.get("aroundWeld")),
                "shop": bool(weld.get("shopWeld")),
                "size_above": as_float(weld.get("sizeAbove") or weld.get("size")),
                "size_below": as_float(weld.get("sizeBelow")),
                "weld_type": text(weld.get("weldType") or weld.get("type")),
                "main": main_id,
                "secondary": secondary_id,
            }
            weld_geom[frozenset({main_id, secondary_id})] = _merge_weld_info(
                weld_geom.get(frozenset({main_id, secondary_id})),
                info,
            )
    return (
        {key: tuple(sorted(value)) for key, value in welds.items()},
        {key: tuple(sorted(value)) for key, value in contacts.items()},
        weld_geom,
    )


def _weld_info_from_relationship(rel: Mapping[str, Any]) -> dict[str, Any]:
    info: dict[str, Any] = {
        "around": bool(rel.get("aroundWeld")),
        "shop": bool(rel.get("shopWeld")),
        "size_above": as_float(rel.get("sizeAbove") or rel.get("size")),
        "size_below": as_float(rel.get("sizeBelow")),
        "weld_type": text(rel.get("weldType")),
        "main": text(rel.get("mainPartId")),
        "secondary": text(rel.get("secondaryPartId")),
    }
    for token in text(rel.get("meta")).split("|"):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip().lower()
        token_value = value.strip()
        if key in {"shop", "shopweld"}:
            info["shop"] = token_value.lower() == "true"
        elif key in {"around", "aroundweld"}:
            info["around"] = token_value.lower() == "true"
        elif key in {"sizeabove", "size"}:
            info["size_above"] = as_float(token_value)
        elif key == "sizebelow":
            info["size_below"] = as_float(token_value)
    return info


def _merge_weld_info(existing: Mapping[str, Any] | None, incoming: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(existing or {})
    for key, value in incoming.items():
        if value in ("", None, 0, 0.0, False):
            continue
        merged[key] = value
    return merged
