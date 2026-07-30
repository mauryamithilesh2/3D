"""
graphics/point_renderer.py
==========================
Plane points and inspection points scatter rendering and label sync.
"""

from __future__ import annotations

import numpy as np

from config.colors import get_color
from core.coordinate_system import CoordinateSystem
from core.measurement import PointMeasurement
from graphics.gl_utils import _make_color_array
from graphics.label_manager import _sync_labels
from utils import format_number, format_signed_distance, format_vector


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

    desired = {
        label: (pos, color_plane_point, f"{label} {format_vector(pos)}")
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
) -> None:
    """Update the inspection point scatter and its labels."""
    if measurements:
        positions = np.stack([m.world_coordinates for m in measurements])
    else:
        positions = np.empty((0, 3))

    color_insp_point = get_color("COLOR_INSPECTION_POINT")
    colors = _make_color_array(color_insp_point, len(positions))
    widget._inspection_points_item.setData(pos=positions, color=colors)

    desired = {}
    for m in measurements:
        if reference_selected:
            dist_text = f"d={format_number(m.distance_to_reference)}"
        else:
            dist_text = f"d={format_signed_distance(abs(m.distance_to_plane))}"
        desired[m.label] = (
            m.world_coordinates,
            color_insp_point,
            f"{m.label} {format_vector(m.world_coordinates)} {dist_text}",
        )
    _sync_labels(widget, widget._inspection_labels, desired)
