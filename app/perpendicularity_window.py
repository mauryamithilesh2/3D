"""
app/perpendicularity_window.py
===============================
Dedicated top-level window for Perpendicularity, following the same Module
Window Standard Contract as CircularityWindow. No pipeline is duplicated --
MainWindow already owns the shared PointManager / BestFitPlane /
CoordinateSystem / Transform / MeasurementEngine / GL3DWidget pipeline,
driven by ModuleSpec. This class just pins module="perpendicularity" via
inheritance so the correct spec is always selected.
"""

from __future__ import annotations

from app.main_window import MainWindow


class PerpendicularityWindow(MainWindow):
    def __init__(self) -> None:
        super().__init__(module="perpendicularity")