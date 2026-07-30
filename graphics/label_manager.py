"""
graphics/label_manager.py
=========================
GLTextItem label lifecycle management (create, update, prune).
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtGui import QFont

from config.colors import get_color
from graphics.gl_utils import _to_qcolor

_LABEL_FONT = QFont("Consolas", 9)


def _sync_labels(
    widget: gl.GLViewWidget,
    existing: dict[str, gl.GLTextItem],
    desired: dict[str, tuple[np.ndarray, tuple[float, float, float, float], str]],
) -> None:
    """Reconcile a label dict with the current set of points."""
    # Remove labels for points that no longer exist.
    for stale_label in list(existing.keys() - desired.keys()):
        widget.removeItem(existing[stale_label])
        del existing[stale_label]

    label_color = _to_qcolor(get_color("COLOR_LABEL_TEXT"))

    # Add or update labels for current points.
    for label, (position, _color, text) in desired.items():
        text_position = position + np.array([0.0, 0.0, 0.4])
        if label in existing:
            existing[label].setData(pos=text_position, text=text, color=label_color)
            existing[label].setVisible(True)
        else:
            item = gl.GLTextItem(
                pos=text_position, text=text, color=label_color, font=_LABEL_FONT
            )
            widget.addItem(item)
            existing[label] = item
