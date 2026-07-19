"""後方互換シム → earpipe.services.ear.postfilter(#35)。"""

from earpipe.services.ear.postfilter import (  # noqa: F401
    apply_postfilter,
    filter_harmonic_ghosts,
    merge_splits,
)

__all__ = ["apply_postfilter", "filter_harmonic_ghosts", "merge_splits"]
