"""
app/module_specs.py
====================
Single source of truth for per-module UI vocabulary/layout flags -- avoids
`if self.module == "perpendicularity"` checks scattered through MainWindow.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    window_title: str

    plane_feature_label: str = "Plane Points"
    inspection_feature_label: str = "Inspection Points"

    # 0 for Distance-style single inspected points; BestFitPlane.MIN_POINTS
    # (3) for an orientation module, where "Inspection Points" is really a
    # second, independently best-fit Inspection PLANE.
    inspection_min_points: int = 0

    uses_distance_panel: bool = True
    uses_edge_axis: bool = True

    # Plane Inclination (world-tilt of the datum plane) and the local-origin
    # Reference selector are Distance-module concepts -- irrelevant once the
    # left panel is Reference Plane vs Inspection Plane.
    show_plane_angle_panel: bool = True
    show_reference_selector: bool = True

    # None if no orientation-style GD&T check; otherwise a key into
    # core.orientation.ORIENTATION_CHECKS used as the shared panel's
    # default selected check.
    orientation_kind: str | None = None


MODULE_SPECS: dict[str, ModuleSpec] = {
    "distance": ModuleSpec(
        module_id="distance",
        window_title="Distance & Coordinate Measurement",
        plane_feature_label="Plane Points",
        inspection_feature_label="Inspection Points",
        inspection_min_points=0,
        uses_distance_panel=True,
        uses_edge_axis=True,
        show_plane_angle_panel=True,
        show_reference_selector=True,
        orientation_kind=None,
    ),
    "perpendicularity": ModuleSpec(
        module_id="perpendicularity",
        window_title="Parallelism & Perpendicularity",
        plane_feature_label="Reference Plane",
        inspection_feature_label="Inspection Plane",
        inspection_min_points=0,
        uses_distance_panel=False,
        uses_edge_axis=False,
        show_plane_angle_panel=False,
        show_reference_selector=False,
        orientation_kind="Perpendicularity",
    ),
    # Parallelism reuses this exact shape -- the ONLY difference is which
    # check is pre-selected (the panel itself switches live regardless):
    #   "parallelism": ModuleSpec(
    #       module_id="parallelism", window_title="Parallelism & Perpendicularity",
    #       plane_feature_label="Reference Plane", inspection_feature_label="Inspection Plane",
    #       inspection_min_points=3, uses_distance_panel=False, uses_edge_axis=False,
    #       show_plane_angle_panel=False, show_reference_selector=False,
    #       orientation_kind="Parallelism",
    #   ),
}

_DEFAULT_SPEC = MODULE_SPECS["distance"]


def get_module_spec(module_id: str) -> ModuleSpec:
    return MODULE_SPECS.get(module_id, _DEFAULT_SPEC)