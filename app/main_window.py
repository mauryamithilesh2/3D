"""
app/main_window.py
==================
Main Window class assembling controls, 3-D view, right results panel, and stringing together the calculations.
Subclasses ``BaseModuleWindow`` to follow standard module window chrome and toolbar contract.
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QSplitter

from app.base_window import BaseModuleWindow
from config import (
    DEFAULT_NEW_POINT,
    INITIAL_INSPECTION_POINTS,
    INITIAL_PLANE_POINTS,
)
from core import (
    BestFitPlane,
    CoordinateSystemBuilder,
    CoordinateSystemError,
    CoordinateTransformer,
    MeasurementEngine,
    OriginReference,
    PlaneFitError,
    edge_axis,
    apply_edge_axis,
    apply_first_second_axis,
)
from graphics import GL3DWidget
from models import PointManager, PointManagerError
from ui import (
    EdgeAxisSelector,
    LeftPanel,
    PlaneAnglePanel,
    PointListPanel,
    ReferenceDistancePanel,
    ReferenceSelector,
    RightPanel,
)
from ui.toolbar import _TOGGLES, AxisAngleWidget
from plc import connection_manager as plc_conn
from plc.point_registers import (
    DATA_TYPE,
    SCALE_FACTOR,
    REFERENCE_POINT_REGISTERS,
    INSPECTION_POINT_REGISTERS,
)


class MainWindow(BaseModuleWindow):
    """Assembles the left control panel, the 3-D view, and the right results panel."""

    _measurements_changed = pyqtSignal()

    def __init__(self, module: str | None = None) -> None:
        super().__init__()
        self.module = module or "distance"
        module_titles = {
            "distance": "Distance & Coordinate Measurement",
            "circularity": "Circularity & Concentricity",
            "parallelism": "Parallelism & Perpendicularity",
        }
        self.module_title = module_titles.get(self.module, self.module.title())
        self._init_chrome(self.module_title)

        self._point_manager = PointManager(parent=self)
        self._transformer: CoordinateTransformer | None = None

        # Cursors into the hard-coded PLC register tables -- each click of
        # "Add" consumes the next register in order instead of dumping all
        # of them in at once.
        self._plc_point_cursor = 0
        self._plc_inspection_cursor = 0

        # -- Build widgets ---------------------------------------------
        self._left_panel, self._reference_selector = self._build_left_panel()
        self._gl_widget = GL3DWidget()
        self._right_panel = RightPanel()

        self._axis_angle_widget = AxisAngleWidget(self)
        self._init_toolbar(self._gl_widget, _TOGGLES, extra_widget=self._axis_angle_widget)
        self._build_status_bar()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._left_panel)
        splitter.addWidget(self._gl_widget)
        splitter.addWidget(self._right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([280, 720, 360])
        self.setCentralWidget(splitter)

        # -- Wire signals
        self._point_manager.plane_points_changed.connect(self._reference_selector.reset_to_placeholder)
        self._point_manager.inspection_points_changed.connect(self._reference_selector.reset_to_placeholder)

        self._point_manager.plane_points_changed.connect(self._recompute)
        self._point_manager.inspection_points_changed.connect(self._recompute)
        self._reference_selector.reference_changed.connect(self._recompute)
        self._reference_selector.reference_changed.connect(
            lambda text: self._point_manager.set_reference_label(
                text if text in self._point_manager.plane_point_labels() else None
            )
        )
        self._edge_axis_selector.changed.connect(self._recompute)

        self._recompute()

    def set_theme(self, theme_name: str) -> None:
        """Switch active theme ('dark' or 'light'), restyle UI chrome and rebuild 3D viewport."""
        super().set_theme(theme_name)

        if hasattr(self, "_left_panel") and hasattr(self._left_panel, "restyle"):
            self._left_panel.restyle()
        if hasattr(self, "_right_panel") and hasattr(self._right_panel, "restyle"):
            self._right_panel.restyle()
        if hasattr(self, "_axis_angle_widget"):
            self._axis_angle_widget.restyle()

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        """Build the industrial-style status bar (plane fit state, point counts, reference)."""
        bar = self.statusBar()

        self._status_fit_label = QLabel("Plane: not fitted")
        self._status_points_label = QLabel("Plane pts: 0   Inspection pts: 0")
        self._status_reference_label = QLabel("Reference: World Origin")

        bar.addWidget(self._status_fit_label)
        bar.addWidget(self._status_points_label)
        bar.addPermanentWidget(self._status_reference_label)

    def _update_status_bar(
        self,
        plane_result,
        active_points: dict,
        reference_label: str | None,
    ) -> None:
        """Refresh the status bar text after every recompute."""
        if plane_result is not None:
            rms = getattr(plane_result, "rms_error", None)
            fit_text = "Plane: fitted" + (f"  (RMS {rms:.4f})" if rms is not None else "")
        else:
            fit_text = "Plane: not fitted (need \u2265 3 points)"
        self._status_fit_label.setText(fit_text)

        n_plane = len(active_points)
        n_inspection = len(self._point_manager.inspection_points())
        self._status_points_label.setText(f"Plane pts: {n_plane}   Inspection pts: {n_inspection}")

        self._status_reference_label.setText(f"Reference: {reference_label or 'World Origin'}")

    # ------------------------------------------------------------------
    # Left panel assembly
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> tuple[LeftPanel, ReferenceSelector]:
        """Assemble the left panel from building blocks directly."""
        default_x, default_y, default_z = DEFAULT_NEW_POINT

        plane_panel = PointListPanel(
            title="Plane Points",
            get_points=lambda: list(
                zip(
                    self._point_manager.plane_point_labels(),
                    self._point_manager.plane_points_array(),
                )
            ),
            add_point=self.add_plc_point,
            update_point=self._point_manager.update_plane_point,
            remove_point=self._point_manager.remove_plane_point,
            min_count=self._point_manager.MIN_PLANE_POINTS,
            changed_signal=self._point_manager.plane_points_changed,
            reset_last_point=self._point_manager.remove_last_plane_point,
            rename_point=self._point_manager.rename_plane_point,
        )

        inspection_panel = PointListPanel(
            title="Inspection Points",
            get_points=self._point_manager.inspection_points,
            add_point=self.add_plc_inspection_point,
            update_point=self._point_manager.update_inspection_point,
            remove_point=self._point_manager.remove_inspection_point,
            min_count=0,
            changed_signal=self._point_manager.inspection_points_changed,
            reset_last_point=self._point_manager.remove_last_inspection_point,
            rename_point=self._point_manager.rename_inspection_point,
        )

        reference_selector = ReferenceSelector(
            get_plane_labels=self._point_manager.plane_point_labels,
            changed_signal=self._point_manager.plane_points_changed,
        )

        self._reference_distance_panel = ReferenceDistancePanel()
        self._plane_angle_panel = PlaneAnglePanel()
        self._edge_axis_selector = EdgeAxisSelector()

        left_panel = LeftPanel(
            plane_panel,
            inspection_panel,
            reference_selector,
            reference_distance_panel=self._reference_distance_panel,
            plane_angle_panel=self._plane_angle_panel,
            edge_axis_selector=self._edge_axis_selector,
        )

        return left_panel, reference_selector

    # ------------------------------------------------------------------
    # PLC point loading
    # ------------------------------------------------------------------

    def _read_plc_point(self, addresses: tuple[int, int, int]) -> tuple[float, float, float] | None:
        """Read one point's X/Y/Z from the live PLC (real connection, or
        SIMULATED_REGISTERS if no real PLC is connected -- see
        plc/read_write.py). `addresses` is (addr_x, addr_y, addr_z).

        SCALE_FACTOR only applies to integer register types (INT16/UINT16/
        INT32) -- those can't natively hold a decimal, so the PLC sends a
        scaled whole number and we divide it back out here. FLOAT32/DOUBLE
        registers already carry real decimal precision on the wire, so they
        are passed through unscaled; dividing them by SCALE_FACTOR too would
        silently corrupt an already-correct value.

        Returns None if ANY axis fails to read, rather than silently
        returning a partial/garbage point -- a bad read should never sneak
        a wrong point into the plane fit or inspection list.
        """
        needs_scaling = DATA_TYPE in ("INT16", "UINT16", "INT32")

        values = []
        for address in addresses:
            raw = plc_conn.operations.read(address, DATA_TYPE)
            if raw is None:
                return None
            values.append(raw / SCALE_FACTOR if needs_scaling else raw)
        return tuple(values)

    def add_plc_point(self) -> None:
        """Add the NEXT plane point, read live from the PLC via
        REFERENCE_POINT_REGISTERS (plc/point_registers.py).

        One click == one point consumed, in table order. Once every point
        has been added, further clicks are a no-op. If the read fails (PLC
        not connected AND no simulated value for that register), the click
        is also a no-op -- the cursor does not advance, so the same point
        will be retried on the next click rather than being skipped.
        """
        names = list(REFERENCE_POINT_REGISTERS.keys())
        if self._plc_point_cursor >= len(names):
            return
        addresses = REFERENCE_POINT_REGISTERS[names[self._plc_point_cursor]]
        point = self._read_plc_point(addresses)
        if point is None:
            self.statusBar().showMessage(
                "PLC read failed — check PLC connection (see status bar on landing page)", 4000
            )
            return
        label = self._point_manager.add_plane_point(*point)
        self._point_manager.update_plane_point(label, *point)
        self._plc_point_cursor += 1

    def add_plc_inspection_point(self) -> None:
        """Add the NEXT inspection point, read live from the PLC via
        INSPECTION_POINT_REGISTERS. Same cursor and failed-read behavior as
        :meth:`add_plc_point`."""
        names = list(INSPECTION_POINT_REGISTERS.keys())
        if self._plc_inspection_cursor >= len(names):
            return
        addresses = INSPECTION_POINT_REGISTERS[names[self._plc_inspection_cursor]]
        point = self._read_plc_point(addresses)
        if point is None:
            self.statusBar().showMessage(
                "PLC read failed — check PLC connection (see status bar on landing page)", 4000
            )
            return
        self._point_manager.add_inspection_point(*point)
        self._plc_inspection_cursor += 1

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
        """Return inspection points as ``(label, LOCAL coordinates)``."""
        points = self._point_manager.inspection_points()
        if self._transformer is None:
            return points
        return [
            (label, self._transformer.world_to_plane(coords).as_array())
            for label, coords in points
        ]

    def _update_inspection_point_local(self, label: str, x: float, y: float, z: float) -> None:
        """Commit an edited LOCAL coordinate row back to the point manager."""
        if self._transformer is None:
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
        """Populate point manager with seed points."""
        for x, y, z in INITIAL_PLANE_POINTS:
            self._point_manager.add_plane_point(x, y, z)
        for x, y, z in INITIAL_INSPECTION_POINTS:
            self._point_manager.add_inspection_point(x, y, z)

    # ------------------------------------------------------------------
    # The pipeline
    # ------------------------------------------------------------------

    def _recompute(self) -> None:
        """Re-run the full pipeline and push fresh results to both views."""
        plane_result = None
        coordinate_system = None
        measurements = []
        self._transformer = None

        active_points = self._point_manager.active_plane_points_dict()
        active_array = self._point_manager.active_plane_points_array()
        from core.tilt import virtual_leveled_points
        leveled_points = virtual_leveled_points(
            active_points, self._point_manager.edited_plane_labels()
        )
        active_array = np.stack(list(leveled_points.values())) if leveled_points else active_array

        if len(active_array) >= BestFitPlane.MIN_POINTS:
            try:
                plane_result = BestFitPlane.fit(active_array)
            except PlaneFitError:
                plane_result = None

        if plane_result is not None:
            self._plane_angle_panel.display(
                plane_result.angle_x_deg(), plane_result.angle_y_deg()
            )
            if hasattr(self, "_axis_angle_widget"):
                self._axis_angle_widget.display(
                    plane_result.angle_x_deg(), plane_result.angle_y_deg()
                )
            coordinate_system = self._build_coordinate_system(plane_result, list(leveled_points.values()))
        else:
            self._plane_angle_panel.display(None, None)
            if hasattr(self, "_axis_angle_widget"):
                self._axis_angle_widget.display(None, None)

        if plane_result is not None and coordinate_system is not None:
            self._transformer = CoordinateTransformer(coordinate_system)
            measurements = MeasurementEngine.measure_points(
                self._point_manager.inspection_points(), plane_result, self._transformer
            )

        # Populate Right Panel Tab 1: Coordinates Table
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
            inspection_points=self._point_manager.inspection_points(),
            reference_label=reference_label,
        )

        if self._transformer is not None:
            for label, world_p in active_points.items():
                loc_p = self._transformer.world_to_plane(world_p).as_array()
                d = float(np.linalg.norm(loc_p))
                coord_rows.append((
                    label,
                    float(world_p[0]), float(world_p[1]), float(world_p[2]),
                    float(loc_p[0]), float(loc_p[1]), float(loc_p[2]),
                    d,
                ))
            for m in measurements:
                loc_p = m.plane_coordinates.as_array()
                world_p = m.world_coordinates
                d = m.distance_to_reference if is_plane_ref else abs(m.distance_to_plane)
                coord_rows.append((
                    m.label,
                    float(world_p[0]), float(world_p[1]), float(world_p[2]),
                    float(loc_p[0]), float(loc_p[1]), float(loc_p[2]),
                    float(d),
                ))
        else:
            for label, world_p in active_points.items():
                d = float(np.linalg.norm(world_p))
                coord_rows.append((
                    label,
                    float(world_p[0]), float(world_p[1]), float(world_p[2]),
                    float(world_p[0]), float(world_p[1]), float(world_p[2]),
                    d,
                ))
            for label, world_p in self._point_manager.inspection_points():
                d = float(np.linalg.norm(world_p))
                coord_rows.append((
                    label,
                    float(world_p[0]), float(world_p[1]), float(world_p[2]),
                    float(world_p[0]), float(world_p[1]), float(world_p[2]),
                    d,
                ))

        self._right_panel.display_coordinates(coord_rows)

        # Populate Right Panel Tab 2: Pairwise Distances Table
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

        # Populate Left Panel Reference -> Inspection Distance panel
        display_ref_label = reference_label if is_plane_ref else "World Origin"
        distance_entries = [
            (
                m.label,
                m.distance_to_reference,
                tuple(float(v) for v in m.plane_coordinates.as_array()),
            )
            for m in measurements
        ]
        self._reference_distance_panel.display(display_ref_label, distance_entries)

        # Populate Right Panel Tab 3: Live Info panel
        active_label = reference_label if is_plane_ref else None
        active_world = reference_point
        active_local = None
        active_distance = None
        if active_world is None and measurements:
            active_label = measurements[0].label
            active_world = measurements[0].world_coordinates
            active_local = measurements[0].plane_coordinates.as_array()
            active_distance = abs(measurements[0].distance_to_plane)
        elif active_world is not None and self._transformer is not None:
            active_local = self._transformer.world_to_plane(active_world).as_array()
            active_distance = float(
                np.dot(active_world - coordinate_system.origin, coordinate_system.z_axis)
            ) if coordinate_system is not None else None

        self._right_panel.display_info(
            rotation_matrix=coordinate_system.rotation_matrix if coordinate_system is not None else None,
            origin=coordinate_system.origin if coordinate_system is not None else None,
            normal=plane_result.normal if plane_result is not None else None,
            inclination_x_deg=plane_result.angle_x_deg() if plane_result is not None else None,
            inclination_y_deg=plane_result.angle_y_deg() if plane_result is not None else None,
            reference_label=display_ref_label if coordinate_system is not None else None,
            active_label=active_label,
            world_coordinates=active_world,
            local_coordinates=active_local,
            distance_to_plane=active_distance,
        )

        self._update_status_bar(plane_result, active_points, display_ref_label if coordinate_system is not None else None)

        self._measurements_changed.emit()

    def _build_coordinate_system(self, plane_result, points_array):
        """Build local frame for reference selector text."""
        plane_result = self._apply_edge_axis_override(plane_result)

        reference_text = self._reference_selector.current_reference_text()
        plane_labels = self._point_manager.plane_point_labels()

        if reference_text in plane_labels:
            try:
                point_index = plane_labels.index(reference_text)
                return CoordinateSystemBuilder.build_at_plane_point(
                    plane_result, np.stack(points_array), point_index
                )
            except CoordinateSystemError:
                return CoordinateSystemBuilder.build_at_world_origin(plane_result)

        return CoordinateSystemBuilder.build_at_world_origin(plane_result)

    def _apply_edge_axis_override(self, plane_result):
        if not self._edge_axis_selector.is_side_mode():
            self._edge_axis_selector.set_assigned_axis(None, None)
            return plane_result

        edited = self._point_manager.edited_plane_labels()
        plane_labels = [
            label for label in self._point_manager.plane_point_labels()
            if label in edited
        ]
        if len(plane_labels) < 2:
            self._edge_axis_selector.set_assigned_axis(None, None)
            return plane_result

        axis = self._edge_axis_selector.selected_axis()
        label_1, label_2 = plane_labels[0], plane_labels[1]
        try:
            point_1 = self._point_manager.get_plane_point(label_1)
            point_2 = self._point_manager.get_plane_point(label_2)
            overridden = apply_first_second_axis(plane_result, point_1, point_2, axis)
            self._edge_axis_selector.set_assigned_axis(axis, f"{label_1}\u2192{label_2}")
            return overridden
        except (PointManagerError, PlaneFitError):
            self._edge_axis_selector.set_assigned_axis(None, None)
            return plane_result
