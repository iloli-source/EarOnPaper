"""後方互換シム → earpipe.services.ear.poly(#35)。"""

from earpipe.services.ear.poly import (  # noqa: F401
    _WORKER,
    _validate_worker_json,
    bp_python_path,
    detect_events_poly,
)

__all__ = ["detect_events_poly", "bp_python_path"]
