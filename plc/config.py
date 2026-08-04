"""
plc/config.py
=============
Holds the current PLC connection settings and connection/simulation state.
Ported from the standalone PLC prototype (plc.zip: config.py), unchanged in
behavior -- just typed and documented for this codebase's conventions.
"""

from __future__ import annotations


class PLCConfig:
    """Tracks the current IP/port/protocol and connection/simulation flags.

    A single shared instance of this is passed into PLCConnection so the rest
    of the app (status pill, toolbar, etc.) can inspect connection state
    without reaching into PLCConnection's internals.
    """

    def __init__(self) -> None:
        self.ip: str | None = None
        self.port: str | None = None
        self.protocol: str | None = None
        self.connected: bool = False

        # Starts True on purpose: before any connect attempt (or after a
        # failed one), the app should read SIMULATED_REGISTERS so the graph
        # is testable with no PLC present. A SUCCESSFUL PLCConnection.connect()
        # is the only thing that flips this to False (see plc_connection.py).
        self.simulation_mode: bool = True
        self.refresh_interval: int = 10000

    def update_connection(self, ip: str, port: str, protocol: str) -> None:
        """Record the ip/port/protocol used for the most recent connect attempt."""
        self.ip = ip
        self.port = port
        self.protocol = protocol

    def set_connected(self, status: bool) -> None:
        """Mark whether the PLC is currently connected."""
        self.connected = status

    def enable_simulation(self, status: bool) -> None:
        """Toggle simulation mode (used as a fallback when a real PLC is unreachable)."""
        self.simulation_mode = status