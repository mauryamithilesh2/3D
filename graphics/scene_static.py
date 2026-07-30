"""
graphics/scene_static.py
========================
Static scene item builder for grid floor, world axes, and fixed axis labels.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtGui import QFont

from config import GRID_SIZE, GRID_SPACING
from config.colors import get_color
from graphics.gl_utils import _to_qcolor

_WORLD_AXIS_LENGTH = GRID_SIZE / 2.0
_LABEL_FONT = QFont("Consolas", 9)


def _build_static_items(widget: gl.GLViewWidget) -> None:
    """Create the grid and world axes -- items that never move."""
    grid = gl.GLGridItem()
    grid.setSize(GRID_SIZE, GRID_SIZE)
    grid.setSpacing(GRID_SPACING, GRID_SPACING)
    grid.setColor(_to_qcolor(get_color("COLOR_GRID_DARK")))
    widget.addItem(grid)
    widget._grid = grid

    widget._axis_x = _make_axis_line(
        widget, np.array([[-_WORLD_AXIS_LENGTH, 0, 0], [_WORLD_AXIS_LENGTH, 0, 0]]), get_color("COLOR_AXIS_X")
    )
    widget._axis_y = _make_axis_line(
        widget, np.array([[0, -_WORLD_AXIS_LENGTH, 0], [0, _WORLD_AXIS_LENGTH, 0]]), get_color("COLOR_AXIS_Y")
    )
    widget._axis_z = _make_axis_line(
        widget, np.array([[0, 0, -_WORLD_AXIS_LENGTH], [0, 0, _WORLD_AXIS_LENGTH]]), get_color("COLOR_AXIS_Z")
    )

    # Static axis labels at BOTH ends of every world axis line. References
    # are kept so the "Global Axes" toolbar toggle can hide them together
    # with the axis lines themselves. Text always renders in the shared
    # COLOR_LABEL_TEXT so the direction symbols stay easily readable;
    # the axis lines themselves keep their original per-axis colors.
    widget._axis_label_items = []
    for text, pos in (
        ("+X", np.array([_WORLD_AXIS_LENGTH + 0.5, 0.0, 0.0])),
        ("-X", np.array([-_WORLD_AXIS_LENGTH - 0.5, 0.0, 0.0])),
        ("+Y", np.array([0.0, _WORLD_AXIS_LENGTH + 0.5, 0.0])),
        ("-Y", np.array([0.0, -_WORLD_AXIS_LENGTH - 0.5, 0.0])),
        ("+Z", np.array([0.0, 0.0, _WORLD_AXIS_LENGTH + 0.5])),
        ("-Z", np.array([0.0, 0.0, -_WORLD_AXIS_LENGTH - 0.5])),
    ):
        item = gl.GLTextItem(
            pos=pos, text=text, color=_to_qcolor(get_color("COLOR_LABEL_TEXT")), font=_LABEL_FONT
        )
        widget.addItem(item)
        widget._axis_label_items.append(item)


def _make_axis_line(
    widget: gl.GLViewWidget, pos: np.ndarray, color: tuple[float, float, float, float]
) -> gl.GLLinePlotItem:
    """Create and register a single persistent world-axis line item."""
    item = gl.GLLinePlotItem(
        pos=pos, color=color, width=2.5, mode="lines", antialias=True, glOptions="opaque"
    )
    widget.addItem(item)
    return item
