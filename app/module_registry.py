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
from app.perpendicularity_window import PerpendicularityWindow


def _distance_window() -> MainWindow:
    return MainWindow(module="distance")



MODULE_WINDOWS: dict[str, Callable[[], object]] = {
    "distance": _distance_window,
    "circularity": CircularityWindow,
    # Parallelism has no dedicated datum-plane picker yet, so its landing
    # card opens PerpendicularityWindow -- both are the exact same
    # ModuleSpec-driven pipeline (see app/module_specs.py). Once Parallelism
    # gets its own spec entry, point this at a ParallelismWindow instead.
    "parallelism": PerpendicularityWindow,
}

def create_module_window(module_id: str):
    """Instantiate the window for ``module_id``, falling back to the
    distance module if the id is unrecognized."""
    factory = MODULE_WINDOWS.get(module_id, _distance_window)
    return factory()
