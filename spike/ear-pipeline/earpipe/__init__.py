"""earpipe — 採譜エンジン spike v0（二層構造: 耳=楽器非依存 / 記譜=出力プロファイル）"""

from earpipe.ear import PitchEvent, detect_events
from earpipe.notate import to_score, write_midi, write_musicxml
from earpipe.pipeline import transcribe_file
from earpipe.quantize import QuantizedNote, estimate_tempo, quantize_events

__all__ = [
    "PitchEvent",
    "detect_events",
    "QuantizedNote",
    "estimate_tempo",
    "quantize_events",
    "to_score",
    "write_musicxml",
    "write_midi",
    "transcribe_file",
]
