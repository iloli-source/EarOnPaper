"""後方互換シム → earpipe.services.rhythm.quantize(#35)。"""

from earpipe.contracts import QuantizedNote
from earpipe.services.rhythm.quantize import (  # noqa: F401
    BPM_DEFAULT,
    BPM_MAX,
    BPM_MIN,
    GRID_PER_BEAT,
    estimate_tempo,
    quantize_events,
)

__all__ = ["QuantizedNote", "BPM_DEFAULT", "estimate_tempo", "quantize_events"]
