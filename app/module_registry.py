"""
app/module_registry.py
=======================
Maps a landing-page module id to the window class that implements it.
Adding a new module = one new window class + one line here; nothing about
an existing module needs to change.
"""

from __future__ import annotations

from typing import Callable

from app.circularity_window import CircularityWindow
from app.main_window import MainWindow


def _distance_window() -> MainWindow:
    return MainWindow(module="distance")


def _parallelism_window() -> MainWindow:
    # Parallelism & Perpendicularity module has no dedicated implementation
    # yet -- falls back to the Distance module window (existing behavior)
    # rather than crashing. Once it gets its own dedicated window class, it
    # will follow the same _init_chrome + _init_toolbar contract as Circularity.
    return MainWindow(module="parallelism")


MODULE_WINDOWS: dict[str, Callable[[], object]] = {
    "distance": _distance_window,
    "circularity": CircularityWindow,
    "parallelism": _parallelism_window,
}


def create_module_window(module_id: str):
    """Instantiate the window for ``module_id``, falling back to the
    distance module if the id is unrecognized."""
    factory = MODULE_WINDOWS.get(module_id, _distance_window)
    return factory()
