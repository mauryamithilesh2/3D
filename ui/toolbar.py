"""
ui/toolbar.py
=============
Main window toolbar: Show/Hide toggles for visual scene layers, ghost mode,
Reset View action, and Dark/Light Theme toggle -- wired to :class:`~graphics.gl_widget.GL3DWidget`
and main window theme handler.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QAction, QToolBar

from config.colors import get_active_theme
from ui.styles import get_toolbar_style, TOOLBAR_STYLE

#: (visibility key, action label, tooltip)
_TOGGLES: tuple[tuple[str, str, str], ...] = (
    ("plane", "Plane", "Show/Hide the fitted plane patch"),
    ("global_axes", "Global Axes", "Show/Hide the world X/Y/Z axes"),
    ("local_axes", "Local Axes", "Show/Hide the local (reference point) X/Y/Z frame"),
    ("normal", "Normal", "Show/Hide the plane normal vector arrow"),
    ("projection", "Projection", "Show/Hide the on-plane projection point marker"),
    ("dotted", "Dotted Lines", "Show/Hide the CAD-style dashed construction lines"),
    ("labels", "Labels", "Show/Hide point and axis text labels"),
    ("grid", "Grid", "Show/Hide the reference floor grid"),
)


def build_main_toolbar(main_window) -> QToolBar:
    """Build and return the fully-wired main visualization toolbar."""
    toolbar = QToolBar("Visualization", main_window)
    toolbar.setMovable(False)
    toolbar.setStyleSheet(get_toolbar_style())
    toolbar.setIconSize(toolbar.iconSize())

    gl_widget = main_window._gl_widget

    for key, label, tooltip in _TOGGLES:
        action = QAction(label, main_window)
        action.setCheckable(True)
        action.setChecked(True)
        action.setToolTip(tooltip)
        action.toggled.connect(lambda checked, k=key: gl_widget.set_visibility(k, checked))
        toolbar.addAction(action)

    toolbar.addSeparator()

    ghost_action = QAction("Ghost History", main_window)
    ghost_action.setCheckable(True)
    ghost_action.setChecked(False)
    ghost_action.setToolTip("Show faint overlays of previous plane-fit positions")
    ghost_action.toggled.connect(gl_widget.set_ghost_mode)
    toolbar.addAction(ghost_action)

    toolbar.addSeparator()

    reset_action = QAction("Reset View", main_window)
    reset_action.setToolTip("Reset the camera to the default top-down view")
    reset_action.triggered.connect(gl_widget.reset_camera)
    toolbar.addAction(reset_action)

    toolbar.addSeparator()

    current_theme = get_active_theme()
    theme_action = QAction("Light Theme", main_window)
    theme_action.setCheckable(True)
    theme_action.setChecked(current_theme == "light")
    theme_action.setToolTip("Toggle between Dark and Light themes")

    def _on_theme_toggled(checked: bool) -> None:
        target_theme = "light" if checked else "dark"
        main_window.set_theme(target_theme)

    theme_action.toggled.connect(_on_theme_toggled)
    toolbar.addAction(theme_action)
    main_window._theme_action = theme_action

    return toolbar
