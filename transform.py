"""
transform.py
=============
Converts points between WORLD coordinates (the raw X, Y, Z an operator
types in, or a robot/CMM reports) and PLANE (local) coordinates (X, Y along
the fitted surface, Z as height above it), using a
:class:`~coordinate_system.CoordinateSystem`.

Why do we need an explicit transform module at all?
-----------------------------------------------------
This is precisely what a robot or CMM controller does internally whenever
it reports a measurement "relative to a datum": it does not report raw
machine coordinates, it reports coordinates in the part's own reference
frame. Separating that conversion into its own module (rather than folding
it into the UI or the plane fit) keeps the one genuinely reusable piece of
linear algebra -- rotate-then-translate, and its inverse -- isolated,
tested, and free of any Qt or OpenGL dependency.

Compatible with Python 3.10+, NumPy only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from coordinate_system import CoordinateSystem


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LocalCoordinates:
    """A point expressed in the plane's local (X, Y, Z) frame.

    Attributes
    ----------
    x, y:
        Position along the fitted surface, measured from the local origin
        along ``x_axis`` / ``y_axis``.
    z:
        Height above (positive) or below (negative) the fitted plane,
        measured along the plane normal. Identical in meaning to
        ``BestFitPlaneResult.signed_distance`` when the origin is the
        centroid, since ``z_axis`` is always the plane normal.
    """

    x: float
    y: float
    z: float

    def as_array(self) -> np.ndarray:
        """Return this local coordinate as a NumPy array ``[x, y, z]``."""
        return np.array([self.x, self.y, self.z], dtype=np.float64)

    def as_tuple(self) -> tuple[float, float, float]:
        """Return this local coordinate as a plain ``(x, y, z)`` tuple."""
        return (self.x, self.y, self.z)


# ---------------------------------------------------------------------------
# Transformer
# ---------------------------------------------------------------------------

class CoordinateTransformer:
    """Converts points between world space and a plane's local coordinate frame.

    Parameters
    ----------
    coordinate_system:
        The local frame (origin + orthonormal axes) to transform relative
        to. Immutable for the transformer's lifetime -- callers construct
        a new :class:`CoordinateTransformer` whenever the underlying best
        fit plane or origin reference changes, which keeps this class
        simple and stateless with respect to the geometry pipeline.
    """

    def __init__(self, coordinate_system: CoordinateSystem) -> None:
        self._frame = coordinate_system

    @property
    def coordinate_system(self) -> CoordinateSystem:
        """The local frame this transformer converts relative to."""
        return self._frame

    # ------------------------------------------------------------------
    # World -> Plane
    # ------------------------------------------------------------------

    def world_to_plane(self, world_point: np.ndarray) -> LocalCoordinates:
        """Convert a WORLD-space point into local plane coordinates.

        Parameters
        ----------
        world_point:
            Point as ``[x, y, z]`` in world coordinates.

        Returns
        -------
        LocalCoordinates
            The same physical point, expressed as (local X, local Y,
            local Z) relative to the plane's origin and axes.

        Math
        ----
        local = Rᵀ · (world - origin)

        Why subtract the origin first?
            The rotation matrix R describes an orientation *about the
            origin*; a world point's position relative to the plane only
            makes sense once we measure it from that origin rather than
            from the world's (0, 0, 0), which is an arbitrary point that
            has nothing to do with the fitted surface.

        Why the TRANSPOSE of the rotation matrix, not its inverse?
            R's columns (x_axis, y_axis, z_axis) are mutually orthogonal
            and unit length -- by definition, that makes R an ORTHOGONAL
            matrix, and for any orthogonal matrix R⁻¹ = Rᵀ exactly. This
            is far cheaper and more numerically stable than a general
            matrix inverse (no risk of an ill-conditioned inversion), and
            is the standard technique used throughout robotics for
            converting into a local/body frame.
        """
        world_point = np.asarray(world_point, dtype=np.float64)
        offset = world_point - self._frame.origin
        local = self._frame.rotation_matrix.T @ offset
        return LocalCoordinates(x=float(local[0]), y=float(local[1]), z=float(local[2]))

    # ------------------------------------------------------------------
    # Plane -> World
    # ------------------------------------------------------------------

    def plane_to_world(self, local_point: LocalCoordinates | np.ndarray) -> np.ndarray:
        """Convert a local plane-space point back into WORLD coordinates.

        Parameters
        ----------
        local_point:
            Either a :class:`LocalCoordinates` instance or a raw
            ``[x, y, z]`` array-like in local coordinates.

        Returns
        -------
        np.ndarray
            The same physical point, expressed as ``[x, y, z]`` in world
            coordinates, shape ``(3,)``.

        Math
        ----
        world = R · local + origin

        This is the exact inverse of :meth:`world_to_plane`: rotate the
        local offset back into world orientation using R itself (not its
        transpose -- we are now going in the forward direction), then add
        back the origin we subtracted during the forward conversion.
        """
        if isinstance(local_point, LocalCoordinates):
            local_array = local_point.as_array()
        else:
            local_array = np.asarray(local_point, dtype=np.float64)

        world = self._frame.rotation_matrix @ local_array + self._frame.origin
        return world