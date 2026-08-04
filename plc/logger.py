"""
plc/logger.py
=============
Timestamped file logger for PLC connection/read/write events. Ported from
the standalone PLC prototype (plc.zip: logger.py). Only change from the
original: the log file now lives under plc/logs/ instead of the project
root, so it doesn't clutter the repo, and the folder is created on demand.
"""

from __future__ import annotations

import os
import time
from typing import Callable, Optional

_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "plc.log")


class PLCLogger:
    """Writes timestamped log lines to plc/logs/plc.log and optionally
    forwards each line to a callback (e.g. to display in a UI log panel)."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None) -> None:
        self.log_callback = log_callback
        self.file = _LOG_FILE
        os.makedirs(_LOG_DIR, exist_ok=True)

    def log(self, message: str, level: str = "INFO") -> None:
        """Append a timestamped, leveled log line and forward it to the callback if set."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"

        if self.log_callback:
            self.log_callback(log_line)

        with open(self.file, "a") as f:
            f.write(log_line + "\n")