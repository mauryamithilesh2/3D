"""
graphics/frame_renderer.py
==========================
Renders two additive, purely-visual scene elements sourced from an already
-built :class:`~core.coordinate_system.CoordinateSystem` and
:class:`~core.best_fit_plane.BestFitPlaneResult`:

- The interactive local (X, Y, Z) coordinate frame triad at the selected
  reference point (or the world origin, when no plane point is selected).
- The plane normal, rendered as a proper arrow (shaft + cone head) instead
  of a bare line.

No new geometry/math is introduced here -- every position comes straight
from ``coordinate_system.origin`` / ``.x_axis`` / ``.y_axis`` / ``.z_axis``
and ``plane_result.normal``, which are already computed by ``core/``.
"""

from __future__ import annotations

import numpy as np

from config import (
    LOCAL_AXIS_DISPLAY_LENGTH,
    NORMAL_ARROW_HEAD_LENGTH,
    NORMAL_ARROW_HEAD_RADIUS,
    NORMAL_VECTOR_DISPLAY_LENGTH,
)
from config.colors import get_color
from core.best_fit_plane import BestFitPlaneResult
from core.coordinate_system import CoordinateSystem
from graphics.gl_utils import _make_cone_mesh


def _update_local_axes(
    widget,
    coordinate_system: CoordinateSystem | None,
) -> None:
    """Update the local (reference-point) X/Y/Z coordinate frame triad."""
    if coordinate_system is None:
        widget._local_axis_item.setVisible(False)
        for item in widget._local_axis_label_items.values():
            item.setVisible(False)
        return

    origin = coordinate_system.origin
    axes = (coordinate_system.x_axis, coordinate_system.y_axis, coordinate_system.z_axis)
    colors = (
        get_color("COLOR_LOCAL_AXIS_X"),
        get_color("COLOR_LOCAL_AXIS_Y"),
        get_color("COLOR_LOCAL_AXIS_Z"),
    )
    tips = [origin + LOCAL_AXIS_DISPLAY_LENGTH * axis for axis in axes]

    positions = np.empty((6, 3), dtype=np.float64)
    vertex_colors = np.empty((6, 4), dtype=np.float32)
    for i, (tip, color) in enumerate(zip(tips, colors)):
        positions[2 * i] = origin
        positions[2 * i + 1] = tip
        vertex_colors[2 * i] = color
        vertex_colors[2 * i + 1] = color

    widget._local_axis_item.setData(pos=positions, color=vertex_colors)
    widget._local_axis_item.setVisible(True)

    for label, tip, color in zip(("X", "Y", "Z"), tips, colors):
        item = widget._local_axis_label_items[label]
        item.setData(pos=tip + np.array([0.0, 0.0, 0.25]), text=f"local {label}")
        item.setVisible(True)


def _update_normal_arrow(
    widget,
    plane_result: BestFitPlaneResult | None,
    coordinate_system: CoordinateSystem | None,
) -> None:
    """Update the plane-normal arrow (shaft line + cone head)."""
    if plane_result is None or coordinate_system is None:
        widget._normal_line_item.setVisible(False)
        widget._normal_head_item.setVisible(False)
        return

    origin = coordinate_system.origin
    normal = plane_result.normal
    shaft_length = max(0.0, NORMAL_VECTOR_DISPLAY_LENGTH - NORMAL_ARROW_HEAD_LENGTH)
    shaft_end = origin + shaft_length * normal
    tip = origin + NORMAL_VECTOR_DISPLAY_LENGTH * normal

    widget._normal_line_item.setData(
        pos=np.array([origin, shaft_end]),
        color=get_color("COLOR_PLANE_NORMAL"),
    )
    widget._normal_line_item.setVisible(True)

    cone = _make_cone_mesh(
        axis_dir=normal,
        apex=tip,
        height=NORMAL_ARROW_HEAD_LENGTH,
        radius=NORMAL_ARROW_HEAD_RADIUS,
    )
    widget._normal_head_item.setMeshData(meshdata=cone)
    widget._normal_head_item.setColor(get_color("COLOR_NORMAL_HEAD"))
    widget._normal_head_item.setVisible(True)
