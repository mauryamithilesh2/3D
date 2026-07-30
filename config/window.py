"""
config/window.py
================
Single source of truth for window title, minimum and default dimensions, and panel width limits.
"""

from __future__ import annotations

from typing import Final

WINDOW_TITLE: Final[str] = "Best Fit Plane — Industrial Metrology Demo"
WINDOW_MIN_WIDTH: Final[int] = 1100
WINDOW_MIN_HEIGHT: Final[int] = 650
WINDOW_DEFAULT_WIDTH: Final[int] = 1440
WINDOW_DEFAULT_HEIGHT: Final[int] = 840

LEFT_PANEL_MIN_WIDTH: Final[int] = 260
LEFT_PANEL_MAX_WIDTH: Final[int] = 340
RIGHT_PANEL_MIN_WIDTH: Final[int] = 300
RIGHT_PANEL_MAX_WIDTH: Final[int] = 380
