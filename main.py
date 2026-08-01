"""
main.py
========
Application bootstrap entry point. Enables global OpenGL context sharing,
creates QApplication, constructs app.LandingWindow, shows the window, and runs the Qt event loop.
"""

from __future__ import annotations

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from app import LandingWindow


def main() -> None:
    """Create the QApplication, show the landing window, run the event loop."""
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    window = LandingWindow()
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()