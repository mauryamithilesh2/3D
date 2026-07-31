"""
ui/edge_axis_selector.py
=========================
Mode toggle letting the operator override the plane's default
world-anchored local X/Y axes, reusing the SAME point already chosen in
"Reference Selection" above it -- no separate point picker of its own.

When enabled, the app automatically checks the line from that reference
point to every other plane point, picks whichever one best aligns with a
global axis, and uses it as that axis. There is no manual second-point
choice and no manual X/Y choice.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout

from ui.styles import get_combo_style, get_group_style, get_ui_color


class EdgeAxisSelector(QGroupBox):
    """Mode toggle for the local-axis override, built on top of whichever
    point is currently chosen in "Reference Selection".

    Emits ``changed`` whenever the mode changes, so the main window can
    recompute. When mode is "Auto (World-Anchored)" -- the default --
    :meth:`is_side_mode` returns ``False`` and the plane's local axes
    behave exactly as before (unchanged).

    The main window calls :meth:`set_assigned_axis` after each recompute to
    reflect back which adjacent point and axis were automatically chosen
    (or ``(None, None)`` when no override is active / it could not be
    applied), so the operator gets feedback without picking a second point
    or X/Y themselves.
    """

    changed = pyqtSignal()

    _AUTO_MODE = "Auto (World-Anchored)"
    _SIDE_MODE = "Use Side As Axis"

    def __init__(self) -> None:
        super().__init__("Local Axis Override")
        self.setStyleSheet(get_group_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(4)

        self._hint = QLabel(
            "Optional: reuses the point chosen above in \u201cReference "
            "Selection\u201d. The app automatically checks the line from it "
            "to every other plane point, uses whichever one is closest to a "
            "global axis, and assigns it as local X or Y."
        )
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {get_ui_color('TEXT_SECONDARY')}; font-size: 11px;")
        layout.addWidget(self._hint)

        self._mode_combo = QComboBox()
        self._mode_combo.setStyleSheet(get_combo_style())
        self._mode_combo.addItems([self._AUTO_MODE, self._SIDE_MODE])
        layout.addWidget(self._mode_combo)

        self._axis_combo = QComboBox()
        self._axis_combo.setStyleSheet(get_combo_style())
        self._axis_combo.addItems(["Local X", "Local Y"])
        self._axis_combo.setVisible(False)
        layout.addWidget(self._axis_combo)

        self._assigned_label = QLabel("")

        self._assigned_label.setWordWrap(True)
        self._assigned_label.setStyleSheet(
            f"color: {get_ui_color('ACCENT_HOVER')}; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self._assigned_label)

        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._axis_combo.currentTextChanged.connect(lambda _text: self.changed.emit())
    def restyle(self) -> None:
        """Re-apply active theme styles."""
        self.setStyleSheet(get_group_style())
        self._hint.setStyleSheet(f"color: {get_ui_color('TEXT_SECONDARY')}; font-size: 11px;")
        self._assigned_label.setStyleSheet(
            f"color: {get_ui_color('ACCENT_HOVER')}; font-size: 11px; font-weight: 600;"
        )
        self._mode_combo.setStyleSheet(get_combo_style())
        self._axis_combo.setStyleSheet(get_combo_style())

    def is_side_mode(self) -> bool:
        """Whether "Use Side As Axis" is currently selected."""
        return self._mode_combo.currentText() == self._SIDE_MODE

    def selected_axis(self) -> str:
        """Which axis ('x' or 'y') the operator picked for the 1st->2nd
        plane point line to become. Only meaningful when :meth:`is_side_mode`
        is ``True``."""
        return "x" if self._axis_combo.currentText() == "Local X" else "y"

    def set_assigned_axis(self, axis: str | None, adjacent_label: str | None) -> None:
        """Update the feedback label with which points and axis are
        assigned. Pass ``(None, None)`` when no override is active (Auto
        mode, fewer than 2 plane points, or it could not be applied to the
        current plane fit)."""
        if axis is None or adjacent_label is None:
            self._assigned_label.setText("")
        else:
            axis_name = "Local X" if axis == "x" else "Local Y"
            self._assigned_label.setText(
                f"\u2192 {adjacent_label} assigned as {axis_name}."
            )

    def _on_mode_changed(self, mode: str) -> None:
        self._axis_combo.setVisible(mode == self._SIDE_MODE)
        if mode != self._SIDE_MODE:
            self.set_assigned_axis(None, None)
        self.changed.emit()
