"""
config/sizes.py
================
Single source of truth for sizes, line widths, marker sizes, and grid extents.
"""

from __future__ import annotations

from typing import Final

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

#: Normal vector arrowhead (cone) dimensions, world units.
NORMAL_ARROW_HEAD_LENGTH: Final[float] = 1.4
NORMAL_ARROW_HEAD_RADIUS: Final[float] = 0.55

#: Length the local (reference-point) coordinate frame axes are drawn with.
LOCAL_AXIS_DISPLAY_LENGTH: Final[float] = 4.5

#: Marker size for the translucent glow halo behind the active reference point.
REFERENCE_GLOW_SIZE: Final[float] = 34.0

#: Maximum number of previous plane fits kept for the optional ghost/history mode.
GHOST_HISTORY_DEPTH: Final[int] = 4

#: Duration (milliseconds) of smooth transitions for plane rotation, local
#: axes, normal vector, point movement, and reference switching. Kept in the
#: 200-300 ms band -- perceptible but not sluggish, matching CAD/CMM software.
ANIMATION_DURATION_MS: Final[int] = 260

#: Pixel size (square) of the small fixed-corner orientation triad widget.
ORIENTATION_WIDGET_SIZE: Final[int] = 96
