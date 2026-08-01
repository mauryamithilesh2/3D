"""
app/landing/landing_window.py
=============================
Main QMainWindow landing page window serving as the application entry point and module selector.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow

from app.landing.landing_page import LandingPage
from app.landing.landing_style import LANDING_STYLE_SHEET


class LandingWindow(QMainWindow):
    """Top-level landing window presenting metrology module selection before launching MainWindow."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Industrial Geometry Measurement System - Precision Metrology Platform")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 680)

        # Apply dark industrial styling
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(LANDING_STYLE_SHEET)

        # Central landing widget
        self._landing_page = LandingPage(self)
        self._landing_page.module_selected.connect(self._on_module_selected)
        self.setCentralWidget(self._landing_page)

        self._module_windows: list = []

    def _on_module_selected(self, module_id: str) -> None:
        """Handle module selection: launch the registered window for this
        module in a new window while keeping LandingWindow open."""
        from app.module_registry import create_module_window

        window = create_module_window(module_id)
        window.showMaximized()
        self._module_windows.append(window)
