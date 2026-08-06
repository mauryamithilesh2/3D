"""
graphics/point_renderer.py
==========================
Plane points and inspection points scatter rendering and label sync.
"""

from __future__ import annotations

import numpy as np

from config import POINT_CROSS_ARM_LENGTH
from config.colors import get_color
from core.coordinate_system import CoordinateSystem
from core.measurement import PointMeasurement
from graphics.gl_utils import _make_color_array
from graphics.label_manager import _sync_labels


def _cross_lines_for_points(
    positions: np.ndarray, color: tuple[float, float, float, float], arm: float = POINT_CROSS_ARM_LENGTH
) -> tuple[np.ndarray, np.ndarray]:
    """Build a small 3-D crosshair ("+") through each point in ``positions``.

    Returns a ``(6*N, 3)`` vertex array (3 line segments per point -- one
    along each world axis -- as consecutive start/end pairs for a
    ``GLLinePlotItem`` in ``mode="lines"``) and a matching ``(6*N, 4)``
    per-vertex color array.
    """
    n = len(positions)
    if n == 0:
        return np.empty((0, 3)), np.empty((0, 4), dtype=np.float32)

    offsets = np.array(
        [
            [-arm, 0.0, 0.0], [arm, 0.0, 0.0],
            [0.0, -arm, 0.0], [0.0, arm, 0.0],
            [0.0, 0.0, -arm], [0.0, 0.0, arm],
        ]
    )
    # For every point, 6 vertices (3 segments): shape (N, 6, 3) -> (6*N, 3).
    vertices = positions[:, None, :] + offsets[None, :, :]
    vertices = vertices.reshape(-1, 3)
    colors = _make_color_array(color, len(vertices))
    return vertices, colors


def _update_plane_points(
    widget,
    plane_points: dict[str, np.ndarray],
    coordinate_system: CoordinateSystem | None = None,
    reference_label: str | None = None,
) -> None:
    """Update the plane point scatter and its labels."""
    if plane_points:
        positions = np.stack(list(plane_points.values()))
    else:
        positions = np.empty((0, 3))

    color_plane_point = get_color("COLOR_PLANE_POINT")
    color_ref_ring = get_color("COLOR_REFERENCE_RING")

    colors = _make_color_array(color_plane_point, len(positions))
    if reference_label is not None and reference_label in plane_points:
        ref_index = list(plane_points.keys()).index(reference_label)
        colors[ref_index] = np.array(color_ref_ring, dtype=np.float32)
    widget._plane_points_item.setData(pos=positions, color=colors)

    cross_pos, cross_colors = _cross_lines_for_points(positions, color_plane_point)
    widget._plane_points_cross_item.setData(pos=cross_pos, color=cross_colors)

    desired = {
        label: (pos, color_plane_point,label)
        for label, pos in plane_points.items()
    }
    _sync_labels(widget, widget._plane_labels, desired)

    _update_reference_glow(widget, plane_points, reference_label)


def _update_reference_glow(
    widget,
    plane_points: dict[str, np.ndarray],
    reference_label: str | None,
) -> None:
    """Update the soft translucent halo drawn behind the active reference point."""
    glow_color = get_color("COLOR_REFERENCE_GLOW")
    if reference_label is not None and reference_label in plane_points:
        pos = np.array([plane_points[reference_label]])
        widget._reference_glow_item.setData(
            pos=pos, color=_make_color_array(glow_color, 1)
        )
        widget._reference_glow_item.setVisible(True)
    else:
        widget._reference_glow_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(glow_color, 0)
        )
        widget._reference_glow_item.setVisible(False)



def _update_inspection_points(
    widget,
    measurements: list[PointMeasurement],
    reference_selected: bool = False,
    inspection_points: list[tuple[str, np.ndarray]] | None = None,
) -> None:
    """Update the inspection point scatter and its labels."""
    if measurements:
        positions = np.stack([m.world_coordinates for m in measurements])
    elif inspection_points:
        positions = np.stack([pos for _, pos in inspection_points])
    else:
        positions = np.empty((0, 3))

    color_insp_point = get_color("COLOR_INSPECTION_POINT")
    colors = _make_color_array(color_insp_point, len(positions))
    widget._inspection_points_item.setData(pos=positions, color=colors)

    cross_pos, cross_colors = _cross_lines_for_points(positions, color_insp_point)
    widget._inspection_points_cross_item.setData(pos=cross_pos, color=cross_colors)

    desired = {}
    if measurements:
        for m in measurements:
            desired[m.label] = (
                m.world_coordinates,
                color_insp_point,
                m.label,
            )
    elif inspection_points:
        for label, pos in inspection_points:
            desired[label] = (
                pos,
                color_insp_point,
                label,
            )
    _sync_labels(widget, widget._inspection_labels, desired)
