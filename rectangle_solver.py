"""
rectangle_solver.py
====================
Rigid, arbitrarily-oriented rectangular-plate constraint solver.

This module owns **all** of the constraint mathematics required to make the
4-corner plane quad (``P1, P2, P3, P4``) behave like a real rigid CAD
rectangle floating in 3-D space, instead of four independent points.

Design goals
------------
* One corner (the *pivot*) is held perfectly fixed.
* The user edits exactly **one** coordinate of exactly **one** corner.
* The solver computes the unique, minimal-motion rigid transformation of the
  *entire* rectangle that satisfies that single edited coordinate while
  keeping the pivot fixed and preserving, exactly:

    - planarity            (all 4 points remain coplanar)
    - both edge lengths     (width ``W`` and height ``H``)
    - both right angles     (adjacent edges stay perpendicular)
    - parallelism           (opposite edges stay parallel)

* No axis-aligned assumptions are made anywhere. The rectangle may already
  be rotated arbitrarily in 3-D; the solver works purely with vectors
  relative to the pivot corner, using dot products, cross products,
  normalization and Rodrigues' rotation formula.

Why a *rotation*, not a re-projection?
---------------------------------------
A rigid rectangle with one corner (the pivot) nailed down has exactly three
remaining degrees of freedom: its orientation in space (a rotation
``R ∈ SO(3)`` applied to the pivot-relative corner vectors). Width, height
and the right angle are baked into the *shape* once, at construction time,
and a rotation is an isometry -- it cannot stretch, shear, twist or fold the
shape. So, as long as every update is expressed as "rotate the whole rigid
body about the pivot", the rectangle is *mathematically incapable* of
becoming non-planar, non-rectangular or the wrong size. This is the
approach taken below: every edit is reduced to finding the right rotation.

Compatible with Python 3.11+, NumPy >= 1.24.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import numpy.typing as npt

Vec3 = tuple[float, float, float]
"""A plain (x, y, z) coordinate tuple, the format used by the rest of the app."""

_EPS: float = 1e-9
"""Numerical tolerance used throughout for degenerate-case detection."""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RectangleSolverError(ValueError):
    """Raised when the solver is asked to operate on an invalid configuration.

    Examples: a degenerate (zero-area) rectangle, or a pivot/corner index
    outside the valid ``0..3`` range.
    """


# ---------------------------------------------------------------------------
# Low level vector-math helpers (pure functions, fully unit-testable)
# ---------------------------------------------------------------------------

def _skew(v: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Return the 3x3 skew-symmetric ("cross product") matrix of ``v``.

    For any vector ``w``, ``_skew(v) @ w == np.cross(v, w)``.
    """
    x, y, z = v
    return np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ],
        dtype=np.float64,
    )


def _any_perpendicular(v: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Return an arbitrary unit vector perpendicular to unit vector ``v``.

    Used only for the degenerate 180-degree-rotation edge case, where the
    rotation axis between two anti-parallel vectors is ambiguous and any
    perpendicular axis is equally valid.
    """
    # Pick whichever world axis is least parallel to v, to avoid a
    # near-zero cross product.
    world_axis = np.array([1.0, 0.0, 0.0]) if abs(v[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    perp = np.cross(v, world_axis)
    return perp / np.linalg.norm(perp)


def _rotation_about_axis(axis: npt.NDArray[np.float64], angle: float) -> npt.NDArray[np.float64]:
    """Rodrigues' rotation formula: rotation matrix for ``angle`` radians about ``axis``.

    Parameters
    ----------
    axis:
        Unit-length rotation axis.
    angle:
        Rotation angle in radians (right-hand rule about ``axis``).
    """
    k = _skew(axis)
    return np.eye(3) + math.sin(angle) * k + (1.0 - math.cos(angle)) * (k @ k)


def _rotation_between_vectors(
    a: npt.NDArray[np.float64],
    b: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Return the minimal rotation matrix ``R`` such that ``R @ a == b``.

    Both ``a`` and ``b`` must be unit vectors. Implemented with Rodrigues'
    rotation formula:

        R = I + [v]_x + [v]_x^2 * (1 - cos(theta)) / sin(theta)^2

    where ``v = a x b`` (rotation axis scaled by ``sin(theta)``) and
    ``cos(theta) = a . b``.

    Degenerate cases are handled explicitly:

    * ``a`` parallel to ``b``      -> identity rotation.
    * ``a`` anti-parallel to ``b`` -> 180-degree rotation about any axis
      perpendicular to ``a`` (chosen deterministically).
    """
    v = np.cross(a, b)
    s = np.linalg.norm(v)  # sin(theta)
    c = float(np.dot(a, b))  # cos(theta)

    if s < _EPS:
        if c > 0.0:
            # Vectors already (numerically) identical -> no rotation needed.
            return np.eye(3)
        # Vectors point in exactly opposite directions: rotate 180 degrees
        # about any axis perpendicular to `a`.
        axis = _any_perpendicular(a)
        return _rotation_about_axis(axis, math.pi)

    vx = _skew(v)
    return np.eye(3) + vx + vx @ vx * ((1.0 - c) / (s * s))


# ---------------------------------------------------------------------------
# Rectangle normalization (build a perfect rectangle from 4 approximate corners)
# ---------------------------------------------------------------------------

def _cyclic_neighbors(pivot_index: int) -> tuple[int, int, int]:
    """Return (next_index, opposite_index, prev_index) around the P1-P2-P3-P4 cycle.

    The four corners are assumed to be listed in perimeter order
    (P1 -> P2 -> P3 -> P4 -> P1), i.e. index ``i`` is adjacent to
    ``i-1`` and ``i+1`` (mod 4) and diagonal to ``i+2`` (mod 4).
    """
    nxt = (pivot_index + 1) % 4
    opp = (pivot_index + 2) % 4
    prv = (pivot_index + 3) % 4
    return nxt, opp, prv


def normalize_to_rectangle(
    corners: npt.NDArray[np.float64],
    pivot_index: int,
) -> npt.NDArray[np.float64]:
    """Project 4 approximately-rectangular corners onto the *nearest* perfect rectangle.

    The pivot corner is kept exactly fixed. The edge from the pivot to its
    "next" neighbour defines unit axis ``u`` and height ``H``. The edge from
    the pivot to its "previous" neighbour is Gram-Schmidt orthogonalized
    against ``u`` to define unit axis ``v`` (guaranteed perpendicular to
    ``u``) and width ``W``. The diagonal corner is then placed at
    ``pivot + H*u + W*v``, which is exactly planar, exactly rectangular, and
    matches the input as closely as a true rectangle can.

    This is used once, at construction/reset time, so that every subsequent
    edit -- which only ever *rotates* this already-perfect shape about the
    pivot -- can never drift away from a perfect rectangle.

    Parameters
    ----------
    corners:
        Shape ``(4, 3)`` array of corner points, in perimeter order.
    pivot_index:
        Index (0-3) of the corner to hold fixed.

    Returns
    -------
    ndarray
        Shape ``(4, 3)`` array describing a perfect rectangle.

    Raises
    ------
    RectangleSolverError
        If the input is degenerate (zero-length edge, or the two edges from
        the pivot are collinear so no plane can be formed).
    """
    nxt, opp, prv = _cyclic_neighbors(pivot_index)

    origin = corners[pivot_index].astype(np.float64)
    e1 = corners[nxt].astype(np.float64) - origin
    e2 = corners[prv].astype(np.float64) - origin

    h = float(np.linalg.norm(e1))
    if h < _EPS:
        raise RectangleSolverError(
            "Degenerate rectangle: zero-length edge adjacent to the pivot corner."
        )
    u = e1 / h

    # Gram-Schmidt: remove the component of e2 along u so v is exactly perpendicular.
    e2_perp = e2 - float(np.dot(e2, u)) * u
    w = float(np.linalg.norm(e2_perp))
    if w < _EPS:
        raise RectangleSolverError(
            "Degenerate rectangle: the two edges from the pivot corner are collinear."
        )
    v = e2_perp / w

    result = np.empty((4, 3), dtype=np.float64)
    result[pivot_index] = origin
    result[nxt] = origin + h * u
    result[opp] = origin + h * u + w * v
    result[prv] = origin + w * v
    return result


# ---------------------------------------------------------------------------
# Public solver class
# ---------------------------------------------------------------------------

@dataclass
class RectangleSolver:
    """Stateful rigid-rectangle constraint solver.

    Holds the authoritative geometry (4 corner points, in perimeter order
    ``P1, P2, P3, P4``) and the index of the corner currently acting as the
    fixed pivot. All mutating methods preserve rigidity exactly.

    Typical usage
    -------------
    >>> solver = RectangleSolver(
    ...     (-50.0, -50.0, 0.0),
    ...     (50.0, -50.0, 0.0),
    ...     (50.0, 50.0, 0.0),
    ...     (-50.0, 50.0, 0.0),
    ...     pivot_index=3,
    ... )
    >>> new_corners = solver.update_coordinate(corner_index=0, axis_index=0, new_value=-40.0)
    >>> gl3d_widget.set_plane_points(*new_corners)
    """

    _corners: npt.NDArray[np.float64]
    """Shape (4, 3) float64 array; the single source of truth for the geometry."""

    _pivot_index: int
    """Index (0-3) of the corner (P1=0 .. P4=3) currently held fixed."""

    def __init__(
        self,
        p1: Vec3,
        p2: Vec3,
        p3: Vec3,
        p4: Vec3,
        pivot_index: int = 3,
    ) -> None:
        """Construct a solver, normalizing the input to a perfect rectangle.

        Parameters
        ----------
        p1, p2, p3, p4:
            Initial corner coordinates, in perimeter order.
        pivot_index:
            Index of the corner to hold fixed (0=P1, 1=P2, 2=P3, 3=P4).
            Defaults to ``3`` (P4), matching the example workflow where P4
            stays fixed while P1/P2/P3 move.
        """
        self._validate_index(pivot_index, "pivot_index")
        raw = np.array([p1, p2, p3, p4], dtype=np.float64)
        self._pivot_index = pivot_index
        self._corners = normalize_to_rectangle(raw, pivot_index)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_index(index: int, name: str) -> None:
        if index not in (0, 1, 2, 3):
            raise RectangleSolverError(f"{name} must be 0, 1, 2 or 3 (got {index!r}).")

    @staticmethod
    def _validate_axis(axis_index: int) -> None:
        if axis_index not in (0, 1, 2):
            raise RectangleSolverError(f"axis_index must be 0 (x), 1 (y) or 2 (z) (got {axis_index!r}).")

    # ------------------------------------------------------------------
    # Core constraint solve
    # ------------------------------------------------------------------

    def update_coordinate(
        self,
        corner_index: int,
        axis_index: int,
        new_value: float,
    ) -> tuple[Vec3, Vec3, Vec3, Vec3]:
        """Apply a single-coordinate edit and re-solve the whole rigid rectangle.

        This is the only entry point the UI needs. It implements exactly the
        required behaviour:

        * The pivot corner never moves.
        * ``corner_index``'s edited axis is driven to ``new_value`` exactly
          (unless geometrically unreachable, see *Clamping* below).
        * The other two coordinates of ``corner_index`` are recomputed
          automatically.
        * The two remaining (non-pivot, non-edited) corners move
          automatically so the shape stays a perfect rectangle.

        Mathematics
        -----------
        1. Let ``O`` be the pivot position and ``d_old = corner - O`` the
           pivot-relative vector of the edited corner, with fixed length
           ``r = |d_old|`` (an edge length or the diagonal -- whichever
           corner was edited). Rigidity requires the new pivot-relative
           vector ``d_new`` to also have length ``r``.
        2. The user only constrains one component of ``d_new`` (the edited
           axis): ``d_new[axis] = new_value - O[axis]``. Combined with
           ``|d_new| = r``, this pins ``d_new`` to a **circle**: the
           intersection of a sphere of radius ``r`` and a plane
           perpendicular to the world axis. Among all points on that circle,
           the solver picks the one closest to ``d_old`` (minimal motion),
           which has a closed form: keep the other two components
           proportional to their old values, rescaled to satisfy the sphere
           equation.
        3. The rotation ``R`` that carries ``d_old`` to ``d_new`` (Rodrigues'
           formula, via the cross and dot product of the two unit vectors)
           is then applied rigidly to *every* corner relative to the pivot:
           ``corner_i' = O + R @ (corner_i - O)``. Because ``R`` is a proper
           rotation (orthogonal, det = +1), this transformation is an exact
           isometry -- it cannot change any pairwise distance or angle, so
           planarity, both edge lengths, and both right angles are
           preserved automatically, by construction.

        Special case -- editing the pivot itself
        -----------------------------------------
        If ``corner_index == pivot_index``, there is no pivot-relative
        vector to rotate (the pivot is the origin of that frame). In this
        case the edit is a pure rigid **translation**: the whole rectangle
        is shifted by the requested delta along the given axis, which
        trivially preserves every rigidity property.

        Clamping
        --------
        If ``new_value`` would require the edited corner to move farther
        from the pivot than its fixed length ``r`` allows (i.e. it is
        geometrically unreachable without stretching), the coordinate is
        clamped to the nearest reachable value (``+-r`` from the pivot along
        that axis) so the solver never silently stretches the rectangle.

        Parameters
        ----------
        corner_index:
            Which corner was edited: 0=P1, 1=P2, 2=P3, 3=P4.
        axis_index:
            Which coordinate was edited: 0=x, 1=y, 2=z.
        new_value:
            The new value the user typed for that single coordinate.

        Returns
        -------
        tuple of 4 Vec3
            The updated ``(P1, P2, P3, P4)`` corner coordinates.
        """
        self._validate_index(corner_index, "corner_index")
        self._validate_axis(axis_index)

        if corner_index == self._pivot_index:
            self._corners = self._translate_pivot(axis_index, new_value)
        else:
            self._corners = self._rotate_about_pivot(corner_index, axis_index, new_value)

        return self.get_corners()

    def _translate_pivot(self, axis_index: int, new_value: float) -> npt.NDArray[np.float64]:
        """Translate the entire rigid rectangle so the pivot's coordinate hits ``new_value``."""
        delta = new_value - self._corners[self._pivot_index, axis_index]
        translation = np.zeros(3, dtype=np.float64)
        translation[axis_index] = delta
        return self._corners + translation

    def _rotate_about_pivot(
        self,
        corner_index: int,
        axis_index: int,
        new_value: float,
    ) -> npt.NDArray[np.float64]:
        """Solve for, and apply, the rigid rotation about the pivot (see class docstring)."""
        origin = self._corners[self._pivot_index]
        d_old = self._corners[corner_index] - origin
        r = float(np.linalg.norm(d_old))
        if r < _EPS:
            raise RectangleSolverError(
                "Degenerate rectangle: edited corner coincides with the pivot corner."
            )

        other_axes = [i for i in range(3) if i != axis_index]
        a0, b0 = d_old[other_axes[0]], d_old[other_axes[1]]

        # Target value for the constrained component, clamped to what's
        # geometrically reachable at fixed distance r from the pivot.
        c_target = new_value - origin[axis_index]
        c = float(np.clip(c_target, -r, r))

        remaining_sq = max(r * r - c * c, 0.0)
        remaining = math.sqrt(remaining_sq)
        norm_ab = math.hypot(a0, b0)

        d_new = np.zeros(3, dtype=np.float64)
        d_new[axis_index] = c
        if norm_ab > _EPS:
            scale = remaining / norm_ab
            d_new[other_axes[0]] = a0 * scale
            d_new[other_axes[1]] = b0 * scale
        elif remaining > _EPS:
            # d_old points exactly along `axis_index`: the closest-point
            # direction on the constraint circle is ambiguous. Break the
            # tie deterministically using a perpendicular reference so the
            # result is still well-defined and continuous.
            fallback = _any_perpendicular(np.eye(3)[axis_index])
            d_new[other_axes[0]] = fallback[other_axes[0]] * remaining
            d_new[other_axes[1]] = fallback[other_axes[1]] * remaining
        # else remaining ~ 0: d_new is fully along axis_index already.

        u_old = d_old / r
        new_norm = float(np.linalg.norm(d_new))
        u_new = d_new / new_norm if new_norm > _EPS else u_old

        rotation = _rotation_between_vectors(u_old, u_new)

        new_corners = np.empty_like(self._corners)
        for i in range(4):
            new_corners[i] = origin + rotation @ (self._corners[i] - origin)
        return new_corners

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def get_corners(self) -> tuple[Vec3, Vec3, Vec3, Vec3]:
        """Return the current ``(P1, P2, P3, P4)`` corners as plain float tuples."""
        return tuple(  # type: ignore[return-value]
            (float(row[0]), float(row[1]), float(row[2])) for row in self._corners
        )

    def get_pivot_index(self) -> int:
        """Return the index (0-3) of the corner currently held fixed."""
        return self._pivot_index

    def set_pivot_index(self, pivot_index: int) -> tuple[Vec3, Vec3, Vec3, Vec3]:
        """Change which corner acts as the fixed pivot for future edits.

        The rectangle's current shape and pose are preserved -- only the
        bookkeeping of "which corner is the anchor" changes. The geometry is
        re-normalized about the new pivot to guard against any accumulated
        floating-point drift.
        """
        self._validate_index(pivot_index, "pivot_index")
        self._pivot_index = pivot_index
        self._corners = normalize_to_rectangle(self._corners, pivot_index)
        return self.get_corners()

    def reset(
        self,
        p1: Vec3,
        p2: Vec3,
        p3: Vec3,
        p4: Vec3,
        pivot_index: int | None = None,
    ) -> tuple[Vec3, Vec3, Vec3, Vec3]:
        """Reset the solver to a new (normalized) rectangle.

        Parameters
        ----------
        p1, p2, p3, p4:
            New corner coordinates, in perimeter order.
        pivot_index:
            Optional new pivot index; keeps the current pivot if omitted.
        """
        if pivot_index is not None:
            self._validate_index(pivot_index, "pivot_index")
            self._pivot_index = pivot_index
        raw = np.array([p1, p2, p3, p4], dtype=np.float64)
        self._corners = normalize_to_rectangle(raw, self._pivot_index)
        return self.get_corners()

    # ------------------------------------------------------------------
    # Diagnostics (useful for tests / sanity-checking the invariants)
    # ------------------------------------------------------------------

    def edge_lengths(self) -> tuple[float, float, float, float]:
        """Return the 4 edge lengths in order (P1P2, P2P3, P3P4, P4P1)."""
        c = self._corners
        return (
            float(np.linalg.norm(c[1] - c[0])),
            float(np.linalg.norm(c[2] - c[1])),
            float(np.linalg.norm(c[3] - c[2])),
            float(np.linalg.norm(c[0] - c[3])),
        )

    def is_valid_rectangle(self, tol: float = 1e-6) -> bool:
        """Verify (defensively) that the current corners still form a perfect rectangle.

        Checks coplanarity, opposite-side equality (parallelogram) and one
        right angle (which, combined with the parallelogram property,
        guarantees a rectangle).
        """
        c = self._corners
        e_p1p2, e_p2p3, e_p3p4, e_p4p1 = (
            c[1] - c[0],
            c[2] - c[1],
            c[3] - c[2],
            c[0] - c[3],
        )

        # Opposite sides equal length (parallelogram condition).
        if abs(np.linalg.norm(e_p1p2) - np.linalg.norm(e_p3p4)) > tol:
            return False
        if abs(np.linalg.norm(e_p2p3) - np.linalg.norm(e_p4p1)) > tol:
            return False

        # Right angle at P1.
        if abs(float(np.dot(e_p1p2, -e_p4p1))) > tol * max(
            1.0, float(np.linalg.norm(e_p1p2)) * float(np.linalg.norm(e_p4p1))
        ):
            return False

        # Coplanarity: scalar triple product of 3 independent edge vectors ~ 0.
        normal = np.cross(e_p1p2, -e_p4p1)
        if np.linalg.norm(normal) < _EPS:
            return False
        triple = float(np.dot(e_p2p3, normal))
        if abs(triple) > tol * max(1.0, float(np.linalg.norm(normal))):
            return False

        return True


# ---------------------------------------------------------------------------
# Convenience module-level helpers (stateless, for callers that don't want
# to keep a RectangleSolver instance around)
# ---------------------------------------------------------------------------

def solve_single_coordinate_edit(
    corners: Sequence[Vec3],
    pivot_index: int,
    corner_index: int,
    axis_index: int,
    new_value: float,
) -> tuple[Vec3, Vec3, Vec3, Vec3]:
    """Stateless convenience wrapper around :class:`RectangleSolver`.

    Normalizes ``corners`` to a perfect rectangle about ``pivot_index``,
    applies the single-coordinate edit, and returns the resulting 4 corners.
    Prefer keeping a persistent :class:`RectangleSolver` instance in
    production code to avoid re-normalizing on every call.
    """
    p1, p2, p3, p4 = corners
    solver = RectangleSolver(p1, p2, p3, p4, pivot_index=pivot_index)
    return solver.update_coordinate(corner_index, axis_index, new_value)