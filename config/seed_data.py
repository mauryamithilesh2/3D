"""
config/seed_data.py
===================
Single source of truth for numeric input limits, default point values, and initial seed data.
"""

from __future__ import annotations

from typing import Final

#: Minimum / maximum value accepted in any X/Y/Z coordinate input field.
COORD_MIN: Final[float] = -1_000.0
COORD_MAX: Final[float] = 1_000.0

#: Decimal places accepted while typing a coordinate.
COORD_INPUT_DECIMALS: Final[int] = 2

#: Decimal places used when *displaying* computed results (distances,
#: local coordinates, plane equation coefficients).
RESULT_DISPLAY_DECIMALS: Final[int] = 2

#: Default coordinates assigned to a newly added plane or inspection point
#: before the user edits it.
DEFAULT_NEW_POINT: Final[tuple[float, float, float]] = (0.0, 0.0, 0.0)

#: Initial plane points seed data.
INITIAL_PLANE_POINTS: Final[tuple[tuple[float, float, float], ...]] = ()

#: Initial inspection points seed data.
INITIAL_INSPECTION_POINTS: Final[tuple[tuple[float, float, float], ...]] = ()
