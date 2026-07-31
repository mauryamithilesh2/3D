"""
core/edge_axis.py
==================
Optional override for the plane's local in-plane axes: instead of the
default in ``best_fit_plane.BestFitPlane.fit`` (local X anchored to a
projection of the WORLD X axis onto the plane), let the operator pick a
SINGLE reference plane point, and use whichever line from that point to one
of its adjacent plane points best aligns with a global axis as that axis.

``apply_best_side_axis`` is the fully automatic entry point used by the UI:
given one reference point and the rest of the plane points as candidates,
it checks the line from the reference point to EVERY other plane point,
scores each by how closely it aligns with either global axis, and picks
both the winning line and which axis (X or Y) it becomes -- no manual
second-point choice and no manual X/Y choice.

``apply_edge_axis`` is the lower-level building block that forces a single,
already-known pair of points onto a specific axis -- it is not exposed to
the UI (which only offers the automatic path) but is kept as a small,
independently testable primitive that :func:`apply_best_side_axis` shares
its rotation-matrix-building code with.

Important note on inclined planes
----------------------------------
When the plane is tilted relative to the world XY plane, a line's angle to
world X and its angle to world Y are NOT complementary (they no longer sum
to 90 degrees) -- an inclined line picks up a world-Z component, which
shrinks BOTH cosines compared to the flat-plane case. The scoring here
never assumes complementary angles: it always computes both angles
independently from the actual 3-D line direction and compares them
directly, so the "closest axis" choice stays correct at any plane tilt.

Nothing about the plane fit itself changes -- centroid, normal, rms_error,
singular_values, and point_count all pass through completely unchanged.
Only the in-plane rotation_matrix columns are recomputed, so every existing
consumer (CoordinateSystemBuilder, CoordinateTransformer, MeasurementEngine,
the coordinate table, the 3-D local axes/plane patch rendering) keeps
working exactly as before -- they only ever read ``rotation_matrix`` and
have no idea whether it came from the world-anchored default or a
side-defined override.

Z is completely unaffected by anything in this module. It is already fixed
and canonicalized to a positive world-Z component in
``BestFitPlane.fit`` before any X/Y logic ever runs, and none of the
functions below touch ``normal`` at all -- they only ever read it.

Compatible with Python 3.10+, NumPy only (no SciPy).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from core.best_fit_plane import BestFitPlaneResult, PlaneFitError, _safe_normalize

#: The two supported in-plane axis identities.
_VALID_AXES = ("x", "y")

_WORLD_X = np.array([1.0, 0.0, 0.0])
_WORLD_Y = np.array([0.0, 1.0, 0.0])


def _project_edge_onto_plane(normal: np.ndarray, point_a: np.ndarray, point_b: np.ndarray) -> np.ndarray:
    """Return the unit-length, in-plane direction of ``point_b - point_a``.

    Uses the same in-plane-projection trick already used for the
    world-X-projection method in ``BestFitPlane.fit``: subtract the raw
    edge's component along the normal, leaving only the part that actually
    lies in the plane, then normalize.
    """
    raw_edge = np.asarray(point_b, dtype=np.float64) - np.asarray(point_a, dtype=np.float64)
    in_plane_edge = raw_edge - float(np.dot(raw_edge, normal)) * normal
    return _safe_normalize(
        in_plane_edge, "side-defined local axis (side is nearly parallel to the plane normal)"
    )


def _closest_global_axis_score(edge_direction: np.ndarray) -> tuple[str, float]:
    """Score ``edge_direction`` against both global axes and return
    ``(axis, score)`` for whichever it is closer to.

    A line's angle to world X and to world Y do NOT sum to 90 degrees once
    the plane is inclined (an inclined line has a non-zero world-Z
    component, which shrinks both cosines below their flat-plane values).
    So this always computes both angles independently -- via the ABSOLUTE
    dot product with each global axis, ignoring which way along the line it
    happens to point -- and compares them directly, rather than assuming
    any complementary relationship. Whichever cosine is larger (angle
    smaller) wins; ties default to 'x'. The returned score is that winning
    cosine, so several candidate lines can be ranked against each other by
    how well any of them aligns with EITHER axis.
    """
    cos_to_x = abs(float(np.dot(edge_direction, _WORLD_X)))
    cos_to_y = abs(float(np.dot(edge_direction, _WORLD_Y)))
    return ("x", cos_to_x) if cos_to_x >= cos_to_y else ("y", cos_to_y)


def _build_rotation_matrix(normal: np.ndarray, edge_direction: np.ndarray, axis: str) -> np.ndarray:
    """Build an orthonormal (x_axis, y_axis, normal) rotation matrix with
    ``edge_direction`` (already sign-corrected) assigned to ``axis``."""
    if axis == "x":
        x_axis = edge_direction
        y_axis = _safe_normalize(np.cross(normal, x_axis), "plane local Y axis (derived from side X)")
        x_axis = _safe_normalize(np.cross(y_axis, normal), "plane local X axis (re-orthogonalized)")
    else:
        y_axis = edge_direction
        x_axis = _safe_normalize(np.cross(y_axis, normal), "plane local X axis (derived from side Y)")
        y_axis = _safe_normalize(np.cross(normal, x_axis), "plane local Y axis (re-orthogonalized)")

    rotation_matrix = np.column_stack((x_axis, y_axis, normal))
    assert abs(float(np.linalg.det(rotation_matrix)) - 1.0) < 1e-6
    return rotation_matrix


# def apply_best_side_axis(
#     result: BestFitPlaneResult,
#     reference_point: np.ndarray,
#     candidates: list[tuple[str, np.ndarray]],
# ) -> tuple[BestFitPlaneResult, str, str]:
#     """Pick, fully automatically, the line from ``reference_point`` to
#     whichever OTHER plane point in ``candidates`` best aligns with a
#     global axis, and use it as that axis.

#     No manual second-point choice and no manual X/Y choice: every
#     candidate line (reference -> each adjacent plane point) is checked,
#     scored by how closely it aligns with EITHER global axis (see
#     :func:`_closest_global_axis_score`), and the highest-scoring line wins
#     -- both which point it runs to and which axis (X or Y) it becomes are
#     decided by this scoring.

#     Sign convention
#     ---------------
#     The projected winning line is ambiguous in sign (it flips depending on
#     which of the two points happens to be "reference" vs "adjacent"). It is
#     flipped, if necessary, so it points into the same half-space as the
#     global axis it was assigned to (angle to that axis stays <= 90
#     degrees) -- deterministic regardless of point order.

#     Z is untouched here: ``result.normal`` is only ever read, never
#     modified.

#     Parameters
#     ----------
#     result:
#         An already-fitted plane. Its ``centroid``, ``normal``, ``rms_error``,
#         ``singular_values``, and ``point_count`` are reused unchanged --
#         only ``rotation_matrix`` is replaced.
#     reference_point:
#         World coordinates of the single operator-chosen reference point.
#     candidates:
#         ``(label, world_coordinates)`` pairs for every OTHER plane point to
#         check a line against. Degenerate candidates (coincident with the
#         reference point, or running almost exactly along the plane normal)
#         are silently skipped in favor of the next-best candidate.

#     Returns
#     -------
#     tuple[BestFitPlaneResult, str, str]
#         The plane result with its rotation_matrix updated, which axis
#         ('x' or 'y') was assigned, and the label of the candidate point
#         whose line to the reference point won -- useful for operator
#         feedback (e.g. "PL1 -> PL3 assigned as Local Y").

#     Raises
#     ------
#     PlaneFitError
#         If ``candidates`` is empty, or every candidate line is degenerate.
#     """
#     normal = result.normal

#     best_score = -1.0
#     best_direction: np.ndarray | None = None
#     best_axis: str | None = None
#     best_label: str | None = None

#     for label, point in candidates:
#         try:
#             direction = _project_edge_onto_plane(normal, reference_point, point)
#         except PlaneFitError:
#             continue
#         axis, score = _closest_global_axis_score(direction)
#         if score > best_score:
#             best_score = score
#             best_direction = direction
#             best_axis = axis
#             best_label = label

#     if best_direction is None or best_axis is None or best_label is None:
#         raise PlaneFitError(
#             "No usable line to a candidate plane point was found (all candidates "
#             "coincide with the reference point or run along the plane normal)."
#         )

#     global_axis = _WORLD_X if best_axis == "x" else _WORLD_Y
#     if float(np.dot(best_direction, global_axis)) < 0.0:
#         best_direction = -best_direction

#     rotation_matrix = _build_rotation_matrix(normal, best_direction, best_axis)
#     return replace(result, rotation_matrix=rotation_matrix), best_axis, best_label


def apply_edge_axis(
    result: BestFitPlaneResult,
    point_a: np.ndarray,
    point_b: np.ndarray,
    axis: str,
) -> BestFitPlaneResult:
    """Lower-level building block: force the line ``point_b - point_a``
    (projected onto the plane) to become a SPECIFIC local ``axis``
    ('x' or 'y'), decided by the caller rather than automatically.

    Not used by the UI (which only offers the fully automatic
    :func:`apply_best_side_axis` path) -- kept here as a small,
    independently testable primitive that shares its rotation-matrix
    construction with :func:`apply_best_side_axis`.

    See :func:`apply_best_side_axis` for the sign convention and the
    guarantee that ``centroid``/``normal``/``rms_error``/
    ``singular_values``/``point_count`` all pass through unchanged.

    Raises
    ------
    PlaneFitError
        If ``axis`` is not ``'x'``/``'y'``, or the line direction is
        degenerate.
    """
    axis = axis.lower()
    if axis not in _VALID_AXES:
        raise PlaneFitError(f"axis must be 'x' or 'y', got {axis!r}.")

    normal = result.normal
    edge_direction = _project_edge_onto_plane(normal, point_a, point_b)

    global_axis = _WORLD_X if axis == "x" else _WORLD_Y
    if float(np.dot(edge_direction, global_axis)) < 0.0:
        edge_direction = -edge_direction

    rotation_matrix = _build_rotation_matrix(normal, edge_direction, axis)
    return replace(result, rotation_matrix=rotation_matrix)



def apply_first_second_axis(
    result: BestFitPlaneResult,
    point_1: np.ndarray,
    point_2: np.ndarray,
    axis: str,
) -> BestFitPlaneResult:
    """Use the line from the 1st to the 2nd plane point (insertion order)
    as a local in-plane axis, on whichever axis ('x' or 'y') the operator
    has chosen. Thin wrapper around :func:`apply_edge_axis` so the call
    site in the UI layer only has to think in terms of "1st/2nd point",
    not raw point-pair mechanics."""
    return apply_edge_axis(result, point_1, point_2, axis)