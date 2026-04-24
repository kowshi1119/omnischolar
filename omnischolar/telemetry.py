"""
telemetry.py — Lightweight event telemetry for OmniScholar.
Logs latency and events to SQLite without external dependencies.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any


_db_instance = None


def _get_db():
    global _db_instance
    if _db_instance is None:
        try:
            from database import Database
            _db_instance = Database()
        except Exception:
            pass
    return _db_instance


def log_event(event_type: str, value_ms: float = 0.0, metadata: str = "") -> None:
    """Log a telemetry event to the DB. Fails silently."""
    try:
        db = _get_db()
        if db:
            db.log_telemetry_event(event_type, value_ms, metadata)
    except Exception:
        pass


@contextmanager
def timed(event_type: str, metadata: str = ""):
    """Context manager: auto-log duration in ms on exit."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        log_event(event_type, elapsed_ms, metadata)
