from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..box_section import classify_box_section_evidence
from ..rules import as_float, text


class SegmentContinuityLevel(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    NEAR_CONTINUOUS = "NEAR_CONTINUOUS"
    GAPPED = "GAPPED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class BoxMainMaterialSegmentGroup:
    assembly_id: str
    group_type: str
    face_id: str
    part_ids: list[str]
    part_positions: list[str]
    station_ranges: str
    gap_summary: str
    continuity_level: SegmentContinuityLevel
    evidence_codes: list[str]
    confidence: float
    issue_category: str = ""
    evidence_summary: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "group_type": self.group_type,
            "face_id": self.face_id,
            "part_ids": list(self.part_ids),
            "part_positions": list(self.part_positions),
            "station_ranges": self.station_ranges,
            "gap_summary": self.gap_summary,
            "continuity_level": self.continuity_level.value,
            "evidence_codes": list(self.evidence_codes),
            "confidence": round(self.confidence, 3),
            "issue_category": self.issue_category,
            "evidence_summary": dict(self.evidence_summary),
        }


def classify_box_main_material_segment_groups(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
    confirmed_segment_positions: set[str] | None = None,
) -> list[BoxMainMaterialSegmentGroup]:
    assembly_id = text(assembly.get("assemblyId"))
    parts = list(assembly.get("parts", []))
    missing_evidence_count = sum(1 for part in parts if "mainMaterialEvidence" not in part)
    candidate_parts = sorted(
        [_with_member_axis_projection(part, member) for part in parts if _is_candidate_part(part)],
        key=lambda part: (_station_start(part), _station_end(part), text(part.get("partPosition")), text(part.get("partId"))),
    )
    relationship_edges = _relationship_edges(assembly)
    box_section_evidence = classify_box_section_evidence(assembly)
    section_groups = _section_sample_groups(assembly_id, candidate_parts, relationship_edges, member)
    if section_groups:
        expanded_group = _expanded_wall_trace_group(
            assembly_id,
            candidate_parts,
            relationship_edges,
            section_groups,
            member,
            confirmed_segment_positions or set(),
        )
        groups = [expanded_group] if expanded_group is not None else section_groups
    else:
        components = _face_station_components(candidate_parts, relationship_edges)
        groups = [
            _group_from_parts(assembly_id, component, relationship_edges, missing_evidence_count, box_section_evidence)
            for component in components
        ]

    if not groups and missing_evidence_count:
        groups.append(_insufficient_evidence_group(assembly_id, missing_evidence_count))
    elif groups and missing_evidence_count:
        groups[0] = _with_missing_evidence(groups[0], missing_evidence_count)

    return groups


def _is_candidate_part(part: dict[str, Any]) -> bool:
    evidence = part.get("mainMaterialEvidence")
    return isinstance(evidence, dict) and evidence.get("isBodyWallPlateCandidate") is True and text(evidence.get("bodyFaceId"))


def _relationship_edges(assembly: dict[str, Any]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for rel in assembly.get("relationships", []):
        edge_type = text(rel.get("edgeType")).lower()
        if edge_type not in {"weld", "contact"}:
            continue
        part_a = text(rel.get("partIdA"))
        part_b = text(rel.get("partIdB"))
        if not part_a or not part_b or part_a == part_b:
            continue
        edges.add(tuple(sorted((part_a, part_b))))
    return edges




def _with_member_axis_projection(part: dict[str, Any], member: dict[str, Any] | None) -> dict[str, Any]:
    projection = _member_axis_projection(member, text(part.get("partId")))
    if not projection:
        return part
    updated = dict(part)
    evidence = dict(updated.get("mainMaterialEvidence", {}))
    start = as_float(projection.get("Start"))
    end = as_float(projection.get("End"))
    evidence["axisStationStart"] = start
    evidence["axisStationEnd"] = end
    evidence["axisStationLength"] = max(0.0, end - start)
    evidence["axisStationSource"] = "member.AxisProjection"
    updated["mainMaterialEvidence"] = evidence
    return updated


def _member_axis_projection(member: dict[str, Any] | None, part_id: str) -> dict[str, Any] | None:
    if not member or not part_id:
        return None
    for part in member.get("Parts", []):
        if text(part.get("PartId")) == part_id:
            projection = part.get("AxisProjection", {})
            return projection if isinstance(projection, dict) else None
    return None



def _expanded_wall_trace_group(
    assembly_id: str,
    candidate_parts: list[dict[str, Any]],
    relationship_edges: set[tuple[str, str]],
    section_groups: list[BoxMainMaterialSegmentGroup],
    member: dict[str, Any] | None,
    confirmed_segment_positions: set[str],
) -> BoxMainMaterialSegmentGroup | None:
    seed_ids = {part_id for group in section_groups for part_id in group.part_ids}
    if not seed_ids:
        return None
    by_id = {text(part.get("partId")): part for part in candidate_parts}
    accepted_ids = {part_id for part_id in seed_ids if part_id in by_id}
    changed = True
    while changed:
        changed = False
        accepted_parts = [by_id[part_id] for part_id in accepted_ids]
        for part in candidate_parts:
            part_id = text(part.get("partId"))
            if not part_id or part_id in accepted_ids:
                continue
            if not _is_unsampled_body_wall_candidate(part, member, confirmed_segment_positions):
                continue
            if _touches_axis_trace(part, accepted_parts) or text(part.get("partPosition")) in confirmed_segment_positions:
                accepted_ids.add(part_id)
                changed = True
    parts = sorted(
        [by_id[part_id] for part_id in accepted_ids],
        key=lambda part: (_station_start(part), _station_end(part), text(part.get("partPosition")), text(part.get("partId"))),
    )
    if not parts:
        return None
    base = _group_from_parts(assembly_id, parts, relationship_edges, 0)
    evidence_summary = dict(base.evidence_summary)
    evidence_summary["trace_seed_part_ids"] = ";".join(sorted(seed_ids))
    evidence_summary["trace_seed_part_positions"] = ";".join(_unique_values(part.get("partPosition") for part in parts if text(part.get("partId")) in seed_ids))
    evidence_summary["confirmed_segment_positions_used"] = ";".join(sorted(confirmed_segment_positions))
    evidence_summary["axis_trace_union_gaps"] = _axis_union_gap_summary(parts)
    evidence_codes = [
        "BOX_WALL_TRACE_SEED",
        "BOX_OUTER_WALL_TRACE_CONFIRMED",
        "AXIS_CONTINUITY_EXPANDED",
        "SECTION_VALIDATED",
        "MEMBER_AXIS_PROJECTION",
        "THICKNESS_AUXILIARY_ONLY",
    ]
    if confirmed_segment_positions:
        evidence_codes.append("CASE_BANK_FEEDBACK_CONFIRMED_SET")
    return BoxMainMaterialSegmentGroup(
        assembly_id=assembly_id,
        group_type="BOX_MAIN_WALL_CONFIRMED_SET",
        face_id="BOX_MAIN_WALL_CONFIRMED",
        part_ids=base.part_ids,
        part_positions=base.part_positions,
        station_ranges=base.station_ranges,
        gap_summary=evidence_summary["axis_trace_union_gaps"],
        continuity_level=_axis_trace_continuity(parts),
        evidence_codes=_dedupe(evidence_codes),
        confidence=0.92,
        issue_category="",
        evidence_summary=evidence_summary,
    )


def _touches_axis_trace(part: dict[str, Any], accepted_parts: list[dict[str, Any]]) -> bool:
    return any(_axis_intervals_touch(part, accepted) for accepted in accepted_parts)


def _axis_intervals_touch(left: dict[str, Any], right: dict[str, Any], max_gap: float = 200.0) -> bool:
    gap = max(_station_start(left), _station_start(right)) - min(_station_end(left), _station_end(right))
    return gap <= max_gap


def _axis_trace_continuity(parts: list[dict[str, Any]]) -> SegmentContinuityLevel:
    gaps = _axis_union_gaps(parts)
    if not gaps:
        return SegmentContinuityLevel.CONTINUOUS
    max_gap = max(abs(gap) for gap in gaps)
    if max_gap <= 10.0:
        return SegmentContinuityLevel.CONTINUOUS
    if max_gap <= 200.0:
        return SegmentContinuityLevel.NEAR_CONTINUOUS
    return SegmentContinuityLevel.GAPPED


def _axis_union_gap_summary(parts: list[dict[str, Any]]) -> str:
    return ";".join(f"{gap:.1f}" for gap in _axis_union_gaps(parts))


def _axis_union_gaps(parts: list[dict[str, Any]]) -> list[float]:
    intervals = sorted((_station_start(part), _station_end(part)) for part in parts)
    if not intervals:
        return []
    merged = [intervals[0]]
    gaps = []
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
            continue
        gaps.append(start - last_end)
        merged.append((start, end))
    return gaps
def _unsampled_section_fallback_groups(
    assembly_id: str,
    candidate_parts: list[dict[str, Any]],
    relationship_edges: set[tuple[str, str]],
    section_groups: list[BoxMainMaterialSegmentGroup],
    member: dict[str, Any] | None,
    confirmed_segment_positions: set[str],
) -> list[BoxMainMaterialSegmentGroup]:
    sampled_ids = {part_id for group in section_groups for part_id in group.part_ids}
    fallback_parts = [
        part
        for part in candidate_parts
        if text(part.get("partId")) not in sampled_ids
        and text(part.get("mainMaterialEvidence", {}).get("axisStationSource")) == "member.AxisProjection"
        and _is_unsampled_body_wall_candidate(part, member, confirmed_segment_positions)
    ]
    groups = []
    for part in fallback_parts:
        group = _group_from_parts(assembly_id, [part], relationship_edges, 0)
        evidence_codes = [
            code
            for code in group.evidence_codes
            if code not in {"BODY_FACE_BUCKET_AUXILIARY", "SAME_BODY_FACE_BUCKET"}
        ]
        evidence_codes.extend(["SECTION_SAMPLE_NOT_COVERED", "MEMBER_AXIS_PROJECTION", "THICKNESS_AUXILIARY_ONLY"])
        evidence_summary = dict(group.evidence_summary)
        evidence_summary["section_role_hint"] = "unsampled_candidate"
        groups.append(
            BoxMainMaterialSegmentGroup(
                assembly_id=group.assembly_id,
                group_type=group.group_type,
                face_id="SECTION_UNSAMPLED_CANDIDATE",
                part_ids=group.part_ids,
                part_positions=group.part_positions,
                station_ranges=group.station_ranges,
                gap_summary=group.gap_summary,
                continuity_level=SegmentContinuityLevel.INSUFFICIENT_EVIDENCE,
                evidence_codes=_dedupe(evidence_codes),
                confidence=min(group.confidence, 0.35),
                issue_category="FEATURE",
                evidence_summary=evidence_summary,
            )
        )
    return groups

def _is_unsampled_body_wall_candidate(
    part: dict[str, Any],
    member: dict[str, Any] | None,
    confirmed_segment_positions: set[str],
) -> bool:
    if text(part.get("partPosition")) in confirmed_segment_positions:
        return True
    part_id = text(part.get("partId"))
    member_role = _member_part_role(member, part_id)
    if member_role == "wall_candidate":
        return True
    name = text(part.get("name")).upper()
    if name == "COLUMN":
        return True
    return False


def _member_part_role(member: dict[str, Any] | None, part_id: str) -> str:
    if not member or not part_id:
        return ""
    for role in member.get("Classification", {}).get("PartRoles", []):
        if text(role.get("PartId")) == part_id:
            return text(role.get("Role"))
    return ""
def _section_sample_groups(
    assembly_id: str,
    candidate_parts: list[dict[str, Any]],
    relationship_edges: set[tuple[str, str]],
    member: dict[str, Any] | None,
) -> list[BoxMainMaterialSegmentGroup]:
    if not member:
        return []
    sample_roles = _section_sample_role_index(member)
    if not sample_roles:
        return []
    parts_by_id = {text(part.get("partId")): part for part in candidate_parts}
    groups: list[BoxMainMaterialSegmentGroup] = []
    for role in ["flange_candidate", "web_candidate"]:
        role_part_ids = [part_id for part_id, roles in sample_roles.items() if role in roles]
        role_parts = [parts_by_id[part_id] for part_id in role_part_ids if part_id in parts_by_id]
        role_parts = sorted(
            role_parts,
            key=lambda part: (_station_start(part), _station_end(part), text(part.get("partPosition")), text(part.get("partId"))),
        )
        if not role_parts:
            continue
        group = _group_from_parts(assembly_id, role_parts, relationship_edges, 0)
        evidence_codes = [
            code
            for code in group.evidence_codes
            if code not in {"BODY_FACE_BUCKET_AUXILIARY", "SAME_BODY_FACE_BUCKET"}
        ]
        evidence_codes.extend([
            "SECTION_SAMPLE_CLOSED_LOOP",
            "BOX_OUTER_WALL_TRACE_CONFIRMED",
            f"SECTION_ROLE_HINT_{role.upper()}",
            "SECTION_SAMPLES_OVERRIDE_RADIAL_BUCKET",
            "THICKNESS_AUXILIARY_ONLY",
        ])
        evidence_summary = dict(group.evidence_summary)
        evidence_summary["section_role_hint"] = role
        evidence_summary["section_sample_ids"] = ";".join(_section_sample_ids_for_role(member, role))
        evidence_summary["section_closed_loop_samples"] = str(len(_valid_section_samples(member)))
        groups.append(
            BoxMainMaterialSegmentGroup(
                assembly_id=group.assembly_id,
                group_type=group.group_type,
                face_id=f"SECTION_{role.upper()}",
                part_ids=group.part_ids,
                part_positions=group.part_positions,
                station_ranges=group.station_ranges,
                gap_summary=group.gap_summary,
                continuity_level=_role_continuity(role_parts),
                evidence_codes=_dedupe(evidence_codes),
                confidence=max(group.confidence, _role_confidence(role_parts)),
                issue_category="",
                evidence_summary=evidence_summary,
            )
        )
    return groups


def _section_sample_role_index(member: dict[str, Any]) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {}
    for sample in _valid_section_samples(member):
        for section_part in sample.get("SectionParts", []):
            role = text(section_part.get("RoleHint"))
            if role not in {"flange_candidate", "web_candidate"}:
                continue
            if not _is_outer_wall_trace_part(sample, section_part, role):
                continue
            part_id = text(section_part.get("PartId"))
            if not part_id:
                continue
            roles.setdefault(part_id, set()).add(role)
    return roles



def _is_outer_wall_trace_part(sample: dict[str, Any], section_part: dict[str, Any], role: str) -> bool:
    cut_length = as_float(section_part.get("TotalCutLength"))
    if cut_length <= 0:
        return True
    features = sample.get("SectionFeatures", {})
    reference = as_float(features.get("OuterWidth" if role == "flange_candidate" else "OuterHeight"))
    if reference <= 0:
        return True
    return (cut_length / reference) >= 0.65
def _valid_section_samples(member: dict[str, Any]) -> list[dict[str, Any]]:
    samples = member.get("Samples", [])
    valid = []
    for sample in samples:
        features = sample.get("SectionFeatures", {})
        if sample.get("IsAbnormal") is True:
            continue
        if as_float(features.get("ClosedLoops")) < 1 or as_float(features.get("CavityCount")) < 1:
            continue
        valid.append(sample)
    return valid


def _section_sample_ids_for_role(member: dict[str, Any], role: str) -> list[str]:
    sample_ids = []
    for sample in _valid_section_samples(member):
        if any(text(part.get("RoleHint")) == role for part in sample.get("SectionParts", [])):
            sample_id = text(sample.get("SampleId"))
            if sample_id and sample_id not in sample_ids:
                sample_ids.append(sample_id)
    return sample_ids


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
def _face_station_components(
    parts: list[dict[str, Any]],
    relationship_edges: set[tuple[str, str]],
) -> list[list[dict[str, Any]]]:
    components: list[list[dict[str, Any]]] = []
    by_face: dict[str, list[dict[str, Any]]] = {}
    for part in parts:
        face_id = text(part.get("mainMaterialEvidence", {}).get("bodyFaceId"))
        by_face.setdefault(face_id, []).append(part)

    for face_id in sorted(by_face):
        face_parts = sorted(
            by_face[face_id],
            key=lambda part: (_station_start(part), _station_end(part), text(part.get("partPosition")), text(part.get("partId"))),
        )
        if not face_parts:
            continue
        current = [face_parts[0]]
        for part in face_parts[1:]:
            previous = current[-1]
            if _station_related(previous, part) and _has_relationship(previous, part, relationship_edges):
                current.append(part)
            else:
                components.append(current)
                current = [part]
        components.append(current)
    return components

def _group_from_parts(
    assembly_id: str,
    parts: list[dict[str, Any]],
    relationship_edges: set[tuple[str, str]],
    missing_evidence_count: int,
    box_section_evidence: dict[str, Any] | None = None,
) -> BoxMainMaterialSegmentGroup:
    ranges = [(_station_start(part), _station_end(part), part) for part in parts]
    station_ranges = ";".join(
        f"{text(part.get('partPosition'))}:{start:.1f}-{end:.1f}" for start, end, part in ranges
    )
    gaps = [ranges[index][0] - ranges[index - 1][1] for index in range(1, len(ranges))]
    gap_summary = ";".join(f"{gap:.1f}" for gap in gaps)
    topology_ok = _has_relationship_chain(parts, relationship_edges)
    level = _continuity_level(gaps, topology_ok)
    faces = _unique_values(part.get("mainMaterialEvidence", {}).get("bodyFaceId") for part in parts)
    evidence_codes = [
        "AXIS_STATION_ORDER",
        "RELATIONSHIP_TOPOLOGY_CHAIN" if topology_ok else "RELATIONSHIP_TOPOLOGY_GAP",
        "BODY_FACE_BUCKET_AUXILIARY",
        "THICKNESS_AUXILIARY_ONLY",
    ]
    if len(faces) == 1:
        evidence_codes.append("SAME_BODY_FACE_BUCKET")
    if level == SegmentContinuityLevel.GAPPED:
        evidence_codes.append("STATION_GAP_EXCEEDS_LIMIT")
    if missing_evidence_count:
        evidence_codes.append("MISSING_MAIN_MATERIAL_EVIDENCE")

    return BoxMainMaterialSegmentGroup(
        assembly_id=assembly_id,
        group_type="BOX_MAIN_MATERIAL_SEGMENT_GROUP",
        face_id=";".join(faces),
        part_ids=[text(part.get("partId")) for part in parts],
        part_positions=[text(part.get("partPosition")) for part in parts],
        station_ranges=station_ranges,
        gap_summary=gap_summary,
        continuity_level=level,
        evidence_codes=evidence_codes,
        confidence=_confidence(level, topology_ok, missing_evidence_count),
        issue_category="FEATURE" if missing_evidence_count or level == SegmentContinuityLevel.INSUFFICIENT_EVIDENCE else "",
        evidence_summary={
            "thicknesses": ";".join(_unique_values(part.get("thickness") for part in parts)),
            "profiles": ";".join(_unique_values(part.get("profileString") for part in parts)),
            "body_face_ids": ";".join(faces),
            "box_section_sides": ";".join(_box_section_sides(parts, box_section_evidence or {})),
            "evidence_sources": ";".join(
                _unique_values(part.get("mainMaterialEvidence", {}).get("evidenceSource") for part in parts)
            ),
        },
    )



def classify_main_material_segment_groups(
    assembly: dict[str, Any],
    member: dict[str, Any] | None = None,
    confirmed_segment_positions: set[str] | None = None,
) -> list[BoxMainMaterialSegmentGroup]:
    family = _infer_profile_family(assembly)
    if family in {"H", "GL", "BEAM"}:
        return _classify_h_or_gl_main_material_groups(assembly, family)
    return _with_role_summary(
        classify_box_main_material_segment_groups(assembly, member, confirmed_segment_positions or set()),
        "BOX_WALL_FACE",
        ["PROFILE_FAMILY_BOX_OR_FALLBACK"],
    )


def _infer_profile_family(assembly: dict[str, Any]) -> str:
    assembly_position = text(assembly.get("metadata", {}).get("assemblyPosition") or assembly.get("assemblyPosition")).upper()
    names = [text(part.get("name")) for part in assembly.get("parts", [])]
    if "GL" in assembly_position or any(name in {"上翼缘", "下翼缘", "腹板"} for name in names):
        return "GL"
    if any("翼缘" in name or "腹板" in name for name in names):
        return "H"
    if "GKZ" in assembly_position or "BOX" in assembly_position:
        return "BOX"
    return "UNKNOWN"


def _classify_h_or_gl_main_material_groups(assembly: dict[str, Any], family: str) -> list[BoxMainMaterialSegmentGroup]:
    assembly_id = text(assembly.get("assemblyId"))
    relationship_edges = _relationship_edges(assembly)
    role_parts: dict[str, list[dict[str, Any]]] = {"TOP_FLANGE": [], "WEB": [], "BOTTOM_FLANGE": []}
    for part in assembly.get("parts", []):
        role = _h_or_gl_part_role(part)
        if not role:
            continue
        role_parts[role].append(part)

    groups: list[BoxMainMaterialSegmentGroup] = []
    for role in ["TOP_FLANGE", "WEB", "BOTTOM_FLANGE"]:
        parts = sorted(role_parts[role], key=lambda item: (_station_start(item), _station_end(item), text(item.get("partPosition"))))
        if not parts:
            continue
        group = _group_from_parts(assembly_id, parts, relationship_edges, 0)
        evidence_summary = dict(group.evidence_summary)
        evidence_summary["main_material_role"] = role
        evidence_summary["profile_family"] = family
        evidence_codes = list(group.evidence_codes)
        evidence_codes.append("PROFILE_FAMILY_H_OR_GL")
        evidence_codes.append(f"ROLE_{role}")
        groups.append(
            BoxMainMaterialSegmentGroup(
                assembly_id=group.assembly_id,
                group_type="MAIN_MATERIAL_SEGMENT_GROUP",
                face_id=group.face_id,
                part_ids=group.part_ids,
                part_positions=group.part_positions,
                station_ranges=group.station_ranges,
                gap_summary=group.gap_summary,
                continuity_level=_role_continuity(parts),
                evidence_codes=evidence_codes,
                confidence=_role_confidence(parts),
                issue_category="" if len(parts) >= 1 else "FEATURE",
                evidence_summary=evidence_summary,
            )
        )
    return groups


def _h_or_gl_part_role(part: dict[str, Any]) -> str:
    name = text(part.get("name"))
    if "上翼缘" in name:
        return "TOP_FLANGE"
    if "下翼缘" in name:
        return "BOTTOM_FLANGE"
    if "腹板" in name:
        return "WEB"
    return ""


def _role_continuity(parts: list[dict[str, Any]]) -> SegmentContinuityLevel:
    if len(parts) == 1:
        return SegmentContinuityLevel.CONTINUOUS
    gaps = [_station_start(parts[index]) - _station_end(parts[index - 1]) for index in range(1, len(parts))]
    max_gap = max(abs(gap) for gap in gaps)
    if max_gap <= 10.0:
        return SegmentContinuityLevel.CONTINUOUS
    if max_gap <= 150.0:
        return SegmentContinuityLevel.NEAR_CONTINUOUS
    return SegmentContinuityLevel.GAPPED


def _role_confidence(parts: list[dict[str, Any]]) -> float:
    level = _role_continuity(parts)
    if level == SegmentContinuityLevel.CONTINUOUS:
        return 0.96
    if level == SegmentContinuityLevel.NEAR_CONTINUOUS:
        return 0.84
    return 0.45


def _with_role_summary(groups: list[BoxMainMaterialSegmentGroup], role: str, extra_evidence: list[str]) -> list[BoxMainMaterialSegmentGroup]:
    updated: list[BoxMainMaterialSegmentGroup] = []
    for group in groups:
        evidence_summary = dict(group.evidence_summary)
        evidence_summary["main_material_role"] = role
        evidence_codes = list(group.evidence_codes) + list(extra_evidence)
        updated.append(
            BoxMainMaterialSegmentGroup(
                assembly_id=group.assembly_id,
                group_type=group.group_type,
                face_id=group.face_id,
                part_ids=group.part_ids,
                part_positions=group.part_positions,
                station_ranges=group.station_ranges,
                gap_summary=group.gap_summary,
                continuity_level=group.continuity_level,
                evidence_codes=evidence_codes,
                confidence=group.confidence,
                issue_category=group.issue_category,
                evidence_summary=evidence_summary,
            )
        )
    return updated


def _box_section_sides(parts: list[dict[str, Any]], evidence: dict[str, Any]) -> list[str]:
    sides = []
    for part in parts:
        item = evidence.get(text(part.get("partId")))
        side = text(getattr(item, "side", ""))
        if side and side not in sides:
            sides.append(side)
    return sides

def _insufficient_evidence_group(assembly_id: str, missing_evidence_count: int) -> BoxMainMaterialSegmentGroup:
    return BoxMainMaterialSegmentGroup(
        assembly_id=assembly_id,
        group_type="BOX_MAIN_MATERIAL_SEGMENT_GROUP",
        face_id="",
        part_ids=[],
        part_positions=[],
        station_ranges="",
        gap_summary="",
        continuity_level=SegmentContinuityLevel.INSUFFICIENT_EVIDENCE,
        evidence_codes=["MISSING_MAIN_MATERIAL_EVIDENCE"],
        confidence=0.0,
        issue_category="FEATURE",
        evidence_summary={"missing_main_material_evidence_count": str(missing_evidence_count)},
    )


def _with_missing_evidence(
    group: BoxMainMaterialSegmentGroup,
    missing_evidence_count: int,
) -> BoxMainMaterialSegmentGroup:
    evidence_summary = dict(group.evidence_summary)
    evidence_summary["missing_main_material_evidence_count"] = str(missing_evidence_count)
    evidence_codes = list(group.evidence_codes)
    if "MISSING_MAIN_MATERIAL_EVIDENCE" not in evidence_codes:
        evidence_codes.append("MISSING_MAIN_MATERIAL_EVIDENCE")
    return BoxMainMaterialSegmentGroup(
        assembly_id=group.assembly_id,
        group_type=group.group_type,
        face_id=group.face_id,
        part_ids=group.part_ids,
        part_positions=group.part_positions,
        station_ranges=group.station_ranges,
        gap_summary=group.gap_summary,
        continuity_level=SegmentContinuityLevel.INSUFFICIENT_EVIDENCE,
        evidence_codes=evidence_codes,
        confidence=min(group.confidence, 0.4),
        issue_category="FEATURE",
        evidence_summary=evidence_summary,
    )


def _station_start(part: dict[str, Any]) -> float:
    return as_float(part.get("mainMaterialEvidence", {}).get("axisStationStart"))


def _station_end(part: dict[str, Any]) -> float:
    return as_float(part.get("mainMaterialEvidence", {}).get("axisStationEnd"))


def _has_relationship(left: dict[str, Any], right: dict[str, Any], edges: set[tuple[str, str]]) -> bool:
    return tuple(sorted((text(left.get("partId")), text(right.get("partId"))))) in edges


def _station_related(left: dict[str, Any], right: dict[str, Any]) -> bool:
    start_gap = max(_station_start(left), _station_start(right)) - min(_station_end(left), _station_end(right))
    if start_gap > 150.0:
        return False
    overlap = min(_station_end(left), _station_end(right)) - max(_station_start(left), _station_start(right))
    if overlap > 150.0:
        return False
    return True


def _has_relationship_chain(parts: list[dict[str, Any]], edges: set[tuple[str, str]]) -> bool:
    if len(parts) < 2:
        return False
    for index in range(1, len(parts)):
        if not _has_relationship(parts[index - 1], parts[index], edges):
            return False
    return True


def _continuity_level(gaps: list[float], topology_ok: bool) -> SegmentContinuityLevel:
    if not gaps or not topology_ok:
        return SegmentContinuityLevel.INSUFFICIENT_EVIDENCE
    max_gap = max(abs(gap) for gap in gaps)
    if max_gap <= 10.0:
        return SegmentContinuityLevel.CONTINUOUS
    if max_gap <= 150.0:
        return SegmentContinuityLevel.NEAR_CONTINUOUS
    return SegmentContinuityLevel.GAPPED


def _confidence(level: SegmentContinuityLevel, topology_ok: bool, missing_evidence_count: int) -> float:
    if missing_evidence_count:
        return 0.4
    if level == SegmentContinuityLevel.CONTINUOUS:
        return 0.96 if topology_ok else 0.5
    if level == SegmentContinuityLevel.NEAR_CONTINUOUS:
        return 0.84 if topology_ok else 0.45
    if level == SegmentContinuityLevel.GAPPED:
        return 0.45
    return 0.0


def _unique_values(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        item = text(value)
        if item and item not in result:
            result.append(item)
    return result
























