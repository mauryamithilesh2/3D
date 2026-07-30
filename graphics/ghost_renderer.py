"""
graphics/ghost_renderer.py
==========================
Optional "ghost" / history mode: keeps a short rolling history of previous
fitted-plane vertex snapshots and renders them as very faint, translucent
overlays behind the current plane, so an operator can see how the plane has
drifted across recent edits.

Purely a display feature -- it captures whatever vertex array the live
plane mesh item already held right before it gets overwritten with the new
fit, so it introduces no geometry of its own and never touches the best fit
plane math.
"""

from __future__ import annotations

import numpy as np

from config import GHOST_HISTORY_DEPTH


def _capture_current_plane_vertices(widget) -> np.ndarray | None:
    """Return the plane mesh's currently-displayed vertices, or ``None``.

    Called right before the live plane mesh is overwritten with a freshly
    fitted shape, so the about-to-be-replaced vertices can be preserved as
    a ghost snapshot.
    """
    if not widget._plane_mesh_item.visible():
        return None
    meshdata = widget._plane_mesh_item.opts.get("meshdata")
    if meshdata is None:
        return None
    vertices = meshdata.vertexes()
    if vertices is None or len(vertices) == 0:
        return None
    return np.array(vertices, dtype=np.float64, copy=True)


def _push_ghost_history(widget, vertices: np.ndarray | None) -> None:
    """Push a captured snapshot onto the rolling ghost history, if it differs
    meaningfully from the last one already stored (avoids piling up
    duplicate ghosts while the plane is not actually changing)."""
    if vertices is None:
        return
    history: list[np.ndarray] = widget._ghost_history
    if history and vertices.shape == history[-1].shape:
        if np.allclose(vertices, history[-1], atol=1e-6):
            return
    history.append(vertices)
    if len(history) > GHOST_HISTORY_DEPTH:
        del history[: len(history) - GHOST_HISTORY_DEPTH]


def _render_ghost_history(widget) -> None:
    """Push the current history onto the fixed pool of ghost mesh items."""
    import pyqtgraph.opengl as gl

    items = widget._ghost_mesh_items
    if not widget._ghost_mode_enabled:
        for item in items:
            item.setVisible(False)
        return

    history = widget._ghost_history
    # Most recent first, skip the very last entry (that is effectively the
    # live plane that is already drawn by the main plane mesh item).
    snapshots = list(reversed(history[:-1])) if len(history) > 1 else []

    for i, item in enumerate(items):
        if i < len(snapshots):
            vertices = snapshots[i]
            faces = np.array([[0, 1, 2], [0, 2, 3]]) if len(vertices) == 4 else np.array(
                [[0, j + 1, j + 2] for j in range(len(vertices) - 2)]
            )
            item.setMeshData(meshdata=gl.MeshData(vertexes=vertices, faces=faces))
            item.setVisible(True)
        else:
            item.setVisible(False)
