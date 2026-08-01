"""
app/landing/widgets/module_card.py
==================================
Reusable industrial module card widget with SVG icon, feature list, open button,
rounded corners, soft shadow, and hover/pressed animation effects.
"""

from __future__ import annotations

from typing import Any, Dict, List
from PyQt5.QtCore import QByteArray, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ModuleCard(QFrame):
    """Interactive industrial card widget representing a metrology measurement module."""

    module_selected = pyqtSignal(str)

    def __init__(self, config: Dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ModuleCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self._module_id: str = config.get("id", "")
        self._title: str = config.get("title", "")
        self._subtitle: str = config.get("subtitle", "")
        self._badge: str = config.get("badge", "")
        self._description: List[str] = config.get("description", [])
        self._icon_svg: str = config.get("icon_svg", "")
        self._button_text: str = config.get("button_text", "Open Module")

        self.setMinimumWidth(280)
        self.setMinimumHeight(380)

        # Drop Shadow Effect for soft depth & hover elevation
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(16)
        self._shadow.setColor(QColor(15, 23, 42, 40))
        self._shadow.setOffset(0, 4)
        self.setGraphicsEffect(self._shadow)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct card layout hierarchy."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Row: Badge & SVG Icon
        top_row = QHBoxLayout()

        badge_label = QLabel(self._badge)
        badge_label.setObjectName("CardBadge")

        icon_widget = QSvgWidget()
        icon_widget.setFixedSize(52, 52)
        if self._icon_svg:
            icon_widget.load(QByteArray(self._icon_svg.encode("utf-8")))

        top_row.addWidget(badge_label, alignment=Qt.AlignLeft | Qt.AlignTop)
        top_row.addStretch()
        top_row.addWidget(icon_widget, alignment=Qt.AlignRight | Qt.AlignTop)

        # Title & Subtitle Stack
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title_label = QLabel(self._title)
        title_label.setObjectName("CardTitle")
        title_label.setWordWrap(True)

        subtitle_label = QLabel(self._subtitle)
        subtitle_label.setObjectName("CardSubtitle")

        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)

        # Feature List Bullets
        bullet_box = QVBoxLayout()
        bullet_box.setSpacing(8)
        bullet_box.setContentsMargins(0, 8, 0, 8)

        for item in self._description:
            row = QHBoxLayout()
            row.setSpacing(8)

            dot = QLabel("•")
            dot.setStyleSheet("color: #2563eb; font-weight: bold; font-size: 14px;")

            bullet_text = QLabel(item)
            bullet_text.setObjectName("CardBulletItem")

            row.addWidget(dot)
            row.addWidget(bullet_text, stretch=1)
            bullet_box.addLayout(row)

        bullet_box.addStretch()

        # Action Button
        self.open_button = QPushButton(self._button_text)
        self.open_button.setObjectName("OpenModuleBtn")
        self.open_button.setCursor(Qt.PointingHandCursor)
        self.open_button.clicked.connect(self._on_button_clicked)

        layout.addLayout(top_row)
        layout.addLayout(title_box)
        layout.addLayout(bullet_box, stretch=1)
        layout.addWidget(self.open_button)

    def enterEvent(self, event: Any) -> None:
        """Hover Animation: Increase shadow intensity on mouse enter."""
        self._shadow.setBlurRadius(24)
        self._shadow.setColor(QColor(37, 99, 235, 80))
        self._shadow.setOffset(0, 8)
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        """Hover Animation: Reset shadow on mouse leave."""
        self._shadow.setBlurRadius(16)
        self._shadow.setColor(QColor(15, 23, 42, 40))
        self._shadow.setOffset(0, 4)
        super().leaveEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        """Pressed Animation: Visual shift on card press."""
        if event.button() == Qt.LeftButton:
            self._shadow.setOffset(0, 2)
            self._on_button_clicked()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Reset shadow offset after press release."""
        self._shadow.setOffset(0, 8 if self.underMouse() else 4)
        super().mouseReleaseEvent(event)

    def _on_button_clicked(self) -> None:
        """Emit module selection signal."""
        self.module_selected.emit(self._module_id)
