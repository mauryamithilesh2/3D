"""core/tilt.py — rigid tilt helpers that preserve true pairwise distance."""
from __future__ import annotations
import numpy as np


def pivot_tilt(pivot: np.ndarray, moving: np.ndarray, target_z_offset: float) -> np.ndarray:
    """Swing `moving` around `pivot` so its height reaches
    `pivot[2] + target_z_offset`, while its TRUE 3-D distance to `pivot`
    stays EXACTLY the original distance (like a rigid rod / fixed
    diameter -- not a telescoping one that stretches when you lift it).

    This preserves the full 3-D arm length ``hypot(dx, dy, dz)``, not just
    the X-Z planar distance, and swings along whatever horizontal
    direction (dx, dy) the point actually started in -- it does not
    assume the offset lies along world X.
    """
    offset = moving - pivot
    horiz_len = float(np.hypot(offset[0], offset[1]))
    arm = float(np.hypot(horiz_len, offset[2]))
    if arm < 1e-9:
        raise ValueError("Moving point coincides with pivot; no direction to tilt along.")

    # Clamp to what's physically reachable: the point can never get
    # farther from the pivot (vertically) than the arm length itself.
    target_z_offset = max(-arm, min(arm, target_z_offset))
    new_horiz_len = float(np.sqrt(max(arm * arm - target_z_offset * target_z_offset, 0.0)))

    if horiz_len < 1e-9:
        # Point started directly above/below the pivot with no horizontal
        # direction to preserve -- swing along world X arbitrarily.
        ux, uy = 1.0, 0.0
    else:
        ux, uy = offset[0] / horiz_len, offset[1] / horiz_len

    new_x = pivot[0] + ux * new_horiz_len
    new_y = pivot[1] + uy * new_horiz_len
    new_z = pivot[2] + target_z_offset
    return np.array([new_x, new_y, new_z], dtype=np.float64)


def axis_tilt(points: np.ndarray, axis_point: np.ndarray, axis_dir: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate all `points` rigidly about the line (axis_point, axis_dir) by angle_deg.
    Preserves ALL pairwise distances exactly (standard Rodrigues rotation)."""
    axis = axis_dir / np.linalg.norm(axis_dir)
    theta = np.radians(angle_deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)
    return (points - axis_point) @ R.T + axis_point

def resolve_quad_topology(points: dict) -> dict:
    """Given exactly 4 {label: (x,y,z)} points forming a quad, figure out
    the diagonal (opposite-corner) pairing purely from XY geometry: the
    diagonal pairing is whichever split into two pairs has the largest
    total distance (diagonals are always longer than sides in a convex quad).
    Returns {label: {"opposite": label, "adjacent": (label, label)}}."""
    labels = list(points.keys())
    if len(labels) != 4:
        return {}
    xy = {l: points[l][:2] for l in labels}
    def dist(a, b):
        return float(np.linalg.norm(xy[a] - xy[b]))
    a, b, c, d = labels
    pairings = [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]
    best = max(pairings, key=lambda pr: dist(*pr[0]) + dist(*pr[1]))
    (p1, p2), (p3, p4) = best
    return {
        p1: {"opposite": p2, "adjacent": (p3, p4)},
        p2: {"opposite": p1, "adjacent": (p3, p4)},
        p3: {"opposite": p4, "adjacent": (p1, p2)},
        p4: {"opposite": p3, "adjacent": (p1, p2)},
    }


def virtual_leveled_points(points: dict, edited_labels) -> dict:
    """Return a NEW dict (never mutates `points`) where, IF exactly one
    corner of a 4-point quad has been manually edited by the user, its two
    adjacent corners get a virtual, computation-only Z so the whole quad is
    coplanar. The opposite corner and all raw stored values are left
    untouched.

    ``edited_labels`` is the FULL set of plane-point labels the user has
    manually edited (see ``PointManager.edited_plane_labels``) -- not just
    the most recent one. This distinction matters: the single-corner
    "auto-level" model only makes sense when exactly one corner has
    actually deviated from the reference plane. As soon as a SECOND corner
    is genuinely, independently edited (e.g. the user raises two adjacent
    corners), the model has no way to know which of the two real edits
    should "win" the virtual override -- silently overwriting one of them
    produced the reported "plane distorted / tilts the wrong way" bug. In
    that case we simply return the raw, untouched points, so the plane fit
    downstream reflects the real, actual position of every edited corner.
    """
    leveled = {k: v.copy() for k, v in points.items()}
    if not edited_labels:
        return leveled

    topology = resolve_quad_topology(points)
    if not topology:
        return leveled

    quad_labels = set(topology.keys())
    edited_in_quad = quad_labels & set(edited_labels)
    if len(edited_in_quad) != 1:
        # Zero edited corners (nothing to level yet), or 2+ genuinely
        # edited corners (model is no longer well-defined) -- use raw data.
        return leveled

    (edited_label,) = edited_in_quad
    info = topology[edited_label]
    z_edited = float(points[edited_label][2])
    z_opposite = float(points[info["opposite"]][2])
    adjacent_z = (z_edited + z_opposite) / 2.0
    for adj_label in info["adjacent"]:
        ax, ay, _ = points[adj_label]
        leveled[adj_label] = np.array([ax, ay, adjacent_z], dtype=np.float64)
    return leveled