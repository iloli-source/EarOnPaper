"""後方互換シム → earpipe.services.ear.mono(移行はADR-001サービス分割・#35)。"""

from earpipe.contracts import PitchEvent
from earpipe.services.ear.mono import (  # noqa: F401
    FMAX,
    FMIN,
    FRAME,
    HOP,
    MIN_CONFIDENCE,
    MIN_DUR_SEC,
    detect_events,
)

__all__ = ["PitchEvent", "detect_events"]
