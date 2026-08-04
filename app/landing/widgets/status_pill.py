"""
app/landing/widgets/status_pill.py
===================================
Reusable 3-state status pill for the landing page status bar.

Not tied to PLC code directly — it only knows how to render three visual
states (idle / ok / error). Later steps will call set_ok()/set_error()/set_idle()
from the PLC connection logic; this widget has no knowledge of PLC internals.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QWidget


class StatusPill(QLabel):
    """Small pill-shaped indicator with three states: idle, ok, error.

    - idle  -> yellow  -> shown before a connection attempt / while disconnected
    - ok    -> green   -> shown after a successful connection
    - error -> red     -> shown when a connection attempt fails or drops
    """

    _OBJECT_NAMES = {
        "idle": "StatusPillWarning",
        "ok": "StatusPillReady",
        "error": "StatusPillError",
    }

    _DEFAULT_TEXT = {
        "idle": "● WAITING FOR PLC CONNECTION",
        "ok": "● SYSTEM READY",
        "error": "● CONNECTION ERROR",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = "idle"
        self.set_idle()

    def set_idle(self, text: str | None = None) -> None:
        """Yellow state — not connected yet / connecting / disconnected."""
        self._apply_state("idle", text)

    def set_ok(self, text: str | None = None) -> None:
        """Green state — PLC connected successfully."""
        self._apply_state("ok", text)

    def set_error(self, text: str | None = None) -> None:
        """Red state — connection attempt failed or PLC reported an error."""
        self._apply_state("error", text)

    @property
    def state(self) -> str:
        """Current state key: 'idle' | 'ok' | 'error'."""
        return self._state

    def _apply_state(self, state: str, text: str | None) -> None:
        self._state = state
        self.setText(text if text is not None else self._DEFAULT_TEXT[state])
        self.setObjectName(self._OBJECT_NAMES[state])
        style = self.style()
        style.unpolish(self)
        style.polish(self)