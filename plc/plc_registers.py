"""
plc_registers.py

Purpose
-------
Hardcoded PLC register data for UI and graph testing.

This file simulates PLC register values so the application can
be developed and tested without a real PLC.

Future:
Replace this file with the real PLC communication driver.
"""

# ----------------------------------------------------------------------
# Hardcoded PLC Points
# ----------------------------------------------------------------------

PLC_POINTS = {

    # Register 1
    1: (0.00, 0.00, 0.00),

    # Register 2
    2: (0.00, 10.00, 0.00),

    # Register 3
    3: (10.00, 0.00, 0.00),

    # Register 4
    4: (5.00, 15.00, 0.00),

    # Register 5
    5: (25.00, 15.00, 3.00),

    # Register 6
    6: (15.00, 10.00, 5.00),

    # Register 7
    7: (18.00, 25.00, 5.00),

    # # Register 8
    # 8: (260.70, 145.80, 60.90),

    # # Register 9
    # 9: (278.50, 160.20, 70.30),

    # # Register 10
    # 10: (300.00, 180.00, 80.00),
}

PLC_INSPECTION_POINTS = {
    1: (10.00, 10.00, 20.00),
    2: (15.00, 15.00, 15.50),
    3: (10.00, 15.00, 10.00),
}
# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------

def get_point(register: int):
    """
    Return X, Y, Z for a given register.

    Example:
        x, y, z = get_point(3)
    """
    return PLC_POINTS.get(register)


def register_exists(register: int) -> bool:
    """
    Check whether a register exists.
    """
    return register in PLC_POINTS


def total_registers() -> int:
    """
    Return total number of registers.
    """
    return len(PLC_POINTS)


def get_all_points():
    """
    Return all registered points.
    """
    return PLC_POINTS