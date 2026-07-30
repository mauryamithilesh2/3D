"""
ui/point_list_panel.py
======================
Dynamic add/remove-able list panel for plane or inspection coordinate rows.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout

from ui.coordinate_row import CoordinateRow
from ui.styles import get_button_style, get_group_style, _BUTTON_STYLE, _GROUP_STYLE


class PointListPanel(QGroupBox):
    """A titled group box managing a dynamic list of :class:`CoordinateRow`."""

    def __init__(
        self,
        title: str,
        get_points: Callable[[], list[tuple[str, np.ndarray]]],
        add_point: Callable[[], None],
        update_point: Callable[[str, float, float, float], None],
        remove_point: Callable[[str], None],
        min_count: int,
        changed_signal,
        reset_last_point: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(title)
        self.setStyleSheet(get_group_style())

        self._get_points = get_points
        self._update_point = update_point
        self._remove_point = remove_point
        self._min_count = min_count
        self._rows: dict[str, CoordinateRow] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 10, 6, 8)
        outer.setSpacing(4)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(2)
        outer.addLayout(self._rows_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self._add_button = QPushButton("+ Add Point")
        self._add_button.setStyleSheet(get_button_style())
        self._add_button.clicked.connect(add_point)
        btn_layout.addWidget(self._add_button)

        self._reset_button: QPushButton | None = None
        if reset_last_point is not None:
            self._reset_button = QPushButton("Reset")
            self._reset_button.setStyleSheet(get_button_style())
            self._reset_button.setToolTip(f"Remove the last point in {title} (one per click)")
            self._reset_button.clicked.connect(reset_last_point)
            btn_layout.addWidget(self._reset_button)

        outer.addLayout(btn_layout)

        changed_signal.connect(self._reconcile)
        self._reconcile()

    def restyle(self) -> None:
        """Re-apply active theme styles to group box, buttons, and child rows."""
        self.setStyleSheet(get_group_style())
        btn_style = get_button_style()
        if hasattr(self, "_add_button") and self._add_button is not None:
            self._add_button.setStyleSheet(btn_style)
        if hasattr(self, "_reset_button") and self._reset_button is not None:
            self._reset_button.setStyleSheet(btn_style)
        for row in self._rows.values():
            if hasattr(row, "restyle"):
                row.restyle()

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    def _reconcile(self) -> None:
        """Sync displayed rows with current point collection state."""
        current_points = self._get_points()
        current_labels = [label for label, _ in current_points]

        if set(current_labels) != set(self._rows.keys()):
            self._rebuild_rows(current_points)
        else:
            for label, coordinates in current_points:
                x, y, z = (float(v) for v in coordinates)
                self._rows[label].set_values(x, y, z)

        self._update_removability(len(current_points))

    def _rebuild_rows(self, points: list[tuple[str, np.ndarray]]) -> None:
        """Recreate row widgets to match changed set of labels."""
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

        for label, coordinates in points:
            x, y, z = (float(v) for v in coordinates)
            row = CoordinateRow(label, x, y, z, removable=True)
            row.values_committed.connect(self._on_row_committed)
            row.remove_requested.connect(self._on_row_remove_requested)
            self._rows_layout.addWidget(row)
            self._rows[label] = row

    def _update_removability(self, count: int) -> None:
        """Disable every row's remove button once the list is at ``min_count``."""
        removable = count > self._min_count
        for row in self._rows.values():
            row.set_removable(removable)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_row_committed(self, label: str, x: float, y: float, z: float) -> None:
        self._update_point(label, x, y, z)

    def _on_row_remove_requested(self, label: str) -> None:
        try:
            self._remove_point(label)
        except ValueError:
            pass
