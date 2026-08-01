"""
graphics/base_gl_widget.py
==========================
Base 3D OpenGL viewport class (BaseGLWidget) built on ``pyqtgraph.opengl``.
Encapsulates generic viewport scaffolding: camera positioning, theme-aware background,
static grid and world axes, corner orientation triad, smooth-transition animator,
resize handler, and basic layer visibility overrides.
"""

from __future__ import annotations

import pyqtgraph.opengl as gl

from config import ANIMATION_DURATION_MS
from config.colors import get_color
from graphics.animation import SceneAnimator
from graphics.gl_utils import _to_qcolor
from graphics.orientation_widget import OrientationTriadWidget
from graphics.scene_static import _build_static_items


class BaseGLWidget(gl.GLViewWidget):
    """Generic 3-D viewport scaffolding shared across module viewports."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._apply_default_camera()
        self.setBackgroundColor(_to_qcolor(get_color("COLOR_VIEWPORT_BG")))

        # Show/Hide toolbar toggle state -- base generic keys
        self._visibility: dict[str, bool] = {
            "grid": True,
            "global_axes": True,
            "labels": True,
        }

        self._last_update_args: tuple | None = None
        self._last_update_kwargs: dict | None = None
        self._animator = SceneAnimator(duration_ms=ANIMATION_DURATION_MS, parent=self)

        self._build_static_items()

        self._orientation_widget = OrientationTriadWidget(self)
        self._orientation_widget.reposition()

    def _build_static_items(self) -> None:
        """Create grid and world axes via shared scene static builder."""
        _build_static_items(self)

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

        if hasattr(self, "_orientation_widget"):
            self._orientation_widget.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if hasattr(self, "_orientation_widget"):
            self._orientation_widget.reposition()

    def reset_camera(self) -> None:
        """Restore default camera position."""
        self._apply_default_camera()

    def _apply_default_camera(self) -> None:
        """Set standard camera viewing angle (elev=90, azim=-90). Subclasses may override."""
        self.setCameraPosition(distance=45.0, elevation=90.0, azimuth=-90.0)

    def set_visibility(self, key: str, visible: bool) -> None:
        """Toggle one visual layer on/off (toolbar action handler)."""
        if key not in self._visibility:
            return
        self._visibility[key] = visible
        if self._last_update_args is not None:
            kwargs = self._last_update_kwargs or {}
            if hasattr(self, "update_scene"):
                self.update_scene(*self._last_update_args, **kwargs, animate=False)
        else:
            self._apply_visibility_overrides()

    def _apply_visibility_overrides(self) -> None:
        """Apply generic visibility state to visual scene items."""
        v = self._visibility

        if hasattr(self, "_grid") and self._grid is not None:
            self._grid.setVisible(v.get("grid", True))

        show_axes = v.get("global_axes", True)
        for attr in ("_axis_x", "_axis_y", "_axis_z"):
            if hasattr(self, attr):
                item = getattr(self, attr)
                if item is not None:
                    item.setVisible(show_axes)

        show_axis_labels = show_axes and v.get("labels", True)
        if hasattr(self, "_axis_label_items"):
            for item in self._axis_label_items:
                if item is not None:
                    item.setVisible(show_axis_labels)
