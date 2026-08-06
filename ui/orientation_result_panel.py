"""
ui/orientation_result_panel.py
===============================
ONE reusable right-panel widget for plane-to-plane GD&T orientation checks
(Perpendicularity, Parallelism today; Angularity/Coplanarity later).

Compares TWO ACTUAL FITTED PLANES -- the Reference (datum) Plane and the
Inspection Plane, each independently best-fit from its own >=3-point set
(see app/main_window.py::_recompute). Which relation is checked
(Perpendicularity vs Parallelism) is a live dropdown backed by
core.orientation.ORIENTATION_CHECKS -- both modules share this exact same
widget/class with zero duplication.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout

from core.best_fit_plane import BestFitPlaneResult
from core.orientation import ORIENTATION_CHECKS
from ui.styles import get_field_style, get_group_style, get_ui_color, _make_coord_edit
from utils import format_number, parse_float

_NO_FIT_TEXT = "Add at least 3 points to BOTH Reference Plane and Inspection Plane."


class OrientationResultPanel(QGroupBox):
    """Check-type selector + tolerance, plus deviation angle and PASS/FAIL,
    for the Reference Plane vs. Inspection Plane the owning window's shared
    pipeline currently holds."""

    #: Emitted after every render: an OrientationResult, or None when either
    #: plane isn't fitted yet.
    measured = pyqtSignal(object)

    def __init__(self, default_check: str | None = None) -> None:
        super().__init__("Orientation Result")
        self.setStyleSheet(get_group_style())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 10, 8, 8)
        outer.setSpacing(6)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.addWidget(QLabel("Check"))
        self._check_combo = QComboBox()
        self._check_combo.addItems(list(ORIENTATION_CHECKS.keys()))
        if default_check in ORIENTATION_CHECKS:
            self._check_combo.setCurrentText(default_check)
        self._check_combo.setStyleSheet(get_field_style())
        self._check_combo.currentTextChanged.connect(self._render)
        controls.addWidget(self._check_combo)

        controls.addWidget(QLabel("Tol (\u00b0)"))
        self._tolerance_edit = _make_coord_edit()
        self._tolerance_edit.setText(format_number(0.5))
        self._tolerance_edit.editingFinished.connect(self._render)
        controls.addWidget(self._tolerance_edit)
        outer.addLayout(controls)

        result_grid = QGridLayout()
        result_grid.setSpacing(4)

        self._deviation_label = QLabel(_NO_FIT_TEXT)
        self._deviation_label.setWordWrap(True)
        self._deviation_label.setStyleSheet(
            f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;"
        )
        result_grid.addWidget(self._deviation_label, 0, 0, 1, 2)

        self._status_label = QLabel("--")
        self._status_label.setStyleSheet("font-weight: bold;")
        result_grid.addWidget(QLabel("Status"), 1, 0)
        result_grid.addWidget(self._status_label, 1, 1)
        outer.addLayout(result_grid)

        self._reference_plane: BestFitPlaneResult | None = None
        self._inspection_plane: BestFitPlaneResult | None = None
        self._inspection_error: str | None = None
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display(
        self,
        reference_plane: BestFitPlaneResult | None,
        inspection_plane: BestFitPlaneResult | None,
        inspection_error: str | None = None,
    ) -> None:
        """Cache the latest fitted Reference/Inspection planes and re-render.
        ``inspection_error`` is BestFitPlane's own PlaneFitError message when
        >=3 Inspection Plane points were supplied but are collinear/coincident
        -- surfaced verbatim so "not enough points" and "these points don't
        form a plane" never look like the same problem."""
        self._reference_plane = reference_plane
        self._inspection_plane = inspection_plane
        self._inspection_error = inspection_error
        self._render()

    def restyle(self) -> None:
        self.setStyleSheet(get_group_style())
        self._check_combo.setStyleSheet(get_field_style())
        self._tolerance_edit.setStyleSheet(get_field_style())
        self._render()

    def current_check(self) -> str:
        """Currently selected check name ('Perpendicularity' or
        'Parallelism') -- read by the 3-D overlay so only the ACTIVE
        check's angle symbol is drawn, never both at once."""
        return self._check_combo.currentText()
    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _render(self) -> None:
        if self._reference_plane is None or self._inspection_plane is None:
            self._deviation_label.setText(self._inspection_error or _NO_FIT_TEXT)
            self._deviation_label.setStyleSheet(
                f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;"
            )
            self._status_label.setText("--")
            self._status_label.setStyleSheet("font-weight: bold;")
            self.measured.emit(None)
            return

        check_name = self._check_combo.currentText()
        measure_fn = ORIENTATION_CHECKS[check_name]
        tolerance = abs(parse_float(self._tolerance_edit.text()))

        result = measure_fn(self._reference_plane, self._inspection_plane)
        passed = result.is_within_tolerance(tolerance)
        symbol = "\u22a5" if check_name == "Perpendicularity" else "\u2225"

        self._deviation_label.setStyleSheet(
            f"color: {get_ui_color('TEXT_PRIMARY')}; font-size: 11px; "
            f"font-family: 'Consolas', 'Courier New', monospace;"
        )
        self._deviation_label.setText(
            f"Inspection Plane {symbol} Reference Plane: "
            f"{format_number(result.deviation_angle_deg)}\u00b0 deviation "
            f"(tolerance \u00b1{format_number(tolerance)}\u00b0)"
        )

        status_color = get_ui_color("ACCENT_HOVER") if passed else "#ff5c5c"
        self._status_label.setText("PASS" if passed else "FAIL")
        self._status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")

        self.measured.emit(result)