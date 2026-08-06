"""
core/orientation.py
====================
GD&T Perpendicularity and Parallelism between TWO independently best-fit
planes -- a Reference (datum) Plane and an Inspection Plane.

Geometry
--------
Let theta = angle_between_normals_deg(n_ref, n_insp), in [0, 180].

Parallelism (two planes are parallel <=> their normals are parallel,
regardless of which way either normal points):
    deviation = arccos(|n_ref . n_insp|)   -- 0 deg = perfectly parallel.

Perpendicularity (two planes are perpendicular <=> the dihedral angle
between them is 90 deg, which equals the angle between their normals):
    deviation = |90 - theta|               -- 0 deg = perfectly perpendicular.
    Sign-invariant: flipping either normal maps theta -> 180 - theta, and
    |90 - (180 - theta)| == |theta - 90|.

No plane fitting happens here -- exactly like core.perpendicularity, this
consumes already-fitted BestFitPlaneResult objects. Zero PyQt/OpenGL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from core.best_fit_plane import BestFitPlaneResult

__all__ = [
    "OrientationResult",
    "angle_between_normals_deg",
    "measure_perpendicularity_planes",
    "measure_parallelism_planes",
    "plane_intersection_line",
    "ORIENTATION_CHECKS",
]


@dataclass(frozen=True)
class OrientationResult:
    relation: str                # "Perpendicularity" | "Parallelism"
    deviation_angle_deg: float   # 0 = perfect match for that relation
    reference_normal: np.ndarray
    inspection_normal: np.ndarray

    def is_within_tolerance(self, tolerance_deg: float) -> bool:
        return self.deviation_angle_deg <= abs(tolerance_deg)


def angle_between_normals_deg(normal_a: np.ndarray, normal_b: np.ndarray) -> float:
    """Raw angle, in degrees [0, 180], between two normal vectors."""
    a = np.asarray(normal_a, dtype=np.float64)
    b = np.asarray(normal_b, dtype=np.float64)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        raise ValueError("normals must be non-zero vectors")
    cos_angle = float(np.clip(np.dot(a / norm_a, b / norm_b), -1.0, 1.0))
    return float(np.degrees(np.arccos(cos_angle)))


def measure_perpendicularity_planes(
    reference_plane: BestFitPlaneResult, inspection_plane: BestFitPlaneResult
) -> OrientationResult:
    """0 deg deviation = Inspection Plane sits exactly 90 deg to the
    Reference (datum) Plane."""
    theta = angle_between_normals_deg(reference_plane.normal, inspection_plane.normal)
    deviation = abs(90.0 - theta)
    return OrientationResult(
        relation="Perpendicularity",
        deviation_angle_deg=deviation,
        reference_normal=np.asarray(reference_plane.normal, dtype=np.float64).copy(),
        inspection_normal=np.asarray(inspection_plane.normal, dtype=np.float64).copy(),
    )


def measure_parallelism_planes(
    reference_plane: BestFitPlaneResult, inspection_plane: BestFitPlaneResult
) -> OrientationResult:
    """0 deg deviation = Inspection Plane sits exactly parallel to the
    Reference (datum) Plane."""
    n_ref = np.asarray(reference_plane.normal, dtype=np.float64)
    n_insp = np.asarray(inspection_plane.normal, dtype=np.float64)
    cos_angle = float(np.clip(
        abs(np.dot(n_ref / np.linalg.norm(n_ref), n_insp / np.linalg.norm(n_insp))),
        -1.0, 1.0,
    ))
    deviation = float(np.degrees(np.arccos(cos_angle)))
    return OrientationResult(
        relation="Parallelism",
        deviation_angle_deg=deviation,
        reference_normal=n_ref.copy(),
        inspection_normal=n_insp.copy(),
    )


#: Selectable checks for ui.orientation_result_panel.OrientationResultPanel.
#: A future plane-to-plane relation (e.g. Coplanarity) = one new function
#: above + one new entry here; the panel and MainWindow never change.
ORIENTATION_CHECKS: dict[str, Callable[[BestFitPlaneResult, BestFitPlaneResult], OrientationResult]] = {
    "Perpendicularity": measure_perpendicularity_planes,
    "Parallelism": measure_parallelism_planes,
}


def plane_intersection_line(
    reference_plane: BestFitPlaneResult, inspection_plane: BestFitPlaneResult
) -> tuple[np.ndarray, np.ndarray] | None:
    """The actual 3-D line where the Reference Plane and Inspection Plane
    cut each other -- returns (point_on_line, unit_direction), or None
    when the two planes are (near-)parallel and have no single
    intersection line to anchor on.

    Solves the 3x3 system [n_ref; n_insp; direction] . x = [d_ref; d_insp; 0],
    where direction = n_ref x n_insp -- the third equation pins down the
    unique point on the line closest to the world origin.
    """
    n_ref = np.asarray(reference_plane.normal, dtype=np.float64)
    n_insp = np.asarray(inspection_plane.normal, dtype=np.float64)
    direction = np.cross(n_ref, n_insp)
    norm_dir = np.linalg.norm(direction)
    if norm_dir < 1e-9:
        return None
    direction = direction / norm_dir

    d_ref = float(np.dot(n_ref, reference_plane.centroid))
    d_insp = float(np.dot(n_insp, inspection_plane.centroid))

    a = np.array([n_ref, n_insp, direction])
    b = np.array([d_ref, d_insp, 0.0])
    point = np.linalg.solve(a, b)
    return point, direction