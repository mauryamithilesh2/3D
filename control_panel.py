"""
control_panel.py
================
Reusable right-side control panel for the 3-D widget demo.

Responsibilities
----------------
* Provide labelled QLineEdit fields (with QDoubleValidator) for the
  point and plane coordinates.
* Emit Qt signals whenever the user commits a new coordinate value.
* Expose ``Reset Camera`` and ``Reset Coordinates`` buttons via signals.
* Never touch the OpenGL scene directly.

Public signals
--------------
point_changed(float, float, float)
    Emitted when any point coordinate is committed.
plane_changed(tuple, tuple, tuple, tuple)
    Emitted with the new (P1, P2, P3, P4) corners after a rigid rectangle
    re-solve.
reset_camera_requested()
    Emitted when the Reset Camera button is clicked.
reset_coordinates_requested()
    Emitted when the Reset Coordinates button is clicked.

Rigid rectangle editing
------------------------
The 4 plane corners no longer move independently. Editing a single
coordinate of a single corner is delegated to a :class:`RectangleSolver`
(see ``rectangle_solver.py``), which re-solves the *entire* rigid rectangle
-- keeping one corner (the pivot, selectable via the "Fixed Corner"
dropdown) exactly fixed, and rotating the rest of the rigid shape so the
edited coordinate lands on the requested value while every other geometric
property (planarity, edge lengths, right angles) is preserved exactly. This
widget only collects the single edited value and displays the solver's
results; it never computes rectangle geometry itself.

Compatible with Python 3.11+, PyQt5 ≥ 5.15.9.
"""

from __future__ import annotations

from typing import Final

from rectangle_solver import RectangleSolver, RectangleSolverError, Vec3

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QFont, QColor, QPalette
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_VALUE: Final[float] = 0.0
_COORD_MIN: Final[float] = -1_000.0
_COORD_MAX: Final[float] = 1_000.0
_COORD_DECIMALS: Final[int] = 4
_FIELD_WIDTH: Final[int] = 110  # px


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _make_coord_edit(parent: QWidget | None = None) -> QLineEdit:
    """Create a styled coordinate QLineEdit with QDoubleValidator.

    Parameters
    ----------
    parent:
        Optional Qt parent widget.

    Returns
    -------
    QLineEdit
        Pre-configured with validator, fixed width, and default text "0".
    """
    edit = QLineEdit(parent)
    validator = QDoubleValidator(_COORD_MIN, _COORD_MAX, _COORD_DECIMALS, edit)
    validator.setNotation(QDoubleValidator.StandardNotation)
    edit.setValidator(validator)
    edit.setText("0")
    edit.setFixedWidth(_FIELD_WIDTH)
    edit.setAlignment(Qt.AlignRight)
    edit.setStyleSheet(
        """
        QLineEdit {
            background-color: #ffffff;
            color: #2c3040;
            border: 1px solid #c8ccd6;
            border-radius: 3px;
            padding: 4px 8px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
        }
        QLineEdit:focus {
            border: 1px solid #5a8ad4;
            background-color: #f4f7fd;
        }
        QLineEdit:hover {
            border: 1px solid #a0aabf;
        }
        """
    )
    return edit


def _make_label(text: str, parent: QWidget | None = None) -> QLabel:
    """Create a styled axis label.

    Parameters
    ----------
    text:
        Label text (e.g. ``"X"``).
    parent:
        Optional Qt parent widget.

    Returns
    -------
    QLabel
        Pre-styled label widget.
    """
    label = QLabel(text, parent)
    label.setFixedWidth(28)
    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    label.setStyleSheet(
        """
        QLabel {
            color: #5a6480;
            font-weight: bold;
            font-size: 12px;
        }
        """
    )
    return label


def _make_button(text: str, accent: bool = False, parent: QWidget | None = None) -> QPushButton:
    """Create a styled action button.

    Parameters
    ----------
    text:
        Button label.
    accent:
        If ``True``, uses a highlighted (primary action) colour.
    parent:
        Optional Qt parent widget.

    Returns
    -------
    QPushButton
        Pre-styled push button.
    """
    btn = QPushButton(text, parent)
    if accent:
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3a6ab5;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2e5aa0;
            }
            QPushButton:pressed {
                background-color: #274d8a;
            }
            """
        )
    else:
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f0f1f4;
                color: #3a4055;
                border: 1px solid #c8ccd6;
                border-radius: 4px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e4e7ee;
                border-color: #a0aabf;
            }
            QPushButton:pressed {
                background-color: #d8dce8;
            }
            """
        )
    return btn


def _make_group_box(title: str, parent: QWidget | None = None) -> QGroupBox:
    """Create a styled QGroupBox.

    Parameters
    ----------
    title:
        Group box title text.
    parent:
        Optional Qt parent widget.

    Returns
    -------
    QGroupBox
        Pre-styled group box.
    """
    box = QGroupBox(title, parent)
    box.setStyleSheet(
        """
        QGroupBox {
            color: #3a4a6a;
            font-weight: bold;
            font-size: 12px;
            border: 1px solid #d0d4de;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 6px;
            background-color: #fafbfc;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            left: 10px;
        }
        """
    )
    return box


def _make_separator(parent: QWidget | None = None) -> QFrame:
    """Create a thin horizontal separator line.

    Parameters
    ----------
    parent:
        Optional Qt parent widget.

    Returns
    -------
    QFrame
        Styled horizontal line.
    """
    sep = QFrame(parent)
    sep.setFrameShape(QFrame.HLine)
    sep.setFrameShadow(QFrame.Plain)
    sep.setStyleSheet("color: #d8dce8;")
    return sep


def _make_compact_coord_edit(parent: QWidget | None = None) -> QLineEdit:
    """Create a compact coordinate QLineEdit for horizontal point rows."""
    edit = QLineEdit(parent)
    validator = QDoubleValidator(_COORD_MIN, _COORD_MAX, _COORD_DECIMALS, edit)
    validator.setNotation(QDoubleValidator.StandardNotation)
    edit.setValidator(validator)
    edit.setText("0")
    edit.setFixedWidth(52)
    edit.setAlignment(Qt.AlignRight)
    edit.setStyleSheet(
        """
        QLineEdit {
            background-color: #ffffff;
            color: #2c3040;
            border: 1px solid #c8ccd6;
            border-radius: 3px;
            padding: 3px 4px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 11px;
        }
        QLineEdit:focus {
            border: 1px solid #5a8ad4;
            background-color: #f4f7fd;
        }
        QLineEdit:hover {
            border: 1px solid #a0aabf;
        }
        """
    )
    return edit


class _PointRow(QWidget):
    """A single horizontal row for a 3D point containing point name + X, Y, Z inputs.

    Example layout:
    P1: X1 [ -50.0 ]  Y1 [ -50.0 ]  Z1 [ 0.0 ]
    """

    def __init__(
        self,
        point_label: str,
        x_name: str,
        y_name: str,
        z_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Main point label (P0:, P1:, P2:, P3:, P4:)
        p_lbl = QLabel(f"{point_label}:", self)
        p_lbl.setFixedWidth(24)
        p_lbl.setStyleSheet("color: #2c3850; font-weight: bold; font-size: 12px;")
        layout.addWidget(p_lbl)

        def _axis_lbl(txt: str) -> QLabel:
            lbl = QLabel(txt, self)
            lbl.setStyleSheet("color: #6a7490; font-size: 11px; font-weight: bold;")
            return lbl

        # X input
        layout.addWidget(_axis_lbl(x_name))
        self._edit_x = _make_compact_coord_edit(self)
        layout.addWidget(self._edit_x)

        # Y input
        layout.addWidget(_axis_lbl(y_name))
        self._edit_y = _make_compact_coord_edit(self)
        layout.addWidget(self._edit_y)

        # Z input
        layout.addWidget(_axis_lbl(z_name))
        self._edit_z = _make_compact_coord_edit(self)
        layout.addWidget(self._edit_z)

    @property
    def edit_x(self) -> QLineEdit:
        return self._edit_x

    @property
    def edit_y(self) -> QLineEdit:
        return self._edit_y

    @property
    def edit_z(self) -> QLineEdit:
        return self._edit_z

    def values(self) -> tuple[float, float, float]:
        def _parse(edit: QLineEdit) -> float:
            try:
                return float(edit.text().replace(",", "."))
            except ValueError:
                return 0.0
        return (_parse(self._edit_x), _parse(self._edit_y), _parse(self._edit_z))

    def set_values(self, x: float, y: float, z: float) -> None:
        for edit, val in ((self._edit_x, x), (self._edit_y, y), (self._edit_z, z)):
            edit.blockSignals(True)
            edit.setText(f"{val:.4g}")
            edit.blockSignals(False)


# ---------------------------------------------------------------------------
# ControlPanel — the public widget
# ---------------------------------------------------------------------------

class ControlPanel(QWidget):
    """Right-side control panel for the 3-D widget demo.

    Provides coordinate editors for a 3-D *point* and a 3-D *plane*, plus
    camera and coordinate reset buttons.  All scene updates are communicated
    exclusively via Qt signals; this widget never touches OpenGL directly.

    Signals
    -------
    point_changed(float, float, float)
        Emitted when any point coordinate is committed (editingFinished).
    plane_changed(float, float, float)
        Emitted when any plane coordinate is committed.
    reset_camera_requested()
        Emitted when the "Reset Camera" button is clicked.
    reset_coordinates_requested()
        Emitted when the "Reset Coordinates" button is clicked.

    Parameters
    ----------
    parent:
        Optional Qt parent widget.
    """

    # Qt signals ----------------------------------------------------------------
    point_changed = pyqtSignal(float, float, float)
    plane_changed = pyqtSignal(tuple, tuple, tuple, tuple)
    reset_camera_requested = pyqtSignal()
    reset_coordinates_requested = pyqtSignal()

    # Default rectangle (matches the GL3DWidget's initial state) ----------------
    _DEFAULT_P1: Final[Vec3] = (-50.0, -50.0, 0.0)
    _DEFAULT_P2: Final[Vec3] = (50.0, -50.0, 0.0)
    _DEFAULT_P3: Final[Vec3] = (50.0, 50.0, 0.0)
    _DEFAULT_P4: Final[Vec3] = (-50.0, 50.0, 0.0)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._set_default_values()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct all child widgets and layouts."""
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet(
            """
            ControlPanel {
                background-color: #f5f6f9;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            """
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area container for smooth scrolling
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_content = QWidget(scroll)
        scroll_content.setStyleSheet("background-color: #f5f6f9;")
        scroll.setWidget(scroll_content)

        root = QVBoxLayout(scroll_content)
        root.setContentsMargins(10, 14, 10, 14)
        root.setSpacing(12)

        # ── Header label ────────────────────────────────────────────────
        header = QLabel("3D Scene Controls", scroll_content)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(
            """
            QLabel {
                color: #3a4a6a;
                font-size: 13px;
                font-weight: bold;
                padding-bottom: 4px;
            }
            """
        )
        root.addWidget(header)
        root.addWidget(_make_separator(scroll_content))

        # ── Point P0 group ───────────────────────────────────────────────
        point_group = _make_group_box("Point P0", scroll_content)
        point_layout = QVBoxLayout(point_group)
        point_layout.setContentsMargins(6, 10, 6, 8)

        self._row_p0 = _PointRow("P0", "X0", "Y0", "Z0", point_group)
        point_layout.addWidget(self._row_p0)
        root.addWidget(point_group)

        # ── Plane Corners Group (P1–P4) ──────────────────────
        plane_group = _make_group_box("Plane Corners (P1–P4)", scroll_content)
        plane_layout = QVBoxLayout(plane_group)
        plane_layout.setContentsMargins(6, 10, 6, 8)
        plane_layout.setSpacing(6)

        # Fixed-corner (pivot) selector: this corner never moves; editing
        # any coordinate of any other corner rotates the rigid rectangle
        # about this one. Defaults to P4, matching the canonical workflow.
        pivot_row = QHBoxLayout()
        pivot_row.setSpacing(6)
        pivot_label = QLabel("Fixed Corner:", plane_group)
        pivot_label.setStyleSheet("color: #5a6480; font-weight: bold; font-size: 12px;")
        self._pivot_combo = QComboBox(plane_group)
        self._pivot_combo.addItems(["P1", "P2", "P3", "P4"])
        self._pivot_combo.setCurrentIndex(3)  # P4 fixed by default
        self._pivot_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #ffffff;
                color: #2c3040;
                border: 1px solid #c8ccd6;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 12px;
            }
            """
        )
        pivot_row.addWidget(pivot_label)
        pivot_row.addWidget(self._pivot_combo)
        plane_layout.addLayout(pivot_row)

        self._row_p1 = _PointRow("P1", "X1", "Y1", "Z1", plane_group)
        self._row_p2 = _PointRow("P2", "X2", "Y2", "Z2", plane_group)
        self._row_p3 = _PointRow("P3", "X3", "Y3", "Z3", plane_group)
        self._row_p4 = _PointRow("P4", "X4", "Y4", "Z4", plane_group)

        plane_layout.addWidget(self._row_p1)
        plane_layout.addWidget(self._row_p2)
        plane_layout.addWidget(self._row_p3)
        plane_layout.addWidget(self._row_p4)

        root.addWidget(plane_group)
        root.addWidget(_make_separator(scroll_content))

        # ── Buttons ─────────────────────────────────────────────────────
        self._btn_reset_cam = _make_button("⟳  Reset Camera", accent=False, parent=scroll_content)
        self._btn_reset_coord = _make_button("✕  Reset Coordinates", accent=True, parent=scroll_content)

        root.addWidget(self._btn_reset_cam)
        root.addWidget(self._btn_reset_coord)
        root.addStretch()

        outer_layout.addWidget(scroll)

    def _set_default_values(self) -> None:
        """Set default initial values for point and plane quadrants.

        Also (re)creates the :class:`RectangleSolver` with the default
        rectangle so the solver and the displayed fields never disagree.
        """
        self._row_p0.set_values(0.0, 0.0, 0.0)

        pivot_index = self._pivot_combo.currentIndex() if hasattr(self, "_pivot_combo") else 3
        self._solver = RectangleSolver(
            self._DEFAULT_P1, self._DEFAULT_P2, self._DEFAULT_P3, self._DEFAULT_P4,
            pivot_index=pivot_index,
        )
        self._refresh_plane_fields()

    def _connect_signals(self) -> None:
        """Wire internal widgets to public signals."""
        for edit in (self._row_p0.edit_x, self._row_p0.edit_y, self._row_p0.edit_z):
            edit.editingFinished.connect(self._on_point_edited)

        rows = (self._row_p1, self._row_p2, self._row_p3, self._row_p4)
        for corner_index, row in enumerate(rows):
            for axis_index, edit in enumerate((row.edit_x, row.edit_y, row.edit_z)):
                edit.editingFinished.connect(
                    lambda c=corner_index, a=axis_index, e=edit: self._on_corner_coordinate_edited(c, a, e)
                )

        self._pivot_combo.currentIndexChanged.connect(self._on_pivot_changed)

        # Buttons
        self._btn_reset_cam.clicked.connect(self.reset_camera_requested)
        self._btn_reset_coord.clicked.connect(self._on_reset_coordinates_clicked)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_point_edited(self) -> None:
        """Emit :attr:`point_changed` with the current point coordinates."""
        x, y, z = self._row_p0.values()
        self.point_changed.emit(x, y, z)

    def _on_corner_coordinate_edited(self, corner_index: int, axis_index: int, edit: QLineEdit) -> None:
        """Delegate a single edited coordinate to the :class:`RectangleSolver`.

        Parameters
        ----------
        corner_index:
            Which corner was edited: 0=P1, 1=P2, 2=P3, 3=P4.
        axis_index:
            Which coordinate was edited: 0=x, 1=y, 2=z.
        edit:
            The QLineEdit the user just committed, used to read the new value.
        """
        try:
            new_value = float(edit.text().replace(",", "."))
        except ValueError:
            new_value = 0.0

        try:
            self._solver.update_coordinate(corner_index, axis_index, new_value)
        except RectangleSolverError:
            # Degenerate/unsolvable edit (e.g. zero-length rectangle) — leave
            # the solver's last valid state untouched and just redraw the
            # fields so the UI snaps back to a consistent rectangle.
            pass

        self._refresh_plane_fields()
        self.plane_changed.emit(*self._solver.get_corners())

    def _on_pivot_changed(self, new_pivot_index: int) -> None:
        """Switch which corner is held fixed, preserving the current shape/pose."""
        self._solver.set_pivot_index(new_pivot_index)
        self._refresh_plane_fields()
        self.plane_changed.emit(*self._solver.get_corners())

    def _refresh_plane_fields(self) -> None:
        """Push the solver's current corners into the P1–P4 fields (no signals)."""
        p1, p2, p3, p4 = self._solver.get_corners()
        self._row_p1.set_values(*p1)
        self._row_p2.set_values(*p2)
        self._row_p3.set_values(*p3)
        self._row_p4.set_values(*p4)

    def _on_reset_coordinates_clicked(self) -> None:
        """Reset all fields to default values and emit the reset signal."""
        self._set_default_values()
        self.reset_coordinates_requested.emit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_point_fields(self, x: float, y: float, z: float) -> None:
        """Programmatically update the point coordinate display."""
        self._row_p0.set_values(x, y, z)

    def set_plane_fields(
        self,
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        p3: tuple[float, float, float],
        p4: tuple[float, float, float],
    ) -> None:
        """Programmatically reset the plane to new corners via the solver.

        The 4 points are normalized to the nearest perfect rectangle (about
        the currently selected pivot) before being displayed, so the solver
        and the UI can never disagree.
        """
        self._solver.reset(p1, p2, p3, p4)
        self._refresh_plane_fields()

    def get_point_values(self) -> tuple[float, float, float]:
        """Return the current point coordinates shown in the UI."""
        return self._row_p0.values()

    def get_plane_values(self) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        """Return the current 4 plane corner coordinates from the solver."""
        return self._solver.get_corners()

    def _reset_all_fields(self) -> None:
        """Set every coordinate field back to default (no signals emitted)."""
        self._set_default_values()