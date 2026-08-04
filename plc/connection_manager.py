"""
plc/connection_manager.py
==========================
Single shared PLC connection for the whole application.

Every part of the app (the landing page Connect button, and later every
module window's graph feed) imports THESE module-level objects instead of
constructing its own PLCConfig/PLCLogger/PLCConnection/PLCOperations.
Because Python only ever executes a module's top-level code once per
process, `config`, `logger`, `connection`, and `operations` below are true
singletons for the lifetime of the app.

Usage elsewhere in the app:

    from plc.connection_manager import connect, disconnect, operations, config

    ok = connect("192.168.1.10", "502")
    if ok:
        value = operations.read(40001, "INT16")
"""

from __future__ import annotations

from plc.config import PLCConfig
from plc.logger import PLCLogger
from plc.plc_connection import PLCConnection
from plc.read_write import PLCOperations

config = PLCConfig()
logger = PLCLogger()
connection = PLCConnection(logger, config)
operations = PLCOperations(connection, logger)


def connect(ip: str, port: str) -> bool:
    """Connect the shared PLCConnection to ip:port. Returns True on success,
    False if it fell back to simulation mode (see PLCConnection.connect)."""
    return connection.connect(ip, port)


def disconnect() -> None:
    """Disconnect the shared PLCConnection."""
    connection.disconnect()


def is_connected() -> bool:
    """Whether the shared connection is currently connected (not simulating)."""
    return config.connected