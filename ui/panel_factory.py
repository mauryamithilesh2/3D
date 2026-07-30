"""
ui/panel_factory.py
===================
Convenience factory function for building and wiring a LeftPanel and ReferenceSelector to a PointManager.
"""

from __future__ import annotations

from config import DEFAULT_NEW_POINT
from ui.left_panel import LeftPanel
from ui.point_list_panel import PointListPanel
from ui.reference_selector import ReferenceSelector


def build_left_panel(point_manager) -> tuple[LeftPanel, ReferenceSelector]:
    """Construct a :class:`LeftPanel` fully wired to a live ``PointManager``.

    Parameters
    ----------
    point_manager:
        A :class:`~models.point_manager.PointManager` instance.

    Returns
    -------
    tuple[LeftPanel, ReferenceSelector]
        The assembled panel, plus the reference selector.
    """
    default_x, default_y, default_z = DEFAULT_NEW_POINT

    plane_panel = PointListPanel(
        title="Plane Points",
        get_points=lambda: list(
            zip(point_manager.plane_point_labels(), point_manager.plane_points_array())
        ),
        add_point=lambda: point_manager.add_plane_point(default_x, default_y, default_z),
        update_point=point_manager.update_plane_point,
        remove_point=point_manager.remove_plane_point,
        min_count=point_manager.MIN_PLANE_POINTS,
        changed_signal=point_manager.plane_points_changed,
    )

    inspection_panel = PointListPanel(
        title="Inspection Points",
        get_points=point_manager.inspection_points,
        add_point=lambda: point_manager.add_inspection_point(default_x, default_y, default_z),
        update_point=point_manager.update_inspection_point,
        remove_point=point_manager.remove_inspection_point,
        min_count=0,
        changed_signal=point_manager.inspection_points_changed,
    )

    reference_selector = ReferenceSelector(
        get_plane_labels=point_manager.plane_point_labels,
        changed_signal=point_manager.plane_points_changed,
    )

    left_panel = LeftPanel(plane_panel, inspection_panel, reference_selector)
    return left_panel, reference_selector
