"""
graphics/dotted_line_renderer.py
================================
Industrial-style coordinate projection dotted construction lines rendering for inspection points.

Provides two visualization modes:
- Mode 1 (World Coordinate System): Dotted lines along global X, Y, Z axes from world origin (0,0,0) to P0.
- Mode 2 (Local Coordinate System): Dotted lines along local X, Y, Z axes from selected local reference origin to P0.
"""

from __future__ import annotations

import numpy as np

from config.colors import get_color
from core.coordinate_system import CoordinateSystem
from core.measurement import PointMeasurement
from graphics.gl_utils import _make_color_array


def _update_dotted_lines(
    widget,
    inspection_points: list[tuple[str, np.ndarray]],
    measurements: list[PointMeasurement],
    coordinate_system: CoordinateSystem | None,
    reference_selected: bool = False,
    reference_point: np.ndarray | None = None,
) -> None:
    """Update World and Local GLScatterPlotItem-based dotted construction projection lines for inspection points."""
    color_world_dotted = get_color("COLOR_WORLD_DOTTED")
    color_local_dotted = get_color("COLOR_LOCAL_DOTTED")

    # ------------------------------------------------------------------
    # MODE 1: World Coordinate System (Default, Always Active)
    # ------------------------------------------------------------------
    world_positions: list[np.ndarray] = []
    if measurements:
        world_positions = [m.world_coordinates for m in measurements]
    elif inspection_points:
        world_positions = [pos for _, pos in inspection_points]

    world_dots: list[np.ndarray] = []
    world_origin = np.array([0.0, 0.0, 0.0], dtype=np.float64)

    for p0 in world_positions:
        # Step 1: Origin (0,0,0) -> (X, 0, 0) along World X
        foot1 = np.array([p0[0], 0.0, 0.0], dtype=np.float64)
        # Step 2: (X, 0, 0) -> (X, Y, 0) along World Y
        foot2 = np.array([p0[0], p0[1], 0.0], dtype=np.float64)
        # Step 3: (X, Y, 0) -> (X, Y, Z) along World Z (ending at P0)
        foot3 = np.asarray(p0, dtype=np.float64)

        _sample_segment_dots(world_dots, world_origin, foot1)
        _sample_segment_dots(world_dots, foot1, foot2)
        _sample_segment_dots(world_dots, foot2, foot3)

    if world_dots:
        pos_arr = np.stack(world_dots)
        colors = _make_color_array(color_world_dotted, len(pos_arr))
        widget._world_dotted_item.setData(pos=pos_arr, color=colors)
        widget._world_dotted_item.setVisible(True)
    else:
        widget._world_dotted_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(color_world_dotted, 0)
        )
        widget._world_dotted_item.setVisible(False)

    # ------------------------------------------------------------------
    # MODE 2: Local Reference Coordinate System
    # ------------------------------------------------------------------
    local_dots: list[np.ndarray] = []

    if reference_selected and coordinate_system is not None and measurements:
        origin = coordinate_system.origin
        x_axis = coordinate_system.x_axis
        y_axis = coordinate_system.y_axis
        z_axis = coordinate_system.z_axis

        for m in measurements:
            loc = m.plane_coordinates  # LocalCoordinates(x, y, z)

            # Step 1: Reference Origin -> move along Local X
            foot1 = origin + loc.x * x_axis
            # Step 2: foot1 -> move along Local Y
            foot2 = foot1 + loc.y * y_axis
            # Step 3: foot2 -> move along Local Z (ending at P0)
            foot3 = foot2 + loc.z * z_axis

            _sample_segment_dots(local_dots, origin, foot1)
            _sample_segment_dots(local_dots, foot1, foot2)
            _sample_segment_dots(local_dots, foot2, foot3)

    if local_dots:
        pos_arr = np.stack(local_dots)
        colors = _make_color_array(color_local_dotted, len(pos_arr))
        widget._local_dotted_item.setData(pos=pos_arr, color=colors)
        widget._local_dotted_item.setVisible(True)
    else:
        widget._local_dotted_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(color_local_dotted, 0)
        )
        widget._local_dotted_item.setVisible(False)


def _sample_segment_dots(
    target_list: list[np.ndarray],
    start: np.ndarray,
    end: np.ndarray,
    step_dist: float = 0.4,
) -> None:
    """Sample a 3D line segment at fixed distance intervals (1-2 world units) to generate GLScatterPlotItem dots."""
    vec = end - start
    length = float(np.linalg.norm(vec))
    if length < 1e-6:
        return

    num_samples = max(2, int(round(length / step_dist)) + 1)
    for i in range(num_samples):
        t = i / float(num_samples - 1)
        p = start + t * vec
        target_list.append(p)
