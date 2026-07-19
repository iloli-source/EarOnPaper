"""後方互換シム → earpipe.services.notate.score(#35)。"""

from earpipe.services.notate.score import (  # noqa: F401
    to_score,
    write_midi,
    write_musicxml,
)

__all__ = ["to_score", "write_midi", "write_musicxml"]
