import math
import re
from collections import Counter, defaultdict


def text(value):
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def norm_spec(value):
    return text(value).replace("×", "*").replace("x", "*").upper()


def parse_pl(spec):
    match = re.match(r"^PL\s*(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)$", norm_spec(spec))
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def as_int(value, default=0):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return int(round(float(value)))
    except Exception:
        return default


def as_float(value, default=0.0):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def _obb_values(part):
    dims = part.get("obbDims") or {}
    return sorted([as_float(dims.get(key)) for key in ("x", "y", "z") if as_float(dims.get(key)) > 0], reverse=True)


def _contour_segment_lengths(part):
    values = []
    for segment in part.get("contourSegments") or []:
        length = as_float(segment.get("length"))
        if length > 0:
            values.append(length)
    return values


def _nominal_dimension_candidates(part):
    thickness = as_float(part.get("thickness"))
    candidates = []
    for value in _obb_values(part):
        if value <= 0:
            continue
        if thickness > 0 and abs(value - thickness) <= 0.8:
            continue
        candidates.append(value)
    candidates.extend(_contour_segment_lengths(part))
    return candidates


def _nominal_dimension_pairs(part):
    pairs = []
    thickness = as_float(part.get("thickness"))
    obb = [value for value in _obb_values(part) if not (thickness > 0 and abs(value - thickness) <= 0.8)]
    if len(obb) >= 2:
        pairs.append((obb[0], obb[1]))

    segments = _contour_segment_lengths(part)
    for index, length_a in enumerate(segments):
        length_b = segments[(index + 1) % len(segments)] if segments else 0.0
        if length_a > 0 and length_b > 0:
            pairs.append((max(length_a, length_b), min(length_a, length_b)))
    return pairs


def nominal_plate_dimensions(part, row=None):
    """Return manufacturing length/width for plate matching.

    ContourPlate OBB can be larger than the processing dimensions when the
    plate is skewed. If an Excel row is available, choose contour edges nearest
    to the declared length and width.
    """
    obb = _obb_values(part)
    fallback_length = obb[0] if obb else 0.0
    fallback_width = obb[1] if len(obb) > 1 else 0.0

    pairs = _nominal_dimension_pairs(part)
    if text(part.get("runtimeType")) != "ContourPlate" or not pairs:
        return fallback_length, fallback_width

    if row:
        spec = norm_spec(row.get("规格"))
        length = as_float(row.get("长度"))
        pl = parse_pl(spec)
        if pl and length > 0:
            _, width = pl
            length_candidate, width_candidate = min(
                pairs,
                key=lambda pair: abs(pair[0] - length) + abs(pair[1] - width) * 2,
            )
            length_ok = abs(length_candidate - length) <= max(10.0, min(120.0, length * 0.08))
            width_ok = abs(width_candidate - width) <= max(8.0, width * 0.08)
            if length_ok and width_ok:
                return length_candidate, width_candidate
            return length_candidate, width_candidate

    return pairs[0]


def part_profile_norm(part, row=None):
    profile = norm_spec(part.get("profileString"))
    if "*" in profile:
        return profile
    thickness = part.get("thickness")
    part_length, part_width = nominal_plate_dimensions(part, row)
    if profile.startswith("PL") and thickness and part_width > 0:
        return f"PL{int(round(as_float(thickness)))}*{int(round(part_width))}"
    return profile


def part_length_approx(part, row=None):
    part_length, _ = nominal_plate_dimensions(part, row)
    return part_length


def part_width_approx(part, row=None):
    _, part_width = nominal_plate_dimensions(part, row)
    return part_width


def row_part_score(row, part):
    spec = norm_spec(row["规格"])
    length = as_float(row["长度"])
    pl = parse_pl(spec)
    part_spec = part_profile_norm(part, row)
    part_len = part_length_approx(part, row)
    part_width = part_width_approx(part, row)

    spec_ok = part_spec == spec
    if not spec_ok and pl:
        thickness, width = pl
        spec_ok = (
            bool(part.get("isPlateLike"))
            and abs(as_float(part.get("thickness")) - thickness) <= 0.6
            and abs(part_width - width) <= max(8.0, width * 0.08)
        )

    length_tol = max(10.0, min(120.0, length * 0.08))
    length_ok = abs(part_len - length) <= length_tol
    return spec_ok, length_ok, abs(part_len - length), part_spec, part_len, part_width


def parts_match_row(row, parts):
    if not parts:
        return False
    spec = norm_spec(row["规格"])
    if spec.startswith("D"):
        return all(
            part_profile_norm(part, row) == spec
            and abs(part_length_approx(part, row) - row["长度"]) <= max(25.0, row["长度"] * 0.15)
            for part in parts
        )

    pl = parse_pl(spec)
    if pl and row["长度"] > 9000 and pl[1] >= 850:
        thickness, width = pl
        return all(
            part.get("isPlateLike")
            and abs(as_float(part.get("thickness")) - thickness) <= 0.6
            and abs(part_width_approx(part, row) - width) <= max(15.0, width * 0.05)
            for part in parts
        )
    return all(row_part_score(row, part)[0] and row_part_score(row, part)[1] for part in parts)


def candidate_parts(row, all_parts, relaxed=False):
    spec = norm_spec(row["规格"])
    length = row["长度"]
    candidates = []
    for part in all_parts:
        spec_ok, length_ok, delta, _, _, _ = row_part_score(row, part)
        if spec_ok and length_ok:
            candidates.append((delta, part))

    if candidates:
        return [part for _, part in sorted(candidates, key=lambda item: item[0])]

    if not relaxed:
        return []

    pl = parse_pl(spec)
    if not pl:
        return []
    thickness, width = pl
    loose = []
    for part in all_parts:
        if not part.get("isPlateLike"):
            continue
        if abs(as_float(part.get("thickness")) - thickness) > 0.6:
            continue
        part_len = part_length_approx(part, row)
        part_width = part_width_approx(part, row)
        width_ok = abs(part_width - width) <= max(12.0, width * 0.12)
        length_ok = abs(part_len - length) <= max(40.0, min(300.0, length * 0.25))
        if width_ok and length_ok:
            loose.append((abs(part_len - length) + abs(part_width - width), part))
    return [part for _, part in sorted(loose, key=lambda item: item[0])]


def format_candidate_notes(parts, row=None, limit=5):
    notes = []
    for part in parts[:limit]:
        notes.append(
            f"{text(part.get('partPosition'))}/{text(part.get('name'))}/"
            f"{text(part.get('profileString'))}/"
            f"{part_length_approx(part, row):.1f}x{part_width_approx(part, row):.1f}/"
            f"id={part.get('partId')}"
        )
    return "; ".join(notes)


def base_h_profile_part_name(part_name):
    match = re.match(r"^(.+-H-\d+)[a-z]$", text(part_name), flags=re.IGNORECASE)
    return match.group(1) if match else ""


def is_derived_h_profile_plate(row, parent_parts):
    if not parent_parts:
        return False

    base_name = base_h_profile_part_name(row["零件名称"])
    if not base_name:
        return False

    pl = parse_pl(row["规格"])
    if not pl:
        return False

    thickness, width = pl
    length = as_float(row["长度"])
    suffix = text(row["零件名称"])[-1:].lower()
    for part in parent_parts:
        if text(part.get("partPosition")) != base_name:
            continue

        profile = norm_spec(part.get("profileString"))
        dims = sorted([part_length_approx(part), part_width_approx(part)], reverse=True)
        length_ok = any(abs(value - length) <= max(10.0, length * 0.06) for value in dims)
        parent_cut_length = dims[1] if len(dims) > 1 else 0.0
        if not length_ok and parent_cut_length > 0:
            length_ok = parent_cut_length * 0.6 <= length <= parent_cut_length * 1.05
        if not length_ok:
            continue

        numeric = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", profile)]
        if profile.startswith("BH") and len(numeric) >= 4:
            height, flange_width, web_thickness, flange_thickness = numeric[:4]
            if suffix in {"s", "x"} and abs(thickness - flange_thickness) <= 0.6 and abs(width - flange_width) <= 8.0:
                return True
            if suffix == "f" and abs(thickness - web_thickness) <= 0.6 and abs(width - length) <= 15.0:
                return True
            if suffix == "f" and abs(thickness - web_thickness) <= 0.6 and abs(width - height) <= 30.0:
                return True

    return False


def nearest_candidates(row, all_parts, limit=5):
    pl = parse_pl(row["规格"])
    length = row["长度"]
    scored = []
    for part in all_parts:
        part_len = part_length_approx(part, row)
        part_width = part_width_approx(part, row)
        part_spec = part_profile_norm(part, row)
        score = abs(part_len - length)
        spec_hit = part_spec == norm_spec(row["规格"])
        if pl and part.get("isPlateLike"):
            thickness, width = pl
            score += abs(part_width - width) * 2
            score += abs(as_float(part.get("thickness")) - thickness) * 20
            spec_hit = spec_hit or abs(part_width - width) <= max(20.0, width * 0.2)
        if spec_hit:
            scored.append((score, part))
    return [part for _, part in sorted(scored, key=lambda item: item[0])[:limit]]


def find_equivalent_parts(row, by_pos, all_parts):
    exact = by_pos.get(row["零件名称"], [])
    if exact:
        if parts_match_row(row, exact):
            return exact, "partPosition", ""
        return exact, "partPositionConflict", format_candidate_notes(exact, row)

    base_name = base_h_profile_part_name(row["零件名称"])
    if base_name:
        parent_parts = by_pos.get(base_name, [])
        if is_derived_h_profile_plate(row, parent_parts):
            return parent_parts, "derivedFromProfilePart", format_candidate_notes(parent_parts, row)

    return [], "missing", format_candidate_notes(nearest_candidates(row, all_parts), row)


def summarize_parts(parts, rel_by_part=None, roles=None, row=None):
    rel_by_part = rel_by_part or defaultdict(Counter)
    roles = roles or {}
    profile_counter = Counter(norm_spec(p.get("profileString")) for p in parts)
    name_counter = Counter(text(p.get("name")) for p in parts)
    runtime_counter = Counter(text(p.get("runtimeType")) for p in parts)
    rel_counter = Counter()
    role_counter = Counter()
    bolt_holes = 0
    boolean_cuts = 0
    contour_vertices = 0
    concave_corners = 0
    has_arc = False
    is_special = False
    is_plate_like = False
    thicknesses = []
    lengths = []
    widths = []
    part_ids = []

    for part in parts:
        part_id = str(part.get("partId"))
        part_ids.append(part_id)
        bolt_holes += as_int(part.get("boltHoleCount"))
        boolean_cuts += as_int(part.get("booleanCutCount"))
        contour_vertices += as_int(part.get("contourVertexCount"))
        concave_corners += as_int(part.get("concaveCornerCount"))
        has_arc = has_arc or bool(part.get("hasArcContour"))
        is_special = is_special or bool(part.get("isSpecialShape"))
        is_plate_like = is_plate_like or bool(part.get("isPlateLike"))
        if part.get("thickness") is not None:
            thicknesses.append(as_float(part.get("thickness")))
        lengths.append(part_length_approx(part, row))
        widths.append(part_width_approx(part, row))
        rel_counter.update(rel_by_part.get(part_id, {}))
        if part_id in roles:
            role_counter.update([roles[part_id].get("Role", "")])

    return {
        "tekla_count": len(parts),
        "part_ids": ",".join(part_ids[:12]) + ("..." if len(part_ids) > 12 else ""),
        "tekla_names": ";".join(f"{key}:{value}" for key, value in name_counter.most_common(4)),
        "tekla_profiles": ";".join(f"{key}:{value}" for key, value in profile_counter.most_common(4)),
        "runtime_types": ";".join(f"{key}:{value}" for key, value in runtime_counter.most_common(4)),
        "role_candidates": ";".join(f"{key}:{value}" for key, value in role_counter.most_common(4)),
        "rel_counts": ";".join(f"{key}:{value}" for key, value in rel_counter.most_common(4)),
        "bolt_holes": bolt_holes,
        "boolean_cuts": boolean_cuts,
        "contour_vertices": contour_vertices,
        "concave_corners": concave_corners,
        "has_arc_contour": has_arc,
        "is_special_shape": is_special,
        "is_plate_like": is_plate_like,
        "max_length": round(max(lengths) if lengths else 0.0, 1),
        "max_width": round(max(widths) if widths else 0.0, 1),
        "thicknesses": ",".join(str(int(x)) if abs(x - int(x)) < 1e-6 else f"{x:.1f}" for x in sorted(set(thicknesses))),
    }
