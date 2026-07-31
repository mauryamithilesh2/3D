"""
ui/toolbar.py
=============
Main window toolbar: Show/Hide toggles for visual scene layers, ghost mode,
Reset View action, and Dark/Light Theme toggle -- wired to :class:`~graphics.gl_widget.GL3DWidget`
and main window theme handler.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolBar,
    QToolButton,
    QWidget,
)

from config.colors import get_active_theme
from ui.styles import get_toolbar_style, get_ui_color
from utils import format_number

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


class AxisAngleWidget(QWidget):
    """Toolbar control: pick an axis (X or Y) and see the fitted plane's
    inclination angle relative to that axis, kept in sync with the existing
    ``BestFitPlaneResult.angle_x_deg()`` / ``.angle_y_deg()`` calculations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        self._button = QToolButton(self)
        self._button.setText("Angles")
        self._button.setToolTip("Angle between the fitted plane and a chosen world axis")
        self._button.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(self._button)
        group = QActionGroup(menu)
        group.setExclusive(True)

        self._action_x = QAction("X Axis", menu, checkable=True)
        self._action_y = QAction("Y Axis", menu, checkable=True)
        self._action_x.setChecked(True)
        for action in (self._action_x, self._action_y):
            group.addAction(action)
            menu.addAction(action)
            action.triggered.connect(self._refresh_label)
        self._button.setMenu(menu)

        self._value_label = QLabel("X: --\u00b0")
        self._value_label.setStyleSheet(
            f"color: {get_ui_color('TEXT_PRIMARY')}; font-weight: 600; padding: 0 4px;"
        )

        layout.addWidget(self._button)
        layout.addWidget(self._value_label)

        self._angle_x: float | None = None
        self._angle_y: float | None = None

    def display(self, angle_x_deg: float | None, angle_y_deg: float | None) -> None:
        """Update the cached plane inclination angles and refresh the label."""
        self._angle_x = angle_x_deg
        self._angle_y = angle_y_deg
        self._refresh_label()

    def restyle(self) -> None:
        """Re-apply active theme styles."""
        self._value_label.setStyleSheet(
            f"color: {get_ui_color('TEXT_PRIMARY')}; font-weight: 600; padding: 0 4px;"
        )

    def _refresh_label(self) -> None:
        axis_name = "X" if self._action_x.isChecked() else "Y"
        angle = self._angle_x if self._action_x.isChecked() else self._angle_y
        if angle is None:
            self._value_label.setText(f"{axis_name}: --\u00b0")
        else:
            self._value_label.setText(f"{axis_name}: {format_number(angle)}\u00b0")


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

    axis_angle_widget = AxisAngleWidget(main_window)
    toolbar.addWidget(axis_angle_widget)
    main_window._axis_angle_widget = axis_angle_widget

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
