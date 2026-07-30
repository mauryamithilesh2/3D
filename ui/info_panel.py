"""
ui/info_panel.py
================
Live numeric readout panel: 3x3 rotation matrix, 4x4 homogeneous
transformation matrix, plane normal, roll/pitch/yaw, plane inclination,
and the active point's world/local coordinates + distance to plane.
"""

from __future__ import annotations

from math import atan2, degrees, sqrt

import numpy as np
from PyQt5.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from ui.styles import get_group_style, get_panel_bg_style, get_ui_color, _make_separator
from utils import format_number, format_vector


def _rotation_matrix_to_rpy_deg(rotation_matrix: np.ndarray) -> tuple[float, float, float]:
    r = rotation_matrix
    pitch = atan2(-r[2, 0], sqrt(r[0, 0] ** 2 + r[1, 0] ** 2))
    roll = atan2(r[2, 1], r[2, 2])
    yaw = atan2(r[1, 0], r[0, 0])
    return degrees(roll), degrees(pitch), degrees(yaw)


def _format_matrix(matrix: np.ndarray) -> str:
    rows = []
    for row in matrix:
        rows.append("  ".join(f"{format_number(v):>9}" for v in row))
    return "\n".join(rows)


def _get_mono_style() -> str:
    return f"color: {get_ui_color('TEXT_PRIMARY')}; font-size: 11px; font-family: 'Consolas', 'Courier New', monospace;"


def _get_mono_muted_style() -> str:
    return f"color: {get_ui_color('TEXT_MUTED')}; font-size: 11px; padding: 2px;"


class _InfoSection(QGroupBox):
    def __init__(self, title: str, placeholder: str) -> None:
        super().__init__(title)
        self.setStyleSheet(get_group_style())
        self._placeholder = placeholder
        self._is_muted = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(4)

        self._label = QLabel(placeholder)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(_get_mono_muted_style())
        layout.addWidget(self._label)

    def set_text(self, text: str | None) -> None:
        if text is None:
            self._is_muted = True
            self._label.setText(self._placeholder)
            self._label.setStyleSheet(_get_mono_muted_style())
        else:
            self._is_muted = False
            self._label.setText(text)
            self._label.setStyleSheet(_get_mono_style())

    def restyle(self) -> None:
        self.setStyleSheet(get_group_style())
        if self._is_muted:
            self._label.setStyleSheet(_get_mono_muted_style())
        else:
            self._label.setStyleSheet(_get_mono_style())


class InfoPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self._content = QWidget()
        self._content.setStyleSheet(get_panel_bg_style())
        layout = QVBoxLayout(self._content)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(8)

        self._reference_section = _InfoSection(
            "Reference Frame", "Origin reference : World Origin"
        )
        layout.addWidget(self._reference_section)
        layout.addWidget(_make_separator())

        self._rotation_section = _InfoSection(
            "Rotation Matrix (3x3)", "--   (need >= 3 plane points)"
        )
        layout.addWidget(self._rotation_section)

        self._transform_section = _InfoSection(
            "Transformation Matrix (4x4, homogeneous)", "--"
        )
        layout.addWidget(self._transform_section)
        layout.addWidget(_make_separator())

        self._normal_section = _InfoSection("Plane Normal", "--")
        layout.addWidget(self._normal_section)

        self._rpy_section = _InfoSection("Roll / Pitch / Yaw (deg)", "--")
        layout.addWidget(self._rpy_section)

        self._inclination_section = _InfoSection(
            "Plane Inclination", "Add at least 3 plane points to see plane inclination."
        )
        layout.addWidget(self._inclination_section)
        layout.addWidget(_make_separator())

        self._active_point_section = _InfoSection(
            "Active Point", "Select or add a point to see its live coordinates here."
        )
        layout.addWidget(self._active_point_section)

        layout.addStretch()

        scroll.setWidget(self._content)
        outer.addWidget(scroll)

        self._last_display_kwargs: dict = {}
        self.display()

    def restyle(self) -> None:
        if hasattr(self, "_content"):
            self._content.setStyleSheet(get_panel_bg_style())
        for section in (
            self._reference_section,
            self._rotation_section,
            self._transform_section,
            self._normal_section,
            self._rpy_section,
            self._inclination_section,
            self._active_point_section,
        ):
            section.restyle()

    def display(
        self,
        rotation_matrix: np.ndarray | None = None,
        origin: np.ndarray | None = None,
        normal: np.ndarray | None = None,
        inclination_x_deg: float | None = None,
        inclination_y_deg: float | None = None,
        reference_label: str | None = None,
        active_label: str | None = None,
        world_coordinates: np.ndarray | None = None,
        local_coordinates: np.ndarray | None = None,
        distance_to_plane: float | None = None,
    ) -> None:
        self._reference_section.set_text(
            f"Origin reference : {reference_label or 'World Origin'}"
        )

        if rotation_matrix is not None:
            self._rotation_section.set_text(_format_matrix(np.asarray(rotation_matrix)))
        else:
            self._rotation_section.set_text(None)

        if rotation_matrix is not None and origin is not None:
            t = np.eye(4)
            t[:3, :3] = rotation_matrix
            t[:3, 3] = origin
            self._transform_section.set_text(_format_matrix(t))
        else:
            self._transform_section.set_text(None)

        self._normal_section.set_text(format_vector(normal) if normal is not None else None)

        if rotation_matrix is not None:
            roll, pitch, yaw = _rotation_matrix_to_rpy_deg(np.asarray(rotation_matrix))
            self._rpy_section.set_text(
                f"Roll:  {format_number(roll)}    "
                f"Pitch: {format_number(pitch)}    "
                f"Yaw:   {format_number(yaw)}"
            )
        else:
            self._rpy_section.set_text(None)

        if inclination_x_deg is not None and inclination_y_deg is not None:
            self._inclination_section.set_text(
                f"X-axis tilt: {format_number(inclination_x_deg)}\u00b0    "
                f"Y-axis tilt: {format_number(inclination_y_deg)}\u00b0"
            )
        else:
            self._inclination_section.set_text(None)

        if world_coordinates is not None:
            title = f"Active Point{'  (' + active_label + ')' if active_label else ''}"
            self._active_point_section.setTitle(title)
            local_text = (
                format_vector(local_coordinates) if local_coordinates is not None else "--"
            )
            distance_text = (
                format_number(distance_to_plane) if distance_to_plane is not None else "--"
            )
            self._active_point_section.set_text(
                f"World coordinates : {format_vector(world_coordinates)}\n"
                f"Local coordinates : {local_text}\n"
                f"Distance to plane : {distance_text}"
            )
        else:
            self._active_point_section.setTitle("Active Point")
            self._active_point_section.set_text(None)
