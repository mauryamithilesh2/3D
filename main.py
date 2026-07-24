"""
main.py
=======
Application entry point for the 3-D widget demo.

Responsibilities
----------------
* Bootstrap the QApplication with the correct OpenGL/HiDPI attributes.
* Construct and wire :class:`GL3DWidget` and :class:`ControlPanel`.
* Assemble the main window layout (3-D view left, control panel right).
* Start the Qt event loop.

Run directly with::

    python main.py

Compatible with Python 3.11+, PyQt5 ≥ 5.15.9, pyqtgraph ≥ 0.13.3.
"""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from control_panel import ControlPanel
from gl3d_widget import GL3DWidget


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Primary application window.

    Lays out the :class:`GL3DWidget` on the left and the
    :class:`ControlPanel` on the right, wires their signals, and applies a
    cohesive dark-theme palette to the window chrome.

    Parameters
    ----------
    parent:
        Optional Qt parent widget (``None`` for a top-level window).
    """

    _WINDOW_TITLE: str = "3D Scene Viewer — PyQt5 + pyqtgraph.opengl"
    _MIN_WIDTH: int = 860
    _MIN_HEIGHT: int = 540
    _DEFAULT_WIDTH: int = 1280
    _DEFAULT_HEIGHT: int = 740
    _SPLITTER_HANDLE_WIDTH: int = 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gl_widget = GL3DWidget(self)
        self._control_panel = ControlPanel(self)
        self._setup_window()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure the window title, size, and palette."""
        self.setWindowTitle(self._WINDOW_TITLE)
        self.setMinimumSize(self._MIN_WIDTH, self._MIN_HEIGHT)
        self.resize(self._DEFAULT_WIDTH, self._DEFAULT_HEIGHT)
        self._apply_light_palette()

    def _apply_light_palette(self) -> None:
        """Apply a clean light-mode colour palette to the window."""
        palette = QPalette()
        bg = QColor(245, 246, 249)        # near-white
        panel_bg = QColor(255, 255, 255)  # white
        text = QColor(44, 48, 64)         # dark charcoal
        accent = QColor(58, 106, 181)     # muted blue
        mid = QColor(220, 222, 230)

        palette.setColor(QPalette.Window, bg)
        palette.setColor(QPalette.WindowText, text)
        palette.setColor(QPalette.Base, panel_bg)
        palette.setColor(QPalette.AlternateBase, QColor(235, 237, 243))
        palette.setColor(QPalette.Text, text)
        palette.setColor(QPalette.BrightText, Qt.black)
        palette.setColor(QPalette.Button, QColor(235, 237, 242))
        palette.setColor(QPalette.ButtonText, text)
        palette.setColor(QPalette.Highlight, accent)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, text)

        self.setPalette(palette)
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f6f9;
            }
            QSplitter::handle {
                background-color: #d0d4de;
            }
            QSplitter::handle:hover {
                background-color: #a8b8d0;
            }
            QStatusBar {
                background-color: #eceef2;
                color: #6a7490;
                font-size: 11px;
                border-top: 1px solid #d0d4de;
            }
            """
        )

    def _setup_central_widget(self) -> None:
        """Build the splitter layout: GL view left, control panel right."""
        central = QWidget(self)
        central.setStyleSheet("background-color: #f5f6f9;")

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, central)
        splitter.setHandleWidth(self._SPLITTER_HANDLE_WIDTH)
        splitter.setChildrenCollapsible(False)

        # ── Left: 3-D view ─────────────────────────────────────────────
        # Wrap in a container so the border styling is independent of GLViewWidget.
        gl_container = QWidget(splitter)
        gl_container.setStyleSheet("background-color: #eceef2;")
        gl_layout = QVBoxLayout(gl_container)
        gl_layout.setContentsMargins(0, 0, 0, 0)
        gl_layout.setSpacing(0)
        gl_layout.addWidget(self._gl_widget)

        # ── Right: control panel ────────────────────────────────────────
        panel_container = QWidget(splitter)
        panel_container.setStyleSheet(
            "background-color: #f5f6f9; border-left: 1px solid #d0d4de;"
        )
        panel_layout = QVBoxLayout(panel_container)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        panel_layout.addWidget(self._control_panel)

        splitter.addWidget(gl_container)
        splitter.addWidget(panel_container)

        # Give all extra horizontal space to the GL view.
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([self._DEFAULT_WIDTH - 260, 260])

        root_layout.addWidget(splitter)
        self.setCentralWidget(central)

    def _setup_status_bar(self) -> None:
        """Configure a minimal status bar showing coordinate hints."""
        bar: QStatusBar = self.statusBar()
        bar.setSizeGripEnabled(True)
        self._status_label = QLabel(
            "  Point: (0, 0, 0)   |   Plane: (0, 0, 0)", bar
        )
        self._status_label.setStyleSheet("color: #6a7490; font-size: 11px;")
        bar.addWidget(self._status_label, 1)

        hint = QLabel("Rotate: LMB  ·  Pan: MMB  ·  Zoom: Wheel  ", bar)
        hint.setStyleSheet("color: #9aa0b8; font-size: 11px;")
        bar.addPermanentWidget(hint)

    def _connect_signals(self) -> None:
        """Wire the control panel to the GL widget and the status bar."""
        # One call connects all four signals (point, plane, camera, reset).
        self._gl_widget.connect_control_panel(self._control_panel)

        # Also refresh the status bar whenever coordinates change.
        self._control_panel.point_changed.connect(self._on_point_changed)
        self._control_panel.plane_changed.connect(self._on_plane_changed)
        self._control_panel.reset_coordinates_requested.connect(
            self._on_coordinates_reset
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_point_changed(self, x: float, y: float, z: float) -> None:
        """Update the status bar when Point P0 moves."""
        self._status_label.setText(
            f"  P0: ({x:.3g}, {y:.3g}, {z:.3g})"
            f"   |   Plane Corners P1–P4 Active"
        )

    def _on_plane_changed(
        self,
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        p3: tuple[float, float, float],
        p4: tuple[float, float, float],
    ) -> None:
        """Update the status bar when plane corners change."""
        ptx, pty, ptz = self._gl_widget.get_point()
        self._status_label.setText(
            f"  P0: ({ptx:.3g}, {pty:.3g}, {ptz:.3g})"
            f"   |   Plane: P1({p1[0]:.1f},{p1[1]:.1f},{p1[2]:.1f}) P2({p2[0]:.1f},{p2[1]:.1f},{p2[2]:.1f}) P3({p3[0]:.1f},{p3[1]:.1f},{p3[2]:.1f}) P4({p4[0]:.1f},{p4[1]:.1f},{p4[2]:.1f})"
        )

    def _on_coordinates_reset(self) -> None:
        """Reset the status bar to default values after a coordinate reset."""
        self._status_label.setText("  P0: (0, 0, 0)   |   Plane: P1–P4 Default Corners")


# ---------------------------------------------------------------------------
# Application bootstrap
# ---------------------------------------------------------------------------

def _configure_application_attributes() -> None:
    """Set QApplication attributes that must be applied before instantiation.

    These are required for correct OpenGL behaviour on Windows (and macOS).
    """
    # Request the native desktop OpenGL driver (avoids ANGLE/software fallback).
    QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)
    # Allow OpenGL contexts created in different threads to share resources.
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    # HiDPI support.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def main() -> int:
    """Create and run the application.

    Returns
    -------
    int
        Exit code forwarded from :func:`QApplication.exec_`.
    """
    _configure_application_attributes()

    app = QApplication(sys.argv)
    app.setApplicationName("3D Scene Viewer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("3DWidgetDemo")

    # Use a system font with a clean, modern weight as the application default.
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
