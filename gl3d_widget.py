"""
gl3d_widget.py
================
The interactive 3-D OpenGL viewport, built on ``pyqtgraph.opengl``. Renders
the grid, world axes, plane points, inspection points, the fitted best fit
plane, its normal, projection points, distance lines, and text labels.

Why update existing OpenGL items instead of recreating them every refresh?
------------------------------------------------------------------------------
Destroying and recreating GL items (buffers, VAOs, shader bindings) on
every keystroke would be wasteful and, on some drivers, visibly flicker.
Every item this widget can know about IN ADVANCE (the grid, the 3 world
axes, the fitted plane patch, the normal indicator, the point/projection
scatters, the distance-line set) is created exactly ONCE in ``__init__``
and only ever has its data replaced via ``setData`` / ``setMeshData``
afterwards. The one exception is text labels: because the *number* of
plane/inspection points is dynamic and unbounded, label items are created
lazily the first time a given point label appears and destroyed only when
that specific point is removed -- never wholesale on every refresh.

Compatible with Python 3.10+, PyQt5, pyqtgraph.opengl, NumPy.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtGui import QColor, QFont

from best_fit_plane import BestFitPlaneResult
from coordinate_system import CoordinateSystem, OriginReference
from config import (
    COLOR_AXIS_X,
    COLOR_AXIS_Y,
    COLOR_AXIS_Z,
    COLOR_DISTANCE_LINE,
    COLOR_FITTED_PLANE,
    COLOR_GRID,
    COLOR_IMAGINARY_POINT,
    COLOR_INSPECTION_POINT,
    COLOR_ORIGIN_POINT,
    COLOR_PLANE_NORMAL,
    COLOR_PLANE_POINT,
    COLOR_PROJECTION_POINT,
    GRID_SIZE,
    GRID_SPACING,
    IMAGINARY_POINT_SIZE,
    INSPECTION_POINT_SIZE,
    NORMAL_VECTOR_DISPLAY_LENGTH,
    PLANE_PATCH_HALF_EXTENT,
    PLANE_POINT_SIZE,
    PROJECTION_POINT_SIZE,
)
from measurement import PointMeasurement
from transform import CoordinateTransformer
from utils import format_number, format_signed_distance, format_vector


# ---------------------------------------------------------------------------
# World axis length -- purely a visual choice, tied to the grid extent so
# the axes always reach the edge of the drawn floor grid.
# ---------------------------------------------------------------------------
_WORLD_AXIS_LENGTH = GRID_SIZE / 2.0

_LABEL_FONT = QFont("Consolas", 9)


class GL3DWidget(gl.GLViewWidget):
    """The persistent 3-D scene showing the plane fit and its measurements.

    This widget has no knowledge of PyQt line-edits or the point manager --
    it only ever receives already-computed geometry through
    :meth:`update_scene`. That keeps it reusable and testable independently
    of the rest of the UI.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._apply_default_camera()
        self.setBackgroundColor(QColor(238, 240, 244))

        # Dynamic per-label text items, keyed by point label. Populated and
        # pruned by ``_sync_labels`` as points are added/removed.
        self._plane_labels: dict[str, gl.GLTextItem] = {}
        self._inspection_labels: dict[str, gl.GLTextItem] = {}

        self._build_static_items()
        self._build_dynamic_items()

    # ------------------------------------------------------------------
    # One-time construction
    # ------------------------------------------------------------------

    def _build_static_items(self) -> None:
        """Create the grid and world axes -- items that never move."""
        grid = gl.GLGridItem()
        grid.setSize(GRID_SIZE, GRID_SIZE)
        grid.setSpacing(GRID_SPACING, GRID_SPACING)
        grid.setColor(_to_qcolor(COLOR_GRID))
        self.addItem(grid)
        self._grid = grid

        self._axis_x = self._make_axis_line(
            np.array([[-_WORLD_AXIS_LENGTH, 0, 0], [_WORLD_AXIS_LENGTH, 0, 0]]), COLOR_AXIS_X
        )
        self._axis_y = self._make_axis_line(
            np.array([[0, -_WORLD_AXIS_LENGTH, 0], [0, _WORLD_AXIS_LENGTH, 0]]), COLOR_AXIS_Y
        )
        self._axis_z = self._make_axis_line(
            np.array([[0, 0, -_WORLD_AXIS_LENGTH], [0, 0, _WORLD_AXIS_LENGTH]]), COLOR_AXIS_Z
        )

        # Static axis labels at BOTH ends of every world axis line, so the
        # full +/- extent of X, Y, and Z is always identifiable on screen
        # regardless of how the view has been rotated.
        for text, pos, color in (
            ("+X", np.array([_WORLD_AXIS_LENGTH + 0.5, 0.0, 0.0]), COLOR_AXIS_X),
            ("-X", np.array([-_WORLD_AXIS_LENGTH - 0.5, 0.0, 0.0]), COLOR_AXIS_X),
            ("+Y", np.array([0.0, _WORLD_AXIS_LENGTH + 0.5, 0.0]), COLOR_AXIS_Y),
            ("-Y", np.array([0.0, -_WORLD_AXIS_LENGTH - 0.5, 0.0]), COLOR_AXIS_Y),
            ("+Z", np.array([0.0, 0.0, _WORLD_AXIS_LENGTH + 0.5]), COLOR_AXIS_Z),
            ("-Z", np.array([0.0, 0.0, -_WORLD_AXIS_LENGTH - 0.5]), COLOR_AXIS_Z),
        ):
            self.addItem(gl.GLTextItem(pos=pos, text=text, color=_to_qcolor(color), font=_LABEL_FONT))

    def _make_axis_line(self, pos: np.ndarray, color: tuple[float, float, float, float]) -> gl.GLLinePlotItem:
        """Create and register a single persistent world-axis line item."""
        item = gl.GLLinePlotItem(
            pos=pos, color=color, width=2.0, mode="lines", antialias=True, glOptions="opaque"
        )
        self.addItem(item)
        return item

    def _build_dynamic_items(self) -> None:
        """Create the (initially empty) items whose DATA changes live."""
        # Plane points, inspection points, and their plane projections each
        # get one persistent scatter item -- every point of that category
        # is drawn by a single GL object, sized by point count only.
        # The fitted plane patch itself: a single quad (2 triangles),
        # re-meshed in place whenever the fit or its origin changes.
        placeholder = gl.MeshData(
            vertexes=np.zeros((4, 3)),
            faces=np.array([[0, 1, 2], [0, 2, 3]]),
        )
        self._plane_mesh_item = gl.GLMeshItem(
            meshdata=placeholder,
            smooth=False,
            drawEdges=True,
            edgeColor=(0.25, 0.35, 0.55, 0.6),
            shader="balloon",
            glOptions="translucent",
        )
        self._plane_mesh_item.setVisible(False)
        self.addItem(self._plane_mesh_item)

        # Line connecting 2 plane points when count == 2
        self._plane_line_item = gl.GLLinePlotItem(
            pos=np.empty((0, 3)),
            color=COLOR_PLANE_POINT,
            width=2.5,
            mode="line_strip",
            antialias=True,
            glOptions="opaque",
        )
        self._plane_line_item.setVisible(False)
        self.addItem(self._plane_line_item)

        # One line item, drawn in 'lines' mode, holds ALL distance
        # segments (inspection point -> its projection) as a single batch.
        self._distance_lines_item = gl.GLLinePlotItem(
            pos=np.empty((0, 3)),
            color=COLOR_DISTANCE_LINE,
            width=1.5,
            mode="lines",
            antialias=True,
            glOptions="opaque",
        )
        self.addItem(self._distance_lines_item)

        # The plane normal indicator: a single 2-point line along fitted normal.
        self._normal_line_item = gl.GLLinePlotItem(
            pos=np.zeros((2, 3)),
            color=COLOR_PLANE_NORMAL,
            width=2.5,
            mode="line_strip",
            antialias=True,
            glOptions="opaque",
        )
        self._normal_line_item.setVisible(False)
        self.addItem(self._normal_line_item)

        # Scatter plot point items (plane points, inspection points, projections, origin)
        # added LAST so their dark dots are rendered on top of mesh and lines
        # at the exact (x, y, z) coordinates where each point lies.
        # IMPORTANT: GLScatterPlotItem defaults to glOptions='additive',
        # which disables depth testing and BLENDS colors by adding them to
        # whatever is already on screen. A pure black point (0, 0, 0)
        # therefore adds nothing and is completely invisible no matter its
        # size or alpha -- this was why the point markers were not showing
        # up. 'opaque' draws a solid, depth-tested dot instead, so black
        # (or any color) renders correctly and is properly occluded by/
        # occludes other solid geometry as the view is rotated.
        self._plane_points_item = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=_make_color_array(COLOR_PLANE_POINT, 0),
            size=PLANE_POINT_SIZE,
            pxMode=True,
            glOptions="opaque",
        )
        self._inspection_points_item = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=_make_color_array(COLOR_INSPECTION_POINT, 0),
            size=INSPECTION_POINT_SIZE,
            pxMode=True,
            glOptions="opaque",
        )
        self._projection_points_item = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=_make_color_array(COLOR_PROJECTION_POINT, 0),
            size=PROJECTION_POINT_SIZE,
            pxMode=True,
            glOptions="opaque",
        )
        self._origin_point_item = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=_make_color_array(COLOR_ORIGIN_POINT, 0),
            size=14.0,
            pxMode=True,
            glOptions="opaque",
        )
        # Imaginary 4th rectangle corner, auto-completed from exactly 3
        # active plane points. Rendered in a visually distinct color
        # (COLOR_IMAGINARY_POINT) so it is never mistaken for a real,
        # user-entered plane point.
        self._imaginary_point_item = gl.GLScatterPlotItem(
            pos=np.empty((0, 3)),
            color=_make_color_array(COLOR_IMAGINARY_POINT, 0),
            size=IMAGINARY_POINT_SIZE,
            pxMode=True,
            glOptions="opaque",
        )
        for item in (
            self._plane_points_item,
            self._inspection_points_item,
            self._projection_points_item,
            self._origin_point_item,
            self._imaginary_point_item,
        ):
            self.addItem(item)

    # ------------------------------------------------------------------
    # Public API -- the only entry point the rest of the app needs
    # ------------------------------------------------------------------

    def update_scene(
        self,
        plane_points: dict[str, np.ndarray],
        inspection_measurements: list[PointMeasurement],
        plane_result: BestFitPlaneResult | None,
        coordinate_system: CoordinateSystem | None,
        reference_selected: bool = False,
        reference_point: np.ndarray | None = None,
    ) -> None:
        """Refresh every dynamic item in the scene from current geometry.

        Parameters
        ----------
        reference_selected:
            ``True`` once the user has picked a plane-point reference in
            the Reference Selection panel. Before that, inspection-point
            distance is shown/drawn as the perpendicular point-to-plane
            distance (the existing default). Once a reference is picked,
            distance switches to point-to-point.
        reference_point:
            The world coordinates of the currently selected reference
            plane point, or ``None`` if ``reference_selected`` is
            ``False``. When both are set, exactly one line per
            inspection point is drawn -- from THIS reference point to
            the inspection point, not from every plane point.
        """
        self._update_plane_points(plane_points, coordinate_system)
        self._update_inspection_points(inspection_measurements, reference_selected)
        self._update_plane_and_normal(plane_points, plane_result, coordinate_system)
        self._update_distance_lines(inspection_measurements, reference_point, reference_selected)

    def reset_camera(self) -> None:
        """Restore the default camera position (used by a "Reset View" action)."""
        self._apply_default_camera()

    def _apply_default_camera(self) -> None:
        """Set the camera so the screen matches the standard engineering convention.

        Why elevation=90, azimuth=-90 specifically?
            pyqtgraph's Euler camera places the eye at
            ``center + distance * (cos(elev)cos(azim), cos(elev)sin(azim), sin(elev))``
            and orients the view so that, at elevation=90 (looking straight
            down the world Z axis), the on-screen basis becomes a pure
            function of azimuth alone. Working out that rotation shows
            azimuth=-90 is the one value that maps:
                world +X -> screen right (horizontal)
                world +Y -> screen up (vertical)
                world +Z -> straight out of the screen, toward the viewer
            This is the conventional "looking at the XY plane face-on, Z
            coming toward you" view used throughout CAD/metrology
            software, and it is why the fitted plane and its normal read
            correctly the instant the app opens -- before the user has
            rotated anything.
        """
        self.setCameraPosition(distance=45.0, elevation=90.0, azimuth=-90.0)

    # ------------------------------------------------------------------
    # Per-category update helpers
    # ------------------------------------------------------------------

    def _update_plane_points(
        self,
        plane_points: dict[str, np.ndarray],
        coordinate_system: CoordinateSystem | None = None,
    ) -> None:
        """Update the plane point scatter and its labels."""
        if plane_points:
            positions = np.stack(list(plane_points.values()))
        else:
            positions = np.empty((0, 3))
        colors = _make_color_array(COLOR_PLANE_POINT, len(positions))
        self._plane_points_item.setData(pos=positions, color=colors)

        desired = {
            label: (pos, COLOR_PLANE_POINT, f"{label} {format_vector(pos)}")
            for label, pos in plane_points.items()
        }
        self._sync_labels(self._plane_labels, desired)

    def _update_inspection_points(
        self,
        measurements: list[PointMeasurement],
        reference_selected: bool = False,
    ) -> None:
        """Update the inspection point scatter and its labels.

        The distance shown on each label is the perpendicular
        point-to-plane distance by default; once ``reference_selected``
        is ``True`` it switches to the point-to-point distance from the
        chosen reference plane point instead (``distance_to_reference``),
        matching what the left/right panels show in that mode.
        """
        if measurements:
            positions = np.stack([m.world_coordinates for m in measurements])
        else:
            positions = np.empty((0, 3))
        colors = _make_color_array(COLOR_INSPECTION_POINT, len(positions))
        self._inspection_points_item.setData(pos=positions, color=colors)

        desired = {}
        for m in measurements:
            if reference_selected:
                dist_text = f"d={format_number(m.distance_to_reference)}"
            else:
                dist_text = f"d={format_signed_distance(abs(m.distance_to_plane))}"
            desired[m.label] = (
                m.world_coordinates,
                COLOR_INSPECTION_POINT,
                f"{m.label} {format_vector(m.world_coordinates)} {dist_text}",
            )
        self._sync_labels(self._inspection_labels, desired)

    def _update_plane_and_normal(
        self,
        plane_points: dict[str, np.ndarray],
        plane_result: BestFitPlaneResult | None,
        coordinate_system: CoordinateSystem | None,
    ) -> None:
        """Update the fitted plane patch, 2-point line, normal indicator, and origin dot."""
        count = len(plane_points)

        if coordinate_system is not None:
            colors = _make_color_array(COLOR_ORIGIN_POINT, 1)
            self._origin_point_item.setData(
                pos=np.array([coordinate_system.origin]), color=colors
            )
            self._origin_point_item.setVisible(True)
        else:
            colors = _make_color_array(COLOR_ORIGIN_POINT, 0)
            self._origin_point_item.setData(pos=np.empty((0, 3)), color=colors)
            self._origin_point_item.setVisible(False)

        if count < 2:
            self._plane_line_item.setVisible(False)
            self._plane_mesh_item.setVisible(False)
            self._normal_line_item.setVisible(False)
            self._imaginary_point_item.setData(
                pos=np.empty((0, 3)), color=_make_color_array(COLOR_IMAGINARY_POINT, 0)
            )
            return

        if count == 2:
            positions = np.stack(list(plane_points.values()))
            self._plane_line_item.setData(pos=positions)
            self._plane_line_item.setVisible(True)
            self._plane_mesh_item.setVisible(False)
            self._normal_line_item.setVisible(False)
            self._imaginary_point_item.setData(
                pos=np.empty((0, 3)), color=_make_color_array(COLOR_IMAGINARY_POINT, 0)
            )
            return

        # 3 or 4+ points: hide 2-point line segment
        self._plane_line_item.setVisible(False)

        # The imaginary 4th rectangle corner only ever applies to the
        # exact 3-point case (see below); with 4+ real points there is
        # nothing to auto-complete, so clear it here and let the count==3
        # branch below repopulate it when applicable.
        if count != 3:
            self._imaginary_point_item.setData(
                pos=np.empty((0, 3)), color=_make_color_array(COLOR_IMAGINARY_POINT, 0)
            )

        if plane_result is None or coordinate_system is None:
            self._plane_mesh_item.setVisible(False)
            self._normal_line_item.setVisible(False)
            return

        origin = coordinate_system.origin
        x_axis = coordinate_system.x_axis
        y_axis = coordinate_system.y_axis
        normal = coordinate_system.z_axis

        if count == 3:
            # Auto-complete a 4th, IMAGINARY corner so the patch renders as
            # a rectangle (parallelogram) instead of a bare triangle. Given
            # the 3 real corners in insertion order (p0, p1, p2), treating
            # p1 as the shared corner between the two diagonals gives the
            # opposite corner: D = p0 + p2 - p1. This point is purely
            # visual -- it is never added to the point manager and never
            # feeds into the plane fit or any measurement.
            p0, p1, p2 = list(plane_points.values())
            imaginary_point = p0 + p2 - p1
            vertices = np.array([p0, p1, p2, imaginary_point])
            faces = np.array([[0, 1, 2], [0, 2, 3]])
            face_colors = np.array([COLOR_FITTED_PLANE, COLOR_FITTED_PLANE])

            self._imaginary_point_item.setData(
                pos=np.array([imaginary_point]),
                color=_make_color_array(COLOR_IMAGINARY_POINT, 1),
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
            face_colors = np.array([COLOR_FITTED_PLANE, COLOR_FITTED_PLANE])

        mesh = gl.MeshData(vertexes=vertices, faces=faces, faceColors=face_colors)
        self._plane_mesh_item.setMeshData(meshdata=mesh)
        self._plane_mesh_item.setVisible(True)

        self._normal_line_item.setVisible(False)

    def _update_distance_lines(
        self,
        measurements: list[PointMeasurement],
        reference_point: np.ndarray | None = None,
        reference_selected: bool = False,
    ) -> None:
        """Update the inspection-point distance segments.

        Default (no reference selected yet): one perpendicular segment per
        inspection point, from the point straight down to its projection
        on the fitted plane -- unchanged from before.

        Once ``reference_selected`` is ``True``: point-to-point mode --
        a single straight segment from the SELECTED REFERENCE plane point
        to each inspection point (not from every plane point).
        """
        if not measurements:
            self._distance_lines_item.setData(pos=np.empty((0, 3)))
            self._projection_points_item.setData(
                pos=np.empty((0, 3)), color=_make_color_array(COLOR_PROJECTION_POINT, 0)
            )
            return

        if reference_selected and reference_point is not None:
            segment_points = []
            for measurement in measurements:
                segment_points.append(reference_point)
                segment_points.append(measurement.world_coordinates)

            self._distance_lines_item.setData(pos=np.stack(segment_points))
            self._distance_lines_item.setVisible(True)
            # Point-to-point mode has no "projection on plane" concept.
            self._projection_points_item.setData(
                pos=np.empty((0, 3)), color=_make_color_array(COLOR_PROJECTION_POINT, 0)
            )
            return

        segment_points = []
        projections = []
        for measurement in measurements:
            segment_points.append(measurement.world_coordinates)
            segment_points.append(measurement.projection_world)
            projections.append(measurement.projection_world)

        self._distance_lines_item.setData(pos=np.stack(segment_points))
        self._distance_lines_item.setVisible(True)
        proj_arr = np.stack(projections)
        self._projection_points_item.setData(
            pos=proj_arr, color=_make_color_array(COLOR_PROJECTION_POINT, len(proj_arr))
        )

    # ------------------------------------------------------------------
    # Label lifecycle management
    # ------------------------------------------------------------------

    def _sync_labels(
        self,
        existing: dict[str, gl.GLTextItem],
        desired: dict[str, tuple[np.ndarray, tuple[float, float, float, float], str]],
    ) -> None:
        """Reconcile a label dict with the current set of points.

        Parameters
        ----------
        existing:
            The widget's current ``{label: GLTextItem}`` dict for this
            point category (mutated in place).
        desired:
            The point labels that SHOULD have a text item right now,
            mapped to their ``(position, color, text)``. ``text`` is the
            string actually drawn (e.g. ``"P0 (5.0, 5.0, 8.0) d=+7.8"``) --
            kept separate from the dict key so results (coordinate,
            distance) can be rendered directly on the graph instead of a
            separate results panel, while reconciliation still keys off
            the stable point label.

        Behaviour
        ---------
        * A label present in ``desired`` but not ``existing`` gets a new
          :class:`~pyqtgraph.opengl.GLTextItem`, created once and added to
          the view.
        * A label present in both gets its existing item's position and
          text updated via ``setData`` -- never recreated.
        * A label present in ``existing`` but not ``desired`` (the point
          was removed) has its item removed from the view and dict.
        """
        # Remove labels for points that no longer exist.
        for stale_label in list(existing.keys() - desired.keys()):
            self.removeItem(existing[stale_label])
            del existing[stale_label]

        # Add or update labels for current points.
        for label, (position, color, text) in desired.items():
            text_position = position + np.array([0.0, 0.0, 0.4])
            if label in existing:
                existing[label].setData(pos=text_position, text=text)
            else:
                item = gl.GLTextItem(
                    pos=text_position, text=text, color=_to_qcolor(color), font=_LABEL_FONT
                )
                self.addItem(item)
                existing[label] = item


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _to_qcolor(rgba: tuple[float, float, float, float]) -> QColor:
    """Convert a ``config.py``-style 0-1 float RGBA tuple to a QColor."""
    r, g, b, a = rgba
    color = QColor()
    color.setRgbF(r, g, b, a)
    return color


def _make_color_array(color: tuple[float, float, float, float], count: int) -> np.ndarray:
    """Return an (N, 4) float32 numpy array of RGBA colors for GLScatterPlotItem VBO compatibility."""
    if count <= 0:
        return np.empty((0, 4), dtype=np.float32)
    return np.tile(np.array(color, dtype=np.float32), (count, 1))