"""
ui/plane_angle_panel.py
=======================
Panel displaying the fitted plane's inclination angles (tilt along X and Y axes).
"""

from __future__ import annotations

from PyQt5.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from ui.styles import get_group_style, get_ui_color
from utils import format_number


class PlaneAnglePanel(QGroupBox):
    """Group box displaying the fitted plane's X-axis and Y-axis inclination angles."""

    _NO_FIT_TEXT = "Add at least 3 plane points to see plane inclination."

    def __init__(self) -> None:
        super().__init__("Plane Inclination")
        self.setStyleSheet(get_group_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(4)

        self._label = QLabel(self._NO_FIT_TEXT)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;"
        )
        layout.addWidget(self._label)

        self._last_x: float | None = None
        self._last_y: float | None = None

    def restyle(self) -> None:
        """Re-apply active theme styles."""
        self.setStyleSheet(get_group_style())
        if self._last_x is None or self._last_y is None:
            self._label.setStyleSheet(f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;")
        else:
            self._label.setStyleSheet(
                f"color: {get_ui_color('TEXT_PRIMARY')}; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;"
            )

    def display(self, angle_x_deg: float | None, angle_y_deg: float | None) -> None:
        """Update displayed plane inclination angles."""
        self._last_x = angle_x_deg
        self._last_y = angle_y_deg
        if angle_x_deg is None or angle_y_deg is None:
            self._label.setText(self._NO_FIT_TEXT)
            self._label.setStyleSheet(f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;")
            return

        self._label.setStyleSheet(
            f"color: {get_ui_color('TEXT_PRIMARY')}; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;"
        )
        self._label.setText(
            f"X-axis tilt: {format_number(angle_x_deg)}\u00b0    "
            f"Y-axis tilt: {format_number(angle_y_deg)}\u00b0"
        )
