"""
ui/left_panel.py
================
Left-hand control column assembling plane points, inspection points, reference selection, and distance panels.
"""

from __future__ import annotations

from typing import Callable

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import LEFT_PANEL_MIN_WIDTH

from ui.edge_axis_selector import EdgeAxisSelector
from ui.plane_angle_panel import PlaneAnglePanel
from ui.point_list_panel import PointListPanel

from ui.reference_distance_panel import ReferenceDistancePanel
from ui.reference_selector import ReferenceSelector
from ui.styles import (
    get_button_style,
    get_panel_bg_style,
    get_panel_header_style,
    get_ui_color,
    _make_separator,
)


class LeftPanel(QWidget):
    """The left-hand control column: Plane Points, Plane Inclination, Inspection Points, Reference."""

    def __init__(
        self,
        plane_points_panel: PointListPanel,
        inspection_points_panel: PointListPanel,
        reference_selector: ReferenceSelector,
        on_reset: Callable[[], None] | None = None,
        reference_distance_panel: ReferenceDistancePanel | None = None,
        plane_angle_panel: PlaneAnglePanel | None = None,
        edge_axis_selector: EdgeAxisSelector | None = None,
        show_reference_selector: bool = True,
    ) -> None:
        super().__init__()
        self._plane_points_panel = plane_points_panel
        self._inspection_points_panel = inspection_points_panel
        self._reference_selector = reference_selector
        self._reference_distance_panel = reference_distance_panel
        self._plane_angle_panel = plane_angle_panel
        self._edge_axis_selector = edge_axis_selector

        self.setMinimumWidth(LEFT_PANEL_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet(get_panel_bg_style())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet(get_panel_bg_style())
        layout = QVBoxLayout(self._content_widget)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        self._header_label = QLabel("Best Fit Plane — Controls")
        self._header_label.setStyleSheet(get_panel_header_style())
        header_layout.addWidget(self._header_label)
        header_layout.addStretch()

        self._reset_button = QPushButton("Reset")
        self._reset_button.setStyleSheet(get_button_style())
        self._reset_button.setToolTip("Remove plane points one at a time per click (reverse order)")
        if on_reset is not None:
            self._reset_button.clicked.connect(on_reset)
        header_layout.addWidget(self._reset_button)

        layout.addLayout(header_layout)
        self._separator = _make_separator()
        layout.addWidget(self._separator)

        layout.addWidget(plane_points_panel)
        if plane_angle_panel is not None:
            layout.addWidget(plane_angle_panel)
        layout.addWidget(inspection_points_panel)

        if reference_distance_panel is not None:
            layout.addWidget(reference_distance_panel)
        if show_reference_selector:
            layout.addWidget(reference_selector)
        if edge_axis_selector is not None:
            layout.addWidget(edge_axis_selector)
        layout.addStretch()

        scroll.setWidget(self._content_widget)
        outer.addWidget(scroll)

    def restyle(self) -> None:
        """Re-apply active theme styles to panel and child sub-panels."""
        self.setStyleSheet(get_panel_bg_style())
        if hasattr(self, "_content_widget"):
            self._content_widget.setStyleSheet(get_panel_bg_style())
        if hasattr(self, "_header_label"):
            self._header_label.setStyleSheet(get_panel_header_style())
        if hasattr(self, "_reset_button"):
            self._reset_button.setStyleSheet(get_button_style())
        if hasattr(self, "_separator"):
            b = get_ui_color("BORDER")
            self._separator.setStyleSheet(f"color: {b}; background-color: {b}; max-height: 1px;")

        for widget in (
            self._plane_points_panel,
            self._inspection_points_panel,
            self._reference_selector,
            self._reference_distance_panel,
            self._plane_angle_panel,
            self._edge_axis_selector,
        ):
            
            if widget is not None and hasattr(widget, "restyle"):
                widget.restyle()