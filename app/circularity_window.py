"""
app/circularity_window.py
==========================
Top-level window for the Circularity & Concentricity module.
Subclasses ``BaseModuleWindow`` to follow standard module window chrome and toolbar contract.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSplitter

from app.base_window import BaseModuleWindow
from graphics.circularity_gl_widget import CircularityGLWidget
from ui.circularity_panel import CircularityPanel

_CIRCULARITY_TOGGLES: tuple[tuple[str, str, str], ...] = (
    ("grid", "Grid", "Show/Hide the reference floor grid"),
    ("global_axes", "Global Axes", "Show/Hide the world X/Y/Z axes"),
)


class CircularityWindow(BaseModuleWindow):
    """Hosts the concentricity input/result panel alongside a 3D view of
    the two hole centers and the axial/radial misalignment breakdown."""

    def __init__(self) -> None:
        super().__init__()
        self._init_chrome("Circularity & Concentricity")

        self._central_panel = CircularityPanel()
        self._gl_widget = CircularityGLWidget()

        self._init_toolbar(self._gl_widget, _CIRCULARITY_TOGGLES)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._central_panel)
        splitter.addWidget(self._gl_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 760])
        self.setCentralWidget(splitter)

        self._central_panel.measured.connect(self._gl_widget.update_scene)
        # Draw once at startup with the panel's default values.
        self._central_panel.measure()
