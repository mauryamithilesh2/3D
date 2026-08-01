"""
app/landing/widgets/logo_widget.py
==================================
Header widget displaying Company Logo (SVG), Company Name, Software Name,
Subtitle, and Version Badge in an industrial layout.
"""

from __future__ import annotations

import os
from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


# High precision metrology logo badge SVG fallback
COMPANY_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="56" height="56">
  <defs>
    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00d2ff"/>
      <stop offset="50%" stop-color="#007acc"/>
      <stop offset="100%" stop-color="#004499"/>
    </linearGradient>
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4f8ff7"/>
      <stop offset="100%" stop-color="#00b0ff"/>
    </linearGradient>
  </defs>
  <!-- Background Badge Hexagon/Shield -->
  <rect x="4" y="4" width="72" height="72" rx="18" fill="#141822" stroke="url(#ringGrad)" stroke-width="2"/>
  <!-- Concentric Outer Ring -->
  <circle cx="40" cy="40" r="26" fill="none" stroke="url(#logoGrad)" stroke-width="3"/>
  <!-- Inner Ring -->
  <circle cx="40" cy="40" r="15" fill="none" stroke="#2b3b5c" stroke-width="2" stroke-dasharray="4 2"/>
  <!-- Center Precise Target Dot -->
  <circle cx="40" cy="40" r="4" fill="#ffffff"/>
  <!-- Crosshairs with Tick Marks -->
  <line x1="40" y1="8" x2="40" y2="72" stroke="#00b0ff" stroke-width="2"/>
  <line x1="8" y1="40" x2="72" y2="40" stroke="#00b0ff" stroke-width="2"/>
  <!-- Corner Alignment Nodes -->
  <circle cx="20" cy="20" r="2" fill="#00d2ff"/>
  <circle cx="60" cy="20" r="2" fill="#00d2ff"/>
  <circle cx="20" cy="60" r="2" fill="#00d2ff"/>
  <circle cx="60" cy="60" r="2" fill="#00d2ff"/>
</svg>"""


def create_logo_widget(
    logo_path: str | None = None, size: tuple[int, int] = (110, 80)
) -> QWidget:
    """Create and return a QWidget displaying the logo PNG from assets or fallback SVG."""
    if logo_path is None:
        # Default to assets/logo.png in project root
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        logo_path = os.path.join(base_dir, "assets", "logo.png")

    if os.path.exists(logo_path):
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            label = QLabel()
            label.setFixedSize(size[0], size[1])
            scaled_pm = pixmap.scaled(
                size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            label.setPixmap(scaled_pm)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background: transparent;")
            return label

    # Fallback vector SVG widget
    logo_svg_widget = QSvgWidget()
    logo_svg_widget.setFixedSize(size[0], size[1])
    logo_svg_widget.load(QByteArray(COMPANY_LOGO_SVG.encode("utf-8")))
    return logo_svg_widget


class LogoWidget(QFrame):
    """Header widget displaying corporate branding and metrology software metadata."""

    def __init__(
        self,
        company_name: str = "PRECISION METROLOGY SYSTEMS",
        software_name: str = "Industrial Geometry Measurement System",
        subtitle: str = "Precision Metrology & Coordinate Inspection Platform",
        version: str = "Version 1.0.0",
        logo_path: str | None = None,
        logo_size: tuple[int, int] = (110, 80),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("LogoWidgetContainer")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(20)

        # Logo Icon Widget (loads assets/logo.png)
        logo_icon_widget = create_logo_widget(logo_path=logo_path, size=logo_size)

        # Text Metadata Stack
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        company_label = QLabel(company_name)
        company_label.setObjectName("HeaderCompanyName")

        title_label = QLabel(software_name)
        title_label.setObjectName("HeaderTitle")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("HeaderSubtitle")

        text_layout.addWidget(company_label)
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        # Right-side Version Badge
        version_label = QLabel(version)
        version_label.setObjectName("HeaderVersionBadge")
        version_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(logo_icon_widget)
        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(version_label, alignment=Qt.AlignVCenter)

