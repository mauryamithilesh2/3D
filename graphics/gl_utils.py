"""
graphics/gl_utils.py
====================
Helper functions for color format conversion between config RGBA float tuples,
QColor instances, and pyqtgraph NumPy color arrays.
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtGui import QColor


def _to_qcolor(color_tuple: tuple[float, ...] | tuple[int, ...]) -> QColor:
    """Convert a config color tuple (RGB 0-255 or RGBA float 0-1) to a QColor."""
    if len(color_tuple) == 3:
        r, g, b = color_tuple
        if isinstance(r, int) and r > 1:
            return QColor(r, g, b)
        color = QColor()
        color.setRgbF(float(r), float(g), float(b), 1.0)
        return color
    elif len(color_tuple) == 4:
        r, g, b, a = color_tuple
        if isinstance(r, int) and r > 1:
            alpha = int(a * 255) if isinstance(a, float) else a
            return QColor(r, g, b, alpha)
        color = QColor()
        color.setRgbF(float(r), float(g), float(b), float(a))
        return color
    return QColor()


def _make_color_array(color: tuple[float, float, float, float], count: int) -> np.ndarray:
    """Return an (N, 4) float32 numpy array of RGBA colors for GLScatterPlotItem VBO compatibility."""
    if count <= 0:
        return np.empty((0, 4), dtype=np.float32)
    return np.tile(np.array(color, dtype=np.float32), (count, 1))


def _lerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """Linearly interpolate two same-shaped arrays: ``a + (b - a) * t``.

    Pure display-layer helper used by the animation controller to produce
    in-between frames for smooth transitions -- never touches any of the
    underlying measurement/plane math.
    """
    return a + (b - a) * float(t)


def _ease_out_cubic(t: float) -> float:
    """Standard ease-out-cubic easing curve, ``t`` in ``[0, 1]``."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _make_cone_mesh(
    axis_dir: np.ndarray,
    apex: np.ndarray,
    height: float,
    radius: float,
    segments: int = 14,
):
    """Build a solid cone :class:`~pyqtgraph.opengl.MeshData` used as an arrowhead."""
    import pyqtgraph.opengl as gl

    axis = np.asarray(axis_dir, dtype=np.float64)
    norm = np.linalg.norm(axis)
    axis = axis / norm if norm > 1e-12 else np.array([0.0, 0.0, 1.0])

    helper = np.array([1.0, 0.0, 0.0]) if abs(axis[2]) < 0.999 else np.array([0.0, 1.0, 0.0])
    u = np.cross(helper, axis)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)

    base_center = np.asarray(apex, dtype=np.float64) - axis * height
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    ring = np.array(
        [base_center + radius * (np.cos(a) * u + np.sin(a) * v) for a in angles]
    )

    vertexes = np.vstack([[apex], [base_center], ring])
    apex_idx, base_idx = 0, 1
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append([apex_idx, 2 + i, 2 + j])
        faces.append([base_idx, 2 + j, 2 + i])

    return gl.MeshData(vertexes=vertexes, faces=np.array(faces))
