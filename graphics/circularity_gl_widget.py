"""
graphics/circularity_gl_widget.py
==================================
3D viewport for the Circularity & Concentricity module: draws the two hole
centers, the ideal (coaxial) rod axis, and the radial misalignment as a
distinct segment -- so the numbers in the results panel have a matching
picture. Subclasses ``BaseGLWidget`` for shared viewport scaffolding.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl

from config.colors import get_color
from core.circularity import ConcentricityResult, perpendicular_basis
from graphics.base_gl_widget import BaseGLWidget
from graphics.gl_utils import _lerp, _to_qcolor
from graphics.label_manager import _sync_labels

#: Visual-only hole radius for drawing the circle rings. The PLC only
#: supplies center points, not bore diameter, so this is illustrative --
#: it does not affect any of the computed numbers.
_DISPLAY_RADIUS = 8.0
_CIRCLE_SEGMENTS = 48


def _circle_points(center: np.ndarray, normal: np.ndarray, radius: float) -> np.ndarray:
    """Ring of points forming a circle of ``radius`` centered at ``center``,
    lying in the plane perpendicular to ``normal``."""
    u, v = perpendicular_basis(normal)
    angles = np.linspace(0.0, 2.0 * np.pi, _CIRCLE_SEGMENTS, endpoint=True)
    return np.array([center + radius * (np.cos(a) * u + np.sin(a) * v) for a in angles])


class CircularityGLWidget(BaseGLWidget):
    """Minimal 3D scene: two hole circles, the ideal rod axis, and the
    radial-misalignment segment between them."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._hole_1_item = gl.GLLinePlotItem(mode="line_strip", width=3, antialias=True)
        self._hole_2_item = gl.GLLinePlotItem(mode="line_strip", width=3, antialias=True)
        self._axial_item = gl.GLLinePlotItem(mode="lines", width=3, antialias=True)
        self._radial_item = gl.GLLinePlotItem(mode="lines", width=3, antialias=True)
        self._straight_item = gl.GLLinePlotItem(mode="lines", width=1.5, antialias=True)
        self._centers_item = gl.GLScatterPlotItem(size=12)

        for item in (
            self._hole_1_item, self._hole_2_item, self._axial_item,
            self._radial_item, self._straight_item, self._centers_item,
        ):
            self.addItem(item)

        self._last_positions: dict[str, np.ndarray] | None = None

        # C1/C2 text labels next to each hole center, kept in sync via the
        # same _sync_labels helper the distance module uses for its point
        # labels -- so styling/behavior stays consistent app-wide.
        self._center_labels: dict[str, gl.GLTextItem] = {}

    def _apply_default_camera(self) -> None:
        """Set camera viewing angle for circularity viewport."""
        self.setCameraPosition(distance=140, elevation=22, azimuth=35)

    def update_scene(
        self,
        center_1: np.ndarray,
        center_2: np.ndarray,
        rod_axis: np.ndarray,
        result: ConcentricityResult,
    ) -> None:
        """Redraw the two holes and the axial/radial breakdown for the given
        measurement. ``result`` must have been produced by
        :func:`core.circularity.measure_concentricity` with the same
        ``center_1``/``center_2``/``rod_axis`` so the picture matches the
        numbers shown in the results panel."""
        self._last_update_args = (center_1, center_2, rod_axis, result)
        self._last_update_kwargs = {}

        c1 = np.asarray(center_1, dtype=np.float64)
        c2 = np.asarray(center_2, dtype=np.float64)
        axis = np.asarray(rod_axis, dtype=np.float64)
        axis = axis / np.linalg.norm(axis)

        # Point on the ideal (coaxial) rod axis line, level with hole 2 --
        # same "nearest point" the axial/radial decomposition is built from.
        nearest_on_axis = c1 + result.delta_axial * axis

        # Grow the displayed circle radius whenever the offset between the
        # two centers exceeds the default radius -- so the picture makes
        # the misalignment visually obvious instead of silently overlapping.
        # Both circles share one default radius, so both grow together by
        # the same amount when triggered (smoothly animated via the normal
        # position-lerp below, since it only changes vertex positions).
        offset = result.radial_displacement
        effective_radius = (
            _DISPLAY_RADIUS + offset if offset > _DISPLAY_RADIUS else _DISPLAY_RADIUS
        )

        new_positions = {
            "_hole_1_item": _circle_points(c1, axis, effective_radius),
            "_hole_2_item": _circle_points(c2, axis, effective_radius),
            "_axial_item": np.array([c1, nearest_on_axis]),
            "_radial_item": np.array([nearest_on_axis, c2]),
            "_straight_item": np.array([c1, c2]),
            "_centers_item": np.array([c1, c2]),
        }

        colors = {
            "_hole_1_item": _to_qcolor(get_color("COLOR_PLANE_POINT")).getRgbF(),
            "_hole_2_item": _to_qcolor(get_color("COLOR_INSPECTION_POINT")).getRgbF(),
            "_axial_item": _to_qcolor(get_color("COLOR_LOCAL_AXIS_Z")).getRgbF(),
            "_radial_item": _to_qcolor(get_color("COLOR_LOCAL_AXIS_X")).getRgbF(),
            "_straight_item": (0.6, 0.6, 0.6, 0.6),
        }
        for name, color in colors.items():
            getattr(self, name).setData(color=color)
        self._centers_item.setData(color=np.array([colors["_hole_1_item"], colors["_hole_2_item"]]), size=12)

        previous = self._last_positions
        self._last_positions = new_positions

        # Only animate when shapes match a prior frame (same as GL3DWidget's
        # rule) -- first draw or a shape change just applies instantly.
        if previous is not None and all(
            previous[name].shape == new_positions[name].shape for name in new_positions
        ):
            def apply(t: float) -> None:
                for name, end in new_positions.items():
                    start = previous[name]
                    getattr(self, name).setData(pos=_lerp(start, end, t))

            self._animator.start(apply)
        else:
            for name, pos in new_positions.items():
                getattr(self, name).setData(pos=pos)

        self._apply_visibility_overrides()

        # Keep the "C1"/"C2" text labels pinned to the current centers.
        color_c1 = _to_qcolor(get_color("COLOR_PLANE_POINT")).getRgbF()
        color_c2 = _to_qcolor(get_color("COLOR_INSPECTION_POINT")).getRgbF()
        desired_labels = {
            "C1": (c1, color_c1, "C1"),
            "C2": (c2, color_c2, "C2"),
        }
        _sync_labels(self, self._center_labels, desired_labels)