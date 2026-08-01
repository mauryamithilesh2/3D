"""
ui/base_toolbar.py
==================
Generic toolbar factory for 3D measurement modules.
Builds visual layer toggle actions, Reset View, Theme toggle, and optional custom widgets
wired to any module window and viewport widget.
"""

from __future__ import annotations

from typing import Callable, Sequence

from PyQt5.QtWidgets import QAction, QToolBar, QWidget

from config.colors import get_active_theme
from ui.styles import get_toolbar_style


def build_module_toolbar(
    window: QWidget,
    gl_widget: QWidget,
    toggles: Sequence[tuple[str, str, str]],
    *,
    extra_widget: QWidget | None = None,
    on_theme_toggle: Callable[[bool], None] | None = None,
) -> tuple[QToolBar, QAction | None]:
    """Build a reusable visualization toolbar for any top-level module window.

    :param window: Parent window hosting the toolbar.
    :param gl_widget: The module's OpenGL viewport widget.
    :param toggles: Sequence of ``(visibility_key, label, tooltip)`` tuples.
    :param extra_widget: Optional custom widget to embed in the toolbar (e.g. AxisAngleWidget).
    :param on_theme_toggle: Optional callback receiving boolean checked state when theme action toggles.
    :return: Tuple of ``(toolbar, theme_action)``.
    """
    toolbar = QToolBar("Visualization", window)
    toolbar.setMovable(False)
    toolbar.setStyleSheet(get_toolbar_style())
    toolbar.setIconSize(toolbar.iconSize())

    for key, label, tooltip in toggles:
        action = QAction(label, window)
        action.setCheckable(True)
        action.setChecked(True)
        action.setToolTip(tooltip)
        action.toggled.connect(lambda checked, k=key: gl_widget.set_visibility(k, checked))
        toolbar.addAction(action)

    if extra_widget is not None:
        toolbar.addSeparator()
        toolbar.addWidget(extra_widget)

    if hasattr(gl_widget, "set_ghost_mode") and callable(getattr(gl_widget, "set_ghost_mode")):
        toolbar.addSeparator()
        ghost_action = QAction("Ghost History", window)
        ghost_action.setCheckable(True)
        ghost_action.setChecked(False)
        ghost_action.setToolTip("Show faint overlays of previous plane-fit positions")
        ghost_action.toggled.connect(gl_widget.set_ghost_mode)
        toolbar.addAction(ghost_action)

    if hasattr(gl_widget, "reset_camera") and callable(getattr(gl_widget, "reset_camera")):
        toolbar.addSeparator()
        reset_action = QAction("Reset View", window)
        reset_action.setToolTip("Reset the camera to the default top-down view")
        reset_action.triggered.connect(gl_widget.reset_camera)
        toolbar.addAction(reset_action)

    theme_action: QAction | None = None
    if on_theme_toggle is not None:
        toolbar.addSeparator()
        current_theme = get_active_theme()
        theme_action = QAction("Light Theme", window)
        theme_action.setCheckable(True)
        theme_action.setChecked(current_theme == "light")
        theme_action.setToolTip("Toggle between Dark and Light themes")
        theme_action.toggled.connect(on_theme_toggle)
        toolbar.addAction(theme_action)

    return toolbar, theme_action
