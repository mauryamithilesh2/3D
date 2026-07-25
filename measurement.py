"""
measurement.py
================
Turns a raw inspection point plus an already-fitted plane into a complete,
ready-to-display measurement: its world coordinates, its coordinates in the
plane's local frame, its orthogonal projection onto the plane, and its
signed point-to-plane distance. Also provides a general point-to-point
distance helper.

Why does this module exist separately from best_fit_plane / transform?
--------------------------------------------------------------------------
``best_fit_plane.py`` and ``transform.py`` each expose one focused piece of
math (fit a plane / signed distance / projection; world <-> local
conversion). Every actual "measurement" the UI needs to show is a small
bundle of results from BOTH of those modules for the same point, computed
together so they can never drift out of sync with each other (e.g. a
displayed local Z that doesn't match the displayed signed distance). This
module owns that bundling and nothing else -- it introduces no new
geometry of its own, it only orchestrates ``best_fit_plane`` and
``transform``.

Compatible with Python 3.10+, NumPy only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from best_fit_plane import BestFitPlaneResult
from transform import CoordinateTransformer, LocalCoordinates


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PointMeasurement:
    """The complete set of computed geometry for one inspection point."""

    label: str
    world_coordinates: np.ndarray
    plane_coordinates: LocalCoordinates
    projection_world: np.ndarray
    distance_to_plane: float
    distance_to_reference: float


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MeasurementEngine:
    """Computes :class:`PointMeasurement` results against a fitted plane."""

    @staticmethod
    def measure_point(
        label: str,
        coordinates: np.ndarray,
        plane: BestFitPlaneResult,
        transformer: CoordinateTransformer,
    ) -> PointMeasurement:
        """Compute the full :class:`PointMeasurement` for a single point."""
        world = np.asarray(coordinates, dtype=np.float64)
        plane_coordinates = transformer.world_to_plane(world)
        projection_world = plane.project_point(world)
        distance_to_plane = plane.signed_distance(world)
        distance_to_reference = float(np.linalg.norm(plane_coordinates.as_array()))

        return PointMeasurement(
            label=label,
            world_coordinates=world,
            plane_coordinates=plane_coordinates,
            projection_world=projection_world,
            distance_to_plane=distance_to_plane,
            distance_to_reference=distance_to_reference,
        )

    @staticmethod
    def measure_points(
        points: list[tuple[str, np.ndarray]],
        plane: BestFitPlaneResult,
        transformer: CoordinateTransformer,
    ) -> list[PointMeasurement]:
        """Compute :class:`PointMeasurement` for every ``(label, coordinates)`` pair.

        Parameters
        ----------
        points:
            ``[(label, [x, y, z]), ...]`` -- exactly the structure returned
            by ``point_manager.PointManager.inspection_points()``.
        plane, transformer:
            See :meth:`measure_point`.

        Returns
        -------
        list[PointMeasurement]
            One measurement per input point, in the same order, ready to
            hand directly to ``ui.ResultsPanel.display_results`` and
            ``gl3d_widget.GL3DWidget.update_scene``.
        """
        return [
            MeasurementEngine.measure_point(label, coordinates, plane, transformer)
            for label, coordinates in points
        ]


# ---------------------------------------------------------------------------
# Standalone helper: point-to-point distance
# ---------------------------------------------------------------------------

def point_to_point_distance(point_a: np.ndarray, point_b: np.ndarray) -> float:
    """Euclidean (straight-line) distance between two world-space points.

    Why does this live here rather than in ``utils.py``?
        ``utils.py`` is explicitly scoped to string parsing/formatting (see
        its module docstring) with no geometry of its own. A point-to-point
        distance is a measurement in the same sense as point-to-plane
        distance -- it belongs alongside the rest of this module's
        measurement math, not in the formatting-only utility module.

    This does not depend on any plane or coordinate system -- it is a
    plain Euclidean distance, useful for ad-hoc comparisons such as
    "how far apart are two inspection points" independent of the fitted
    surface.
    """
    a = np.asarray(point_a, dtype=np.float64)
    b = np.asarray(point_b, dtype=np.float64)
    return float(np.linalg.norm(a - b))