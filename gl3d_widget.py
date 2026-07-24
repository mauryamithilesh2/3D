"""
gl3d_widget.py
==============
Reusable PyQt5 / pyqtgraph OpenGL 3-D scene widget.

Responsibilities
----------------
* Initialise the OpenGL scene (background, camera, grid, axes).
* Create and own all scene items (point, plane).
* Never recreate scene items — update existing items in-place.
* Provide a clean, framework-agnostic public API.
* Wire itself to a :class:`ControlPanel` instance via Qt signals.

Public API
----------
set_point(x, y, z)
set_plane_position(x, y, z)
get_point() -> tuple[float, float, float]
get_plane_position() -> tuple[float, float, float]
reset_camera()
reset_coordinates()
connect_control_panel(panel)

Compatible with Python 3.11+, PyQt5 ≥ 5.15.9, pyqtgraph ≥ 0.13.3,
NumPy ≥ 1.24.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final

import numpy as np
import numpy.typing as npt
import pyqtgraph.opengl as gl

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel

from geometry import (
    AxisLineData,
    bgr_to_rgba,
    calculate_point_to_plane_perpendicular,
    create_axis_lines,
    create_origin_point,
    create_plane_face_colors,
    create_plane_mesh,
    make_point_pos,
)

if TYPE_CHECKING:
    # Imported only for static type-checking — avoids circular imports at runtime.
    from control_panel import ControlPanel


# ---------------------------------------------------------------------------
# Scene configuration constants
# ---------------------------------------------------------------------------

_BG_COLOR: Final[tuple[int, int, int, int]] = (236, 238, 242, 255)
"""Light grey background — (R, G, B, A) in 0-255 range."""

_CAMERA_DISTANCE: Final[float] = 160.0
_CAMERA_ELEVATION: Final[float] = 28.0
_CAMERA_AZIMUTH: Final[float] = 45.0
"""Default isometric-style camera position."""

_GRID_EXTENT: Final[float] = 200.0
_GRID_SPACING: Final[float] = 10.0
_GRID_COLOR: Final[tuple[int, int, int, int]] = (150, 155, 165, 140)
"""Neutral grey grid lines for light backgrounds."""

_AXIS_LENGTH: Final[float] = 65.0
_AXIS_WIDTH: Final[float] = 2.5

_POINT_COLOR: Final[tuple[float, float, float, float]] = bgr_to_rgba(0, 0, 0)
"""Scatter point colour — BGR(0, 0, 0) = pure black."""
_POINT_SIZE: Final[float] = 15.0

_PLANE_EDGE_COLOR: Final[tuple[float, float, float, float]] = bgr_to_rgba(217, 115, 51)
"""Edge outline — BGR(217, 115, 51) ≈ mid-blue."""

_DIST_LINE_COLOR: Final[tuple[float, float, float, float]] = bgr_to_rgba(38, 38, 38)
"""Distance indicator line — BGR(38, 38, 38) = dark charcoal."""


# ---------------------------------------------------------------------------
# GL3DWidget
# ---------------------------------------------------------------------------

class GL3DWidget(gl.GLViewWidget):
    """Reusable OpenGL 3-D scene widget derived from :class:`GLViewWidget`.

    The widget owns all scene items and maintains the canonical coordinate
    state for the *point* and *plane* objects.  Scene items are created once
    during initialisation and updated in-place thereafter.

    Parameters
    ----------
    parent:
        Optional Qt parent widget.

    Example
    -------
    >>> app = QApplication(sys.argv)
    >>> widget = GL3DWidget()
    >>> widget.set_point(10.0, 5.0, 3.0)
    >>> widget.show()
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Internal coordinate state — single source of truth.
        self._point_coords: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._plane_p1: tuple[float, float, float] = (-50.0, -50.0, 0.0)
        self._plane_p2: tuple[float, float, float] = (50.0, -50.0, 0.0)
        self._plane_p3: tuple[float, float, float] = (50.0, 50.0, 0.0)
        self._plane_p4: tuple[float, float, float] = (-50.0, 50.0, 0.0)

        # Scene item references — typed for IDE support.
        self._grid_item: gl.GLGridItem
        self._axis_items: list[gl.GLLinePlotItem]
        self._origin_marker: gl.GLScatterPlotItem
        self._point_item: gl.GLScatterPlotItem
        self._plane_item: gl.GLMeshItem
        self._plane_meshdata: gl.MeshData
        self._corner_points_item: gl.GLScatterPlotItem
        self._dist_line: gl.GLLinePlotItem
        self._dist_label: QLabel
        self._p0_label_item: gl.GLTextItem
        self._p1_label_item: gl.GLTextItem
        self._p2_label_item: gl.GLTextItem
        self._p3_label_item: gl.GLTextItem
        self._p4_label_item: gl.GLTextItem

        self._build_scene()

    # ------------------------------------------------------------------
    # Scene construction (called once)
    # ------------------------------------------------------------------

    def _build_scene(self) -> None:
        """Initialise every scene element in dependency order."""
        self._configure_background()
        self._configure_camera()
        self._create_grid()
        self._create_axes()
        self._create_point()
        self._create_plane()
        self._create_distance_indicators()

    def _configure_background(self) -> None:
        """Set the dark industrial background colour."""
        self.setBackgroundColor(_BG_COLOR)

    def _configure_camera(self) -> None:
        """Position the camera at the default isometric viewpoint."""
        self.setCameraPosition(
            distance=_CAMERA_DISTANCE,
            elevation=_CAMERA_ELEVATION,
            azimuth=_CAMERA_AZIMUTH,
        )

    def _create_grid(self) -> None:
        """Add a flat XY reference grid centred at the world origin."""
        self._grid_item = gl.GLGridItem()
        self._grid_item.setSize(x=_GRID_EXTENT, y=_GRID_EXTENT, z=1.0)
        self._grid_item.setSpacing(x=_GRID_SPACING, y=_GRID_SPACING, z=1.0)
        self._grid_item.setColor(_GRID_COLOR)
        self.addItem(self._grid_item)

    def _create_axes(self) -> None:
        """Add X (red), Y (green), Z (blue) axis lines and an origin marker."""
        self._axis_items = []

        axes: list[AxisLineData] = create_axis_lines(length=_AXIS_LENGTH)
        for axis in axes:
            line = gl.GLLinePlotItem(
                pos=axis.pos,
                color=axis.color,
                width=_AXIS_WIDTH,
                antialias=False,
                mode="line_strip",
                glOptions="opaque",
            )
            self.addItem(line)
            self._axis_items.append(line)

        # Small white marker at the world origin for visual clarity.
        origin = create_origin_point(color=(1.0, 1.0, 1.0, 0.85), size=7.0)
        self._origin_marker = gl.GLScatterPlotItem(
            pos=origin.pos,
            color=np.array(origin.color, dtype=np.float32),
            size=origin.size,
            pxMode=True,
        )
        self.addItem(self._origin_marker)

        # 3D Capital Axis Labels: X (Red), Y (Green), Z (Blue)
        offset = _AXIS_LENGTH + 4.0
        x_text = gl.GLTextItem(pos=[offset, 0.0, 0.0], text="X", color=(220, 30, 30))
        y_text = gl.GLTextItem(pos=[0.0, offset, 0.0], text="Y", color=(30, 180, 30))
        z_text = gl.GLTextItem(pos=[0.0, 0.0, offset], text="Z", color=(30, 100, 220))

        font = QFont("Arial", 12, QFont.Bold)
        x_text.font = font
        y_text.font = font
        z_text.font = font

        self.addItem(x_text)
        self.addItem(y_text)
        self.addItem(z_text)

    def _create_point(self) -> None:
        """Add the controllable scatter point at the world origin."""
        initial_pos: npt.NDArray[np.float32] = make_point_pos(0.0, 0.0, 0.0)
        self._point_item = gl.GLScatterPlotItem(
            pos=initial_pos,
            color=np.array(_POINT_COLOR, dtype=np.float32),
            size=_POINT_SIZE,
            pxMode=True,
            glOptions="opaque",
        )
        self.addItem(self._point_item)

        # 3D coordinate label for P0
        self._p0_label_item = gl.GLTextItem(
            pos=[1.5, 1.5, 1.5],
            text="P0(0.0, 0.0, 0.0)",
            color=(0, 0, 0),
        )
        self._p0_label_item.font = QFont("Arial", 10, QFont.Bold)
        self.addItem(self._p0_label_item)

    def _create_plane(self) -> None:
        """Add the plane quad defined by vertices P1–P4.

        Its MeshData is constructed once; subsequently only vertex coordinates
        are updated in-place via setVertexes / meshDataChanged.
        """
        mesh_data = create_plane_mesh(
            self._plane_p1, self._plane_p2, self._plane_p3, self._plane_p4
        )
        self._plane_meshdata = mesh_data
        face_colors = create_plane_face_colors(
            rgba=(0.15, 0.45, 1.0, 0.32),
            num_faces=2,
        )
        mesh_data.setFaceColors(face_colors)

        self._plane_item = gl.GLMeshItem(
            meshdata=mesh_data,
            smooth=False,
            drawEdges=True,
            edgeColor=np.array(_PLANE_EDGE_COLOR, dtype=np.float32),
            glOptions="translucent",
        )
        self.addItem(self._plane_item)

        # 3D scatter point markers for all 4 plane corners (P1, P2, P3, P4)
        corner_pos = np.array(
            [self._plane_p1, self._plane_p2, self._plane_p3, self._plane_p4],
            dtype=np.float32,
        )
        self._corner_points_item = gl.GLScatterPlotItem(
            pos=corner_pos,
            color=np.array(bgr_to_rgba(217, 115, 51), dtype=np.float32),
            size=10.0,
            pxMode=True,
            glOptions="opaque",
        )
        self.addItem(self._corner_points_item)

        # 3D coordinate labels for plane corners P1, P2, P3, P4
        lbl_font = QFont("Arial", 9, QFont.Bold)

        p1 = self._plane_p1
        self._p1_label_item = gl.GLTextItem(
            pos=[p1[0] + 1.5, p1[1] + 1.5, p1[2] + 1.5],
            text=f"P1({p1[0]:.1f}, {p1[1]:.1f}, {p1[2]:.1f})",
            color=(30, 80, 200),
        )
        self._p1_label_item.font = lbl_font
        self.addItem(self._p1_label_item)

        p2 = self._plane_p2
        self._p2_label_item = gl.GLTextItem(
            pos=[p2[0] + 1.5, p2[1] + 1.5, p2[2] + 1.5],
            text=f"P2({p2[0]:.1f}, {p2[1]:.1f}, {p2[2]:.1f})",
            color=(30, 80, 200),
        )
        self._p2_label_item.font = lbl_font
        self.addItem(self._p2_label_item)

        p3 = self._plane_p3
        self._p3_label_item = gl.GLTextItem(
            pos=[p3[0] + 1.5, p3[1] + 1.5, p3[2] + 1.5],
            text=f"P3({p3[0]:.1f}, {p3[1]:.1f}, {p3[2]:.1f})",
            color=(30, 80, 200),
        )
        self._p3_label_item.font = lbl_font
        self.addItem(self._p3_label_item)

        p4 = self._plane_p4
        self._p4_label_item = gl.GLTextItem(
            pos=[p4[0] + 1.5, p4[1] + 1.5, p4[2] + 1.5],
            text=f"P4({p4[0]:.1f}, {p4[1]:.1f}, {p4[2]:.1f})",
            color=(30, 80, 200),
        )
        self._p4_label_item.font = lbl_font
        self.addItem(self._p4_label_item)

    def _create_distance_indicators(self) -> None:
        """Create the distance line and overlay label."""
        initial_pos: npt.NDArray[np.float32] = np.zeros((2, 3), dtype=np.float32)
        self._dist_line = gl.GLLinePlotItem(
            pos=initial_pos,
            color=_DIST_LINE_COLOR,
            width=2.0,
            antialias=False,
            mode="line_strip",
            glOptions="opaque",
        )
        self.addItem(self._dist_line)

        self._dist_label = QLabel("Distance: 0.000", self)
        self._dist_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._dist_label.setStyleSheet(
            """
            QLabel {
                background-color: rgba(255, 255, 255, 220);
                color: #1a1a1a;
                border: 1px solid #888888;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            """
        )
        self._dist_label.adjustSize()
        self._dist_label.move(10, 10)
        self._dist_label.show()
        self._dist_label.raise_()

    # ------------------------------------------------------------------
    # Public API — coordinate setters
    # ------------------------------------------------------------------

    def set_point(self, x: float, y: float, z: float) -> None:
        """Move the scatter point to the given world-space coordinates."""
        self._point_coords = (float(x), float(y), float(z))
        self._point_item.setData(pos=make_point_pos(x, y, z))
        self._p0_label_item.setData(
            pos=[x + 1.5, y + 1.5, z + 1.5],
            text=f"P0({x:.1f}, {y:.1f}, {z:.1f})",
        )
        self._update_distance_indicators()

    def set_plane_points(
        self,
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        p3: tuple[float, float, float],
        p4: tuple[float, float, float],
    ) -> None:
        """Update the 4 corner vertices defining the plane quad in-place."""
        self._plane_p1 = (float(p1[0]), float(p1[1]), float(p1[2]))
        self._plane_p2 = (float(p2[0]), float(p2[1]), float(p2[2]))
        self._plane_p3 = (float(p3[0]), float(p3[1]), float(p3[2]))
        self._plane_p4 = (float(p4[0]), float(p4[1]), float(p4[2]))

        vertex_array = np.array(
            [self._plane_p1, self._plane_p2, self._plane_p3, self._plane_p4],
            dtype=np.float32,
        )
        self._plane_meshdata.setVertexes(vertex_array)
        self._plane_item.meshDataChanged()
        self._corner_points_item.setData(pos=vertex_array)

        # Update 3D coordinate labels for P1..P4
        p1_val, p2_val, p3_val, p4_val = self._plane_p1, self._plane_p2, self._plane_p3, self._plane_p4
        self._p1_label_item.setData(
            pos=[p1_val[0] + 1.5, p1_val[1] + 1.5, p1_val[2] + 1.5],
            text=f"P1({p1_val[0]:.1f}, {p1_val[1]:.1f}, {p1_val[2]:.1f})",
        )
        self._p2_label_item.setData(
            pos=[p2_val[0] + 1.5, p2_val[1] + 1.5, p2_val[2] + 1.5],
            text=f"P2({p2_val[0]:.1f}, {p2_val[1]:.1f}, {p2_val[2]:.1f})",
        )
        self._p3_label_item.setData(
            pos=[p3_val[0] + 1.5, p3_val[1] + 1.5, p3_val[2] + 1.5],
            text=f"P3({p3_val[0]:.1f}, {p3_val[1]:.1f}, {p3_val[2]:.1f})",
        )
        self._p4_label_item.setData(
            pos=[p4_val[0] + 1.5, p4_val[1] + 1.5, p4_val[2] + 1.5],
            text=f"P4({p4_val[0]:.1f}, {p4_val[1]:.1f}, {p4_val[2]:.1f})",
        )

        self._update_distance_indicators()

    def set_plane_position(self, p1, p2=None, p3=None, p4=None) -> None:
        """Overloaded setter compatible with 4 points or (p1, p2, p3, p4) tuples."""
        if p2 is not None and p3 is not None and p4 is not None:
            self.set_plane_points(p1, p2, p3, p4)
        elif isinstance(p1, (tuple, list)) and len(p1) == 4:
            self.set_plane_points(p1[0], p1[1], p1[2], p1[3])

    # ------------------------------------------------------------------
    # Public API — coordinate getters
    # ------------------------------------------------------------------

    def get_point(self) -> tuple[float, float, float]:
        """Return the current point coordinates."""
        return self._point_coords

    def get_plane_position(self) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        """Return the 4 corner points (P1, P2, P3, P4) of the plane."""
        return (self._plane_p1, self._plane_p2, self._plane_p3, self._plane_p4)

    # ------------------------------------------------------------------
    # Public API — camera and resets
    # ------------------------------------------------------------------

    def reset_camera(self) -> None:
        """Restore the camera to the default isometric position."""
        self.setCameraPosition(
            distance=_CAMERA_DISTANCE,
            elevation=_CAMERA_ELEVATION,
            azimuth=_CAMERA_AZIMUTH,
        )

    def reset_coordinates(self) -> None:
        """Move the point and plane back to default origin values."""
        self.set_point(0.0, 0.0, 0.0)
        self.set_plane_points(
            (-50.0, -50.0, 0.0),
            (50.0, -50.0, 0.0),
            (50.0, 50.0, 0.0),
            (-50.0, 50.0, 0.0),
        )

    # ------------------------------------------------------------------
    # Distance indicator helpers (private)
    # ------------------------------------------------------------------

    def _update_distance_indicators(self) -> None:
        """Recompute and redraw the perpendicular distance line and label."""
        dist, foot = calculate_point_to_plane_perpendicular(
            self._point_coords,
            self._plane_p1,
            self._plane_p2,
            self._plane_p3,
        )
        ptx, pty, ptz = self._point_coords

        line_pos: npt.NDArray[np.float32] = np.array(
            [[ptx, pty, ptz], foot], dtype=np.float32
        )
        self._dist_line.setData(pos=line_pos)

        self._dist_label.setText(f"⊥ Distance: {dist:.3f}")
        self._dist_label.adjustSize()
        self._dist_label.raise_()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def connect_control_panel(self, panel: "ControlPanel") -> None:
        """Connect a :class:`ControlPanel` instance to this widget's API."""
        panel.point_changed.connect(self.set_point)
        panel.plane_changed.connect(self.set_plane_points)
        panel.reset_camera_requested.connect(self.reset_camera)
        panel.reset_coordinates_requested.connect(self.reset_coordinates)
