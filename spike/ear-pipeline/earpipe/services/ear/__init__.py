from earpipe.services.ear.adaptive import AdaptiveSelection, detect_events_adaptive
from earpipe.services.ear.mono import detect_events
from earpipe.services.ear.poly import bp_python_path, detect_events_poly
from earpipe.services.ear.field_select import gate_by_class, select_events
from earpipe.services.ear.octave_arbiter import (
    arbitrate_octaves,
    complete_fifths,
    complete_missed_strokes,
)
from earpipe.services.ear.postfilter import apply_postfilter, cleanup_upper_harmonics
from earpipe.services.ear.engine_select import (
    EngineChoice,
    choose_engine,
    estimate_polyphony,
)
from earpipe.services.ear.instrument_classify import (
    InstrumentGuess,
    classify_instrument,
)
from earpipe.services.ear.pedal import (
    SustainSpan,
    detect_sustain,
    detect_sustain_audio,
)
from earpipe.services.ear.velocity import (
    DYNAMIC_MARKS,
    estimate_velocities,
    to_dynamic_marks,
)
from earpipe.services.ear.drums import detect_drums
from earpipe.services.ear.hints import AnalysisHints, apply_hints

__all__ = [
    "InstrumentGuess",
    "classify_instrument",
    "AnalysisHints",
    "apply_hints",
    "SustainSpan",
    "detect_sustain",
    "detect_sustain_audio",
    "DYNAMIC_MARKS",
    "estimate_velocities",
    "to_dynamic_marks",
    "detect_drums",
    "AdaptiveSelection",
    "detect_events",
    "detect_events_adaptive",
    "detect_events_poly",
    "bp_python_path",
    "apply_postfilter",
    "arbitrate_octaves",
    "complete_fifths",
    "complete_missed_strokes",
    "cleanup_upper_harmonics",
    "select_events",
    "gate_by_class",
    "EngineChoice",
    "choose_engine",
    "estimate_polyphony",
]
