"""
plc/point_registers.py
=======================
Real Modbus register addresses for each measurement point's X/Y/Z, plus a
SIMULATED_REGISTERS table used only when no real PLC is connected (so the
app keeps working for development/demo without hardware, same role that
the hardcoded PLC_POINTS dict in plc_registers.py used to serve alone).

ASSUMPTION -- please confirm against your real PLC program:
    Each axis (X, Y, Z) is read as ONE INT16 holding register, and the raw
    integer is a fixed-point value scaled by SCALE_FACTOR, i.e.:
        millimeters = raw_register_value / SCALE_FACTOR
    This is inferred from your sample data (e.g. raw X = 12540 for a point
    that lines up with ~125.40mm in the old hardcoded points). If your PLC
    program actually sends plain mm as FLOAT32 registers instead, or uses a
    different scale, change DATA_TYPE / SCALE_FACTOR below -- every read in
    the app goes through these two constants, nothing else needs to change.
"""

from __future__ import annotations

DATA_TYPE = "INT16"
SCALE_FACTOR = 100  # millimeters = raw register value / SCALE_FACTOR

# Reference (plane) points -- read in this order by add_plc_point().
# Each value is (address_x, address_y, address_z).
REFERENCE_POINT_REGISTERS: dict[str, tuple[int, int, int]] = {
    "Reference Point 1": (100, 101, 102),
    "Reference Point 2": (103, 104, 105),
    "Reference Point 3": (106, 107, 108),
}

# Inspection points -- read in this order by add_plc_inspection_point().
INSPECTION_POINT_REGISTERS: dict[str, tuple[int, int, int]] = {
    "Inspection Point 1": (200, 201, 202),
    "Inspection Point 2": (203, 204, 205),
}

# Used ONLY when plc.connection_manager is in simulation mode (no real PLC
# reachable) -- ported directly from the register map you provided.
# NOTE: Inspection Point 2 (203-205) has no simulated values yet -- add
# them here if you want simulation mode to cover it too.
SIMULATED_REGISTERS: dict[int, int] = {
    # Reference Point 1
    100: 1050,
    101: 1550,
    102: 0000,

    # Reference Point 2
    103: 1500,
    104: 0000,
    105: 500,

    # Reference Point 3
    106: 2000,
    107: 1050,
    108: 0000,

    109: 1200,
    110: 1550,
    111: 600,

    # Inspection Point 1
    200: 1000,
    201: 1000,
    202: 1000,

    203: 1000,
    204: 1500,
    205: 1500,

    # Hole 1 Center
    300: 1000,
    301: 500,
    302: 2050,

    # Hole 2 Center
    303: 1520,
    304: 510,
    305: 0000,
}

CIRCULARITY_HOLE_REGISTERS: dict[str, tuple[int, int, int]] = {
    "Hole 1 Center": (300, 301, 302),
    "Hole 2 Center": (303, 304, 305),
}