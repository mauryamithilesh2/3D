"""
geometry.py
===========
Reusable, UI-free geometry factory functions for the 3-D widget demo.

All public functions are pure — they accept numeric parameters and return
NumPy arrays or pyqtgraph MeshData objects.  No Qt or OpenGL objects are
created here; callers are responsible for constructing scene items.

Compatible with Python 3.11+, NumPy ≥ 1.24, pyqtgraph ≥ 0.13.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np
import numpy.typing as npt
from pyqtgraph.opengl import MeshData  # type: ignore[import]


# ---------------------------------------------------------------------------
# Public data containers
# ---------------------------------------------------------------------------

class AxisLineData(NamedTuple):
    """Holds the vertex positions and RGBA colour for one axis line."""

    pos: npt.NDArray[np.float32]
    """Shape (2, 3) — start and end vertices."""

    color: tuple[float, float, float, float]
    """RGBA colour in the range [0, 1]."""


@dataclass(frozen=True)
class OriginPointData:
    """Holds the position and visual properties for the origin marker."""

    pos: npt.NDArray[np.float32]
    """Shape (1, 3) — single 3-D position."""

    color: tuple[float, float, float, float] = field(
        default=(1.0, 1.0, 1.0, 1.0)
    )
    """RGBA colour — white by default."""

    size: float = 8.0
    """Screen-space diameter in pixels."""


# ---------------------------------------------------------------------------
# BGR colour utility
# ---------------------------------------------------------------------------

def bgr_to_rgba(
    b: int,
    g: int,
    r: int,
    a: int = 255,
) -> tuple[float, float, float, float]:
    """Convert a BGR integer colour to a normalised RGBA float tuple.

    Uses the BGR channel ordering used by OpenCV (Blue-Green-Red), converting
    each channel from the range ``[0, 255]`` to ``[0.0, 1.0]`` and
    reordering to ``(R, G, B, A)`` as required by pyqtgraph GL items.

    Parameters
    ----------
    b:
        Blue channel, 0-255.
    g:
        Green channel, 0-255.
    r:
        Red channel, 0-255.
    a:
        Alpha channel, 0-255 (default 255 = fully opaque).

    Returns
    -------
    tuple[float, float, float, float]
        Normalised ``(R, G, B, A)`` tuple ready for pyqtgraph GL.

    Examples
    --------
    >>> bgr_to_rgba(0, 0, 255)         # BGR red  → (1.0, 0.0, 0.0, 1.0)
    (1.0, 0.0, 0.0, 1.0)
    >>> bgr_to_rgba(255, 0, 0)         # BGR blue → (0.0, 0.0, 1.0, 1.0)
    (0.0, 0.0, 1.0, 1.0)
    >>> bgr_to_rgba(0, 255, 0)         # BGR green→ (0.0, 1.0, 0.0, 1.0)
    (0.0, 1.0, 0.0, 1.0)
    """
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


# ---------------------------------------------------------------------------
# Plane geometry
# ---------------------------------------------------------------------------

def create_plane_mesh(
    p1: tuple[float, float, float] = (-50.0, -50.0, 0.0),
    p2: tuple[float, float, float] = (50.0, -50.0, 0.0),
    p3: tuple[float, float, float] = (50.0, 50.0, 0.0),
    p4: tuple[float, float, float] = (-50.0, 50.0, 0.0),
) -> MeshData:
    """Return a ``MeshData`` object for a plane quad defined by 4 corner points.

    Parameters
    ----------
    p1, p2, p3, p4:
        3-D coordinates of the 4 plane vertices.

    Returns
    -------
    MeshData
        Ready to pass to ``GLMeshItem(meshdata=...)``.
    """
    vertexes: npt.NDArray[np.float32] = np.array(
        [p1, p2, p3, p4],
        dtype=np.float32,
    )

    faces: npt.NDArray[np.int32] = np.array(
        [
            [0, 1, 2],
            [0, 2, 3],
        ],
        dtype=np.int32,
    )

    return MeshData(vertexes=vertexes, faces=faces)


def calculate_point_to_plane_perpendicular(
    point: tuple[float, float, float],
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    p3: tuple[float, float, float],
) -> tuple[float, npt.NDArray[np.float32]]:
    """Calculate the perpendicular distance and perpendicular foot from a point to a plane.

    The plane is defined by three non-collinear 3-D points ``p1, p2, p3``.

    Parameters
    ----------
    point:
        Coordinates of the query point ``(x, y, z)``.
    p1, p2, p3:
        Three corner vertices defining the plane.

    Returns
    -------
    tuple[float, ndarray]
        ``(distance, foot_coords)`` where ``foot_coords`` is a ``(3,)`` float32 array
        representing the perpendicular foot on the plane.
    """
    pt = np.array(point, dtype=np.float64)
    v1 = np.array(p2, dtype=np.float64) - np.array(p1, dtype=np.float64)
    v2 = np.array(p3, dtype=np.float64) - np.array(p1, dtype=np.float64)

    normal = np.cross(v1, v2)
    norm_len = float(np.linalg.norm(normal))

    if norm_len < 1e-8:
        # Fallback if vertices are collinear: default vertical drop
        foot = np.array([point[0], point[1], p1[2]], dtype=np.float32)
        dist = abs(point[2] - p1[2])
        return dist, foot

    unit_normal = normal / norm_len
    p1_vec = np.array(p1, dtype=np.float64)

    # Signed distance = (Point - P1) . N
    proj = float(np.dot(pt - p1_vec, unit_normal))
    dist = abs(proj)
    foot = (pt - proj * unit_normal).astype(np.float32)

    return dist, foot


def compute_flat_plane_p4(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    p3: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Compute P4 = P1 + P3 - P2 to guarantee a perfectly flat 3D plane quad.

    Parameters
    ----------
    p1, p2, p3:
        Three corner points of the plane quad.

    Returns
    -------
    tuple[float, float, float]
        Coordinates of P4 ensuring the 4 points lie on the exact same flat plane.
    """
    return (
        float(p1[0] + p3[0] - p2[0]),
        float(p1[1] + p3[1] - p2[1]),
        float(p1[2] + p3[2] - p2[2]),
    )


def create_plane_face_colors(
    rgba: tuple[float, float, float, float] = (0.15, 0.45, 1.0, 0.35),
    num_faces: int = 2,
) -> npt.NDArray[np.float32]:
    """Return a per-face RGBA colour array for the plane mesh.

    Parameters
    ----------
    rgba:
        Colour applied to every face.  Defaults to semi-transparent blue.
    num_faces:
        Number of faces in the mesh (must match ``create_plane_mesh``).

    Returns
    -------
    ndarray
        Shape ``(num_faces, 4)``, dtype ``float32``.
    """
    colors: npt.NDArray[np.float32] = np.tile(
        np.array(rgba, dtype=np.float32), (num_faces, 1)
    )
    return colors


# ---------------------------------------------------------------------------
# Axis lines
# ---------------------------------------------------------------------------

def create_axis_lines(length: float = 50.0) -> list[AxisLineData]:
    """Return position and colour data for the three Cartesian axis lines.

    Each axis is represented as a two-point line segment starting at the
    origin and extending to ``length`` along the positive direction.

    Parameters
    ----------
    length:
        Half-extent of each axis arrow (default 50 world units).

    Returns
    -------
    list[AxisLineData]
        Three entries in X → Y → Z order.
    """
    origin: npt.NDArray[np.float32] = np.zeros(3, dtype=np.float32)

    axes: list[AxisLineData] = [
        AxisLineData(
            pos=np.array([origin, [length, 0.0, 0.0]], dtype=np.float32),
            color=bgr_to_rgba(0, 0, 255),    # BGR(0,0,255) → Red   — X axis
        ),
        AxisLineData(
            pos=np.array([origin, [0.0, length, 0.0]], dtype=np.float32),
            color=bgr_to_rgba(0, 255, 0),    # BGR(0,255,0) → Green — Y axis
        ),
        AxisLineData(
            pos=np.array([origin, [0.0, 0.0, length]], dtype=np.float32),
            color=bgr_to_rgba(255, 0, 0),    # BGR(255,0,0) → Blue  — Z axis
        ),
    ]
    return axes


# ---------------------------------------------------------------------------
# Origin marker
# ---------------------------------------------------------------------------

def create_origin_point(
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    size: float = 8.0,
) -> OriginPointData:
    """Return data describing a small marker at the world origin.

    Parameters
    ----------
    color:
        RGBA colour (default white, fully opaque).
    size:
        Screen-space point size in pixels (default 8).

    Returns
    -------
    OriginPointData
        Immutable container with ``pos``, ``color``, and ``size``.
    """
    pos: npt.NDArray[np.float32] = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
    return OriginPointData(pos=pos, color=color, size=size)


# ---------------------------------------------------------------------------
# Convenience: scatter-ready point position array
# ---------------------------------------------------------------------------

def make_point_pos(x: float, y: float, z: float) -> npt.NDArray[np.float32]:
    """Return a ``(1, 3)`` float32 array suitable for ``GLScatterPlotItem.setData``.

    Parameters
    ----------
    x, y, z:
        World-space coordinates of the point.

    Returns
    -------
    ndarray
        Shape ``(1, 3)``, dtype ``float32``.
    """
    return np.array([[x, y, z]], dtype=np.float32)
