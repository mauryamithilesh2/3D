"""
utils/formatting.py
===================
Number, vector, and distance string formatting helper functions.
"""

from __future__ import annotations

import numpy as np

from config import RESULT_DISPLAY_DECIMALS


def format_number(value: float, decimals: int = RESULT_DISPLAY_DECIMALS) -> str:
    """Format a float for display with a fixed decimal count and no signed zero.

    Parameters
    ----------
    value:
        Number to format.
    decimals:
        Decimal places to show.

    Returns
    -------
    str
        Formatted number, e.g. ``"3.1416"``. Values that round to zero are
        always shown as positive zero (``"0.0000"``, never ``"-0.0000"``).
    """
    rounded = round(float(value), decimals)
    if rounded == 0.0:
        rounded = 0.0  # normalizes -0.0 to 0.0
    return f"{rounded:.{decimals}f}"


def format_vector(vector: np.ndarray, decimals: int = RESULT_DISPLAY_DECIMALS) -> str:
    """Format a 3-element vector as ``"(x, y, z)"`` using :func:`format_number`."""
    x, y, z = (float(v) for v in vector)
    return (
        f"({format_number(x, decimals)}, "
        f"{format_number(y, decimals)}, "
        f"{format_number(z, decimals)})"
    )


def format_signed_distance(value: float, decimals: int = RESULT_DISPLAY_DECIMALS) -> str:
    """Format a signed distance with an explicit leading ``+`` or ``-`` sign."""
    rounded = round(float(value), decimals)
    if rounded == 0.0:
        rounded = 0.0
    sign = "+" if rounded >= 0 else "-"
    return f"{sign}{abs(rounded):.{decimals}f}"
