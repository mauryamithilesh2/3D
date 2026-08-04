"""
plc/read_write.py
==================
Thin, friendlier read/write API in front of PLCConnection. Ported from the
standalone PLC prototype (plc.zip: read_write.py) -- unchanged behavior,
just typed and the commented-out dead code removed. This is the class
Step 5 will call from MainWindow.add_plc_point() instead of reading the
hardcoded PLC_POINTS dict.
"""

from __future__ import annotations

from plc.logger import PLCLogger
from plc.plc_connection import PLCConnection


class PLCOperations:
    """Convenience wrapper: read(address, data_type) / write(address, value, data_type)."""

    def __init__(self, plc: PLCConnection, logger: PLCLogger) -> None:
        self.plc = plc
        self.logger = logger

    def read(self, address, data_type: str):
        """Read a single value from the PLC. If the shared connection is in
        simulation mode (i.e. the last real connect attempt failed), this
        transparently serves a value from SIMULATED_REGISTERS instead --
        callers (like MainWindow.add_plc_point) don't need to know whether
        they're getting real or simulated data. Returns None on any failure,
        including "no simulated value exists for this address"."""
        if self.plc.config.simulation_mode:
            from plc.point_registers import SIMULATED_REGISTERS
            return SIMULATED_REGISTERS.get(int(address))
        return self.plc.read_register(address, data_type)

    def write(self, address, value, data_type: str) -> bool:
        """Write a single value to the PLC. Returns True on success."""
        return self.plc.write_register(address, value, data_type)