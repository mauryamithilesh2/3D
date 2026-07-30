"""
graphics/distance_renderer.py
============================
Perpendicular and reference-relative distance line segments rendering.
"""

from __future__ import annotations

import numpy as np

from config.colors import get_color
from core.measurement import PointMeasurement
from graphics.gl_utils import _make_color_array


def _update_distance_lines(
    widget,
    measurements: list[PointMeasurement],
    reference_point: np.ndarray | None = None,
    reference_selected: bool = False,
) -> None:
    """Update the inspection-point distance segments."""
    dist_color = get_color("COLOR_DISTANCE_LINE")
    proj_color = get_color("COLOR_PROJECTION_POINT")

    if not measurements:
        widget._distance_lines_item.setData(pos=np.empty((0, 3)), color=dist_color)
        widget._projection_points_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(proj_color, 0)
        )
        return

    if reference_selected and reference_point is not None:
        segment_points = []
        for measurement in measurements:
            segment_points.append(reference_point)
            segment_points.append(measurement.world_coordinates)

        widget._distance_lines_item.setData(pos=np.stack(segment_points), color=dist_color)
        widget._distance_lines_item.setVisible(True)
        widget._projection_points_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(proj_color, 0)
        )
        return

    segment_points = []
    projections = []
    for measurement in measurements:
        segment_points.append(measurement.world_coordinates)
        segment_points.append(measurement.projection_world)
        projections.append(measurement.projection_world)

    widget._distance_lines_item.setData(pos=np.stack(segment_points), color=dist_color)
    widget._distance_lines_item.setVisible(True)
    proj_arr = np.stack(projections)
    widget._projection_points_item.setData(
        pos=proj_arr, color=_make_color_array(proj_color, len(proj_arr))
    )
    widget._projection_points_item.setVisible(True)
