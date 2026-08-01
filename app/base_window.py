"""
app/base_window.py
===================
Shared window chrome (title, sizing, stylesheet, status bar skeleton) and
visualization toolbar contract for module windows launched from the landing page.

Module Window Standard Contract:
--------------------------------
Every top-level module window (e.g. ``MainWindow``, ``CircularityWindow``) should:
  1. Subclass :class:`BaseModuleWindow`.
  2. Instantiate a 3D viewport subclassing :class:`graphics.base_gl_widget.BaseGLWidget`.
  3. Call ``self._init_chrome(module_title)`` after ``super().__init__()``.
  4. Call ``self._init_toolbar(gl_widget, toggles, extra_widget=...)`` to automatically
     create, wire, and attach the visualization toolbar.
"""

from __future__ import annotations

from typing import Sequence

from PyQt5.QtWidgets import QLabel, QMainWindow, QWidget

from config import (
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from config.colors import set_active_theme
from ui.base_toolbar import build_module_toolbar
from ui.styles import get_app_stylesheet, get_statusbar_style, get_toolbar_style


class BaseModuleWindow(QMainWindow):
    """Common chrome and toolbar scaffolding for top-level module windows."""

    def _init_chrome(self, module_title: str) -> None:
        """Initialize window title, default sizing, application stylesheet, and status bar skeleton."""
        self.module_title = module_title
        self.setWindowTitle(f"Industrial Geometry Measurement System - {module_title}")
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setStyleSheet(get_app_stylesheet())

        bar = self.statusBar()
        bar.setStyleSheet(get_statusbar_style())
        self._status_module_label = QLabel(f"Module: {module_title}")
        self._status_module_label.setStyleSheet("color: #4f8ff7; font-weight: bold; padding: 0 8px;")
        bar.addWidget(self._status_module_label)

    def _init_toolbar(
        self,
        gl_widget: QWidget,
        toggles: Sequence[tuple[str, str, str]],
        *,
        extra_widget: QWidget | None = None,
    ) -> None:
        """Build, wire, and attach the standard module visualization toolbar."""
        self._toolbar, self._theme_action = build_module_toolbar(
            self,
            gl_widget,
            toggles,
            extra_widget=extra_widget,
            on_theme_toggle=self.set_theme,
        )
        self.addToolBar(self._toolbar)

    def set_theme(self, theme_name: str) -> None:
        """Switch active theme ('dark' or 'light') and restyle window chrome and viewport."""
        set_active_theme(theme_name)
        self.setStyleSheet(get_app_stylesheet())
        self.statusBar().setStyleSheet(get_statusbar_style())
        if hasattr(self, "_toolbar") and self._toolbar is not None:
            self._toolbar.setStyleSheet(get_toolbar_style())
        if hasattr(self, "_central_panel") and hasattr(self._central_panel, "restyle"):
            self._central_panel.restyle()
        if hasattr(self, "_gl_widget") and hasattr(self._gl_widget, "apply_theme"):
            self._gl_widget.apply_theme()
        if hasattr(self, "_theme_action") and self._theme_action is not None:
            self._theme_action.blockSignals(True)
            self._theme_action.setChecked(theme_name == "light")
            self._theme_action.blockSignals(False)
