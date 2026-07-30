"""
graphics/orientation_widget.py
==============================
A small, fixed-corner XYZ orientation triad overlay -- the "navigation
cube"-style indicator every CAD/CMM viewer has in one corner of the 3-D
view, showing which way the world axes currently point given the camera's
azimuth/elevation.

Implemented as a lightweight transparent child QWidget drawn with QPainter
(2-D projection of the 3 world axes), not as extra OpenGL geometry -- this
keeps it decoupled from the actual GL scene items and their
setData/setMeshData lifecycle.
"""

from __future__ import annotations

from math import cos, radians, sin

import numpy as np
from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from config import ORIENTATION_WIDGET_SIZE
from config.colors import get_color


def _to_qcolor255(rgba: tuple[float, float, float, float], alpha_scale: float = 1.0) -> QColor:
    r, g, b, a = rgba
    color = QColor()
    color.setRgbF(r, g, b, max(0.0, min(1.0, a * alpha_scale)))
    return color


class OrientationTriadWidget(QWidget):
    """Transparent overlay widget drawing a small rotating XYZ triad."""

    def __init__(self, gl_widget) -> None:
        super().__init__(gl_widget)
        self._gl_widget = gl_widget
        self.setFixedSize(ORIENTATION_WIDGET_SIZE, ORIENTATION_WIDGET_SIZE)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    # ------------------------------------------------------------------

    def _camera_basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (right, up, forward) unit vectors for the current camera view."""
        opts = getattr(self._gl_widget, "opts", {})
        elevation = radians(opts.get("elevation", 30))
        azimuth = radians(opts.get("azimuth", 45))

        cam_dir = np.array(
            [cos(elevation) * cos(azimuth), cos(elevation) * sin(azimuth), sin(elevation)]
        )
        norm = np.linalg.norm(cam_dir)
        forward = -cam_dir / norm if norm > 1e-9 else np.array([0.0, 0.0, -1.0])

        world_up = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(forward, world_up)) > 0.999:
            world_up = np.array([0.0, 1.0, 0.0])

        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        return right, up, forward

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.34

        right, up, forward = self._camera_basis()
        axes = (
            ("X", np.array([1.0, 0.0, 0.0]), get_color("COLOR_AXIS_X")),
            ("Y", np.array([0.0, 1.0, 0.0]), get_color("COLOR_AXIS_Y")),
            ("Z", np.array([0.0, 0.0, 1.0]), get_color("COLOR_AXIS_Z")),
        )

        # Draw back-to-front by depth (dot with forward) so nearer axes overlap farther ones.
        entries = []
        for label, axis, color in axes:
            sx = float(np.dot(axis, right))
            sy = float(np.dot(axis, up))
            depth = float(np.dot(axis, forward))
            entries.append((depth, label, sx, sy, color))
        entries.sort(key=lambda e: e[0])

        font = QFont("Consolas", 8, QFont.Bold)
        painter.setFont(font)

        for depth, label, sx, sy, color in entries:
            # Nearer axes (toward camera, depth closer to +1) drawn fuller/brighter.
            alpha_scale = 0.45 + 0.55 * max(0.0, (depth + 1.0) / 2.0)
            end = QPointF(cx + sx * radius, cy - sy * radius)
            pen_color = _to_qcolor255(color, alpha_scale)
            pen = QPen(pen_color)
            pen.setWidthF(2.2)
            painter.setPen(pen)
            painter.drawLine(QPointF(cx, cy), end)
            painter.setBrush(pen_color)
            painter.drawEllipse(end, 3.0, 3.0)
            painter.setPen(QPen(pen_color))
            painter.drawText(end + QPointF(4, 4), label)

        border_color = QColor(100, 105, 120, 160) if get_color("COLOR_VIEWPORT_BG")[0] > 100 else QColor(210, 214, 224, 160)
        painter.setPen(QPen(border_color))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius + 6, radius + 6)
        painter.end()

    def reposition(self) -> None:
        """Pin the widget to the bottom-right corner of its parent viewport."""
        margin = 10
        parent = self._gl_widget
        self.move(
            max(0, parent.width() - self.width() - margin),
            max(0, parent.height() - self.height() - margin),
        )
