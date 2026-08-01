"""
app/landing/landing_page.py
===========================
Central Landing Page component assembling the header logo widget, dynamic module card
grid from module_config, and bottom industrial status bar.
"""

from __future__ import annotations

from typing import Any
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.landing.module_config import MODULES
from app.landing.widgets import LogoWidget, ModuleCard


class LandingPage(QWidget):
    """Main Landing Page composite widget containing header, dynamic module grid, and status bar."""

    module_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LandingPageContainer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct full page layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Section Header Logo Widget
        self._header = LogoWidget(
            company_name="KADENCE AUTOMATION & ROBOTICS SYSTEMS",
            software_name="Industrial Geometry Measurement System",
            subtitle="Precision Metrology & Coordinate Inspection Platform",
            version="Version 1.0.0",
        )
        main_layout.addWidget(self._header)

        # 2. Center Section Scrollable Module Grid Container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")

        center_content = QWidget()
        center_content.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center_content)
        center_layout.setContentsMargins(40, 36, 40, 36)
        center_layout.setSpacing(24)

        # Section Header Tagline
        section_tag = QLabel("SELECT MEASUREMENT MODULE")
        section_tag.setStyleSheet(
            "color: #2563eb; font-size: 13px; font-weight: 800; letter-spacing: 2px;"
        )
        center_layout.addWidget(section_tag)

        # Horizontal Row / Dynamic Card Grid
        cards_row = QHBoxLayout()
        cards_row.setSpacing(24)
        cards_row.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        for mod_config in MODULES:
            card = ModuleCard(mod_config)
            card.module_selected.connect(self.module_selected.emit)
            cards_row.addWidget(card)

        center_layout.addLayout(cards_row)
        center_layout.addStretch()

        scroll_area.setWidget(center_content)
        main_layout.addWidget(scroll_area, stretch=1)

        # 3. Bottom Section Industrial Status Bar
        self._status_bar = self._build_status_bar()
        main_layout.addWidget(self._status_bar)

    def _build_status_bar(self) -> QFrame:
        """Construct bottom industrial status bar."""
        bar = QFrame()
        bar.setObjectName("LandingStatusBar")
        bar.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(32, 10, 32, 10)
        layout.setSpacing(16)

        # Left Info Labels
        sys_status_pill = QLabel("● SYSTEM READY")
        sys_status_pill.setObjectName("StatusPillReady")

        license_pill = QLabel("LICENSE: ENTERPRISE ACTIVE")
        license_pill.setObjectName("StatusPillLicense")

        ver_text = QLabel("System Version: 1.0.0")
        ver_text.setObjectName("StatusText")

        comp_text = QLabel("Precision Metrology Corp.")
        comp_text.setObjectName("StatusText")

        copyright_text = QLabel("© 2026 Kadence Automation & Robotics System. All Rights Reserved.")
        copyright_text.setObjectName("StatusText")

        layout.addWidget(sys_status_pill)
        layout.addWidget(license_pill)
        layout.addWidget(ver_text)
        layout.addWidget(comp_text)
        layout.addStretch()
        layout.addWidget(copyright_text)

        return bar
