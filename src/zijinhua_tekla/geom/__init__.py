"""Thin geometry kernel for recognition.

P0/P1: 3D primitives and tolerances live here. Planar topology stays behind
`geom.planar` (Shapely). Classifiers must not import shapely directly in new code.
"""

from __future__ import annotations

from dataclasses import dataclass


LINEAR_TOL_MM = 1.0


@dataclass(frozen=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


__all__ = ["LINEAR_TOL_MM", "Vec3"]
