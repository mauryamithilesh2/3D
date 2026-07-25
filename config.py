"""
config.py
==========
Single source of truth for constants shared across the application:
numeric limits, default values, display formatting, and visual styling.

Why centralize these instead of inlining them in each file?
--------------------------------------------------------------
The project's coding style explicitly avoids hardcoded values scattered
through the codebase. Any number that affects behaviour or appearance in
more than one place (or that a reviewer might reasonably want to tune --
a color, a decimal precision, a default coordinate) lives here so it can
be changed once, with no risk of a stray hardcoded duplicate elsewhere
silently disagreeing with it.

This module has no dependencies on the rest of the application and can be
imported from anywhere (UI, OpenGL, geometry) without creating cycles.
"""

from __future__ import annotations

from typing import Final


# ---------------------------------------------------------------------------
# Coordinate entry limits
# ---------------------------------------------------------------------------

#: Minimum / maximum value accepted in any X/Y/Z coordinate input field.
COORD_MIN: Final[float] = -1_000.0
COORD_MAX: Final[float] = 1_000.0

#: Decimal places accepted while typing a coordinate.
COORD_INPUT_DECIMALS: Final[int] = 2

#: Decimal places used when *displaying* computed results (distances,
#: local coordinates, plane equation coefficients). Kept separate from
#: input decimals because a display value is read-only and can afford a
#: little more precision without cluttering data entry.
RESULT_DISPLAY_DECIMALS: Final[int] = 2

#: Default coordinates assigned to a newly added plane or inspection point
#: before the user edits it.
DEFAULT_NEW_POINT: Final[tuple[float, float, float]] = (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Default seed data
# ---------------------------------------------------------------------------

#: The application starts with this many plane points already present, so
#: the plane fit and 3-D view are meaningful immediately on launch rather
#: than showing an unsolvable "fewer than 3 points" state.
INITIAL_PLANE_POINTS: Final[tuple[tuple[float, float, float], ...]] = ()

#: The application starts with zero inspection points by default.
INITIAL_INSPECTION_POINTS: Final[tuple[tuple[float, float, float], ...]] = ()


# ---------------------------------------------------------------------------
# 3-D scene styling (RGBA, 0-1 float range -- pyqtgraph.opengl convention)
# ---------------------------------------------------------------------------

COLOR_GRID: Final[tuple[float, float, float, float]] = (0.55, 0.58, 0.65, 0.35)
COLOR_AXIS_X: Final[tuple[float, float, float, float]] = (0.85, 0.25, 0.25, 1.0)
COLOR_AXIS_Y: Final[tuple[float, float, float, float]] = (0.25, 0.70, 0.30, 1.0)
COLOR_AXIS_Z: Final[tuple[float, float, float, float]] = (0.20, 0.45, 0.90, 1.0)

COLOR_DARK_DOT: Final[tuple[float, float, float, float]] = (0.0, 0.0, 0.0, 1.0)
COLOR_PLANE_POINT: Final[tuple[float, float, float, float]] = COLOR_DARK_DOT
COLOR_INSPECTION_POINT: Final[tuple[float, float, float, float]] = COLOR_DARK_DOT
COLOR_PROJECTION_POINT: Final[tuple[float, float, float, float]] = COLOR_DARK_DOT
COLOR_ORIGIN_POINT: Final[tuple[float, float, float, float]] = COLOR_DARK_DOT

COLOR_FITTED_PLANE: Final[tuple[float, float, float, float]] = (0.30, 0.55, 0.85, 0.28)
COLOR_PLANE_NORMAL: Final[tuple[float, float, float, float]] = (0.85, 0.35, 0.75, 1.0)
COLOR_DISTANCE_LINE: Final[tuple[float, float, float, float]] = (0.90, 0.55, 0.10, 0.9)

#: Distinct color for the imaginary (auto-completed) 4th rectangle corner
#: shown when exactly 3 plane points are active -- deliberately different
#: from COLOR_PLANE_POINT so it reads as a visual aid, never as a real,
#: user-entered point.
COLOR_IMAGINARY_POINT: Final[tuple[float, float, float, float]] = (0.60, 0.20, 0.75, 1.0)

#: Marker size for plane points / inspection points, in the same units
#: pyqtgraph.opengl's GLScatterPlotItem expects.
PLANE_POINT_SIZE: Final[float] = 14.0
INSPECTION_POINT_SIZE: Final[float] = 14.0
PROJECTION_POINT_SIZE: Final[float] = 10.0
IMAGINARY_POINT_SIZE: Final[float] = 14.0

#: Length (world units) the normal indicator is drawn with, independent of
#: the actual (unit-length) mathematical normal vector -- purely visual.
NORMAL_VECTOR_DISPLAY_LENGTH: Final[float] = 6.0

#: Half-size of the rendered plane patch, in local (plane) units, centered
#: on the coordinate system's origin.
PLANE_PATCH_HALF_EXTENT: Final[float] = 12.0

#: Spacing and extent of the reference floor grid.
GRID_SPACING: Final[float] = 5.0
GRID_SIZE: Final[float] = 60.0


# ---------------------------------------------------------------------------
# Window / layout
# ---------------------------------------------------------------------------

WINDOW_TITLE: Final[str] = "Best Fit Plane — Industrial Metrology Demo"
WINDOW_MIN_WIDTH: Final[int] = 1100
WINDOW_MIN_HEIGHT: Final[int] = 650
WINDOW_DEFAULT_WIDTH: Final[int] = 1440
WINDOW_DEFAULT_HEIGHT: Final[int] = 840

LEFT_PANEL_MIN_WIDTH: Final[int] = 260
LEFT_PANEL_MAX_WIDTH: Final[int] = 340
RIGHT_PANEL_MIN_WIDTH: Final[int] = 300
RIGHT_PANEL_MAX_WIDTH: Final[int] = 380