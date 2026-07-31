"""
graphics/scene_dynamic.py
=========================
Persistent dynamic OpenGL scene items creation (mesh, lines, scatters).
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtGui import QFont

from config import (
    COLOR_DISTANCE_LINE,
    COLOR_GHOST_PLANE,
    COLOR_IMAGINARY_POINT,
    COLOR_INSPECTION_POINT,
    COLOR_LABEL_TEXT,
    COLOR_LOCAL_DOTTED,
    COLOR_NORMAL_HEAD,
    COLOR_ORIGIN_POINT,
    COLOR_PLANE_EDGE,
    COLOR_PLANE_NORMAL,
    COLOR_PLANE_POINT,
    COLOR_PROJECTION_POINT,
    COLOR_REFERENCE_GLOW,
    COLOR_WORLD_DOTTED,
    GHOST_HISTORY_DEPTH,
    IMAGINARY_POINT_SIZE,
    INSPECTION_POINT_SIZE,
    PLANE_POINT_SIZE,
    PROJECTION_POINT_SIZE,
    REFERENCE_GLOW_SIZE,
)
from graphics.gl_utils import _make_color_array, _to_qcolor

_LABEL_FONT = QFont("Consolas", 8)


def _build_dynamic_items(widget: gl.GLViewWidget) -> None:
    """Create the (initially empty) items whose DATA changes live."""
    placeholder = gl.MeshData(
        vertexes=np.zeros((4, 3)),
        faces=np.array([[0, 1, 2], [0, 2, 3]]),
    )
    widget._plane_mesh_item = gl.GLMeshItem(
        meshdata=placeholder,
        smooth=False,
        drawEdges=True,
        edgeColor=COLOR_PLANE_EDGE,
        shader=None,
        computeNormals=False,
        glOptions="translucent",
    )
    widget._plane_mesh_item.setVisible(False)
    widget.addItem(widget._plane_mesh_item)

    # Ghost / history mode: a fixed-size pool of translucent plane meshes
    # reused every refresh (never recreated) to show previous plane fits.
    widget._ghost_mesh_items: list[gl.GLMeshItem] = []
    for _ in range(GHOST_HISTORY_DEPTH):
        ghost = gl.GLMeshItem(
            meshdata=placeholder,
            smooth=False,
            drawEdges=False,
            shader="balloon",
            glOptions="translucent",
        )
        ghost.setColor(COLOR_GHOST_PLANE)
        ghost.setVisible(False)
        widget.addItem(ghost)
        widget._ghost_mesh_items.append(ghost)

    # Line connecting 2 plane points when count == 2
    widget._plane_line_item = gl.GLLinePlotItem(
        pos=np.empty((0, 3)),
        color=COLOR_PLANE_POINT,
        width=2.5,
        mode="line_strip",
        antialias=True,
        glOptions="opaque",
    )
    widget._plane_line_item.setVisible(False)
    widget.addItem(widget._plane_line_item)

    # One line item holds ALL distance segments
    widget._distance_lines_item = gl.GLLinePlotItem(
        pos=np.empty((0, 3)),
        color=COLOR_DISTANCE_LINE,
        width=1.5,
        mode="lines",
        antialias=True,
        glOptions="opaque",
    )
    widget.addItem(widget._distance_lines_item)

    # Mode 1: World coordinate system dotted construction points (blue dots, 6px)
    widget._world_dotted_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_WORLD_DOTTED, 0),
        size=4.0,
        pxMode=True,
        glOptions="opaque",
    )
    widget.addItem(widget._world_dotted_item)

    # Mode 2: Local reference coordinate system dotted construction points (black dots, 6px)
    widget._local_dotted_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_LOCAL_DOTTED, 0),
        size=4.0,
        pxMode=True,
        glOptions="opaque",
    )
    widget.addItem(widget._local_dotted_item)

    # The plane normal indicator
    widget._normal_line_item = gl.GLLinePlotItem(
        pos=np.zeros((2, 3)),
        color=COLOR_PLANE_NORMAL,
        width=2.5,
        mode="line_strip",
        antialias=True,
        glOptions="opaque",
    )
    widget._normal_line_item.setVisible(False)
    widget.addItem(widget._normal_line_item)

    # Scatter plot point items
    widget._plane_points_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_PLANE_POINT, 0),
        size=PLANE_POINT_SIZE,
        pxMode=True,
        glOptions="opaque",
    )
    widget._inspection_points_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_INSPECTION_POINT, 0),
        size=INSPECTION_POINT_SIZE,
        pxMode=True,
        glOptions="opaque",
    )
    widget._projection_points_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_PROJECTION_POINT, 0),
        size=PROJECTION_POINT_SIZE,
        pxMode=True,
        glOptions="opaque",
    )
    widget._origin_point_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_ORIGIN_POINT, 0),
        size=14.0,
        pxMode=True,
        glOptions="opaque",
    )
    widget._imaginary_point_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_IMAGINARY_POINT, 0),
        size=IMAGINARY_POINT_SIZE,
        pxMode=True,
        glOptions="opaque",
    )
    # Small 3-D crosshair ("+") drawn through the center of every plane and
    # inspection point marker, on top of the round scatter dot, so the exact
    # point location reads clearly from any camera angle.
    widget._plane_points_cross_item = gl.GLLinePlotItem(
        pos=np.empty((0, 3)),
        color=np.empty((0, 4), dtype=np.float32),
        width=2.0,
        mode="lines",
        antialias=True,
        glOptions="opaque",
    )
    widget._inspection_points_cross_item = gl.GLLinePlotItem(
        pos=np.empty((0, 3)),
        color=np.empty((0, 4), dtype=np.float32),
        width=2.0,
        mode="lines",
        antialias=True,
        glOptions="opaque",
    )
    # Translucent glow halo drawn behind the active reference point.
    widget._reference_glow_item = gl.GLScatterPlotItem(
        pos=np.empty((0, 3)),
        color=_make_color_array(COLOR_REFERENCE_GLOW, 0),
        size=REFERENCE_GLOW_SIZE,
        pxMode=True,
        glOptions="translucent",
    )
    widget._reference_glow_item.setVisible(False)

    for item in (
        widget._plane_points_item,
        widget._inspection_points_item,
        widget._projection_points_item,
        widget._origin_point_item,
        widget._imaginary_point_item,
        widget._reference_glow_item,
        widget._plane_points_cross_item,
        widget._inspection_points_cross_item,
    ):
        widget.addItem(item)

    # Interactive local (X, Y, Z) coordinate frame triad at the selected
    # reference point -- one line item, 3 segments, per-vertex colored.
    widget._local_axis_item = gl.GLLinePlotItem(
        pos=np.zeros((6, 3)),
        color=np.zeros((6, 4), dtype=np.float32),
        width=3.5,
        mode="lines",
        antialias=True,
        glOptions="opaque",
    )
    widget._local_axis_item.setVisible(False)
    widget.addItem(widget._local_axis_item)

    widget._local_axis_label_items = {}
    for axis_label in ("X", "Y", "Z"):
        item = gl.GLTextItem(
            pos=np.zeros(3), text="", color=_to_qcolor(COLOR_LABEL_TEXT), font=_LABEL_FONT
        )
        item.setVisible(False)
        widget.addItem(item)
        widget._local_axis_label_items[axis_label] = item

    # Plane normal arrowhead (cone mesh capping the normal shaft line).
    cone_placeholder = gl.MeshData(
        vertexes=np.zeros((3, 3)),
        faces=np.array([[0, 1, 2]]),
    )
    widget._normal_head_item = gl.GLMeshItem(
        meshdata=cone_placeholder,
        smooth=True,
        drawEdges=False,
        shader="shaded",
        glOptions="opaque",
    )
    widget._normal_head_item.setColor(COLOR_NORMAL_HEAD)
    widget._normal_head_item.setVisible(False)
    widget.addItem(widget._normal_head_item)