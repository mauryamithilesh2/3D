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
    QCheckBox,
    )

from core.circularity import _WORLD_X, _WORLD_Y, _WORLD_Z, measure_concentricity
from ui.styles import get_button_style, get_field_style, get_group_style, get_ui_color, _make_coord_edit
from utils import format_number, parse_float
from plc import connection_manager as plc_conn
from plc.point_registers import DATA_TYPE, SCALE_FACTOR, CIRCULARITY_HOLE_REGISTERS

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

        self._axis_combo.setEnabled(False)  # auto-detect is on by default

        axis_layout.addWidget(self._axis_combo)

        self._auto_axis_checkbox = QCheckBox("Auto-detect")
        self._auto_axis_checkbox.setChecked(True)
        self._auto_axis_checkbox.stateChanged.connect(self._on_auto_axis_toggled)
        axis_layout.addWidget(self._auto_axis_checkbox)

        axis_layout.addStretch(1)

        outer.addWidget(self._hole_1_box)
        outer.addWidget(self._hole_2_box)
        outer.addWidget(self._axis_box)

        self._load_plc_button = QPushButton("Load from PLC")
        self._load_plc_button.setStyleSheet(get_button_style())
        self._load_plc_button.clicked.connect(self.load_from_plc)
        outer.addWidget(self._load_plc_button)

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

    def _read_plc_point(self, addresses: tuple[int, int, int]) -> tuple[float, float, float] | None:
        """Read one X/Y/Z point from the PLC (or SIMULATED_REGISTERS if no
        real PLC is connected). Mirrors MainWindow._read_plc_point."""
        needs_scaling = DATA_TYPE in ("INT16", "UINT16", "INT32")
        values = []
        for address in addresses:
            raw = plc_conn.operations.read(address, DATA_TYPE)
            if raw is None:
                return None
            values.append(raw / SCALE_FACTOR if needs_scaling else raw)
        return tuple(values)

    def load_from_plc(self) -> None:
        """Read both hole centers from the PLC, fill the X/Y/Z fields, and
        immediately re-measure so the graph updates."""
        hole_1 = self._read_plc_point(CIRCULARITY_HOLE_REGISTERS["Hole 1 Center"])
        hole_2 = self._read_plc_point(CIRCULARITY_HOLE_REGISTERS["Hole 2 Center"])
        if hole_1 is None or hole_2 is None:
            self.window().statusBar().showMessage(
                "PLC read failed — check PLC connection", 4000
            )
            return

        for value, axis in zip(hole_1, ("X", "Y", "Z")):
            self._hole_1_edits[axis].setText(format_number(value))
        for value, axis in zip(hole_2, ("X", "Y", "Z")):
            self._hole_2_edits[axis].setText(format_number(value))

        self.measure()

    def _on_auto_axis_toggled(self, state: int) -> None:
        """Enable/disable manual axis selection based on the checkbox."""
        is_auto = state == Qt.Checked
        self._axis_combo.setEnabled(not is_auto)
        self.measure()

    def _detect_axis(self, center_1: np.ndarray, center_2: np.ndarray) -> str:
        """Pick whichever world axis (X/Y/Z) the two centers are separated
        along the most, and use it as the nominal rod axis.

        CAVEAT: this derives the axis from the same two points being
        measured, so it is NOT a true independent nominal axis -- it will
        tend to flatter the result (radial_displacement biased low) versus
        a real machine/design axis. Uncheck "Auto-detect" and pick the
        known machine axis manually whenever accuracy matters more than
        convenience.
        """
        offset = np.asarray(center_2, dtype=np.float64) - np.asarray(center_1, dtype=np.float64)
        idx = int(np.argmax(np.abs(offset)))
        return ("X", "Y", "Z")[idx]

    def measure(self) -> None:
        """Read the current inputs, compute concentricity, and update the
        result labels. Emits :attr:`measured` on success so a listener
        (e.g. the 3D viewport) can redraw."""
        center_1 = self._read_vector(self._hole_1_edits)
        center_2 = self._read_vector(self._hole_2_edits)
        if self._auto_axis_checkbox.isChecked():
            axis_name = self._detect_axis(center_1, center_2)
            self._axis_combo.blockSignals(True)
            self._axis_combo.setCurrentText(axis_name)
            self._axis_combo.blockSignals(False)
        else:
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