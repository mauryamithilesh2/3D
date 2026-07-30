"""
ui/coordinate_row.py
====================
Single labeled, editable (X, Y, Z) coordinate entry row.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget

from config import COORD_INPUT_DECIMALS
from ui.styles import get_field_style, get_ui_color, _make_coord_edit
from utils import format_number, parse_float


class CoordinateRow(QWidget):
    """One labeled, editable (X, Y, Z) row."""

    values_committed = pyqtSignal(str, float, float, float)
    remove_requested = pyqtSignal(str)

    def __init__(self, label: str, x: float, y: float, z: float, removable: bool = True) -> None:
        super().__init__()
        self._label = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        self._name_label = QLabel(label)
        self._name_label.setFixedWidth(32)
        self._name_label.setStyleSheet(f"color: {get_ui_color('ACCENT_HOVER')}; font-weight: bold; font-size: 12px;")
        layout.addWidget(self._name_label)

        self._edit_x = _make_coord_edit()
        self._edit_y = _make_coord_edit()
        self._edit_z = _make_coord_edit()
        self.set_values(x, y, z)
        for edit in (self._edit_x, self._edit_y, self._edit_z):
            layout.addWidget(edit)
            edit.editingFinished.connect(self._on_edited)

    @property
    def label(self) -> str:
        """The point label this row displays (e.g. ``"PL1"``, ``"P0"``)."""
        return self._label

    def values(self) -> tuple[float, float, float]:
        """Current (X, Y, Z) shown in the row's fields."""
        return (
            parse_float(self._edit_x.text()),
            parse_float(self._edit_y.text()),
            parse_float(self._edit_z.text()),
        )

    def set_values(self, x: float, y: float, z: float) -> None:
        """Programmatically update the displayed fields (emits no signal)."""
        self._edit_x.setText(format_number(x, COORD_INPUT_DECIMALS))
        self._edit_y.setText(format_number(y, COORD_INPUT_DECIMALS))
        self._edit_z.setText(format_number(z, COORD_INPUT_DECIMALS))

    def set_removable(self, removable: bool) -> None:
        """No-op retained for API compatibility."""

    def restyle(self) -> None:
        """Re-apply active theme styles."""
        self._name_label.setStyleSheet(f"color: {get_ui_color('ACCENT_HOVER')}; font-weight: bold; font-size: 12px;")
        field_style = get_field_style()
        for edit in (self._edit_x, self._edit_y, self._edit_z):
            edit.setStyleSheet(field_style)

    def _on_edited(self) -> None:
        """Forward the row's current values whenever any field is committed."""
        x, y, z = self.values()
        self.values_committed.emit(self._label, x, y, z)
