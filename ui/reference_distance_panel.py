"""
ui/reference_distance_panel.py
==============================
Panel displaying reference-point to inspection-point distances and relative coordinates.
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from config.colors import get_active_theme
from ui.styles import get_group_style, get_ui_color
from utils import format_number, format_vector


class ReferenceDistancePanel(QGroupBox):
    """Sits directly below the Inspection Points list."""

    _NO_REFERENCE_TEXT = "Select a reference point to see distances here."
    _NO_INSPECTION_TEXT = "Add an inspection point to see distances here."

    def __init__(self) -> None:
        super().__init__("Reference \u2192 Inspection Distance")
        self.setStyleSheet(get_group_style())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 10, 6, 8)
        outer.setSpacing(6)

        self._placeholder = QLabel(self._NO_REFERENCE_TEXT)
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;")
        outer.addWidget(self._placeholder)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(8)
        outer.addLayout(self._rows_layout)

        self._last_reference_label: str | None = None
        self._last_entries: list[tuple[str, float, tuple[float, float, float]]] = []

    def restyle(self) -> None:
        """Re-apply active theme styles."""
        self.setStyleSheet(get_group_style())
        self._placeholder.setStyleSheet(f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;")
        if self._last_reference_label is not None or self._last_entries:
            self.display(self._last_reference_label, self._last_entries)

    def display(
        self,
        reference_label: str | None,
        entries: list[tuple[str, float, tuple[float, float, float]]],
    ) -> None:
        """Rebuild the panel body."""
        self._last_reference_label = reference_label
        self._last_entries = entries
        self._clear_rows()

        if reference_label is None:
            self._placeholder.setText(self._NO_REFERENCE_TEXT)
            self._placeholder.setVisible(True)
            return

        if not entries:
            self._placeholder.setText(self._NO_INSPECTION_TEXT)
            self._placeholder.setVisible(True)
            return

        self._placeholder.setVisible(False)
        for entry in entries:
            label = entry[0]
            distance = entry[1]
            coordinate = entry[2]
            self._rows_layout.addWidget(
                self._build_entry_row(reference_label, label, distance, coordinate)
            )

    def _build_entry_row(
        self,
        reference_label: str,
        label: str,
        distance: float,
        coordinate: tuple[float, float, float],
    ) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        if get_active_theme() == "light":
            hl_style = (
                "background-color: #fef8e7; color: #856404; font-weight: bold; "
                "font-size: 12px; border: 1px solid #ffeeba; border-radius: 3px; padding: 3px 6px;"
            )
        else:
            hl_style = (
                "background-color: #3a3220; color: #f0c852; font-weight: bold; "
                "font-size: 12px; border: 1px solid #5a4d28; border-radius: 3px; padding: 3px 6px;"
            )

        highlight = QLabel(f"{reference_label} \u2192 {label}:  {format_number(distance)}")
        highlight.setStyleSheet(hl_style)
        layout.addWidget(highlight)

        coord_label = QLabel(f"New Coordinate ({label}): {format_vector(np.array(coordinate))}")
        coord_label.setWordWrap(True)
        coord_label.setStyleSheet(
            f"color: {get_ui_color('TEXT_PRIMARY')}; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;"
        )
        layout.addWidget(coord_label)

        return box

    def _clear_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
