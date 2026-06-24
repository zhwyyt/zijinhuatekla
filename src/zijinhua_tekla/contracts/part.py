"""Part contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PartRecord:
    part_id: str
    position: str = ""
    name: str = ""
    profile: str = ""
    material: str = ""
    runtime_type: str = ""
    is_plate_like: bool = False
    thickness: float = 0.0
    length: float = 0.0
    width: float = 0.0
    bolt_hole_count: int = 0
    boolean_cut_count: int = 0
    weld_count: int = 0


@dataclass(frozen=True)
class PartFeatureSnapshot:
    part_id: str
    position: str = ""
    name: str = ""
    profile: str = ""
    material: str = ""
    runtime_type: str = ""
    is_plate_like: bool = False
    is_special_shape: bool = False
    thickness: float = 0.0
    obb_dims: dict[str, float] = field(default_factory=dict)
    contour_segment_lengths: list[float] = field(default_factory=list)
    contour_vertex_count: int = 0
    concave_corner_count: int = 0
    hole_like_feature_count: int = 0
    boolean_cut_count: int = 0
    bolt_hole_count: int = 0
    chamfer_count: int = 0
    cutout_count: int = 0
    notch_count: int = 0
    bending_count: int = 0
    weld_count: int = 0
    has_arc_contour: bool = False
    shape_type: str = ""
    is_regular_shape: bool = True