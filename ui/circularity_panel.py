"""
ui/circularity_panel.py
========================
Input + result panel for the Circularity & Concentricity module: two
hole-center coordinates (typically fed by a PLC) plus a rod axis, and the
resulting coaxiality/concentricity numbers.
"""

from __future__ import annotations


import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    )

from core.circularity import _WORLD_X, _WORLD_Y, _WORLD_Z, measure_concentricity
from ui.styles import get_button_style, get_field_style, get_group_style, get_ui_color, _make_coord_edit
from utils import format_number, parse_float

_BASE_AXIS_OPTIONS: dict[str, tuple[np.ndarray, str, str]] = {
    "X": (_WORLD_X, "Y", "Z"),
    "Y": (_WORLD_Y, "X", "Z"),
    "Z": (_WORLD_Z, "X", "Y"),
}

def _coord_group(
    title: str,
    default: tuple[float, float, float],
    *,
    with_radius: bool = False,
    default_radius: float = 4.0,
) -> tuple[QGroupBox, dict[str, QLineEdit]]:
    """Build a titled X/Y/Z entry row and return it with its edit widgets.

    When ``with_radius`` is True, an additional "R" field is appended,
    keyed as ``"R"`` in the returned edits dict.
    """
    box = QGroupBox(title)
    box.setStyleSheet(get_group_style())
    layout = QHBoxLayout(box)
    layout.setContentsMargins(8, 10, 8, 8)
    layout.setSpacing(6)

    edits: dict[str, QLineEdit] = {}
    for axis_name, value in zip(("X", "Y", "Z"), default):
        layout.addWidget(QLabel(axis_name))
        edit = _make_coord_edit()
        edit.setText(format_number(value))
        layout.addWidget(edit)
        edits[axis_name] = edit

    if with_radius:
        layout.addWidget(QLabel("R"))
        radius_edit = _make_coord_edit()
        radius_edit.setText(format_number(default_radius))
        layout.addWidget(radius_edit)
        edits["R"] = radius_edit

    return box, edits


class CircularityPanel(QWidget):
    """Two hole-center inputs, a rod-axis input, and the concentricity result."""

    #: Emitted after every successful measurement: (center_1, center_2, rod_axis, ConcentricityResult)
    measured = pyqtSignal(object, object, object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)
        outer.setAlignment(Qt.AlignTop)

        self._hole_1_box, self._hole_1_edits = _coord_group("Hole 1 Center (from PLC)", (0.0, 0.0, 0.0))
        self._hole_2_box, self._hole_2_edits = _coord_group("Hole 2 Center (from PLC)", (0.0, 0.0, 0.0))
        self._axis_box = QGroupBox("Base Axis (cylinder's nominal direction)")
        self._axis_box.setStyleSheet(get_group_style())
        axis_layout = QHBoxLayout(self._axis_box)
        axis_layout.setContentsMargins(8, 10, 8, 8)
        axis_layout.setSpacing(6)
        axis_layout.addWidget(QLabel("Axis"))
        self._axis_combo = QComboBox()
        self._axis_combo.addItems(list(_BASE_AXIS_OPTIONS.keys()))
        self._axis_combo.setStyleSheet(get_field_style())
        self._axis_combo.currentTextChanged.connect(self.measure)
        axis_layout.addWidget(self._axis_combo)
        axis_layout.addStretch(1)

        outer.addWidget(self._hole_1_box)
        outer.addWidget(self._hole_2_box)
        outer.addWidget(self._axis_box)

        self._measure_button = QPushButton("Measure Concentricity")
        self._measure_button.setStyleSheet(get_button_style())
        self._measure_button.clicked.connect(self.measure)
        outer.addWidget(self._measure_button)

        self._result_box = QGroupBox("Result")
        self._result_box.setStyleSheet(get_group_style())
        result_layout = QGridLayout(self._result_box)
        result_layout.setContentsMargins(8, 10, 8, 8)
        result_layout.setSpacing(4)

        self._result_labels: dict[str, QLabel] = {}
        rows = [
            ("cylinder_type", "Cylinder Type"),
            ("other_1", "Displacement (axis 1)"),
            ("other_2", "Displacement (axis 2)"),
            ("radial_displacement", "Offset (Center Displacement)"),
        ]
        self._result_captions: dict[str, QLabel] = {}
        for row_index, (key, caption) in enumerate(rows):
            caption_label = QLabel(caption)
            value_label = QLabel("--")
            value_label.setAlignment(Qt.AlignRight)
            value_label.setStyleSheet(f"color: {get_ui_color('ACCENT_HOVER')}; font-weight: bold;")
            result_layout.addWidget(caption_label, row_index, 0)
            result_layout.addWidget(value_label, row_index, 1)
            self._result_labels[key] = value_label
            self._result_captions[key] = caption_label

        outer.addWidget(self._result_box)
        outer.addStretch(1)

    def _read_vector(self, edits: dict[str, QLineEdit]) -> np.ndarray:
        return np.array([parse_float(edits[axis].text()) for axis in ("X", "Y", "Z")], dtype=np.float64)

    def measure(self) -> None:
        """Read the current inputs, compute concentricity, and update the
        result labels. Emits :attr:`measured` on success so a listener
        (e.g. the 3D viewport) can redraw."""
        center_1 = self._read_vector(self._hole_1_edits)
        center_2 = self._read_vector(self._hole_2_edits)
        axis_name = self._axis_combo.currentText()
        rod_axis, other_1_name, other_2_name = _BASE_AXIS_OPTIONS[axis_name]

        try:
            result = measure_concentricity(center_1, center_2, rod_axis=rod_axis)
        except ValueError:
            for label in self._result_labels.values():
                label.setText("invalid axis")
            return

        offset = center_2 - center_1
        other_axis_vectors = {"X": _WORLD_X, "Y": _WORLD_Y, "Z": _WORLD_Z}
        other_1_value = float(np.dot(offset, other_axis_vectors[other_1_name]))
        other_2_value = float(np.dot(offset, other_axis_vectors[other_2_name]))

        is_right = result.radial_displacement < 1e-9

        self._result_captions["other_1"].setText(f"Displacement along {other_1_name}")
        self._result_captions["other_2"].setText(f"Displacement along {other_2_name}")
        self._result_labels["cylinder_type"].setText("RIGHT" if is_right else "OBLIQUE")
        type_color = get_ui_color("ACCENT_HOVER") if is_right else "#ff5c5c"
        self._result_labels["cylinder_type"].setStyleSheet(f"color: {type_color}; font-weight: bold;")
        self._result_labels["other_1"].setText(format_number(other_1_value))
        self._result_labels["other_2"].setText(format_number(other_2_value))

        self._result_labels["radial_displacement"].setText(format_number(result.radial_displacement))
        # Note: result still carries delta_axial, straight_line_distance,
        # boundary_distance/contained/boundary_margin etc. -- computed and
        # available (e.g. to the 3D viewport via the `measured` signal) --
        # this panel just no longer displays them, per current request to
        # show only the center-to-center offset here.

        self.measured.emit(center_1, center_2, rod_axis, result)

    def restyle(self) -> None:
            """Reapply styles after a theme switch."""
            for box in (self._hole_1_box, self._hole_2_box, self._axis_box, self._result_box):
                box.setStyleSheet(get_group_style())
            self._measure_button.setStyleSheet(get_button_style())
            self._axis_combo.setStyleSheet(get_field_style())
            for edits in (self._hole_1_edits, self._hole_2_edits):
                for edit in edits.values():
                    edit.setStyleSheet(get_field_style())