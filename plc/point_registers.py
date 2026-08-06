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

# ---------------------------------------------------------------------------
# Perpendicularity module -- DELIBERATELY separate register addresses (400s
# / 500s) so it never reads the same PLC points as the Distance module,
# even though both currently share MainWindow's PLC-loading code. See
# MODULE_REFERENCE_POINT_REGISTERS / MODULE_INSPECTION_POINT_REGISTERS
# below, and app/main_window.py's _reference_point_registers() /
# _inspection_point_registers(), which pick the right table by self.module.
# ---------------------------------------------------------------------------
PERPENDICULARITY_REFERENCE_POINT_REGISTERS: dict[str, tuple[int, int, int]] = {
    "Reference Point 1": (400, 401, 402),
    "Reference Point 2": (403, 404, 405),
    "Reference Point 3": (406, 407, 408),
}

PERPENDICULARITY_INSPECTION_POINT_REGISTERS: dict[str, tuple[int, int, int]] = {
    # 3 points minimum -- "Inspection Points" here is a real, independently
    # best-fit Inspection PLANE, not single distance-checked points.
    "Inspection Point 1": (500, 501, 502),
    "Inspection Point 2": (503, 504, 505),
    "Inspection Point 3": (506, 507, 508),
}

# Per-module lookup, keyed by MainWindow.module. Any module id not listed
# here (e.g. "parallelism", which has no dedicated implementation yet)
# falls back to the Distance module's tables in app/main_window.py.
MODULE_REFERENCE_POINT_REGISTERS: dict[str, dict[str, tuple[int, int, int]]] = {
    "distance": REFERENCE_POINT_REGISTERS,
    "perpendicularity": PERPENDICULARITY_REFERENCE_POINT_REGISTERS,
}

MODULE_INSPECTION_POINT_REGISTERS: dict[str, dict[str, tuple[int, int, int]]] = {
    "distance": INSPECTION_POINT_REGISTERS,
    "perpendicularity": PERPENDICULARITY_INSPECTION_POINT_REGISTERS,
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
    105: 2000,

    # Reference Point 3
    106: 2000,
    107: 1050,
    108: 0000,

    109: 1200,
    110: 1550,
    111: 2000,

    # Inspection Point 1
    200: 1000,
    201: 1000,
    202: 1000,

    203: 1000,
    204: 1500,
    205: 1500,

    # Perpendicularity -- Reference Point 1 (80.00, 80.00, 0.00)
    400: 3000,
    401: 1000,
    402: 0000,

    # Perpendicularity -- Reference Point 2 (120.00, 80.00, 1.50) -- slight
    # tilt so simulation mode demonstrates a small, non-zero perpendicularity
    # deviation instead of a trivially perfect 0.00 degrees every time.
    403: 1200,
    404: 2000,
    405: 1500,

    # Perpendicularity -- Reference Point 3 (80.00, 120.00, 0.80)
    406: 2000,
    407: 1200,
    408: 1280,

    # Perpendicularity -- Inspection Point 1 (100.00, 100.00, 5.00)
    500: 1000,
    501: 1000,
    502: 1500,

    # Perpendicularity -- Inspection Point 2 (60.00, 140.00, 3.00)
# Perpendicularity -- Inspection Point 2 (60.00, 140.00, 3.00)
    503: 1000,
    504: 1400,
    505: 1300,

    # Perpendicularity -- Inspection Point 3 (60.00, 140.00, 43.00) -- same
    # X/Y as Point 2, much larger Z, so the 3 points fit a plane tilted
    # steeply away from the near-horizontal Reference Plane -- gives a
    # clear, non-trivial Perpendicularity/Parallelism deviation in
    # simulation mode instead of a degenerate plane.
    506: 1600,
    507: 1400,
    508: 2300,


    # Hole 1 Center
    300: 1000,
    301: 2000,
    302: 2050,

    # Hole 2 Center
    303: 1520,
    304: 5100,
    305: 0000,
}

CIRCULARITY_HOLE_REGISTERS: dict[str, tuple[int, int, int]] = {
    "Hole 1 Center": (300, 301, 302),
    "Hole 2 Center": (303, 304, 305),
}