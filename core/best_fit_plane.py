"""
core/best_fit_plane.py
======================
Mathematical foundation for plane fitting: fits a plane to a set of 3-D points
in the least-squares sense using 3-point geometry calculation.

Why a "best fit" plane at all?
-------------------------------
In real inspection tasks (CMM probing, laser scanning, robot-mounted
vision) measured points on a physical surface never lie on a mathematically
perfect plane -- there is always sensor noise and surface roughness. Given
3 or more measured points, we do not want *a* plane that passes through
them exactly (over 3 points that is impossible in general); we want the
plane that minimizes the sum of squared perpendicular distances to all of
the points.

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

    # -- Inclination angles ---------------------------------------------

    def angle_x_deg(self) -> float:
        """Plane inclination / tilt magnitude along X axis relative to horizontal (world XY plane).

        Returns positive angle in degrees (0°–90°) between normal projection in X-Z plane and Z axis.
        Uses abs(atan2) to guarantee a positive magnitude without division by zero.
        """
        nx, ny, nz = self.normal
        return float(abs(np.degrees(np.arctan2(nx, nz))))

    def angle_y_deg(self) -> float:
        """Plane inclination / tilt magnitude along Y axis relative to horizontal (world XY plane).

        Returns positive angle in degrees (0°–90°) between normal projection in Y-Z plane and Z axis.
        Uses abs(atan2) to guarantee a positive magnitude without division by zero.
        """
        nx, ny, nz = self.normal
        return float(abs(np.degrees(np.arctan2(ny, nz))))


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

        if pts.shape[0] == 3:
            # -------- EXACT 3-POINT PLANE CALCULATION (P1, P2, P3) --------
            p1 = pts[0]
            p2 = pts[1]
            p3 = pts[2]

            v1 = p2 - p1
            v2 = p3 - p1

            normal_raw = np.cross(v1, v2)
            normal = _safe_normalize(normal_raw, "plane normal from P1, P2, P3")
            centroid = p1.copy()

            offsets = pts - centroid
            distances = offsets @ normal
            rms_error = float(np.sqrt(np.mean(distances ** 2)))
            singular_values = np.array([float(np.linalg.norm(v1)), float(np.linalg.norm(v2)), 0.0])
        else:
            # -------- N > 3 LEAST-SQUARES SVD PLANE FIT --------
            centroid = pts.mean(axis=0)
            centered = pts - centroid
            try:
                _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
            except np.linalg.LinAlgError as exc:
                raise PlaneFitError(f"SVD failed to converge: {exc}") from exc

            spread_scale = max(float(singular_values[0]), 1e-12)
            if float(singular_values[1]) / spread_scale < 1e-6:
                raise PlaneFitError(
                    "Could not fit a plane: the input points are collinear or "
                    "coincident and do not uniquely define a plane orientation."
                )

            normal = _safe_normalize(vh[2], "plane normal from SVD")

            offsets = centered
            distances = offsets @ normal
            rms_error = float(np.sqrt(np.mean(distances ** 2)))

        # -------- CANONICALIZE NORMAL DIRECTION (deterministic sign) --------
        if normal[2] < 0.0:
            normal = -normal

        # -------- DETERMINISTIC, WORLD-ANCHORED IN-PLANE X AXIS --------
        # We deliberately do NOT derive x_axis from the point data at all (not from
        # P2-P1, not from the SVD's first singular vector / vh[0]). Both of those
        # are arbitrary whenever the point layout has no unique dominant in-plane
        # direction -- e.g. a square/diamond of plane points has EQUAL singular
        # values in-plane, so SVD's tie-break for vh[0] is mathematically undefined
        # and can legitimately return any in-plane direction (not just a sign flip)
        # depending on the NumPy/LAPACK build. That is the actual root cause of the
        # "random axis" symptom: the very same plane points can silently produce a
        # local frame rotated by some arbitrary angle from one run/machine to the
        # next, flipping and even swapping the sign of local X/Y for every point
        # measured relative to it.
        #
        # Instead we fix the in-plane X axis to be the projection of the WORLD X
        # axis onto the fitted plane (falling back to world Y when the plane is
        # edge-on to world X, i.e. its normal is nearly parallel to world X, which
        # would make that projection near-zero/unstable). This makes local X/Y
        # depend only on the plane's orientation (its normal) -- never on point
        # order or on SVD's internal tie-breaking -- and keeps local X/Y signs
        # anchored to the global/world X/Y directions the operator already reasons
        # in, exactly like local Z is already anchored to the world-canonicalized
        # normal above.
        world_x = np.array([1.0, 0.0, 0.0])
        world_y = np.array([0.0, 1.0, 0.0])
        # reference_axis = world_x if abs(float(np.dot(normal, world_x))) <= abs(float(np.dot(normal, world_y))) else world_y
      
        EDGE_ON_THRESHOLD = 0.9999
        if abs(float(np.dot(normal, world_x))) < EDGE_ON_THRESHOLD:
            reference_axis = world_x
        else:
            reference_axis = world_y

        in_plane_x = reference_axis - float(np.dot(reference_axis, normal)) * normal
        x_axis = _safe_normalize(in_plane_x, "plane local X axis (world-anchored projection)")

        y_axis = _safe_normalize(np.cross(normal, x_axis), "plane local Y axis")
        x_axis = _safe_normalize(np.cross(y_axis, normal), "plane local X axis")
        rotation_matrix = np.column_stack((x_axis, y_axis, normal))

        assert abs(float(np.linalg.det(rotation_matrix)) - 1.0) < 1e-6

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
