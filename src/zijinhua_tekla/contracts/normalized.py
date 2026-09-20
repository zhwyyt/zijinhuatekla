"""Model-first normalized contracts. Classifiers consume these, never factory Excel."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedPart:
    part_id: str
    part_position: str = ""
    name: str = ""
    profile: str = ""
    material: str = ""
    runtime_type: str = ""
    is_plate_like: bool = False
    is_special_shape: bool = False
    thickness: float = 0.0
    length: float = 0.0
    width: float = 0.0
    contour_vertex_count: int = 0
    concave_corner_count: int = 0
    has_arc_contour: bool = False
    bolt_hole_count: int = 0
    boolean_cut_count: int = 0
    weld_count: int = 0
    hole_like_feature_count: int = 0
    obb_dims: tuple[float, float, float] = (0.0, 0.0, 0.0)
    contour_points: tuple[tuple[float, float, float], ...] = ()
    contour_chamfers: tuple[tuple[str, float, float], ...] = ()
    contour_chamfer_types: tuple[str, ...] = ()
    edge_bevel_count: int = 0
    has_edge_bevel: bool = False
    end_chamfer_count: int = 0
    has_end_chamfer: bool = False
    relationship_counts: tuple[tuple[str, int], ...] = ()

    def rel_count(self, edge_type: str) -> int:
        wanted = edge_type.lower()
        for name, count in self.relationship_counts:
            if name.lower() == wanted:
                return count
        return 0


@dataclass(frozen=True)
class NormalizedMemberDocument:
    member_id: str
    assembly_id: str
    parts: tuple[NormalizedPart, ...] = ()


@dataclass(frozen=True)
class PartSpatialHints:
    """Spatial/main-material evidence from model classifiers. Not factory labels."""

    member_body_type: str = ""
    relation_to_box_body: str = ""
    main_material_role: str = ""
    appendage_role: str = ""
