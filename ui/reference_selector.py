"""
ui/reference_selector.py
========================
Dropdown widget for selecting local coordinate system origin reference point.
"""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout

from ui.styles import get_combo_style, get_group_style, get_ui_color, TEXT_SECONDARY, _COMBO_STYLE, _GROUP_STYLE


class ReferenceSelector(QGroupBox):
    """Dropdown choosing the local coordinate system's origin."""

    reference_changed = pyqtSignal(str)

    _PLACEHOLDER_LABEL = "-- Select Reference Point --"

    def __init__(self, get_plane_labels: Callable[[], list[str]], changed_signal) -> None:
        super().__init__("Reference Selection")
        self.setStyleSheet(get_group_style())
        self._get_plane_labels = get_plane_labels

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)

        self._hint = QLabel("Origin of the local plane coordinate system:")
        self._hint.setStyleSheet(f"color: {get_ui_color('TEXT_SECONDARY')}; font-size: 11px;")
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        self._combo = QComboBox()
        self._combo.setStyleSheet(get_combo_style())
        layout.addWidget(self._combo)

        changed_signal.connect(self._refresh_items)
        self._refresh_items()
        self._combo.currentTextChanged.connect(self.reference_changed.emit)

    def restyle(self) -> None:
        """Re-apply active theme styles."""
        self.setStyleSheet(get_group_style())
        if hasattr(self, "_hint"):
            self._hint.setStyleSheet(f"color: {get_ui_color('TEXT_SECONDARY')}; font-size: 11px;")
        if hasattr(self, "_combo"):
            self._combo.setStyleSheet(get_combo_style())

    def _refresh_items(self) -> None:
        """Rebuild dropdown items from current plane point labels."""
        previous_selection = self._combo.currentText() or self._PLACEHOLDER_LABEL

        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(self._PLACEHOLDER_LABEL)
        self._combo.addItems(self._get_plane_labels())

        index = self._combo.findText(previous_selection)
        self._combo.setCurrentIndex(index if index >= 0 else 0)
        self._combo.blockSignals(False)

        if index < 0:
            self.reference_changed.emit(self._combo.currentText())

    def current_reference_text(self) -> str:
        """The currently selected item's text (placeholder or a plane label)."""
        return self._combo.currentText()

    def reset_to_placeholder(self) -> None:
        """Reset selection back to placeholder ('-- Select Reference Point --')."""
        if self._combo.currentText() != self._PLACEHOLDER_LABEL:
            self._combo.setCurrentIndex(0)
