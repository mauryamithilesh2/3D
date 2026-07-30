"""
core/coordinate_system.py
=========================
Builds the local plane coordinate system (origin + X/Y/Z axes) from a
:class:`~core.best_fit_plane.BestFitPlaneResult`.

Why does the plane need its own coordinate system at all?
-----------------------------------------------------------
A best fit plane on its own only tells us an orientation (the normal) and
a reference point it passes through. To describe *where on the
surface* an inspection point lands -- the way a CMM report shows "Local X /
Local Y / Local Z" relative to a datum -- we need a full origin plus three
orthonormal axes. That local frame is what lets every other module
(``transform.py``, ``measurement.py``) turn a raw world-space (X, Y, Z)
into a physically meaningful "how far along the surface, and how far off
it" description.

Compatible with Python 3.10+, NumPy only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

from core.best_fit_plane import BestFitPlaneResult


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CoordinateSystemError(ValueError):
    """Raised when a local coordinate system cannot be built or referenced."""


# ---------------------------------------------------------------------------
# Origin reference selection
# ---------------------------------------------------------------------------

class OriginReference(Enum):
    """Identifies what the local coordinate system's origin is anchored to."""

    WORLD_ORIGIN = auto()
    PLANE_POINT = auto()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CoordinateSystem:
    """An immutable local coordinate frame anchored on the fitted plane.

    Attributes
    ----------
    origin:
        World-space position of the local frame's origin, shape ``(3,)``.
    x_axis, y_axis, z_axis:
        Unit-length, mutually orthogonal world-space basis vectors of the
        local frame. ``z_axis`` is always identical to the plane's fitted
        normal -- this guarantees "local Z" always means "height above the
        surface" everywhere in the application.
    rotation_matrix:
        3x3 orthonormal matrix with columns ``(x_axis, y_axis, z_axis)``.
        Reused directly by :mod:`transform` for World <-> Plane conversion.
    reference:
        Which :class:`OriginReference` produced this origin.
    reference_point_index:
        If ``reference`` is ``PLANE_POINT``, the index (into the plane
        point list) that was used as the origin. ``None`` otherwise.
    """

    origin: np.ndarray
    x_axis: np.ndarray
    y_axis: np.ndarray
    z_axis: np.ndarray
    rotation_matrix: np.ndarray
    reference: OriginReference
    reference_point_index: int | None = None


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class CoordinateSystemBuilder:
    """Builds a :class:`CoordinateSystem` from a fitted plane and an origin choice."""

    @staticmethod
    def build_at_world_origin(plane: BestFitPlaneResult) -> CoordinateSystem:
        """Build the local frame anchored at the world origin (0, 0, 0)."""
        x_axis, y_axis, z_axis = _axes_from_rotation_matrix(plane.rotation_matrix)
        return CoordinateSystem(
            origin=np.zeros(3, dtype=np.float64),
            x_axis=x_axis,
            y_axis=y_axis,
            z_axis=z_axis,
            rotation_matrix=plane.rotation_matrix.copy(),
            reference=OriginReference.WORLD_ORIGIN,
            reference_point_index=None,
        )

    @staticmethod
    def build_at_plane_point(
        plane: BestFitPlaneResult, plane_points: np.ndarray, point_index: int
    ) -> CoordinateSystem:
        """Build the local frame with its origin at a specific plane point.

        Parameters
        ----------
        plane:
            The fitted plane supplying orientation (the axes never change
            with the choice of origin -- only the frame's position shifts).
        plane_points:
            The full array of plane points that were fitted, shape
            ``(N, 3)``. The chosen origin point is taken from this array
            and then projected onto the plane (see notes below).
        point_index:
            Index of the plane point to use as the local origin.

        Why project the chosen point onto the plane first?
            A raw measured plane point generally does NOT lie exactly on
            the best fit plane (that is the nature of a least-squares fit
            -- see ``rms_error``). Using the raw, slightly off-plane point
            as an origin would tilt the meaning of "local Z = 0" away from
            the fitted surface. Projecting it onto the plane keeps the
            local frame's Z=0 plane exactly equal to the fitted plane,
            while still anchoring X=0, Y=0 at the operator-selected
            physical location.
        """
        if not (0 <= point_index < len(plane_points)):
            raise CoordinateSystemError(
                f"Plane point index {point_index} is out of range for "
                f"{len(plane_points)} plane points."
            )

        raw_point = np.asarray(plane_points[point_index], dtype=np.float64)
        origin = plane.project_point(raw_point)

        x_axis, y_axis, z_axis = _axes_from_rotation_matrix(plane.rotation_matrix)
        return CoordinateSystem(
            origin=origin,
            x_axis=x_axis,
            y_axis=y_axis,
            z_axis=z_axis,
            rotation_matrix=plane.rotation_matrix.copy(),
            reference=OriginReference.PLANE_POINT,
            reference_point_index=point_index,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _axes_from_rotation_matrix(
    rotation_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split a 3x3 rotation matrix's columns back into 3 axis vectors.

    The rotation matrix's columns already are the axes (see
    ``best_fit_plane.BestFitPlane.fit``); this helper just names them so
    every consumer of a :class:`CoordinateSystem` gets self-documenting
    ``x_axis`` / ``y_axis`` / ``z_axis`` fields instead of raw matrix
    columns.
    """
    x_axis = rotation_matrix[:, 0].copy()
    y_axis = rotation_matrix[:, 1].copy()
    z_axis = rotation_matrix[:, 2].copy()
    return x_axis, y_axis, z_axis
