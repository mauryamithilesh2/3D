"""
graphics/plane_renderer.py
==========================
Fitted plane mesh patch, 2-point connecting line, plane normal, and origin dot rendering logic.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl

from config.colors import get_color
from core.best_fit_plane import BestFitPlaneResult
from core.coordinate_system import CoordinateSystem
from graphics.gl_utils import _make_color_array


def _update_plane_and_normal(
    widget,
    plane_points: dict[str, np.ndarray],
    plane_result: BestFitPlaneResult | None,
    coordinate_system: CoordinateSystem | None,
) -> None:
    """Update the fitted plane patch, 2-point line, normal indicator, and origin dot."""
    count = len(plane_points)

    origin_color = get_color("COLOR_ORIGIN_POINT")
    imaginary_color = get_color("COLOR_IMAGINARY_POINT")
    fitted_plane_color = get_color("COLOR_FITTED_PLANE")

    if coordinate_system is not None:
        colors = _make_color_array(origin_color, 1)
        widget._origin_point_item.setData(
            pos=np.array([coordinate_system.origin]), color=colors
        )
        widget._origin_point_item.setVisible(True)
    else:
        colors = _make_color_array(origin_color, 0)
        widget._origin_point_item.setData(pos=np.empty((0, 3)), color=colors)
        widget._origin_point_item.setVisible(False)

    if count < 2:
        widget._plane_line_item.setVisible(False)
        widget._plane_mesh_item.setVisible(False)
        widget._normal_line_item.setVisible(False)
        widget._imaginary_point_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(imaginary_color, 0)
        )
        return

    if count == 2:
        positions = np.stack(list(plane_points.values()))
        widget._plane_line_item.setData(pos=positions)
        widget._plane_line_item.setVisible(True)
        widget._plane_mesh_item.setVisible(False)
        widget._normal_line_item.setVisible(False)
        widget._imaginary_point_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(imaginary_color, 0)
        )
        return

    # 3 or 4+ points: hide 2-point line segment
    widget._plane_line_item.setVisible(False)

    if count != 3:
        widget._imaginary_point_item.setData(
            pos=np.empty((0, 3)), color=_make_color_array(imaginary_color, 0)
        )

    if plane_result is None or coordinate_system is None:
        widget._plane_mesh_item.setVisible(False)
        widget._normal_line_item.setVisible(False)
        return

    origin = coordinate_system.origin
    x_axis = coordinate_system.x_axis
    y_axis = coordinate_system.y_axis

    if count == 3:
        p0, p1, p2 = list(plane_points.values())
        imaginary_point = p0 + p2 - p1
        vertices = np.array([p0, p1, p2, imaginary_point])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        face_colors = np.array([fitted_plane_color, fitted_plane_color])

        widget._imaginary_point_item.setData(
            pos=np.array([imaginary_point]),
            color=_make_color_array(imaginary_color, 1),
        )
    else:
        pts = list(plane_points.values())
        u_vals = [(p - origin) @ x_axis for p in pts]
        v_vals = [(p - origin) @ y_axis for p in pts]
        u_min, u_max = min(u_vals), max(u_vals)
        v_min, v_max = min(v_vals), max(v_vals)

        pad_u = max(1.0, (u_max - u_min) * 0.1)
        pad_v = max(1.0, (v_max - v_min) * 0.1)
        u_min -= pad_u
        u_max += pad_u
        v_min -= pad_v
        v_max += pad_v

        vertices = np.array(
            [
                origin + u_min * x_axis + v_min * y_axis,
                origin + u_max * x_axis + v_min * y_axis,
                origin + u_max * x_axis + v_max * y_axis,
                origin + u_min * x_axis + v_max * y_axis,
            ]
        )
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        face_colors = np.array([fitted_plane_color, fitted_plane_color])

    mesh = gl.MeshData(vertexes=vertices, faces=faces, faceColors=face_colors)

    from graphics.ghost_renderer import _capture_current_plane_vertices, _push_ghost_history, _render_ghost_history

    _push_ghost_history(widget, _capture_current_plane_vertices(widget))
    widget._plane_mesh_item.setMeshData(meshdata=mesh)
    widget._plane_mesh_item.setVisible(True)
    _render_ghost_history(widget)
