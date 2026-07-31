"""
graphics/gl_widget.py
=====================
The interactive 3-D OpenGL viewport shell class (GL3DWidget), built on ``pyqtgraph.opengl``.
Delegates static/dynamic scene construction, point/mesh rendering, and label updates to graphics
submodules, and layers a generic smooth-transition animator plus show/hide toggles, ghost/history
mode, and a fixed-corner orientation triad on top of them.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl

from config import ANIMATION_DURATION_MS
from config.colors import get_color
from core.best_fit_plane import BestFitPlaneResult
from core.coordinate_system import CoordinateSystem
from core.measurement import PointMeasurement
from graphics.animation import SceneAnimator
from graphics.distance_renderer import _update_distance_lines
from graphics.dotted_line_renderer import _update_dotted_lines
from graphics.frame_renderer import _update_local_axes, _update_normal_arrow
from graphics.ghost_renderer import _render_ghost_history
from graphics.gl_utils import _lerp, _to_qcolor
from graphics.label_manager import _sync_labels
from graphics.orientation_widget import OrientationTriadWidget
from graphics.plane_renderer import _update_plane_and_normal
from graphics.point_renderer import _update_inspection_points, _update_plane_points
from graphics.scene_dynamic import _build_dynamic_items
from graphics.scene_static import _build_static_items

#: Scatter items (attribute name -> None) whose ``.pos`` array is smoothly
#: interpolated between refreshes, when shape and visibility are stable.
_ANIMATABLE_SCATTER_ITEMS = (
    "_plane_points_item",
    "_inspection_points_item",
    "_origin_point_item",
    "_projection_points_item",
)

#: Line items animated the same way.
_ANIMATABLE_LINE_ITEMS = (
    "_normal_line_item",
    "_local_axis_item",
    "_distance_lines_item",
    "_plane_points_cross_item",
    "_inspection_points_cross_item",
)


class GL3DWidget(gl.GLViewWidget):
    """The persistent 3-D scene showing the plane fit and its measurements.

    This widget has no knowledge of PyQt line-edits or the point manager --
    it only ever receives already-computed geometry through
    :meth:`update_scene`. Every GL item is created exactly once in
    ``_build_static_items`` / ``_build_dynamic_items`` and only ever
    refreshed afterwards via ``setData`` / ``setMeshData`` -- directly or,
    for a polished feel, through a handful of smoothly-animated in-between
    frames driven by :class:`~graphics.animation.SceneAnimator`.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._apply_default_camera()
        self.setBackgroundColor(_to_qcolor(get_color("COLOR_VIEWPORT_BG")))

        # Dynamic per-label text items, keyed by point label.
        self._plane_labels: dict[str, gl.GLTextItem] = {}
        self._inspection_labels: dict[str, gl.GLTextItem] = {}

        # Ghost / history mode state (populated by graphics.ghost_renderer).
        self._ghost_history: list[np.ndarray] = []
        self._ghost_mode_enabled: bool = False

        # Show/Hide toolbar toggle state -- an AND-mask applied after every
        # refresh so re-enabling a toggle simply re-runs the last known
        # scene update instead of needing bespoke "show" logic per item.
        self._visibility: dict[str, bool] = {
            "plane": True,
            "global_axes": True,
            "local_axes": True,
            "normal": True,
            "projection": True,
            "dotted": True,
            "labels": True,
            "grid": True,
        }

        self._last_update_args: tuple | None = None
        self._last_update_kwargs: dict | None = None
        self._animator = SceneAnimator(duration_ms=ANIMATION_DURATION_MS, parent=self)

        self._build_static_items()
        self._build_dynamic_items()

        self._orientation_widget = OrientationTriadWidget(self)
        self._orientation_widget.reposition()

    # ------------------------------------------------------------------
    # One-time construction delegation
    # ------------------------------------------------------------------

    def _build_static_items(self) -> None:
        """Create grid and world axes."""
        _build_static_items(self)

    def _build_dynamic_items(self) -> None:
        """Create dynamic OpenGL items."""
        _build_dynamic_items(self)

    def apply_theme(self) -> None:
        """Rebuild static viewport items and update background color for active theme."""
        self.setBackgroundColor(_to_qcolor(get_color("COLOR_VIEWPORT_BG")))

        if hasattr(self, "_grid") and self._grid in self.items:
            self.removeItem(self._grid)
        for attr in ("_axis_x", "_axis_y", "_axis_z"):
            if hasattr(self, attr):
                item = getattr(self, attr)
                if item in self.items:
                    self.removeItem(item)
        if hasattr(self, "_axis_label_items"):
            for item in self._axis_label_items:
                if item in self.items:
                    self.removeItem(item)

        self._build_static_items()

        if self._last_update_args is not None and self._last_update_kwargs is not None:
            self.update_scene(*self._last_update_args, **self._last_update_kwargs, animate=False)
        else:
            self._apply_visibility_overrides()

        if hasattr(self, "_orientation_widget"):
            self._orientation_widget.update()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if hasattr(self, "_orientation_widget"):
            self._orientation_widget.reposition()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_scene(
        self,
        plane_points: dict[str, np.ndarray],
        inspection_measurements: list[PointMeasurement],
        plane_result: BestFitPlaneResult | None,
        coordinate_system: CoordinateSystem | None,
        reference_selected: bool = False,
        reference_point: np.ndarray | None = None,
        inspection_points: list[tuple[str, np.ndarray]] | None = None,
        reference_label: str | None = None,
        animate: bool = True,
    ) -> None:
        """Refresh every dynamic item in the scene from current geometry."""
        self._last_update_args = (
            plane_points,
            inspection_measurements,
            plane_result,
            coordinate_system,
        )
        self._last_update_kwargs = {
            "reference_selected": reference_selected,
            "reference_point": reference_point,
            "inspection_points": inspection_points,
            "reference_label": reference_label,
        }

        before = self._snapshot_animatable() if animate else None

        self._update_plane_points(plane_points, coordinate_system, reference_label)
        self._update_inspection_points(inspection_measurements, reference_selected)
        self._update_plane_and_normal(plane_points, plane_result, coordinate_system)
        self._update_local_axes(coordinate_system)
        self._update_normal_arrow(plane_result, coordinate_system)
        self._update_distance_lines(inspection_measurements, reference_point, reference_selected)
        self._update_dotted_lines(
            inspection_points or [],
            inspection_measurements,
            coordinate_system,
            reference_selected=reference_selected,
            reference_point=reference_point,
        )

        self._apply_visibility_overrides()

        if animate:
            after = self._snapshot_animatable()
            self._animate_transition(before, after)

    def reset_camera(self) -> None:
        """Restore default camera position."""
        self._apply_default_camera()

    def _apply_default_camera(self) -> None:
        """Set standard camera viewing angle (elev=90, azim=-90)."""
        self.setCameraPosition(distance=45.0, elevation=90.0, azimuth=-90.0)

    # ------------------------------------------------------------------
    # Show / hide toolbar toggles
    # ------------------------------------------------------------------

    def set_visibility(self, key: str, visible: bool) -> None:
        """Toggle one visual layer on/off (toolbar action handler)."""
        if key not in self._visibility:
            return
        self._visibility[key] = visible
        if self._last_update_args is not None:
            # Re-run the last known scene state so natural (data-driven)
            # visibility recalculates before the override mask is applied --
            # this is what lets re-enabling a toggle correctly show items
            # again instead of only ever being able to hide them.
            self.update_scene(*self._last_update_args, **self._last_update_kwargs, animate=False)
        else:
            self._apply_visibility_overrides()

    def set_ghost_mode(self, enabled: bool) -> None:
        """Enable/disable the optional plane history ghosting overlay."""
        self._ghost_mode_enabled = enabled
        _render_ghost_history(self)

    def _apply_visibility_overrides(self) -> None:
        """Apply visibility state to visual scene items."""
        v = self._visibility

        if not v["plane"]:
            self._plane_mesh_item.setVisible(False)
            self._plane_line_item.setVisible(False)

        if v["global_axes"]:
            self._axis_x.setVisible(True)
            self._axis_y.setVisible(True)
            self._axis_z.setVisible(True)
        else:
            self._axis_x.setVisible(False)
            self._axis_y.setVisible(False)
            self._axis_z.setVisible(False)

        show_axis_labels = v["global_axes"] and v["labels"]
        for item in self._axis_label_items:
            item.setVisible(show_axis_labels)

        if not v["local_axes"]:
            self._local_axis_item.setVisible(False)
            for item in self._local_axis_label_items.values():
                item.setVisible(False)

        if not v["normal"]:
            self._normal_line_item.setVisible(False)
            self._normal_head_item.setVisible(False)

        if not v["projection"]:
            self._projection_points_item.setVisible(False)

        if not v["dotted"]:
            self._world_dotted_item.setVisible(False)
            self._local_dotted_item.setVisible(False)

        if not v["labels"]:
            for item in self._plane_labels.values():
                item.setVisible(False)
            for item in self._inspection_labels.values():
                item.setVisible(False)
            for item in self._local_axis_label_items.values():
                item.setVisible(False)

        self._grid.setVisible(v["grid"])

    # ------------------------------------------------------------------
    # Smooth-transition animation (plane rotation, local axes, normal
    # vector, point movement, reference switching -- 200-300 ms eased)
    # ------------------------------------------------------------------

    def _snapshot_animatable(self) -> dict:
        """Capture the currently-displayed arrays of every animatable item."""
        snap: dict = {}
        for name in _ANIMATABLE_SCATTER_ITEMS + _ANIMATABLE_LINE_ITEMS:
            item = getattr(self, name)
            visible = item.visible()
            pos = getattr(item, "pos", None)
            snap[name] = (np.array(pos, dtype=np.float64, copy=True), visible) if (
                visible and pos is not None and len(pos) > 0
            ) else (None, visible)

        mesh_snapshot = None
        if self._plane_mesh_item.visible():
            meshdata = self._plane_mesh_item.opts.get("meshdata")
            if meshdata is not None:
                vertices = meshdata.vertexes()
                if vertices is not None and len(vertices) > 0:
                    mesh_snapshot = (
                        np.array(vertices, dtype=np.float64, copy=True),
                        np.array(meshdata.faces(), copy=True),
                        None if meshdata.faceColors() is None else np.array(meshdata.faceColors(), copy=True),
                    )
        snap["_plane_mesh_item"] = mesh_snapshot
        return snap

    def _animate_transition(self, before: dict, after: dict) -> None:
        """Start (or restart) the shared animator interpolating ``before -> after``."""
        pairs = {}
        for name in _ANIMATABLE_SCATTER_ITEMS + _ANIMATABLE_LINE_ITEMS:
            before_pos, before_visible = before.get(name, (None, False))
            after_pos, after_visible = after.get(name, (None, False))
            if (
                before_pos is not None
                and after_pos is not None
                and before_visible
                and after_visible
                and before_pos.shape == after_pos.shape
            ):
                pairs[name] = (before_pos, after_pos)

        mesh_pair = None
        before_mesh = before.get("_plane_mesh_item")
        after_mesh = after.get("_plane_mesh_item")
        if before_mesh is not None and after_mesh is not None:
            before_v, _, _ = before_mesh
            after_v, after_faces, after_colors = after_mesh
            if before_v.shape == after_v.shape:
                mesh_pair = (before_v, after_v, after_faces, after_colors)

        if not pairs and mesh_pair is None:
            return  # Nothing eligible to animate -- final state is already applied.

        def apply(t: float) -> None:
            for name, (start, end) in pairs.items():
                item = getattr(self, name)
                interpolated = _lerp(start, end, t)
                item.setData(pos=interpolated)
            if mesh_pair is not None:
                start_v, end_v, faces, colors = mesh_pair
                interpolated_v = _lerp(start_v, end_v, t)
                mesh = gl.MeshData(vertexes=interpolated_v, faces=faces, faceColors=colors)
                self._plane_mesh_item.setMeshData(meshdata=mesh)

        self._animator.start(apply)

    # ------------------------------------------------------------------
    # Rendering delegates
    # ------------------------------------------------------------------

    def _update_plane_points(
        self,
        plane_points: dict[str, np.ndarray],
        coordinate_system: CoordinateSystem | None = None,
        reference_label: str | None = None,
    ) -> None:
        _update_plane_points(self, plane_points, coordinate_system, reference_label)

    def _update_inspection_points(
        self,
        measurements: list[PointMeasurement],
        reference_selected: bool = False,
    ) -> None:
        _update_inspection_points(self, measurements, reference_selected)

    def _update_plane_and_normal(
        self,
        plane_points: dict[str, np.ndarray],
        plane_result: BestFitPlaneResult | None,
        coordinate_system: CoordinateSystem | None,
    ) -> None:
        _update_plane_and_normal(self, plane_points, plane_result, coordinate_system)

    def _update_local_axes(self, coordinate_system: CoordinateSystem | None) -> None:
        _update_local_axes(self, coordinate_system)

    def _update_normal_arrow(
        self,
        plane_result: BestFitPlaneResult | None,
        coordinate_system: CoordinateSystem | None,
    ) -> None:
        _update_normal_arrow(self, plane_result, coordinate_system)

    def _update_distance_lines(
        self,
        measurements: list[PointMeasurement],
        reference_point: np.ndarray | None = None,
        reference_selected: bool = False,
    ) -> None:
        _update_distance_lines(self, measurements, reference_point, reference_selected)

    def _update_dotted_lines(
        self,
        inspection_points: list[tuple[str, np.ndarray]],
        measurements: list[PointMeasurement],
        coordinate_system: CoordinateSystem | None,
        reference_selected: bool = False,
        reference_point: np.ndarray | None = None,
    ) -> None:
        _update_dotted_lines(
            self,
            inspection_points,
            measurements,
            coordinate_system,
            reference_selected=reference_selected,
            reference_point=reference_point,
        )

    def _sync_labels(
        self,
        existing: dict[str, gl.GLTextItem],
        desired: dict[str, tuple[np.ndarray, tuple[float, float, float, float], str]],
    ) -> None:
        _sync_labels(self, existing, desired)
