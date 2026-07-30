"""
main.py
========
Application bootstrap entry point. Creates QApplication, constructs app.MainWindow,
shows the window, and runs the Qt event loop.
"""

from __future__ import annotations

import sys
from PyQt5.QtWidgets import QApplication

from app import MainWindow


def main() -> None:
    """Create the QApplication, show the main window, run the event loop."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()