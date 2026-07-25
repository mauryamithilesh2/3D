"""
best_fit_plane.py
==================
Mathematical foundation of the application: fitting a plane to a set of
3-D points in the least-squares sense using Singular Value Decomposition
(SVD).

Why a "best fit" plane at all?
-------------------------------
In real inspection tasks (CMM probing, laser scanning, robot-mounted
vision) measured points on a physical surface never lie on a mathematically
perfect plane -- there is always sensor noise and surface roughness. Given
3 or more measured points, we do not want *a* plane that passes through
them exactly (over 3 points that is impossible in general); we want the
plane that minimizes the sum of squared perpendicular distances to all of
the points. That is the definition of a least-squares "best fit" plane,
and it is exactly what SVD gives us.

Compatible with Python 3.10+, NumPy only (no SciPy).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PlaneFitError(ValueError):
    """Raised when a best fit plane cannot be computed from the given points."""


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BestFitPlaneResult:
    """Immutable result of a best fit plane computation.

    Attributes
    ----------
    centroid:
        The mean position of all input points, shape ``(3,)``. This is the
        point the plane is guaranteed to pass through.
    normal:
        Unit-length vector perpendicular to the fitted plane, shape ``(3,)``.
    rotation_matrix:
        3x3 orthonormal matrix whose columns are ``(x_axis, y_axis, normal)``
        expressed in world coordinates. This *is* the local plane coordinate
        frame -- it is reused, unmodified, by ``coordinate_system.py``.
    singular_values:
        The 3 singular values returned by the SVD, largest first. The ratio
        between the smallest and the other two indicates how "flat" the
        point cloud is (a perfect plane has a smallest singular value of 0).
    rms_error:
        Root-mean-square of the perpendicular distances from every input
        point to the fitted plane. This is the single number that answers
        "how good is this fit?" -- 0.0 means every point lies exactly on
        the plane.
    point_count:
        Number of points used to compute the fit.
    """

    centroid: np.ndarray
    normal: np.ndarray
    rotation_matrix: np.ndarray
    singular_values: np.ndarray
    rms_error: float
    point_count: int

    # -- Plane equation -----------------------------------------------------

    def plane_equation_coefficients(self) -> tuple[float, float, float, float]:
        """Return (a, b, c, d) for the implicit plane equation a*x+b*y+c*z+d=0.

        Why this form?
            Any plane can be written as the set of points X satisfying
            normal . (X - centroid) = 0, i.e. normal.X - normal.centroid = 0.
            Expanding gives a*x + b*y + c*z + d = 0 with (a, b, c) = normal
            and d = -normal.centroid. This is the standard implicit form
            used throughout metrology and CAD software.
        """
        a, b, c = self.normal
        d = -float(np.dot(self.normal, self.centroid))
        return float(a), float(b), float(c), d

    def plane_equation_string(self, decimals: int = 4) -> str:
        """Human-readable "a*x + b*y + c*z + d = 0" string for display."""
        a, b, c, d = self.plane_equation_coefficients()
        return (
            f"{a:.{decimals}f}\u00b7x + {b:.{decimals}f}\u00b7y + "
            f"{c:.{decimals}f}\u00b7z + {d:.{decimals}f} = 0"
        )

    # -- Measurements ---------------------------------------------------

    def signed_distance(self, point: np.ndarray) -> float:
        """Signed perpendicular distance from ``point`` to the plane.

        Why does a dot product give a distance?
            The vector from the centroid (a known point ON the plane) to
            ``point`` can be decomposed into a component that lies IN the
            plane and a component ALONG the normal. Because ``normal`` is
            unit length, projecting (point - centroid) onto it with a dot
            product directly yields the length of the out-of-plane
            component -- i.e. exactly how far ``point`` sits above (positive)
            or below (negative) the plane, with no extra scaling needed.
        """
        offset = np.asarray(point, dtype=np.float64) - self.centroid
        return float(np.dot(offset, self.normal))

    def project_point(self, point: np.ndarray) -> np.ndarray:
        """Orthogonal projection of ``point`` onto the fitted plane.

        Why subtract (distance * normal)?
            ``point`` equals its in-plane projection plus its out-of-plane
            component. The out-of-plane component is exactly
            (signed_distance * normal), since ``normal`` is unit length and
            signed_distance is the length of that component along it.
            Removing that component leaves only the in-plane part -- the
            projection.
        """
        point = np.asarray(point, dtype=np.float64)
        distance = self.signed_distance(point)
        return point - distance * self.normal


# ---------------------------------------------------------------------------
# Core fitting routine
# ---------------------------------------------------------------------------

class BestFitPlane:
    """Computes a least-squares best fit plane from a set of 3-D points.

    This class holds no state related to the UI; it is a pure geometry
    engine so it can be tested and reused independently of PyQt.
    """

    MIN_POINTS: int = 3

    @staticmethod
    def fit(points: np.ndarray) -> BestFitPlaneResult:
        """Fit a plane to ``points`` (shape ``(N, 3)``, N >= 3) using SVD.

        Parameters
        ----------
        points:
            Array-like of 3-D points, converted to a float64 NumPy array of
            shape ``(N, 3)``.

        Returns
        -------
        BestFitPlaneResult
            The fitted plane, its local coordinate frame, and fit quality.

        Raises
        ------
        PlaneFitError
            If fewer than 3 points are supplied, or the points are
            collinear / coincident and cannot define a plane.
        """
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[1] != 3:
            raise PlaneFitError("Points must be an (N, 3) array of X, Y, Z values.")
        if pts.shape[0] < BestFitPlane.MIN_POINTS:
            raise PlaneFitError(
                f"At least {BestFitPlane.MIN_POINTS} points are required to fit a plane, "
                f"got {pts.shape[0]}."
            )

        # --------------------------------------------------------------
        # Step 1: Centroid.
        #
        # Why compute the centroid?
        #   A plane has 3 rotational degrees of freedom (its normal
        #   direction) plus a location. Rather than solving for location
        #   and orientation simultaneously, we anchor the plane at the
        #   centroid -- the mean position of the data. The centroid is the
        #   unique point that minimizes the sum of squared distances to all
        #   input points along ANY direction, which makes it the natural,
        #   bias-free anchor for the plane we are about to fit.
        # --------------------------------------------------------------
        centroid = pts.mean(axis=0)

        # --------------------------------------------------------------
        # Step 2: Center the points (subtract the centroid).
        #
        # Why subtract the centroid?
        #   Fitting a plane through the origin of the *centered* data is
        #   equivalent to fitting the best plane through the original data
        #   passing through its centroid. Centering removes the
        #   translational component of the problem, leaving only
        #   orientation to solve for -- which is exactly what SVD finds.
        # --------------------------------------------------------------
        centered = pts - centroid

        # --------------------------------------------------------------
        # Step 3: Singular Value Decomposition of the centered points.
        #
        # Why SVD instead of solving directly (e.g. normal equations)?
        #   A naive approach might try to solve a*x + b*y + c*z = 1 in a
        #   least-squares sense, but that formulation cannot represent
        #   planes through the origin and becomes numerically unstable as
        #   a plane approaches that case (coefficients blow up). SVD instead
        #   works directly on the centered coordinate matrix and finds the
        #   directions of greatest and least variance without ever dividing
        #   by a coefficient that could be near zero. It is the numerically
        #   stable, textbook solution to total least-squares plane fitting
        #   (equivalent to PCA on the point cloud).
        #
        #   centered = U @ diag(S) @ Vt
        #   The rows of Vt (columns of V) are the principal directions of
        #   the point cloud, ordered by how much variance (spread) the data
        #   has along each one -- largest first.
        # --------------------------------------------------------------
        try:
            _, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
        except np.linalg.LinAlgError as exc:
            raise PlaneFitError(f"SVD failed to converge: {exc}") from exc

        # --------------------------------------------------------------
        # Degeneracy check using the singular values themselves.
        #
        # Why check singular_values and not the direction vectors?
        #   np.linalg.svd always returns perfectly unit-length, orthonormal
        #   direction vectors -- even for a singular value of exactly 0, it
        #   still returns *some* arbitrary unit vector spanning the missing
        #   direction. So a vector-length check can never detect degeneracy.
        #   What actually tells us the data fails to define a plane is the
        #   SPREAD of the data along each direction, i.e. the singular
        #   values. If the data has almost no spread along the second
        #   principal direction (singular_values[1] ~= 0), every input
        #   point is nearly collinear and any "plane" through that line
        #   could point in any direction -- the fit is not meaningful.
        # --------------------------------------------------------------
        spread_scale = max(singular_values[0], 1e-12)
        if singular_values[1] / spread_scale < 1e-6:
            raise PlaneFitError(
                "Could not fit a plane: the input points are collinear or "
                "coincident and do not uniquely define a plane orientation."
            )

        # --------------------------------------------------------------
        # Step 4: The normal is the LAST singular vector.
        #
        # Why is the last singular vector the normal?
        #   The plane that best fits the data is the one spanned by the two
        #   directions of GREATEST variance (the data spreads out along the
        #   plane, not off it). The remaining direction -- the one with the
        #   LEAST variance -- is therefore the direction the data barely
        #   varies along, i.e. perpendicular to the plane. Because np.linalg
        #   .svd returns singular values in descending order, that direction
        #   is always the last row of Vt.
        # --------------------------------------------------------------
        x_axis_raw = vt[0]
        y_axis_raw = vt[1]
        normal_raw = vt[2]

        # --------------------------------------------------------------
        # Step 5: Normalize the normal vector.
        #
        # Why normalize the normal?
        #   SVD already returns unit-length vectors, but we re-normalize
        #   defensively to guard against floating point drift. A UNIT
        #   normal is required for every downstream calculation:
        #   signed_distance() relies on the dot product directly returning
        #   a physical distance, which is only true if the normal has
        #   length exactly 1. A non-unit normal would silently scale every
        #   distance measurement in the application.
        # --------------------------------------------------------------
        normal = _safe_normalize(normal_raw, "plane normal")
        if normal[2] < 0.0:
            normal = -normal

        # --------------------------------------------------------------
        # Step 6: Build the plane's local coordinate frame / rotation matrix.
        #
        # Align local X-axis in-plane as closely as possible to world X-axis
        # [1, 0, 0] (or world Y [0, 1, 0] if normal is parallel to X), so
        # that local plane coordinates naturally correspond to world coordinates
        # without arbitrary SVD diagonal rotation.
        # --------------------------------------------------------------
        world_x = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        if abs(float(np.dot(world_x, normal))) > 0.99:
            world_x = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        in_plane_x = world_x - float(np.dot(world_x, normal)) * normal
        x_axis = _safe_normalize(in_plane_x, "plane local X axis")
        y_axis = _safe_normalize(np.cross(normal, x_axis), "plane local Y axis")
        x_axis = _safe_normalize(np.cross(y_axis, normal), "plane local X axis")

        rotation_matrix = np.column_stack((x_axis, y_axis, normal))

        # --------------------------------------------------------------
        # Step 7: RMS fitting error.
        #
        # This quantifies fit quality: the smallest singular value relates
        # to the total squared perpendicular distance of the centered
        # points projected onto the normal direction. We compute it
        # directly and robustly from the actual per-point distances rather
        # than only from the singular value, so the reported number always
        # matches what signed_distance() would report for the same points.
        # --------------------------------------------------------------
        distances = centered @ normal
        rms_error = float(np.sqrt(np.mean(distances ** 2)))

        return BestFitPlaneResult(
            centroid=centroid,
            normal=normal,
            rotation_matrix=rotation_matrix,
            singular_values=singular_values,
            rms_error=rms_error,
            point_count=int(pts.shape[0]),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _safe_normalize(vector: np.ndarray, name: str) -> np.ndarray:
    """Normalize ``vector`` to unit length, raising if it is degenerate.

    Parameters
    ----------
    vector:
        Vector to normalize.
    name:
        Human-readable name used in the error message (helps diagnose
        exactly which axis failed when points are degenerate).

    Raises
    ------
    PlaneFitError
        If the vector's length is too close to zero to normalize safely
        (this happens when input points are collinear or coincident,
        which leaves at least one principal direction undefined).
    """
    length = np.linalg.norm(vector)
    if length < 1e-9:
        raise PlaneFitError(
            f"Could not compute {name}: points are collinear or coincident "
            f"and do not uniquely define a plane."
        )
    return vector / length