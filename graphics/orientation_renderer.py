"""
graphics/orientation_renderer.py
=================================
Perpendicularity/Parallelism 3-D overlay: renders the Inspection Plane as
its own translucent mesh SURFACE (not just scatter points), plus an angle
arc + numeric readouts between the Reference Plane's and Inspection
Plane's normals for BOTH relations at once -- Perpendicularity (deviation
from 90 deg) and Parallelism (deviation from 0 deg) -- regardless of which
one is selected in ui.orientation_result_panel.OrientationResultPanel.

Reuses core.orientation (pure math, no duplication) and
core.circularity.perpendicular_basis (building an arbitrary in-plane basis
for a given normal -- the same helper already used for the rod-axis
cross-section in Circularity).
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl

from config.sizes import (
    NORMAL_ARROW_HEAD_LENGTH,
    NORMAL_ARROW_HEAD_RADIUS,
    NORMAL_VECTOR_DISPLAY_LENGTH,
    ORIENTATION_ARC_RADIUS,
    ORIENTATION_INTERSECTION_HALF_LENGTH,
    ORIENTATION_PLANE_HALF_EXTENT,
)
from config.colors import get_color
from core.best_fit_plane import BestFitPlaneResult
from core.circularity import perpendicular_basis
from core.orientation import (
    measure_parallelism_planes,
    measure_perpendicularity_planes,
    plane_intersection_line,
)
from graphics.gl_utils import _make_cone_mesh

# REPLACE lines 35-123 (the whole function, up to but not including `def _slerp_arc`):
def _update_orientation_overlay(
    widget,
    reference_plane: BestFitPlaneResult | None,
    inspection_plane: BestFitPlaneResult | None,
    active_check: str | None = None,
) -> None:
    """(Re)build the Inspection Plane mesh, BOTH planes' normal arrows, the
    line where the two planes actually intersect, and the single active
    check's (Perpendicularity/Parallelism) angle readout -- anchored
    exactly on that intersection line, not on either plane's centroid.
    Hides everything when either plane is missing, or when the two planes
    are (near-)parallel and have no single intersection line to anchor on."""
    if reference_plane is None or inspection_plane is None:
        widget._inspection_plane_mesh_item.setVisible(False)
        widget._orientation_arc_item.setVisible(False)
        widget._orientation_perp_label.setVisible(False)
        widget._orientation_parallel_label.setVisible(False)
        widget._inspection_normal_line_item.setVisible(False)
        widget._inspection_normal_head_item.setVisible(False)
        widget._orientation_intersection_line_item.setVisible(False)
        return

    # ------------------------------------------------------------------
    # Inspection Plane surface -- a bounded quad centered on its fitted
    # centroid, spanned by an arbitrary in-plane basis for its normal.
    # ------------------------------------------------------------------
    color = get_color("COLOR_INSPECTION_PLANE")
    centroid = np.asarray(inspection_plane.centroid, dtype=np.float64)
    normal = np.asarray(inspection_plane.normal, dtype=np.float64)
    u_axis, v_axis = perpendicular_basis(normal)
    half = ORIENTATION_PLANE_HALF_EXTENT

    vertices = np.array([
        centroid - half * u_axis - half * v_axis,
        centroid + half * u_axis - half * v_axis,
        centroid + half * u_axis + half * v_axis,
        centroid - half * u_axis + half * v_axis,
    ])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    mesh = gl.MeshData(vertexes=vertices, faces=faces, faceColors=np.array([color, color]))
    widget._inspection_plane_mesh_item.setMeshData(meshdata=mesh)
    widget._inspection_plane_mesh_item.setVisible(True)

    # ------------------------------------------------------------------
    # Inspection Plane's OWN normal arrow -- so BOTH planes' orientation
    # are independently visualizable, not just the Reference Plane's (the
    # Reference Plane's normal is drawn separately -- see
    # graphics/frame_renderer.py::_update_normal_arrow).
    # ------------------------------------------------------------------
    shaft_length = max(0.0, NORMAL_VECTOR_DISPLAY_LENGTH - NORMAL_ARROW_HEAD_LENGTH)
    shaft_end = centroid + shaft_length * normal
    tip = centroid + NORMAL_VECTOR_DISPLAY_LENGTH * normal

    widget._inspection_normal_line_item.setData(
        pos=np.array([centroid, shaft_end]),
        color=get_color("COLOR_INSPECTION_NORMAL"),
    )
    widget._inspection_normal_line_item.setVisible(True)

    cone = _make_cone_mesh(
        axis_dir=normal,
        apex=tip,
        height=NORMAL_ARROW_HEAD_LENGTH,
        radius=NORMAL_ARROW_HEAD_RADIUS,
    )
    widget._inspection_normal_head_item.setMeshData(meshdata=cone)
    widget._inspection_normal_head_item.setColor(get_color("COLOR_INSPECTION_NORMAL"))
    widget._inspection_normal_head_item.setVisible(True)

    # ------------------------------------------------------------------
    # The actual line where the Reference Plane and Inspection Plane cut
    # each other. Both the drawn segment AND the angle arc/label are
    # anchored here -- not at either plane's centroid. If the two planes
    # are (near-)parallel there is no real intersection line, so nothing
    # is drawn rather than faking a line/angle that doesn't exist.
    # ------------------------------------------------------------------
    line = plane_intersection_line(reference_plane, inspection_plane)
    if line is None:
        widget._orientation_intersection_line_item.setVisible(False)
        widget._orientation_arc_item.setVisible(False)
        widget._orientation_perp_label.setVisible(False)
        widget._orientation_parallel_label.setVisible(False)
        return

    line_point, line_direction = line
    midpoint_ref = (np.asarray(reference_plane.centroid, dtype=np.float64) + centroid) / 2.0
    center = line_point + line_direction * np.dot(midpoint_ref - line_point, line_direction)

    segment = np.array([
        center - ORIENTATION_INTERSECTION_HALF_LENGTH * line_direction,
        center + ORIENTATION_INTERSECTION_HALF_LENGTH * line_direction,
    ])
    widget._orientation_intersection_line_item.setData(pos=segment)
    widget._orientation_intersection_line_item.setVisible(True)

    n_ref = np.asarray(reference_plane.normal, dtype=np.float64)
    arc_points = _slerp_arc(n_ref, normal, segments=24) * ORIENTATION_ARC_RADIUS + center
    widget._orientation_arc_item.setData(pos=arc_points)
    widget._orientation_arc_item.setVisible(True)

    mid = arc_points[len(arc_points) // 2]

    if active_check == "Parallelism":
        parallel_result = measure_parallelism_planes(reference_plane, inspection_plane)
        widget._orientation_parallel_label.setData(
            pos=mid,
            text=f"\u2225 {parallel_result.deviation_angle_deg:.2f}\u00b0",
        )
        widget._orientation_parallel_label.setVisible(True)
        widget._orientation_perp_label.setVisible(False)
    else:
        perp_result = measure_perpendicularity_planes(reference_plane, inspection_plane)
        widget._orientation_perp_label.setData(
            pos=mid,
            text=f"\u22a5 {perp_result.deviation_angle_deg:.2f}\u00b0",
        )
        widget._orientation_perp_label.setVisible(True)
        widget._orientation_parallel_label.setVisible(False)

# Leave `_slerp_arc` (the function right below) untouched.

def _slerp_arc(a: np.ndarray, b: np.ndarray, segments: int) -> np.ndarray:
    """Points along the shortest great-circle arc from unit vector ``a`` to
    unit vector ``b`` (spherical linear interpolation)."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    theta = float(np.arccos(dot))
    if theta < 1e-6:
        return np.tile(a, (segments, 1))
    sin_theta = np.sin(theta)
    out = np.empty((segments, 3))
    for i in range(segments):
        t = i / float(segments - 1)
        out[i] = (np.sin((1.0 - t) * theta) * a + np.sin(t * theta) * b) / sin_theta
    return out