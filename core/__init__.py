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
