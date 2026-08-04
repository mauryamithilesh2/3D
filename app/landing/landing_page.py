"""
app/landing/landing_page.py
===========================
Central Landing Page component assembling the header logo widget, dynamic module card
grid from module_config, and bottom industrial status bar.
"""

from __future__ import annotations

from typing import Any
from PyQt5.QtCore import QThread,Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


from app.landing.module_config import MODULES
from app.landing.widgets import LogoWidget, ModuleCard,StatusPill
from plc import connection_manager as plc_conn

class _PlcConnectWorker(QThread):
    """Runs the blocking plc_conn.connect() call off the main/GUI thread so
    the UI stays responsive during the (up to ~3s) connection attempt."""

    result_ready = pyqtSignal(bool)

    def __init__(self, ip: str, port: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ip = ip
        self._port = port

    def run(self) -> None:
        ok = plc_conn.connect(self._ip, self._port)
        self.result_ready.emit(ok)

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
        # Wire the Connect button now that plc_connect_btn/plc_status_pill exist
        self.plc_connect_btn.clicked.connect(self._on_plc_connect_clicked)


    def _build_status_bar(self) -> QFrame:
        """Construct bottom industrial status bar."""
        bar = QFrame()
        bar.setObjectName("LandingStatusBar")
        bar.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(32, 10, 32, 10)
        layout.setSpacing(16)

        # Left Info Labels
        # StatusPill starts "idle" (yellow) — nothing has attempted a PLC
        # connection yet. A later step will flip this to ok()/error() based
        # on the real connection result.
        self.plc_status_pill = StatusPill()
                # PLC Connection Fields -- UI only for now. Step 4 will wire
        # self.plc_connect_btn.clicked to an actual PLCConnection.connect()
        # call and flip self.plc_status_pill accordingly.
        self.plc_ip_input = QLineEdit()
        self.plc_ip_input.setObjectName("PlcIpInput")
        self.plc_ip_input.setPlaceholderText("PLC IP")
        self.plc_ip_input.setText("127.0.0.1")
        self.plc_ip_input.setFixedWidth(110)

        self.plc_port_input = QLineEdit()
        self.plc_port_input.setObjectName("PlcPortInput")
        self.plc_port_input.setPlaceholderText("Port")
        self.plc_port_input.setText("502")
        self.plc_port_input.setFixedWidth(60)

        self.plc_connect_btn = QPushButton("CONNECT")
        self.plc_connect_btn.setObjectName("PlcConnectBtn")

        license_pill = QLabel("LICENSE: ENTERPRISE ACTIVE")
        license_pill.setObjectName("StatusPillLicense")

        ver_text = QLabel("System Version: 1.0.0")
        ver_text.setObjectName("StatusText")

        comp_text = QLabel("Precision Metrology Corp.")
        comp_text.setObjectName("StatusText")

        copyright_text = QLabel("© 2026 Kadence Automation & Robotics System. All Rights Reserved.")
        copyright_text.setObjectName("StatusText")

        layout.addWidget(self.plc_status_pill)
        layout.addWidget(self.plc_ip_input)
        layout.addWidget(self.plc_port_input)
        layout.addWidget(self.plc_connect_btn)
        layout.addWidget(license_pill)
        layout.addWidget(ver_text)
        layout.addWidget(comp_text)
        layout.addStretch()
        layout.addWidget(copyright_text)

        return bar
    
    def _on_plc_connect_clicked(self) -> None:
            """Connect/disconnect using the shared PLC connection singleton
            (plc/connection_manager.py). The actual connect() call runs on a
            background QThread (_PlcConnectWorker) so a slow/unreachable PLC
            doesn't freeze the UI -- the real result is picked up later in
            _on_plc_connect_result(), never faked here."""
            if plc_conn.is_connected():
                plc_conn.disconnect()
                self.plc_status_pill.set_idle()
                self.plc_connect_btn.setText("CONNECT")
                return

            ip = self.plc_ip_input.text().strip()
            port = self.plc_port_input.text().strip()

            if not ip or not port:
                self.plc_status_pill.set_error("● INVALID IP/PORT")
                return

            self.plc_status_pill.set_idle("● CONNECTING…")
            self.plc_connect_btn.setEnabled(False)

            self._connect_worker = _PlcConnectWorker(ip, port, self)
            self._connect_worker.result_ready.connect(self._on_plc_connect_result)
            self._connect_worker.start()


    def _on_plc_connect_result(self, ok: bool) -> None:
        """Runs on the main thread (Qt marshals queued-connection signals
        back automatically) once _PlcConnectWorker finishes."""
        self.plc_connect_btn.setEnabled(True)
        if ok:
            self.plc_status_pill.set_ok()
            self.plc_connect_btn.setText("DISCONNECT")
        else:
            self.plc_status_pill.set_error("● CONNECTION FAILED")
            self.plc_connect_btn.setText("CONNECT")