"""
plc/data_converter.py
======================
Register <-> value packing/unpacking for INT16/UINT16/INT32/FLOAT32.
Ported from the standalone PLC prototype (plc.zip: data_converter.py),
unchanged behavior.

WARNING -- known inconsistency, not yet resolved:
    DataConverter.decode("FLOAT32") treats registers[0] as the HIGH word
    and registers[1] as the LOW word.
    PLCConnection.read_register("FLOAT32") in plc_connection.py does the
    opposite: it swaps the two registers (r2, r1) before unpacking.
    These two are not currently called together anywhere, but if you ever
    use both against the same PLC you WILL get different float values for
    the same registers. Verify against real hardware which word order your
    PLC actually uses, then make these two agree before relying on both.
"""

from __future__ import annotations

import struct


class DataConverter:
    """Encode a Python value into register words / decode register words
    into a Python value, for INT16, UINT16, INT32, and FLOAT32."""

    def encode(self, value, datatype: str):
        if datatype == "INT16":
            return [int(value)]

        elif datatype == "UINT16":
            return [int(value)]

        elif datatype == "INT32":
            packed = struct.pack(">i", int(value))
            return list(struct.unpack(">HH", packed))

        elif datatype == "FLOAT32":
            packed = struct.pack(">f", float(value))
            return list(struct.unpack(">HH", packed))

        else:
            raise ValueError(f"Unsupported datatype: {datatype}")

    def decode(self, registers, datatype: str):
        if datatype == "INT16":
            return registers[0]

        elif datatype == "UINT16":
            return registers[0]

        elif datatype == "INT32":
            packed = struct.pack(">HH", registers[0], registers[1])
            return struct.unpack(">i", packed)[0]

        elif datatype == "FLOAT32":
            packed = struct.pack(">HH", registers[0], registers[1])
            return round(struct.unpack(">f", packed)[0], 3)

        else:
            raise ValueError(f"Unsupported datatype: {datatype}")