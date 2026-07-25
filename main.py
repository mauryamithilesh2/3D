"""
main.py
========
Application entry point. Creates the ``QApplication``, assembles the main
window from the widgets ``ui.py`` and ``gl3d_widget.py`` already provide,
wires their signals to a single "recompute the pipeline" slot, and starts
the Qt event loop. Coordinate and distance results are rendered directly
as labels on the 3-D graph (``gl3d_widget.py``) rather than in a separate
right-hand results panel.

Design principle: this module contains NO geometry or fitting math.
------------------------------------------------------------------------
Every actual calculation (SVD plane fit, local frame construction, world
<-> plane conversion, point-to-plane measurement) already lives in
``best_fit_plane.py``, ``coordinate_system.py``, ``transform.py``, and
``measurement.py``. ``main.py`` only ever calls into those modules and
hands their *results* to the display widgets -- it never touches a NumPy
array's numbers directly. This mirrors ``ui.py``'s own stated principle of
staying free of geometry, so the whole application has exactly one place
(``main.py::MainWindow._recompute``) where the pipeline is strung
together, and exactly one direction data flows: point edit -> signal ->
recompute -> display.

Live update, no Calculate button
---------------------------------
``PointManager`` emits ``plane_points_changed`` / ``inspection_points_changed``
on every add, remove, or edit, and ``ReferenceSelector`` emits
``reference_changed`` whenever the origin choice changes. ``MainWindow``
connects all three directly to ``_recompute``, so the 3-D view and results
panel are always exactly as current as the last edit -- consistent with
every other module in this project.

Compatible with Python 3.10+, PyQt5.
"""

from __future__ import annotations

import sys

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QSplitter, QWidget

from best_fit_plane import BestFitPlane, PlaneFitError
from config import (
    DEFAULT_NEW_POINT,
    INITIAL_INSPECTION_POINTS,
    INITIAL_PLANE_POINTS,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
)
from coordinate_system import CoordinateSystemBuilder, CoordinateSystemError, OriginReference
from gl3d_widget import GL3DWidget
from measurement import MeasurementEngine
from point_manager import PointManager
from transform import CoordinateTransformer
from ui import LeftPanel, PointListPanel, ReferenceDistancePanel, ReferenceSelector, RightPanel


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Assembles the left control panel, the 3-D view, and the right results panel."""

    _measurements_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_DEFAULT_WIDTH + 360, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH + 300, WINDOW_MIN_HEIGHT)

        self._point_manager = PointManager(parent=self)
        self._transformer: CoordinateTransformer | None = None

        # -- Build widgets ---------------------------------------------
        self._left_panel, self._reference_selector = self._build_left_panel()
        self._gl_widget = GL3DWidget()
        self._right_panel = RightPanel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._left_panel)
        splitter.addWidget(self._gl_widget)
        splitter.addWidget(self._right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([280, 720, 360])
        self.setCentralWidget(splitter)

        # -- Wire signals: any point or reference change re-runs the
        #    pipeline and pushes fresh results into both the 3-D view and
        #    the results panel. No "Calculate" button anywhere.
        #
        #    Entering/editing ANY point first resets the reference
        #    selection back to "no reference selected" -- so a
        #    previously shown reference-relative distance/coordinate is
        #    never left on screen stale; the user must explicitly
        #    reselect a reference point to see distances again.
        self._point_manager.plane_points_changed.connect(self._reference_selector.reset_to_placeholder)
        self._point_manager.inspection_points_changed.connect(self._reference_selector.reset_to_placeholder)

        self._point_manager.plane_points_changed.connect(self._recompute)
        self._point_manager.inspection_points_changed.connect(self._recompute)
        self._reference_selector.reference_changed.connect(self._recompute)

        self._recompute()

    # ------------------------------------------------------------------
    # Left panel assembly
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> tuple[LeftPanel, ReferenceSelector]:
        """Assemble the left panel from ``ui.py``'s building blocks directly."""
        default_x, default_y, default_z = DEFAULT_NEW_POINT

        plane_panel = PointListPanel(
            title="Plane Points",
            get_points=lambda: list(
                zip(
                    self._point_manager.plane_point_labels(),
                    self._point_manager.plane_points_array(),
                )
            ),
            add_point=lambda: self._point_manager.add_plane_point(default_x, default_y, default_z),
            update_point=self._point_manager.update_plane_point,
            remove_point=self._point_manager.remove_plane_point,
            min_count=self._point_manager.MIN_PLANE_POINTS,
            changed_signal=self._point_manager.plane_points_changed,
            reset_last_point=self._point_manager.remove_last_plane_point,
        )

        inspection_panel = PointListPanel(
            title="Inspection Points",
            get_points=self._point_manager.inspection_points,
            add_point=lambda: self._point_manager.add_inspection_point(
                default_x, default_y, default_z
            ),
            update_point=self._point_manager.update_inspection_point,
            remove_point=self._point_manager.remove_inspection_point,
            min_count=0,
            changed_signal=self._point_manager.inspection_points_changed,
            reset_last_point=self._point_manager.remove_last_inspection_point,
        )

        reference_selector = ReferenceSelector(
            get_plane_labels=self._point_manager.plane_point_labels,
            changed_signal=self._point_manager.plane_points_changed,
        )

        self._reference_distance_panel = ReferenceDistancePanel()

        left_panel = LeftPanel(
            plane_panel,
            inspection_panel,
            reference_selector,
            reference_distance_panel=self._reference_distance_panel,
        )
        return left_panel, reference_selector

    def _plane_local_points(self) -> list[tuple[str, np.ndarray]]:
        """Return plane points as ``(label, LOCAL coordinates)``."""
        points = list(
            zip(
                self._point_manager.plane_point_labels(),
                self._point_manager.plane_points_array(),
            )
        )
        if not hasattr(self, "_reference_selector"):
            return points

        reference_text = self._reference_selector.current_reference_text()
        plane_labels = self._point_manager.plane_point_labels()

        if self._transformer is None or reference_text not in plane_labels:
            return points

        return [
            (label, self._transformer.world_to_plane(coords).as_array())
            for label, coords in points
        ]

    def _update_plane_point_local(self, label: str, x: float, y: float, z: float) -> None:
        """Commit an edited LOCAL coordinate row back to the point manager."""
        if not hasattr(self, "_reference_selector"):
            self._point_manager.update_plane_point(label, x, y, z)
            return

        reference_text = self._reference_selector.current_reference_text()
        plane_labels = self._point_manager.plane_point_labels()

        if self._transformer is None or reference_text not in plane_labels:
            self._point_manager.update_plane_point(label, x, y, z)
            return

        world = self._transformer.plane_to_world(np.array([x, y, z], dtype=np.float64))
        self._point_manager.update_plane_point(
            label, float(world[0]), float(world[1]), float(world[2])
        )

    def _inspection_local_points(self) -> list[tuple[str, np.ndarray]]:
        """Return inspection points as ``(label, LOCAL coordinates)``.

        Used as the inspection panel's ``get_points`` callable. Local
        coordinates are relative to whichever reference/centroid is
        currently selected (see :meth:`_build_coordinate_system`), so this
        naturally returns different numbers for the same point as the
        reference selection changes -- the point itself never moves, only
        which frame it is reported in.
        """
        points = self._point_manager.inspection_points()
        if self._transformer is None:
            # No fit yet (fewer than 3 plane points) -- local coordinates
            # are undefined; show world coordinates rather than hide the
            # row entirely.
            return points
        return [
            (label, self._transformer.world_to_plane(coords).as_array())
            for label, coords in points
        ]

    def _update_inspection_point_local(self, label: str, x: float, y: float, z: float) -> None:
        """Commit an edited LOCAL coordinate row back to the point manager.

        The row displays and is edited in LOCAL (reference-relative)
        coordinates, but ``PointManager`` always stores WORLD coordinates
        -- the one physical, reference-independent representation -- so
        the edited value is converted back to world space with the same
        transformer the displayed value came from before being stored.
        """
        if self._transformer is None:
            # No fit yet -- local and world coordinates coincide.
            self._point_manager.update_inspection_point(label, x, y, z)
            return
        world = self._transformer.plane_to_world(np.array([x, y, z], dtype=np.float64))
        self._point_manager.update_inspection_point(
            label, float(world[0]), float(world[1]), float(world[2])
        )

    # ------------------------------------------------------------------
    # Initial seed data
    # ------------------------------------------------------------------

    def _seed_initial_points(self) -> None:
        """Populate the point manager with ``config.py``'s starting points.

        Why seed points here instead of inside ``PointManager`` itself?
            ``PointManager`` is a generic collection owner with no opinion
            on what a *new, empty* application should start with -- that
            is an application-level decision, so it belongs in
            ``main.py`` (the one file allowed to make such decisions),
            leaving ``point_manager.py`` reusable with any starting state,
            including none at all.
        """
        for x, y, z in INITIAL_PLANE_POINTS:
            self._point_manager.add_plane_point(x, y, z)
        for x, y, z in INITIAL_INSPECTION_POINTS:
            self._point_manager.add_inspection_point(x, y, z)

    # ------------------------------------------------------------------
    # The pipeline
    # ------------------------------------------------------------------

    def _recompute(self) -> None:
        """Re-run the full pipeline and push fresh results to both views.

        Pipeline (each stage implemented entirely in its own module):
            1. ``best_fit_plane.BestFitPlane.fit`` -- fit the plane.
            2. ``coordinate_system.CoordinateSystemBuilder`` -- build the
               local frame for the currently selected origin reference.
            3. ``transform.CoordinateTransformer`` -- wrap that frame for
               world <-> plane conversion.
            4. ``measurement.MeasurementEngine.measure_points`` -- measure
               every current inspection point against the fit.

        Any stage that cannot produce a result (fewer than 3 plane points,
        or points too degenerate to define a plane) leaves ``plane_result``,
        ``coordinate_system``, and ``self._transformer`` as ``None`` and
        ``measurements`` empty; ``gl3d_widget.GL3DWidget.update_scene``
        already handles that state (it simply shows no plane patch / no
        distance lines). Coordinate and distance results are rendered
        directly as labels on the 3-D graph rather than in a separate
        panel.

        ``self._transformer`` is stored as instance state (rather than a
        local variable) specifically so :meth:`_inspection_local_points`
        and :meth:`_update_inspection_point_local` can reuse the exact
        same transformer the graph was just drawn with -- guaranteeing the
        left panel's inspection rows and the graph labels always agree.
        """
        plane_result = None
        coordinate_system = None
        measurements = []
        self._transformer = None

        active_points = self._point_manager.active_plane_points_dict()
        active_array = self._point_manager.active_plane_points_array()

        if len(active_array) >= BestFitPlane.MIN_POINTS:
            try:
                plane_result = BestFitPlane.fit(active_array)
            except PlaneFitError:
                plane_result = None

        if plane_result is not None:
            coordinate_system = self._build_coordinate_system(plane_result)

        if plane_result is not None and coordinate_system is not None:
            self._transformer = CoordinateTransformer(coordinate_system)
            measurements = MeasurementEngine.measure_points(
                self._point_manager.inspection_points(), plane_result, self._transformer
            )

        # Populate Right Panel Tab 1: Coordinates (Reference-Relative) Table
        coord_rows = []
        is_plane_ref = (
            coordinate_system is not None
            and coordinate_system.reference == OriginReference.PLANE_POINT
        )
        reference_label = (
            self._reference_selector.current_reference_text() if is_plane_ref else None
        )
        reference_point = (
            active_points.get(reference_label) if reference_label is not None else None
        )

        self._gl_widget.update_scene(
            active_points, measurements, plane_result, coordinate_system,
            reference_selected=is_plane_ref,
            reference_point=reference_point,
        )

        if self._transformer is not None:
            for label, world_p in active_points.items():
                loc_p = self._transformer.world_to_plane(world_p).as_array()
                d = float(np.linalg.norm(loc_p))
                coord_rows.append((label, float(loc_p[0]), float(loc_p[1]), float(loc_p[2]), d))
            for m in measurements:
                loc_p = m.plane_coordinates.as_array()
                d = m.distance_to_reference if is_plane_ref else abs(m.distance_to_plane)
                coord_rows.append((m.label, float(loc_p[0]), float(loc_p[1]), float(loc_p[2]), float(d)))
        else:
            for label, world_p in active_points.items():
                d = float(np.linalg.norm(world_p))
                coord_rows.append((label, float(world_p[0]), float(world_p[1]), float(world_p[2]), d))
            for label, world_p in self._point_manager.inspection_points():
                d = float(np.linalg.norm(world_p))
                coord_rows.append((label, float(world_p[0]), float(world_p[1]), float(world_p[2]), d))

        self._right_panel.display_coordinates(coord_rows)

        # Populate Right Panel Tab 2: Pairwise Distances Table
        #
        # Until a reference point is selected, keep the original behaviour
        # (every pairwise distance among all points). Once a reference
        # plane point IS selected, distance mode switches to point-to-
        # point: show ONLY plane-point -> inspection-point distances
        # (every active plane point to every inspection point), dropping
        # plane-plane and inspection-inspection pairs.
        inspection_pts = self._point_manager.inspection_points()
        if is_plane_ref:
            pairs = [
                (
                    f"{plane_label} - {inspection_label}",
                    float(np.linalg.norm(plane_point - inspection_point)),
                )
                for plane_label, plane_point in active_points.items()
                for inspection_label, inspection_point in inspection_pts
            ]
        else:
            all_pts = list(active_points.items()) + list(inspection_pts)
            pairs = []
            for i in range(len(all_pts)):
                for j in range(i + 1, len(all_pts)):
                    lbl1, p1 = all_pts[i]
                    lbl2, p2 = all_pts[j]
                    dist = float(np.linalg.norm(p1 - p2))
                    pairs.append((f"{lbl1} - {lbl2}", dist))

        self._right_panel.display_distances(pairs)

        # Populate the left-panel Reference -> Inspection Distance panel:
        # until a reference is selected it just shows a hint; once
        # selected, highlight distance-to-reference plus the inspection
        # point's new (reference-relative) coordinate for every inspection
        # point.
        distance_entries = (
            [
                (m.label, m.distance_to_reference, tuple(float(v) for v in m.plane_coordinates.as_array()))
                for m in measurements
            ]
            if is_plane_ref
            else []
        )
        self._reference_distance_panel.display(reference_label, distance_entries)

        self._measurements_changed.emit()

    def _build_coordinate_system(self, plane_result):
        """Build the local frame for whatever the reference selector shows.

        Interprets ``ReferenceSelector.current_reference_text()``:
        - Plane point label (e.g. "PL1") -> build_at_plane_point
        - Default ("Default Origin" or unknown) -> build_at_world_origin
        """
        reference_text = self._reference_selector.current_reference_text()
        plane_labels = self._point_manager.plane_point_labels()

        if reference_text in plane_labels:
            try:
                point_index = plane_labels.index(reference_text)
                return CoordinateSystemBuilder.build_at_plane_point(
                    plane_result, self._point_manager.plane_points_array(), point_index
                )
            except CoordinateSystemError:
                return CoordinateSystemBuilder.build_at_world_origin(plane_result)

        return CoordinateSystemBuilder.build_at_world_origin(plane_result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Create the ``QApplication``, show the main window, run the event loop."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()