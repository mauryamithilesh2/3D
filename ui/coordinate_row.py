"""
ui/coordinate_row.py
====================
Single labeled, editable (X, Y, Z) coordinate entry row.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QWidget, QPushButton

from config import COORD_INPUT_DECIMALS
from ui.styles import get_field_style, get_ui_color, _make_coord_edit
from utils import format_number, parse_float


def _name_edit_style() -> str:
    """Compact borderless style for the editable point-name field."""
    return f"""
    QLineEdit {{
        color: {get_ui_color('ACCENT_HOVER')};
        font-weight: bold;
        font-size: 12px;
        background: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
        padding: 1px 2px;
    }}
    QLineEdit:focus {{
        border: 1px solid {get_ui_color('BORDER_LIGHT')};
        background-color: {get_ui_color('BG_INPUT_FOCUS')};
    }}
"""
def _remove_button_style() -> str:
    """Small, low-emphasis style for the per-row delete ('X') button."""
    return f"""
    QPushButton {{
        color: {get_ui_color('TEXT_SECONDARY')};
        background: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
        font-weight: bold;
        font-size: 11px;
        padding: 0px;
    }}
    QPushButton:hover {{
        color: white;
        background-color: #d9534f;
        border: 1px solid #d9534f;
    }}
"""

class CoordinateRow(QWidget):
    """One row with an editable point name and editable (X, Y, Z) fields."""

    values_committed = pyqtSignal(str, float, float, float)
    remove_requested = pyqtSignal(str)
    #: Emitted when the user finishes editing the point name: (old_label, new_label).
    label_edit_requested = pyqtSignal(str, str)

    def __init__(self, label: str, x: float, y: float, z: float, removable: bool = True) -> None:
        super().__init__()
        self._label = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        self._name_edit = QLineEdit(label)
        self._name_edit.setFixedWidth(48)
        self._name_edit.setToolTip("Point name -- click to rename")
        self._name_edit.setStyleSheet(_name_edit_style())
        self._name_edit.editingFinished.connect(self._on_name_edited)
        layout.addWidget(self._name_edit)

        self._edit_x = _make_coord_edit()
        self._edit_y = _make_coord_edit()
        self._edit_z = _make_coord_edit()
        self.set_values(x, y, z)
        for edit in (self._edit_x, self._edit_y, self._edit_z):
            layout.addWidget(edit)
            edit.editingFinished.connect(self._on_edited)

        self._remove_button = QPushButton("\u2715")
        self._remove_button.setFixedSize(20, 20)
        self._remove_button.setToolTip(f"Delete point {label}")
        self._remove_button.setStyleSheet(_remove_button_style())
        self._remove_button.setVisible(removable)
        self._remove_button.clicked.connect(lambda: self.remove_requested.emit(self._label))
        layout.addWidget(self._remove_button)

    @property
    def label(self) -> str:
        """The point label this row displays (e.g. ``"PL1"``, ``"P0"``)."""
        return self._label

    def set_label_text(self, label: str) -> None:
        """Programmatically reset the displayed name text (emits no signal).

        Used to revert the name field back to its previous value when a
        requested rename is rejected (e.g. duplicate name).
        """
        self._label = label
        self._name_edit.blockSignals(True)
        self._name_edit.setText(label)
        self._name_edit.blockSignals(False)

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
            """Show or hide the per-row delete ('X') button."""
            self._remove_button.setVisible(removable)

    def restyle(self) -> None:
            """Re-apply active theme styles."""
            self._name_edit.setStyleSheet(_name_edit_style())
            field_style = get_field_style()
            for edit in (self._edit_x, self._edit_y, self._edit_z):
                edit.setStyleSheet(field_style)
            self._remove_button.setStyleSheet(_remove_button_style())

    def _on_edited(self) -> None:
        """Forward the row's current values whenever any field is committed."""
        x, y, z = self.values()
        self.values_committed.emit(self._label, x, y, z)

    def _on_name_edited(self) -> None:
        """Request a rename whenever the name field is committed with a new value."""
        new_label = self._name_edit.text().strip()
        if not new_label or new_label == self._label:
            self._name_edit.setText(self._label)
            return
        self.label_edit_requested.emit(self._label, new_label)
