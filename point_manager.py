"""
point_manager.py
==================
Owns the dynamic collections of PLANE points (used to fit the best fit
plane, minimum 3, unlimited maximum) and INSPECTION points (unlimited,
measured against that plane). Emits Qt signals whenever either collection
changes so the rest of the application can recompute the pipeline
(plane -> coordinate system -> transform -> measurements -> OpenGL) with no
"Calculate" button -- every edit propagates live.

Why give this its own class instead of storing points on the UI widgets?
----------------------------------------------------------------------------
The number of plane points and inspection points is dynamic and unbounded,
so there is no fixed set of widgets to "read values from" the way a
hardcoded P1-P4 form would allow. Centralizing the actual point data here
(instead of scattering it across dynamically-created QLineEdit rows) gives
one single source of truth: the UI renders rows FROM this manager and
pushes edits back INTO it, and every non-UI module (best_fit_plane,
coordinate_system, transform, measurement) consumes this manager's data
directly, with no Qt dependency of their own.

Compatible with Python 3.10+, PyQt5, NumPy.
"""

from __future__ import annotations

from typing import Final

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PointManagerError(ValueError):
    """Raised for invalid point operations (duplicate label, below minimum, etc.)."""


# ---------------------------------------------------------------------------
# Point manager
# ---------------------------------------------------------------------------

class PointManager(QObject):
    """Holds and mutates the plane point set and inspection point set.

    Signals
    -------
    plane_points_changed()
        Emitted after any add, remove, or edit of a plane point.
    inspection_points_changed()
        Emitted after any add, remove, or edit of an inspection point.
    """

    plane_points_changed = pyqtSignal()
    inspection_points_changed = pyqtSignal()

    #: Plane points are allowed down to 0 (progressive 0/1/2/3/4+ point visual states).
    MIN_PLANE_POINTS: Final[int] = 0

    _PLANE_LABEL_PREFIX: Final[str] = "PL"
    _INSPECTION_LABEL_PREFIX: Final[str] = "P"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Plain dicts preserve insertion order (Python 3.7+), which keeps
        # plane/inspection rows displayed in the order the user created
        # them -- important for a predictable, professional-feeling UI.
        self._plane_points: dict[str, np.ndarray] = {}
        self._inspection_points: dict[str, np.ndarray] = {}
        # Set of plane point labels whose values have been edited/confirmed by the user.
        # Newly added rows start unconfirmed so they do not distort the fit/rendering
        # with default (0, 0, 0) placeholder values until edited.
        self._active_plane_points: set[str] = set()

        # Monotonically increasing counters used to generate unique default
        # labels. They deliberately never reuse a number after a point is
        # removed -- mirroring how a real probing report never re-issues a
        # deleted point's ID to a new point, to avoid ambiguity in exported
        # results.
        self._plane_label_counter = 0
        self._inspection_label_counter = 0

    # ------------------------------------------------------------------
    # Plane points
    # ------------------------------------------------------------------

    def add_plane_point(
        self, x: float = 0.0, y: float = 0.0, z: float = 0.0, label: str | None = None
    ) -> str:
        """Add a new plane point and return its (possibly auto-generated) label."""
        label = self._resolve_new_label(
            label, self._plane_points, self._PLANE_LABEL_PREFIX, is_plane=True
        )
        z = max(0.0, float(z))
        self._plane_points[label] = np.array([x, y, z], dtype=np.float64)
        self.plane_points_changed.emit()
        return label

    def remove_plane_point(self, label: str) -> None:
        """Remove a plane point by label."""
        if label not in self._plane_points:
            raise PointManagerError(f"No plane point with label '{label}'.")
        self._active_plane_points.discard(label)
        del self._plane_points[label]
        self.plane_points_changed.emit()

    def remove_last_plane_point(self) -> str | None:
        """Remove the most recently added plane point (undo/reset style)."""
        if not self._plane_points:
            return None
        last_label = list(self._plane_points.keys())[-1]
        self._active_plane_points.discard(last_label)
        del self._plane_points[last_label]
        self.plane_points_changed.emit()
        return last_label

    def update_plane_point(self, label: str, x: float, y: float, z: float) -> None:
        """Update an existing plane point's coordinates and mark it active."""
        if label not in self._plane_points:
            raise PointManagerError(f"No plane point with label '{label}'.")
        z = max(0.0, float(z))
        self._plane_points[label] = np.array([x, y, z], dtype=np.float64)
        self._active_plane_points.add(label)
        self.plane_points_changed.emit()

    def plane_point_labels(self) -> list[str]:
        """Return plane point labels in insertion order."""
        return list(self._plane_points.keys())

    def active_plane_points_dict(self) -> dict[str, np.ndarray]:
        """Return dictionary of active (edited/confirmed) plane points only."""
        return {
            label: coords.copy()
            for label, coords in self._plane_points.items()
            if label in self._active_plane_points
        }

    def active_plane_points_array(self) -> np.ndarray:
        """Return active plane points stacked as an ``(N, 3)`` array, insertion order."""
        active = [
            coords
            for label, coords in self._plane_points.items()
            if label in self._active_plane_points
        ]
        if not active:
            return np.empty((0, 3), dtype=np.float64)
        return np.stack(active)

    def active_plane_point_count(self) -> int:
        """Current number of active (edited/confirmed) plane points."""
        return len(self._active_plane_points)

    def plane_points_array(self) -> np.ndarray:
        """Return all plane points stacked as an ``(N, 3)`` array, insertion order."""
        if not self._plane_points:
            return np.empty((0, 3), dtype=np.float64)
        return np.stack(list(self._plane_points.values()))

    def plane_point_count(self) -> int:
        """Current number of total plane points."""
        return len(self._plane_points)

    def get_plane_point(self, label: str) -> np.ndarray:
        """Return a single plane point's coordinates by label.

        Raises
        ------
        PointManagerError
            If ``label`` does not exist.
        """
        if label not in self._plane_points:
            raise PointManagerError(f"No plane point with label '{label}'.")
        return self._plane_points[label].copy()

    # ------------------------------------------------------------------
    # Inspection points
    # ------------------------------------------------------------------

    def add_inspection_point(
        self, x: float = 0.0, y: float = 0.0, z: float = 0.0, label: str | None = None
    ) -> str:
        """Add a new inspection point and return its (possibly auto-generated) label.

        Unlike plane points, there is no minimum count -- inspection points
        are optional measurements against an already-defined plane.

        Returns
        -------
        str
            The label the point was stored under.

        Raises
        ------
        PointManagerError
            If ``label`` is already in use by another inspection point.
        """
        label = self._resolve_new_label(
            label, self._inspection_points, self._INSPECTION_LABEL_PREFIX, is_plane=False
        )
        self._inspection_points[label] = np.array([x, y, z], dtype=np.float64)
        self.inspection_points_changed.emit()
        return label

    def remove_inspection_point(self, label: str) -> None:
        """Remove an inspection point by label.

        Raises
        ------
        PointManagerError
            If ``label`` does not exist.
        """
        if label not in self._inspection_points:
            raise PointManagerError(f"No inspection point with label '{label}'.")
        del self._inspection_points[label]
        self.inspection_points_changed.emit()

    def remove_last_inspection_point(self) -> str | None:
        """Remove the most recently added inspection point (undo/reset style)."""
        if not self._inspection_points:
            return None
        last_label = list(self._inspection_points.keys())[-1]
        del self._inspection_points[last_label]
        self.inspection_points_changed.emit()
        return last_label

    def update_inspection_point(self, label: str, x: float, y: float, z: float) -> None:
        """Update an existing inspection point's coordinates.

        Raises
        ------
        PointManagerError
            If ``label`` does not exist.
        """
        if label not in self._inspection_points:
            raise PointManagerError(f"No inspection point with label '{label}'.")
        self._inspection_points[label] = np.array([x, y, z], dtype=np.float64)
        self.inspection_points_changed.emit()

    def inspection_point_labels(self) -> list[str]:
        """Return inspection point labels in insertion order."""
        return list(self._inspection_points.keys())

    def inspection_points(self) -> list[tuple[str, np.ndarray]]:
        """Return all inspection points as ``(label, coordinates)`` pairs.

        This is the exact structure ``measurement.MeasurementEngine
        .measure_points`` expects.
        """
        return [(label, coords.copy()) for label, coords in self._inspection_points.items()]

    def inspection_point_count(self) -> int:
        """Current number of inspection points."""
        return len(self._inspection_points)

    def get_inspection_point(self, label: str) -> np.ndarray:
        """Return a single inspection point's coordinates by label.

        Raises
        ------
        PointManagerError
            If ``label`` does not exist.
        """
        if label not in self._inspection_points:
            raise PointManagerError(f"No inspection point with label '{label}'.")
        return self._inspection_points[label].copy()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_new_label(
        self,
        requested_label: str | None,
        existing: dict[str, np.ndarray],
        prefix: str,
        is_plane: bool,
    ) -> str:
        """Validate an explicit label, or auto-generate the next default one.

        Parameters
        ----------
        requested_label:
            The caller-supplied label, or ``None`` to auto-generate.
        existing:
            The dict the new label must be unique against.
        prefix:
            Prefix used when auto-generating (``"PL"`` or ``"P"``).
        is_plane:
            Selects which monotonic counter to advance.

        Raises
        ------
        PointManagerError
            If ``requested_label`` is already in use.
        """
        if requested_label is not None:
            if requested_label in existing:
                raise PointManagerError(f"Label '{requested_label}' is already in use.")
            return requested_label

        if is_plane:
            while True:
                self._plane_label_counter += 1
                candidate = f"{prefix}{self._plane_label_counter}"
                if candidate not in existing:
                    return candidate
        else:
            while True:
                candidate = f"{prefix}{self._inspection_label_counter}"
                self._inspection_label_counter += 1
                if candidate not in existing:
                    return candidate