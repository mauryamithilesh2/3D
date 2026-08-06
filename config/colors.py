"""
config/colors.py
================
Single source of truth for all RGBA color constants (0.0 - 1.0 float range, pyqtgraph.opengl convention).
Supports runtime theme switching between Dark and Light palettes.
"""

from __future__ import annotations

from typing import Any
from PyQt5.QtCore import QSettings

DARK_PALETTE: dict[str, Any] = {
    "COLOR_VIEWPORT_BG": (24, 27, 33),
    "COLOR_GRID_DARK": (0.70, 0.75, 0.85, 0.80),
    "COLOR_AXIS_X": (0.85, 0.25, 0.25, 1.0),
    "COLOR_AXIS_Y": (0.25, 0.70, 0.30, 1.0),
    "COLOR_AXIS_Z": (0.20, 0.45, 0.90, 1.0),
    "COLOR_LOCAL_AXIS_X": (1.00, 0.45, 0.35, 1.0),
    "COLOR_LOCAL_AXIS_Y": (0.45, 1.00, 0.45, 1.0),
    "COLOR_LOCAL_AXIS_Z": (0.35, 0.75, 1.00, 1.0),
    "COLOR_LABEL_TEXT": (0.95, 0.97, 1.00, 1.0),
    "COLOR_PLANE_NORMAL": (0.55, 0.95, 0.55, 1.0),
    "COLOR_NORMAL_HEAD": (1.00, 1.00, 1.00, 1.0),
    "COLOR_PLANE_POINT": (0.35, 0.85, 1.00, 1.0),
    "COLOR_INSPECTION_POINT": (1.00, 0.70, 0.20, 1.0),
    "COLOR_ORIGIN_POINT": (1.00, 0.95, 0.35, 1.0),
    "COLOR_WORLD_DOTTED": (0.25, 0.60, 1.00, 0.95),
    "COLOR_LOCAL_DOTTED": (0.95, 0.95, 0.98, 0.95),
    "COLOR_DISTANCE_LINE": (0.90, 0.55, 0.10, 0.9),
    # Extra viewport entries
    "COLOR_GRID": (0.70, 0.75, 0.85, 0.80),
    "COLOR_DARK_DOT": (0.92, 0.94, 0.98, 1.0),
    "COLOR_PROJECTION_POINT": (0.60, 1.00, 0.60, 1.0),
    "COLOR_FITTED_PLANE": (0.30, 0.55, 0.85, 0.28),
    "COLOR_PLANE_EDGE": (0.55, 0.80, 1.00, 0.85),
    "COLOR_NORMAL_SHAFT": (0.95, 0.35, 0.85, 1.0),
    "COLOR_REFERENCE_GLOW": (1.00, 0.82, 0.20, 0.35),
    "COLOR_REFERENCE_RING": (1.00, 0.82, 0.20, 0.95),
    "COLOR_GHOST_PLANE": (0.65, 0.68, 0.75, 0.10),
    "COLOR_INSPECTION_PLANE": (0.85, 0.35, 0.75, 0.30),
    "COLOR_ANGLE_ARC": (1.00, 0.85, 0.20, 1.0),
    "COLOR_IMAGINARY_POINT": (0.60, 0.20, 0.75, 1.0),
    "COLOR_INSPECTION_NORMAL": (0.95, 0.45, 0.85, 1.0),
}

LIGHT_PALETTE: dict[str, Any] = {
    "COLOR_VIEWPORT_BG": (238, 240, 244),
    "COLOR_GRID_DARK": (0.35, 0.40, 0.50, 0.80),
    "COLOR_AXIS_X": (0.78, 0.12, 0.12, 1.0),
    "COLOR_AXIS_Y": (0.10, 0.55, 0.18, 1.0),
    "COLOR_AXIS_Z": (0.10, 0.30, 0.75, 1.0),
    "COLOR_LOCAL_AXIS_X": (0.90, 0.30, 0.15, 1.0),
    "COLOR_LOCAL_AXIS_Y": (0.15, 0.70, 0.25, 1.0),
    "COLOR_LOCAL_AXIS_Z": (0.15, 0.45, 0.85, 1.0),
    "COLOR_LABEL_TEXT": (0.10, 0.11, 0.14, 1.0),
    "COLOR_PLANE_NORMAL": (0.20, 0.55, 0.20, 1.0),
    "COLOR_NORMAL_HEAD": (0.05, 0.05, 0.05, 1.0),
    "COLOR_PLANE_POINT": (0.05, 0.45, 0.65, 1.0),
    "COLOR_INSPECTION_POINT": (0.85, 0.45, 0.0, 1.0),
    "COLOR_ORIGIN_POINT": (0.75, 0.60, 0.0, 1.0),
    "COLOR_WORLD_DOTTED": (0.10, 0.35, 0.80, 0.95),
    "COLOR_LOCAL_DOTTED": (0.15, 0.15, 0.18, 0.85),
    "COLOR_DISTANCE_LINE": (0.70, 0.35, 0.0, 0.9),
    # Extra viewport entries
    "COLOR_GRID": (0.35, 0.40, 0.50, 0.80),
    "COLOR_DARK_DOT": (0.10, 0.12, 0.15, 1.0),
    "COLOR_PROJECTION_POINT": (0.15, 0.60, 0.15, 1.0),
    "COLOR_FITTED_PLANE": (0.20, 0.45, 0.75, 0.25),
    "COLOR_PLANE_EDGE": (0.20, 0.50, 0.80, 0.85),
    "COLOR_NORMAL_SHAFT": (0.20, 0.55, 0.20, 1.0),
    "COLOR_REFERENCE_GLOW": (0.85, 0.55, 0.00, 0.35),
    "COLOR_REFERENCE_RING": (0.85, 0.55, 0.00, 0.95),
    "COLOR_GHOST_PLANE": (0.35, 0.38, 0.45, 0.10),
    "COLOR_INSPECTION_PLANE": (0.70, 0.20, 0.60, 0.30),
    "COLOR_ANGLE_ARC": (0.80, 0.55, 0.00, 1.0),
    "COLOR_INSPECTION_NORMAL": (0.70, 0.15, 0.55, 1.0),
    "COLOR_IMAGINARY_POINT": (0.50, 0.15, 0.65, 1.0),
}


def load_saved_theme() -> str:
    """Read stored theme setting ('light')."""
    return "light"


def save_theme(theme_name: str) -> None:
    """Save theme preference to QSettings."""
    settings = QSettings("3DWidgetApp", "Theme")
    settings.setValue("active_theme", "light")


_ACTIVE_THEME: str = "light"


def get_active_theme() -> str:
    """Return currently active theme name ('light')."""
    return "light"


def set_active_theme(theme_name: str) -> None:
    """Set active theme to light mode."""
    global _ACTIVE_THEME
    _ACTIVE_THEME = "light"
    save_theme("light")


def get_color(name: str) -> Any:
    """Get color constant value for light theme."""
    if name in LIGHT_PALETTE:
        return LIGHT_PALETTE[name]
    return DARK_PALETTE.get(name)


def __getattr__(name: str) -> Any:
    """Dynamic module attribute lookup for backward compatibility."""
    if name in LIGHT_PALETTE:
        return LIGHT_PALETTE[name]
    if name in DARK_PALETTE:
        return DARK_PALETTE[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")