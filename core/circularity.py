"""
core/circularity.py
====================
Coaxiality / concentricity measurement between two hole (bore) centers --
e.g. how far a rod inserted through two aligned holes would have to bend.

Each center is supplied directly (e.g. read from a PLC); this module does
no circle fitting, only the geometric comparison between two known points.
Independent of ``core.edge_axis`` / ``core.best_fit_plane`` -- no shared
state, no shared assumptions -- so it can evolve without risk to the
distance/plane module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_WORLD_X = np.array([1.0, 0.0, 0.0])
_WORLD_Y = np.array([0.0, 1.0, 0.0])
_WORLD_Z = np.array([0.0, 0.0, 1.0])


@dataclass(frozen=True)
class ConcentricityResult:
    """Result of comparing two hole centers against a rod axis."""

    delta_axial: float             # separation ALONG the rod (not an error)
    delta_radial_1: float          # signed offset along in-plane axis 1
    delta_radial_2: float          # signed offset along in-plane axis 2
    radial_displacement: float     # sqrt(delta_radial_1^2 + delta_radial_2^2)
    straight_line_distance: float  # full 3D center-to-center distance


def perpendicular_basis(rod_axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors perpendicular to ``rod_axis`` (and to each other),
    forming a right-handed basis with it. Shared by :func:`measure_concentricity`
    and the 3D visualization so both always agree on the same in-plane axes."""
    axis = np.asarray(rod_axis, dtype=np.float64)
    norm = np.linalg.norm(axis)
    if norm == 0.0:
        raise ValueError("rod_axis must be a non-zero vector")
    axis = axis / norm

    # Pick whichever world axis is least parallel to rod_axis as a helper,
    # to avoid a degenerate cross product when rod_axis is itself close to
    # that world axis.
    helper = _WORLD_Z if abs(float(np.dot(axis, _WORLD_Z))) < 0.9 else _WORLD_Y
    perp_1 = np.cross(axis, helper)
    perp_1 = perp_1 / np.linalg.norm(perp_1)
    perp_2 = np.cross(axis, perp_1)
    return perp_1, perp_2


def measure_concentricity(
    center_1: np.ndarray,
    center_2: np.ndarray,
    rod_axis: np.ndarray = _WORLD_X,
) -> ConcentricityResult:
    """How far two hole centers are offset from being coaxial along ``rod_axis``.

    ``rod_axis`` defaults to world X (the common case: the rod travels along
    a fixed machine axis), but any direction works -- it does not need to be
    normalized or aligned to a global axis. ``rod_axis`` must come from a
    source independent of ``center_1``/``center_2`` (a known machine axis or
    a separate calibration) -- deriving it from the two centers being
    measured would make ``radial_displacement`` trivially zero.
    """
    c1 = np.asarray(center_1, dtype=np.float64)
    c2 = np.asarray(center_2, dtype=np.float64)
    axis = np.asarray(rod_axis, dtype=np.float64)
    norm = np.linalg.norm(axis)
    if norm == 0.0:
        raise ValueError("rod_axis must be a non-zero vector")
    axis = axis / norm

    offset = c2 - c1
    delta_axial = float(np.dot(offset, axis))

    perp_1, perp_2 = perpendicular_basis(axis)

    delta_radial_1 = float(np.dot(offset, perp_1))
    delta_radial_2 = float(np.dot(offset, perp_2))
    radial_displacement = float(np.hypot(delta_radial_1, delta_radial_2))
    straight_line_distance = float(np.linalg.norm(offset))

    return ConcentricityResult(
        delta_axial=delta_axial,
        delta_radial_1=delta_radial_1,
        delta_radial_2=delta_radial_2,
        radial_displacement=radial_displacement,
        straight_line_distance=straight_line_distance,
    )
