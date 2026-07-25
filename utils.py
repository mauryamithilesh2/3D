"""
utils.py
=========
Small, dependency-light helper functions shared by multiple modules --
mainly safe numeric parsing (for live-editing coordinate fields) and
consistent number/vector formatting (for the results panel and status
displays).

Why pull these into their own module?
----------------------------------------
Both the coordinate entry rows and the results panel need to parse and
format floating point numbers, and they need to do it IDENTICALLY --
otherwise a value could round-trip differently depending on which widget
touched it last. Rather than duplicate that logic (or the "-0.0 displays
as 0.0" edge case) in every widget class, it lives here once.

Compatible with Python 3.10+, NumPy only.
"""

from __future__ import annotations

import numpy as np

from config import RESULT_DISPLAY_DECIMALS


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_float(text: str, default: float = 0.0) -> float:
    """Parse user-entered text into a float, tolerating a comma decimal separator.

    Parameters
    ----------
    text:
        Raw text from a coordinate input field.
    default:
        Value returned if ``text`` cannot be parsed (e.g. empty string,
        a lone "-" while the user is still typing).

    Returns
    -------
    float
        The parsed value, or ``default`` if parsing failed.

    Why tolerate a comma?
        Many European keyboard/locale setups produce "1,5" instead of
        "1.5" when a user types a decimal point. Silently accepting both
        avoids a frustrating rejection of an obviously-intended value in a
        live-updating field with no explicit "submit" step to correct on.
    """
    if text is None:
        return default
    cleaned = text.strip().replace(",", ".")
    if cleaned in ("", "-", "+", "."):
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

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
        always shown as positive zero (``"0.0000"``, never ``"-0.0000"``),
        since a signed zero carries no physical meaning here and only
        invites the question "why is this negative?" during a demo.
    """
    rounded = round(float(value), decimals)
    if rounded == 0.0:
        rounded = 0.0  # normalizes -0.0 to 0.0
    return f"{rounded:.{decimals}f}"


def format_vector(vector: np.ndarray, decimals: int = RESULT_DISPLAY_DECIMALS) -> str:
    """Format a 3-element vector as ``"(x, y, z)"`` using :func:`format_number`.

    Parameters
    ----------
    vector:
        Array-like of exactly 3 numeric values.
    decimals:
        Decimal places to show for each component.

    Returns
    -------
    str
        E.g. ``"(1.2500, -0.0003, 4.0000)"``.
    """
    x, y, z = (float(v) for v in vector)
    return (
        f"({format_number(x, decimals)}, "
        f"{format_number(y, decimals)}, "
        f"{format_number(z, decimals)})"
    )


def format_signed_distance(value: float, decimals: int = RESULT_DISPLAY_DECIMALS) -> str:
    """Format a signed distance with an explicit leading ``+`` or ``-`` sign.

    Why show the sign explicitly, unlike :func:`format_number`?
        For a general coordinate, sign is just part of the number. For a
        point-to-plane distance specifically, the sign is the entire point
        of the measurement -- it tells the user which side of the plane
        the point is on -- so it should never be ambiguous or easy to miss.
    """
    rounded = round(float(value), decimals)
    if rounded == 0.0:
        rounded = 0.0
    sign = "+" if rounded >= 0 else "-"
    return f"{sign}{abs(rounded):.{decimals}f}"


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp ``value`` into the inclusive range ``[minimum, maximum]``."""
    return max(minimum, min(maximum, value))