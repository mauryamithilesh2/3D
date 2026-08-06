"""
core package
============
Pure math and domain logic layer for best fit plane computation,
local coordinate system building, coordinate transformations, and point measurements.
Zero dependencies on PyQt or OpenGL.
"""

from core.best_fit_plane import (
    BestFitPlane,
    BestFitPlaneResult,
    PlaneFitError,
)
from core.edge_axis import apply_edge_axis, apply_first_second_axis
from core.circularity import ConcentricityResult, measure_concentricity, perpendicular_basis
from core.perpendicularity import DATUM_AXIS_OPTIONS, PerpendicularityResult, measure_perpendicularity

from core.orientation import (
    OrientationResult,
    angle_between_normals_deg,
    measure_perpendicularity_planes,
    measure_parallelism_planes,
    ORIENTATION_CHECKS,
)

from core.coordinate_system import (
    CoordinateSystem,
    CoordinateSystemBuilder,
    CoordinateSystemError,
    OriginReference,
)
from core.transform import (
    CoordinateTransformer,
    LocalCoordinates,
)
from core.measurement import (
    MeasurementEngine,
    PointMeasurement,
    point_to_point_distance,
)

__all__ = [
    "BestFitPlane",
    "BestFitPlaneResult",
    "PlaneFitError",
    "apply_edge_axis",
    "apply_first_second_axis",
    "ConcentricityResult",
    "measure_concentricity",
    "perpendicular_basis",
    "DATUM_AXIS_OPTIONS",
    "PerpendicularityResult",
    "measure_perpendicularity",
    "OrientationResult",
    "angle_between_normals_deg",
    "measure_perpendicularity_planes",
    "measure_parallelism_planes",
    "ORIENTATION_CHECKS",
    "CoordinateSystem",
    "CoordinateSystemBuilder",
    "CoordinateSystemError",
    "OriginReference",
    "CoordinateTransformer",
    "LocalCoordinates",
    "MeasurementEngine",
    "PointMeasurement",
    "point_to_point_distance",
]
