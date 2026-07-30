"""
graphics/animation.py
======================
A tiny, generic animation controller that smooths transitions of already
-computed OpenGL item data (positions, mesh vertices) between an old and a
new state.

Design
------
Nothing here computes any new geometry. Every value it animates between was
already produced by the existing renderer modules (plane fit, coordinate
system, measurements) -- this controller's only job is to visually
interpolate the *display* of those numbers over ~200-300 ms so that plane
rotation, local axis movement, normal vector reorientation, point movement,
and reference switching read as smooth transitions instead of instant jumps,
exactly like a CMM/robot visualization tool. GL items are never recreated;
every tick calls the same ``setData`` / ``setMeshData`` the static renderers
already use.

Compatible with PyQt5, NumPy only.
"""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import QElapsedTimer, QObject, QTimer

from graphics.gl_utils import _ease_out_cubic


class SceneAnimator(QObject):
    """Drives one shared timer that calls back with an eased ``t in [0, 1]``.

    Parameters
    ----------
    duration_ms:
        Total animation length in milliseconds.
    fps:
        Target callback frequency.
    parent:
        Optional owning QObject (keeps the internal QTimer alive/cleaned up).
    """

    def __init__(self, duration_ms: int = 260, fps: int = 60, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._duration_ms = max(1, int(duration_ms))
        self._timer = QTimer(self)
        self._timer.setInterval(max(1, int(1000 / fps)))
        self._timer.timeout.connect(self._tick)
        self._clock = QElapsedTimer()
        self._apply_fn: Callable[[float], None] | None = None
        self._on_done: Callable[[], None] | None = None

    def start(
        self,
        apply_fn: Callable[[float], None],
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """(Re)start the animation, replacing any transition already in flight.

        ``apply_fn(eased_t)`` is called once immediately at ``t=0`` and then
        on every tick until ``t=1``, after which ``on_done`` (if given) fires
        once and the timer stops.
        """
        self._timer.stop()
        self._apply_fn = apply_fn
        self._on_done = on_done
        self._clock.start()
        self._timer.start()
        self._tick()

    def stop_immediately(self) -> None:
        """Cancel any in-flight animation without calling ``on_done``."""
        self._timer.stop()
        self._apply_fn = None
        self._on_done = None

    def _tick(self) -> None:
        if self._apply_fn is None:
            self._timer.stop()
            return
        elapsed = self._clock.elapsed()
        t = min(1.0, elapsed / self._duration_ms)
        self._apply_fn(_ease_out_cubic(t))
        if t >= 1.0:
            self._timer.stop()
            done = self._on_done
            self._apply_fn = None
            self._on_done = None
            if done is not None:
                done()
