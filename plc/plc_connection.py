"""
plc/plc_connection.py
======================
Modbus TCP connection wrapper: connect/disconnect, auto-reconnect on a
dropped connection, and typed register read/write. Ported from the
standalone PLC prototype (plc.zip: plc_connection.py) with the debug
print() calls removed (PLCLogger.log(...) is used for everything instead)
and type hints added. Behavior is otherwise unchanged from the prototype.
"""

from __future__ import annotations

import struct
from typing import Optional

from pymodbus.client import ModbusTcpClient

from plc.config import PLCConfig
from plc.logger import PLCLogger


class PLCConnection:
    """Owns the ModbusTcpClient and all read/write/reconnect logic.

    A single shared instance of this (plus its PLCConfig/PLCLogger) is
    meant to be created once for the whole app and reused by every module
    window, so there's only ever one real connection to the PLC.
    """

    def __init__(self, logger: PLCLogger, config: PLCConfig) -> None:
        self.client: Optional[ModbusTcpClient] = None
        self.logger = logger
        self.config = config

    def connect(self, ip: str, port: str) -> bool:
        """Attempt a fresh connection to ip:port. On failure, falls back to
        simulation mode (matching the original prototype's behavior) so the
        rest of the UI can keep running with dummy/last-known data."""
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

        try:
            self.client = ModbusTcpClient(ip, port=int(port), timeout=3)
            self.config.update_connection(ip, port, "Modbus TCP")
            if self.client.connect():
                self.config.set_connected(True)
                self.config.enable_simulation(False)
                self.logger.log(f"Connected to PLC {ip}:{port}")
                return True
            else:
                raise Exception("Connection Failed")

        except Exception as e:
            self.logger.log(f"Connection error: {str(e)}", "ERROR")
            self.config.set_connected(False)
            self.config.enable_simulation(True)
            self.logger.log("Simulation mode ENABLED")
            return False

    def disconnect(self) -> None:
        """Close the client cleanly and mark config as disconnected."""
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
        self.config.set_connected(False)
        self.logger.log("Disconnected from PLC")

    def _reconnect(self) -> bool:
        if not self.config.ip or not self.config.port:
            return False
        try:
            if self.client is not None:
                self.client.close()
            self.client = ModbusTcpClient(self.config.ip, port=int(self.config.port), timeout=3)
            if self.client.connect():
                self.logger.log("Reconnected to PLC after dropped connection")
                return True
        except Exception as e:
            self.logger.log(f"Reconnect failed: {e}", "ERROR")
        return False

    @staticmethod
    def _is_connection_drop(exc: Exception) -> bool:
        msg = str(exc).lower()
        markers = (
            "10053", "10054", "10061", "aborted",
            "forcibly closed", "unexpectedly closed",
            "connection", "broken pipe", "reset by peer",
        )
        return any(m in msg for m in markers)

    def read_register(self, address, data_type: str = "INT16", _retry: bool = True):
        """Read one value from a holding register. Returns None on any
        failure (not connected, PLC error response, unsupported type)."""
        try:
            if not self.client:
                self.logger.log("PLC not connected", "ERROR")
                return None

            address = int(address)
            value = None

            if data_type == "INT16":
                result = self.client.read_holding_registers(address=address, count=1, device_id=1)
                if result.isError():
                    return None
                value = result.registers[0]

            elif data_type == "FLOAT32":
                result = self.client.read_holding_registers(address=address, count=2, device_id=1)
                if result.isError() or len(result.registers) < 2:
                    return None
                r1, r2 = result.registers
                raw = struct.pack(">HH", r2, r1)
                value = round(struct.unpack(">f", raw)[0], 2)

            elif data_type == "DOUBLE":
                result = self.client.read_holding_registers(address=address, count=4, device_id=1)
                if result.isError() or len(result.registers) < 4:
                    return None
                r1, r2, r3, r4 = result.registers
                raw = struct.pack(">HHHH", r4, r3, r2, r1)
                value = round(struct.unpack(">d", raw)[0], 4)

            else:
                self.logger.log(f"Unsupported datatype: {data_type}", "ERROR")
                return None

            return value

        except Exception as e:
            self.logger.log(f"Read Error: {e}", "ERROR")
            if _retry and self._is_connection_drop(e):
                if self._reconnect():
                    return self.read_register(address, data_type, _retry=False)
            return None

    def write_register(self, address, value, data_type: str = "INT16") -> bool:
        """Write one value to a holding register. Returns True on success."""
        try:
            address = int(address)

            if data_type == "INT16":
                result = self.client.write_register(address=address, value=int(value), device_id=1)

            elif data_type == "FLOAT32":
                raw = struct.pack(">f", float(value))
                high, low = struct.unpack(">HH", raw)
                result = self.client.write_registers(address=address, values=[low, high], device_id=1)

            elif data_type == "DOUBLE":
                raw = struct.pack(">d", float(value))
                r1, r2, r3, r4 = struct.unpack(">HHHH", raw)
                result = self.client.write_registers(address=address, values=[r4, r3, r2, r1], device_id=1)

            else:
                self.logger.log(f"Unsupported datatype: {data_type}", "ERROR")
                return False

            if result.isError():
                self.logger.log(f"PLC write failed at {address}", "ERROR")
                return False

            self.logger.log(f"WRITE {data_type} Register {address} = {value}")
            return True

        except Exception as e:
            self.logger.log(f"Write Error: {e}", "ERROR")
            return False