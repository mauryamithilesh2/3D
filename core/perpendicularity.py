"""
core/perpendicularity.py
=========================
GD&T Perpendicularity measurement: the angular deviation of an already
fitted plane's normal from an independent datum axis.

Perpendicularity controls how close to exactly 90 degrees a feature sits
relative to a datum. Expressed on a fitted surface, that is exactly the
angle between the surface's normal and the datum axis -- 0 degrees of
deviation means the surface is perfectly perpendicular to the datum.

This module performs NO plane fitting of its own -- it consumes a
BestFitPlaneResult that core.best_fit_plane / the owning window already
computed from the shared PointManager's plane points, exactly the way
core.circularity consumes hole centers supplied by its caller. Zero
dependency on PyQt/OpenGL, consistent with every other core/ module.

``datum_axis`` must come from a source independent of the points that
produced ``plane_result`` (a world/machine axis, or a second, separately
fitted reference plane's normal) -- deriving it from the same plane being
checked would make the deviation trivially zero, for the identical reason
documented in core.circularity.measure_concentricity.

Compatible with Python 3.10+, NumPy only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.best_fit_plane import BestFitPlaneResult
from core.circularity import _WORLD_X, _WORLD_Y, _WORLD_Z

__all__ = [
    "PerpendicularityResult",
    "measure_perpendicularity",
    "DATUM_AXIS_OPTIONS",
]

#: Named datum axis choices for the UI's datum selector -- reuses the same
#: world-axis constants core.circularity already defines rather than
#: redefining them a third time (core.edge_axis has its own 2-D-only pair
#: for a different, plane-local purpose).
DATUM_AXIS_OPTIONS: dict[str, np.ndarray] = {
    "World X": _WORLD_X,
    "World Y": _WORLD_Y,
    "World Z": _WORLD_Z,
}


@dataclass(frozen=True)
class PerpendicularityResult:
    """Result of comparing a fitted plane's normal against a datum axis.

    Attributes
    ----------
    deviation_angle_deg:
        Angle, in degrees (0-90), between the plane normal and the datum
        axis. 0 means perfectly perpendicular (normal parallel to datum);
        90 means the surface actually runs parallel to the datum instead
        of perpendicular to it.
    datum_axis:
        The (unit-length) axis this result was measured against.
    normal:
        The plane normal this result was measured from (copied through
        for display/traceability, unchanged from ``plane_result.normal``).
    """

    deviation_angle_deg: float
    datum_axis: np.ndarray
    normal: np.ndarray

    def is_within_tolerance(self, tolerance_deg: float) -> bool:
        """True if the measured deviation is within ``tolerance_deg`` of
        perfectly perpendicular (0 degrees)."""
        return self.deviation_angle_deg <= abs(tolerance_deg)


def measure_perpendicularity(
    plane_result: BestFitPlaneResult,
    datum_axis: np.ndarray = _WORLD_Z,
) -> PerpendicularityResult:
    """Angular deviation of ``plane_result.normal`` from ``datum_axis``.

    Parameters
    ----------
    plane_result:
        An already-fitted plane (see ``core.best_fit_plane.BestFitPlane.fit``).
        Only its ``normal`` is read; nothing about the fit is modified.
    datum_axis:
        The independent reference direction perpendicularity is measured
        against. Defaults to World Z, the vertical machine axis -- the
        most common CMM/robot datum. Does not need to be pre-normalized.

    Math
    ----
    Both ``normal`` and ``datum_axis`` are unit vectors, so their dot
    product is exactly the cosine of the angle between them. Perfect
    perpendicularity of the SURFACE to the datum axis means the surface's
    NORMAL is exactly PARALLEL to that axis (a flat table top is
    perpendicular to gravity because its normal points straight along the
    vertical) -- so deviation is simply that angle itself, taken via
    ``arccos`` of the absolute dot product (absolute value because a
    normal pointing the "wrong way" along a valid axis is not itself a
    perpendicularity error).

    Raises
    ------
    ValueError
        If ``datum_axis`` is a zero vector.
    """
    normal = np.asarray(plane_result.normal, dtype=np.float64)
    axis = np.asarray(datum_axis, dtype=np.float64)
    norm = np.linalg.norm(axis)
    if norm == 0.0:
        raise ValueError("datum_axis must be a non-zero vector")
    axis = axis / norm

    cos_angle = float(np.clip(abs(np.dot(normal, axis)), -1.0, 1.0))
    deviation_angle_deg = float(np.degrees(np.arccos(cos_angle)))

    return PerpendicularityResult(
        deviation_angle_deg=deviation_angle_deg,
        datum_axis=axis,
        normal=normal.copy(),
    )