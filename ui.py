"""
ui.py
======
All PyQt5 presentation widgets: the LEFT panel (dynamic Plane Points list,
dynamic Inspection Points list, Reference Selection) and the RIGHT panel
(live Results display).

Design principle: this module contains NO geometry or fitting math. It
only ever displays values it is given and forwards user edits to callables
supplied by whoever constructs it (``main.py``). That keeps every class
here testable and reusable without a live :class:`~point_manager.PointManager`
or a real best fit plane -- and keeps all the actual mathematics in
``best_fit_plane.py`` / ``coordinate_system.py`` / ``transform.py`` /
``measurement.py``, exactly where it belongs.

Live update, no Calculate button
---------------------------------
Every coordinate field commits on ``editingFinished`` (Enter, or losing
focus) directly to the point manager, which immediately emits its changed
signal; ``main.py`` reacts to that signal by re-running the whole
pipeline and pushing fresh results back into :class:`ResultsPanel` and the
3-D view. Nothing in this file waits for a button click.

Compatible with Python 3.10+, PyQt5.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QDoubleValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from best_fit_plane import BestFitPlaneResult
from coordinate_system import CoordinateSystem, OriginReference
from config import (
    COORD_INPUT_DECIMALS,
    COORD_MAX,
    COORD_MIN,
    DEFAULT_NEW_POINT,
    LEFT_PANEL_MAX_WIDTH,
    LEFT_PANEL_MIN_WIDTH,
    RIGHT_PANEL_MAX_WIDTH,
    RIGHT_PANEL_MIN_WIDTH,
)
from measurement import PointMeasurement
from utils import format_number, format_signed_distance, format_vector, parse_float


# ---------------------------------------------------------------------------
# Shared styling helpers (kept local to this file -- purely cosmetic, not
# behavioural, so they do not belong in config.py alongside real constants)
# ---------------------------------------------------------------------------

_FIELD_STYLE = """
    QLineEdit {
        background-color: #ffffff;
        color: #2c3040;
        border: 1px solid #c8ccd6;
        border-radius: 3px;
        padding: 3px 6px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
    }
    QLineEdit:focus { border: 1px solid #5a8ad4; background-color: #f4f7fd; }
    QLineEdit:disabled { color: #a0a6b8; background-color: #f0f1f4; }
"""

_BUTTON_STYLE = """
    QPushButton {
        background-color: #f0f1f4;
        color: #3a4055;
        border: 1px solid #c8ccd6;
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 12px;
    }
    QPushButton:hover { background-color: #e4e7ee; border-color: #a0aabf; }
    QPushButton:pressed { background-color: #d8dce8; }
    QPushButton:disabled { color: #b0b4c0; background-color: #f5f6f9; }
"""

_ACCENT_BUTTON_STYLE = """
    QPushButton {
        background-color: #3a6ab5;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }
    QPushButton:hover { background-color: #2e5aa0; }
    QPushButton:pressed { background-color: #274d8a; }
"""

_GROUP_STYLE = """
    QGroupBox {
        color: #3a4a6a;
        font-weight: bold;
        font-size: 12px;
        border: 1px solid #d0d4de;
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }
"""

_REMOVE_BUTTON_STYLE = """
    QPushButton {
        background-color: #f7e9e9;
        color: #a03a3a;
        border: 1px solid #e0c0c0;
        border-radius: 3px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #f0d4d4; }
    QPushButton:disabled { color: #c8b8b8; background-color: #f5f0f0; border-color: #e5dcdc; }
"""


def _make_coord_edit() -> QLineEdit:
    """Create a styled coordinate input with a bounded double validator."""
    edit = QLineEdit()
    validator = QDoubleValidator(COORD_MIN, COORD_MAX, COORD_INPUT_DECIMALS, edit)
    validator.setNotation(QDoubleValidator.StandardNotation)
    edit.setValidator(validator)
    edit.setFixedWidth(72)
    edit.setAlignment(Qt.AlignRight)
    edit.setStyleSheet(_FIELD_STYLE)
    return edit


def _make_separator() -> QFrame:
    """Create a thin horizontal divider line."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #d0d4de;")
    return line


# ---------------------------------------------------------------------------
# A single editable point row (used for both plane points and inspection points)
# ---------------------------------------------------------------------------

class CoordinateRow(QWidget):
    """One labeled, editable (X, Y, Z) row with an optional remove button.

    Signals
    -------
    values_committed(str, float, float, float)
        Emitted with ``(label, x, y, z)`` whenever the user finishes
        editing any of the 3 fields.
    remove_requested(str)
        Emitted with ``label`` when the remove button is clicked.
    """

    values_committed = pyqtSignal(str, float, float, float)
    remove_requested = pyqtSignal(str)

    def __init__(self, label: str, x: float, y: float, z: float, removable: bool = True) -> None:
        super().__init__()
        self._label = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        name_label = QLabel(label)
        name_label.setFixedWidth(32)
        name_label.setStyleSheet("color: #3a4a6a; font-weight: bold; font-size: 12px;")
        layout.addWidget(name_label)

        self._edit_x = _make_coord_edit()
        self._edit_y = _make_coord_edit()
        self._edit_z = _make_coord_edit()
        self.set_values(x, y, z)
        for edit in (self._edit_x, self._edit_y, self._edit_z):
            layout.addWidget(edit)
            edit.editingFinished.connect(self._on_edited)

        self._remove_button = QPushButton("\u2715")
        self._remove_button.setFixedSize(22, 22)
        self._remove_button.setStyleSheet(_REMOVE_BUTTON_STYLE)
        self._remove_button.setToolTip(f"Remove {label}")
        self._remove_button.clicked.connect(lambda: self.remove_requested.emit(self._label))
        self._remove_button.setEnabled(removable)
        layout.addWidget(self._remove_button)

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
        """Enable/disable the remove button (used to enforce a minimum point count)."""
        self._remove_button.setEnabled(removable)
        tooltip = f"Remove {self._label}" if removable else "Minimum point count reached"
        self._remove_button.setToolTip(tooltip)

    def _on_edited(self) -> None:
        """Forward the row's current values whenever any field is committed."""
        x, y, z = self.values()
        self.values_committed.emit(self._label, x, y, z)


# ---------------------------------------------------------------------------
# A dynamic, add/remove-able list of CoordinateRow widgets
# ---------------------------------------------------------------------------

class PointListPanel(QGroupBox):
    """A titled group box managing a dynamic list of :class:`CoordinateRow`.

    This class knows nothing about :class:`~point_manager.PointManager`
    directly -- it is wired entirely through callables, so it works
    equally well for the plane point list and the inspection point list
    (which call different ``PointManager`` methods) without duplicating
    this widget's layout/reconciliation logic in two subclasses.

    Parameters
    ----------
    title:
        Group box title, e.g. ``"Plane Points"``.
    get_points:
        Returns the current ``[(label, [x, y, z]), ...]`` in display order.
    add_point:
        Adds a new point with default coordinates and returns nothing;
        the resulting change is picked up via ``changed_signal``.
    update_point:
        ``(label, x, y, z) -> None``, called when a row commits an edit.
    remove_point:
        ``(label) -> None``, called when a row's remove button is clicked.
        May raise; failures are caught and ignored here since the remove
        button is already disabled whenever removal is not allowed.
    min_count:
        The fewest points this list may ever hold. Remove buttons are
        disabled across all rows whenever the current count is at this
        floor.
    changed_signal:
        The Qt signal (from the point manager) that fires whenever the
        underlying point collection changes for ANY reason -- a row edit,
        an add, a remove -- so this panel can reconcile itself.
    """

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
        self.setStyleSheet(_GROUP_STYLE)

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

        add_button = QPushButton(f"+ Add Point")
        add_button.setStyleSheet(_BUTTON_STYLE)
        add_button.clicked.connect(add_point)
        btn_layout.addWidget(add_button)

        if reset_last_point is not None:
            reset_button = QPushButton("Reset")
            reset_button.setStyleSheet(_BUTTON_STYLE)
            reset_button.setToolTip(f"Remove the last point in {title} (one per click)")
            reset_button.clicked.connect(reset_last_point)
            btn_layout.addWidget(reset_button)

        outer.addLayout(btn_layout)

        changed_signal.connect(self._reconcile)
        self._reconcile()

    # ------------------------------------------------------------------
    # Reconciliation -- the core "no Calculate button" wiring for this list
    # ------------------------------------------------------------------

    def _reconcile(self) -> None:
        """Sync displayed rows with the point manager's current state.

        Rows are only ever created or destroyed when the LABEL SET
        changes (a point was added or removed). If the labels are
        unchanged, existing row widgets are refreshed in place -- so a
        user actively typing in one row never has unrelated rows rebuilt
        underneath them.
        """
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
        """Recreate the row widget list to match a changed set of labels."""
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
    # Row event handlers
    # ------------------------------------------------------------------

    def _on_row_committed(self, label: str, x: float, y: float, z: float) -> None:
        self._update_point(label, x, y, z)

    def _on_row_remove_requested(self, label: str) -> None:
        try:
            self._remove_point(label)
        except ValueError:
            # The point manager enforces its own minimum count; the button
            # is already disabled in that state, so this is a defensive
            # no-op rather than a path expected to trigger in practice.
            pass


# ---------------------------------------------------------------------------
# Reference selection (origin: centroid or a chosen plane point)
# ---------------------------------------------------------------------------

class ReferenceSelector(QGroupBox):
    """Dropdown choosing the local coordinate system's origin.

    Signals
    -------
    reference_changed(str)
        Emitted with either the literal string ``"Centroid"`` or a plane
        point label (e.g. ``"PL2"``) whenever the user changes the
        selection. ``main.py`` interprets this string to decide whether to
        call ``CoordinateSystemBuilder.build_at_centroid`` or
        ``build_at_plane_point``.
    """

    reference_changed = pyqtSignal(str)

    _PLACEHOLDER_LABEL = "-- Select Reference Point --"

    def __init__(self, get_plane_labels: Callable[[], list[str]], changed_signal) -> None:
        super().__init__("Reference Selection")
        self.setStyleSheet(_GROUP_STYLE)
        self._get_plane_labels = get_plane_labels

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)

        hint = QLabel("Origin of the local plane coordinate system:")
        hint.setStyleSheet("color: #5a6480; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._combo = QComboBox()
        self._combo.setStyleSheet(
            "QComboBox { background-color: #ffffff; border: 1px solid #c8ccd6; "
            "border-radius: 3px; padding: 4px 6px; font-size: 12px; }"
        )
        layout.addWidget(self._combo)

        changed_signal.connect(self._refresh_items)
        self._refresh_items()
        self._combo.currentTextChanged.connect(self.reference_changed.emit)

    def _refresh_items(self) -> None:
        """Rebuild the dropdown items from the current plane point labels.

        The previously selected item is preserved if it still exists;
        otherwise selection defaults to the placeholder.
        """
        previous_selection = self._combo.currentText() or self._PLACEHOLDER_LABEL

        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(self._PLACEHOLDER_LABEL)
        self._combo.addItems(self._get_plane_labels())

        index = self._combo.findText(previous_selection)
        self._combo.setCurrentIndex(index if index >= 0 else 0)
        self._combo.blockSignals(False)

        # If the selection fell back to Centroid because the previous
        # plane point was removed, downstream listeners must be told --
        # this is a real change, not just a cosmetic combo refresh.
        if index < 0:
            self.reference_changed.emit(self._combo.currentText())

    def current_reference_text(self) -> str:
        """The currently selected item's text (``"Centroid"`` or a plane label)."""
        return self._combo.currentText()

    def reset_to_placeholder(self) -> None:
        """Reset the selection back to "no reference selected".

        Called whenever the underlying point data changes (a point is
        added, edited, or removed) so a previously shown reference-
        relative distance/coordinate is never left on screen stale --
        the user must explicitly reselect a reference point to see
        distances again. A no-op if the placeholder is already selected.
        """
        if self._combo.currentText() != self._PLACEHOLDER_LABEL:
            self._combo.setCurrentIndex(0)


# ---------------------------------------------------------------------------
# Reference -> Inspection distance panel (bottom of Inspection Points)
# ---------------------------------------------------------------------------

class ReferenceDistancePanel(QGroupBox):
    """Sits directly below the Inspection Points list.

    Until a reference point is selected, this panel just shows a hint.
    Once a reference plane point is selected, for every inspection point
    it highlights the straight-line distance from that reference point to
    the inspection point, and shows the inspection point's new
    (reference-relative) coordinate beneath it.

    This class knows nothing about ``PointManager`` or the measurement
    pipeline -- ``main.py`` computes the values and hands them to
    :meth:`display`, exactly like :class:`ResultsPanel`.
    """

    _NO_REFERENCE_TEXT = "Select a reference point to see distances here."
    _NO_INSPECTION_TEXT = "Add an inspection point to see distances here."

    def __init__(self) -> None:
        super().__init__("Reference \u2192 Inspection Distance")
        self.setStyleSheet(_GROUP_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 10, 6, 8)
        outer.setSpacing(6)

        self._placeholder = QLabel(self._NO_REFERENCE_TEXT)
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet("color: #8890a0; font-size: 11px; padding: 2px;")
        outer.addWidget(self._placeholder)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(8)
        outer.addLayout(self._rows_layout)

    def display(
        self,
        reference_label: str | None,
        entries: list[tuple[str, float, tuple[float, float, float]]],
    ) -> None:
        """Rebuild the panel body.

        Parameters
        ----------
        reference_label:
            The currently selected reference plane point's label, or
            ``None`` if no reference has been selected yet.
        entries:
            ``[(inspection_label, distance_to_reference, (x, y, z)), ...]``
            -- ``(x, y, z)`` is the inspection point's NEW coordinate,
            i.e. its coordinate in the reference-relative local frame.
        """
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
        for label, distance, coordinate in entries:
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

        highlight = QLabel(f"{reference_label} \u2192 {label}:  {format_number(distance)}")
        highlight.setStyleSheet(
            "background-color: #fff2c8; color: #7a5a00; font-weight: bold; "
            "font-size: 12px; border: 1px solid #e8d38a; border-radius: 3px; padding: 3px 6px;"
        )
        layout.addWidget(highlight)

        coord_label = QLabel(f"New Coordinate ({label}): {format_vector(np.array(coordinate))}")
        coord_label.setWordWrap(True)
        coord_label.setStyleSheet(
            "color: #3a4055; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;"
        )
        layout.addWidget(coord_label)

        return box

    def _clear_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


# ---------------------------------------------------------------------------
# Left panel: assembles the 3 groups above into one scrollable column
# ---------------------------------------------------------------------------

class LeftPanel(QWidget):
    """The left-hand control column: Plane Points, Inspection Points, Reference."""

    def __init__(
        self,
        plane_points_panel: PointListPanel,
        inspection_points_panel: PointListPanel,
        reference_selector: ReferenceSelector,
        on_reset: Callable[[], None] | None = None,
        reference_distance_panel: "ReferenceDistancePanel | None" = None,
    ) -> None:
        super().__init__()
        self.setMinimumWidth(LEFT_PANEL_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #f5f6f9;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        content = QWidget()
        content.setStyleSheet("background-color: #f5f6f9;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header = QLabel("Best Fit Plane — Controls")
        header.setStyleSheet("color: #3a4a6a; font-size: 13px; font-weight: bold;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self._reset_button = QPushButton("Reset")
        self._reset_button.setStyleSheet(_BUTTON_STYLE)
        self._reset_button.setToolTip("Remove plane points one at a time per click (reverse order)")
        if on_reset is not None:
            self._reset_button.clicked.connect(on_reset)
        header_layout.addWidget(self._reset_button)

        layout.addLayout(header_layout)
        layout.addWidget(_make_separator())

        layout.addWidget(plane_points_panel)
        layout.addWidget(inspection_points_panel)
        if reference_distance_panel is not None:
            layout.addWidget(reference_distance_panel)
        layout.addWidget(reference_selector)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)


# ---------------------------------------------------------------------------
# Right panel: live results table panel (Coordinates & Distances)
# ---------------------------------------------------------------------------

class RightPanel(QWidget):
    """Right-side results panel containing two tabs: 'Coordinates' and 'Distances'."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #f5f6f9;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 12, 8, 12)
        outer.setSpacing(8)

        header = QLabel("Results & Measurements")
        header.setStyleSheet("color: #3a4a6a; font-size: 13px; font-weight: bold;")
        outer.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #c8ccd6; background: #ffffff; border-radius: 4px; } "
            "QTabBar::tab { background: #e8ecf2; padding: 6px 12px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; } "
            "QTabBar::tab:selected { background: #ffffff; color: #1a2b4c; border-bottom: 2px solid #2a5bd7; }"
        )

        # Tab 1: Coordinates Table
        self._coord_table = QTableWidget()
        self._coord_table.setColumnCount(5)
        self._coord_table.setHorizontalHeaderLabels(["Point", "X (Local)", "Y (Local)", "Z / Height", "Distance (d)"])
        self._coord_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._coord_table.setStyleSheet("QTableWidget { font-size: 11px; } QHeaderView::section { font-weight: bold; background-color: #f0f2f7; }")

        # Tab 2: Pairwise Distances Table
        self._dist_table = QTableWidget()
        self._dist_table.setColumnCount(2)
        self._dist_table.setHorizontalHeaderLabels(["Point Pair", "Distance (3D)"])
        self._dist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._dist_table.setStyleSheet("QTableWidget { font-size: 11px; } QHeaderView::section { font-weight: bold; background-color: #f0f2f7; }")

        self._tabs.addTab(self._coord_table, "Coordinates")
        self._tabs.addTab(self._dist_table, "Distances")
        outer.addWidget(self._tabs)

    def display_coordinates(self, rows: list[tuple[str, float, float, float, float]]) -> None:
        """Populate the Coordinates table."""
        self._coord_table.setRowCount(len(rows))
        for r, (label, x, y, z, d) in enumerate(rows):
            item = QTableWidgetItem(f"●  {label}")
            item.setForeground(QColor(0, 0, 0))
            self._coord_table.setItem(r, 0, item)
            self._coord_table.setItem(r, 1, QTableWidgetItem(f"{x:.2f}"))
            self._coord_table.setItem(r, 2, QTableWidgetItem(f"{y:.2f}"))
            self._coord_table.setItem(r, 3, QTableWidgetItem(f"{z:.2f}"))
            self._coord_table.setItem(r, 4, QTableWidgetItem(f"{d:.2f}"))

    def display_distances(self, pairs: list[tuple[str, float]]) -> None:
        """Populate the Pairwise Distances table."""
        self._dist_table.setRowCount(len(pairs))
        for r, (pair_name, dist) in enumerate(pairs):
            item = QTableWidgetItem(f"●  {pair_name}")
            item.setForeground(QColor(0, 0, 0))
            self._dist_table.setItem(r, 0, item)
            self._dist_table.setItem(r, 1, QTableWidgetItem(f"{dist:.2f}"))


# ---------------------------------------------------------------------------
# Right panel: live results display
# ---------------------------------------------------------------------------

class ResultsPanel(QWidget):
    """Read-only display of the current plane fit, frame, and measurements.

    This panel is fully rebuilt on every :meth:`display_results` call. That
    is a deliberate, different choice from the OpenGL widget's
    "never recreate" rule: these are plain text labels with no expensive
    GPU resources and no user-editable state to lose, so a full rebuild
    keeps this class simple with no measurable cost.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(RIGHT_PANEL_MIN_WIDTH)
        self.setMaximumWidth(RIGHT_PANEL_MAX_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #f5f6f9;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        outer.addWidget(self._scroll)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(10, 12, 10, 12)
        self._layout.setSpacing(10)
        self._scroll.setWidget(self._content)

        header = QLabel("Results")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #3a4a6a; font-size: 13px; font-weight: bold;")
        self._layout.addWidget(header)
        self._layout.addWidget(_make_separator())

        self._body_layout = QVBoxLayout()
        self._body_layout.setSpacing(10)
        self._layout.addLayout(self._body_layout)
        self._layout.addStretch()

    def display_results(
        self,
        plane_result: BestFitPlaneResult | None,
        coordinate_system: CoordinateSystem | None,
        measurements: list[PointMeasurement],
    ) -> None:
        """Rebuild the panel body from the current pipeline output.

        Parameters
        ----------
        plane_result:
            The current fitted plane, or ``None`` if fewer than 3 plane
            points exist.
        coordinate_system:
            The current local frame, or ``None`` alongside ``plane_result``.
        measurements:
            One :class:`~measurement.PointMeasurement` per current
            inspection point.
        """
        self._clear_body()

        if plane_result is None or coordinate_system is None:
            warning = QLabel("Add at least 3 plane points to compute a best fit plane.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #a03a3a; font-size: 12px; padding: 6px;")
            self._body_layout.addWidget(warning)
            return

        self._body_layout.addWidget(self._build_plane_fit_group(plane_result))
        self._body_layout.addWidget(self._build_coordinate_system_group(coordinate_system))

        for measurement in measurements:
            self._body_layout.addWidget(self._build_measurement_group(measurement))

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_plane_fit_group(self, plane: BestFitPlaneResult) -> QGroupBox:
        group = QGroupBox("Best Fit Plane")
        group.setStyleSheet(_GROUP_STYLE)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(3)

        layout.addWidget(self._result_line("Centroid", format_vector(plane.centroid)))
        layout.addWidget(self._result_line("Normal", format_vector(plane.normal)))
        layout.addWidget(self._result_line("Equation", plane.plane_equation_string()))
        layout.addWidget(
            self._result_line("RMS Fit Error", format_number(plane.rms_error))
        )
        layout.addWidget(self._result_line("Points Used", str(plane.point_count)))
        return group

    def _build_coordinate_system_group(self, frame: CoordinateSystem) -> QGroupBox:
        group = QGroupBox("Coordinate System")
        group.setStyleSheet(_GROUP_STYLE)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(3)

        reference_text = (
            "Centroid"
            if frame.reference is OriginReference.CENTROID
            else f"Plane Point (index {frame.reference_point_index})"
        )
        layout.addWidget(self._result_line("Reference", reference_text))
        layout.addWidget(self._result_line("Origin", format_vector(frame.origin)))
        layout.addWidget(self._result_line("Local X Axis", format_vector(frame.x_axis)))
        layout.addWidget(self._result_line("Local Y Axis", format_vector(frame.y_axis)))
        layout.addWidget(self._result_line("Local Z Axis", format_vector(frame.z_axis)))
        return group

    def _build_measurement_group(self, measurement: PointMeasurement) -> QGroupBox:
        group = QGroupBox(f"Inspection Point {measurement.label}")
        group.setStyleSheet(_GROUP_STYLE)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(3)

        layout.addWidget(
            self._result_line("World Coordinate", format_vector(measurement.world_coordinates))
        )
        layout.addWidget(
            self._result_line("Plane Coordinate", format_vector(measurement.plane_coordinates.as_array()))
        )
        layout.addWidget(
            self._result_line("Projection on Plane", format_vector(measurement.projection_world))
        )
        layout.addWidget(
            self._result_line(
                "Distance from Plane", format_signed_distance(measurement.distance_to_plane)
            )
        )
        return group

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _result_line(name: str, value: str) -> QWidget:
        """Build a single "Name:  value" row used throughout the results panel."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(f"{name}:")
        name_label.setStyleSheet("color: #5a6480; font-size: 11px;")
        name_label.setFixedWidth(110)

        value_label = QLabel(value)
        value_label.setStyleSheet(
            "color: #2c3040; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;"
        )
        value_label.setWordWrap(True)

        layout.addWidget(name_label)
        layout.addWidget(value_label, 1)
        return row

    def _clear_body(self) -> None:
        """Remove every widget currently in the results body layout."""
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


# ---------------------------------------------------------------------------
# Convenience factory: builds the fully-wired left panel for a PointManager
# ---------------------------------------------------------------------------

def build_left_panel(point_manager) -> tuple[LeftPanel, ReferenceSelector]:
    """Construct a :class:`LeftPanel` fully wired to a live ``PointManager``.

    Kept as a free function (rather than inline in ``main.py``) so the
    wiring between :class:`PointListPanel` / :class:`ReferenceSelector`
    and the concrete ``PointManager`` method names lives in exactly one
    place.

    Parameters
    ----------
    point_manager:
        A :class:`~point_manager.PointManager` instance.

    Returns
    -------
    tuple[LeftPanel, ReferenceSelector]
        The assembled panel, plus the reference selector specifically
        (``main.py`` needs to connect to its ``reference_changed`` signal
        directly to drive the coordinate-system step of the pipeline).
    """
    default_x, default_y, default_z = DEFAULT_NEW_POINT

    plane_panel = PointListPanel(
        title="Plane Points",
        get_points=lambda: list(
            zip(point_manager.plane_point_labels(), point_manager.plane_points_array())
        ),
        add_point=lambda: point_manager.add_plane_point(default_x, default_y, default_z),
        update_point=point_manager.update_plane_point,
        remove_point=point_manager.remove_plane_point,
        min_count=point_manager.MIN_PLANE_POINTS,
        changed_signal=point_manager.plane_points_changed,
    )

    inspection_panel = PointListPanel(
        title="Inspection Points",
        get_points=point_manager.inspection_points,
        add_point=lambda: point_manager.add_inspection_point(default_x, default_y, default_z),
        update_point=point_manager.update_inspection_point,
        remove_point=point_manager.remove_inspection_point,
        min_count=0,
        changed_signal=point_manager.inspection_points_changed,
    )

    reference_selector = ReferenceSelector(
        get_plane_labels=point_manager.plane_point_labels,
        changed_signal=point_manager.plane_points_changed,
    )

    left_panel = LeftPanel(plane_panel, inspection_panel, reference_selector)
    return left_panel, reference_selector