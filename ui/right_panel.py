"""
ui/right_panel.py
=================
Right-hand results panel: Coordinates (World + Local) and Pairwise Distances
tabbed tables, plus a live numeric "Info" panel (rotation/transform matrices,
normal, RPY, inclination, distances) fed straight from already-computed
core results.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.info_panel import InfoPanel
from ui.styles import get_panel_header_style, get_table_style, get_tab_widget_style
from utils import format_number


class RightPanel(QWidget):
    """Right-side results panel: 'Coordinates', 'Distances', and 'Live Info' tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setObjectName("rightPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 12, 10, 12)
        outer.setSpacing(8)

        self._header = QLabel("Results && Measurements")
        self._header.setStyleSheet(get_panel_header_style())
        outer.addWidget(self._header)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(get_tab_widget_style())

        # Tab 1: Local (Plane-Relative) Coordinates Table
        self._local_table = QTableWidget()
        self._local_table.setColumnCount(5)
        self._local_table.setHorizontalHeaderLabels(["Point", "X", "Y", "Z", "Dist"])
        self._local_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._local_table.verticalHeader().setVisible(False)
        self._local_table.setStyleSheet(get_table_style())
        self._local_table.setAlternatingRowColors(True)

        # Tab 2: Pairwise Distances Table
        self._dist_table = QTableWidget()
        self._dist_table.setColumnCount(2)
        self._dist_table.setHorizontalHeaderLabels(["Point Pair", "Distance (3D)"])
        self._dist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._dist_table.verticalHeader().setVisible(False)
        self._dist_table.setStyleSheet(get_table_style())
        self._dist_table.setAlternatingRowColors(True)

        # Tab 3: Live Info (matrices, normal, RPY, inclination, distances)
        self._info_panel = InfoPanel()

        self._tabs.addTab(self._local_table, "Local Coordinates")
        self._tabs.addTab(self._dist_table, "Distances")
        self._tabs.addTab(self._info_panel, "Live Info")
        outer.addWidget(self._tabs)

        # Caller-supplied GD&T result widget (Perpendicularity, Parallelism,
        # future Angularity, ...). RightPanel never imports or knows about
        # any specific GD&T check -- see add_orientation_panel below.
        self._orientation_panel: QWidget | None = None

    def restyle(self) -> None:
        """Re-apply active theme styles to header, tabs, tables, and info panel."""
        if hasattr(self, "_header"):
            self._header.setStyleSheet(get_panel_header_style())
        if hasattr(self, "_tabs"):
            self._tabs.setStyleSheet(get_tab_widget_style())
        table_style = get_table_style()
        if hasattr(self, "_local_table"):
            self._local_table.setStyleSheet(table_style)
        if hasattr(self, "_dist_table"):
            self._dist_table.setStyleSheet(table_style)
        if hasattr(self, "_info_panel") and hasattr(self._info_panel, "restyle"):
            self._info_panel.restyle()
        if self._orientation_panel is not None and hasattr(self._orientation_panel, "restyle"):
            self._orientation_panel.restyle()

    def display_coordinates(
        self, rows: list[tuple[str, float, float, float, float, float, float, float]]
    ) -> None:
        """Populate the Local coordinates table."""
        self._local_table.setRowCount(len(rows))
        for r, (label, wx, wy, wz, lx, ly, lz, d) in enumerate(rows):
            self._local_table.setItem(r, 0, QTableWidgetItem(f"\u25cf  {label}"))
            for c, value in enumerate((lx, ly, lz, d), start=1):
                cell = QTableWidgetItem(format_number(value))
                cell.setTextAlignment(0x84)  # AlignRight | AlignVCenter
                self._local_table.setItem(r, c, cell)

    def display_distances(self, pairs: list[tuple[str, float]]) -> None:
        """Populate the Pairwise Distances table."""
        self._dist_table.setRowCount(len(pairs))
        for r, (pair_name, dist) in enumerate(pairs):
            item = QTableWidgetItem(f"\u25cf  {pair_name}")
            self._dist_table.setItem(r, 0, item)
            cell = QTableWidgetItem(format_number(dist))
            cell.setTextAlignment(0x84)
            self._dist_table.setItem(r, 1, cell)

    def display_info(self, **kwargs) -> None:
        """Forward live numeric data to the Info tab. See :class:`InfoPanel.display`."""
        self._info_panel.display(**kwargs)

    def add_orientation_panel(self, panel: QWidget, label: str = "Orientation") -> None:
        """Insert a shared orientation-style GD&T result panel (e.g.
        ui.orientation_result_panel.OrientationResultPanel) as the FIRST
        tab, shown by default -- not appended after Local Coordinates.
        Wrapped in its own compact container (panel + stretch) instead of
        being added directly, so it sits at its natural size at the top of
        the tab instead of being stretched to fill the whole tab area.
        RightPanel never imports or knows about any specific GD&T check."""
        if self._orientation_panel is not None:
            return
        self._orientation_panel = panel

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 6, 4, 6)
        container_layout.setSpacing(0)
        container_layout.addWidget(panel)
        container_layout.addStretch()

        self._tabs.insertTab(0, container, label)
        self._tabs.setCurrentIndex(0)

    def set_pairwise_distances_visible(self, visible: bool) -> None:
        """Hide the Distances (pairwise point-to-point) tab for modules
        where it has no GD&T meaning -- e.g. Perpendicularity/Parallelism
        compare two planes, not point pairs."""
        index = self._tabs.indexOf(self._dist_table)
        if index != -1 and not visible:
            self._tabs.removeTab(index)

    def set_live_info_visible(self, visible: bool) -> None:
        """Hide the Live Info tab for modules where the shared Orientation
        Result Panel already IS the live result -- keeps the right panel
        for Perpendicularity/Parallelism small and focused instead of
        repeating the same information in two places."""
        index = self._tabs.indexOf(self._info_panel)
        if index != -1 and not visible:
            self._tabs.removeTab(index)