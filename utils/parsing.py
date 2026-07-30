"""
utils/parsing.py
================
Numeric parsing and clamping helper functions.
"""

from __future__ import annotations


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


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp ``value`` into the inclusive range ``[minimum, maximum]``."""
    return max(minimum, min(maximum, value))
