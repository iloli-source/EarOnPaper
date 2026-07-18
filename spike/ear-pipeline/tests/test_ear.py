"""耳層（音→音程イベント）のユニットテスト。pYIN単音フォールバック実装を検証。"""

import soundfile as sf
from earpipe.ear import detect_events

from tests.conftest import melody_to_seconds, note_f1


class TestDetectEvents:
    def test_simple_melody_events(self, simple_wav):
        path, melody, bpm = simple_wav
        y, sr = sf.read(path)
        events = detect_events(y, sr)
        truth = melody_to_seconds(melody, bpm)
        pred = [(e.midi, e.onset, e.offset) for e in events]
        f1 = note_f1(truth, pred)
        assert f1 >= 0.8, f"ear-layer note F1 {f1:.3f} < 0.8 (events={len(events)})"

    def test_confidence_range(self, simple_wav):
        path, _, _ = simple_wav
        y, sr = sf.read(path)
        for e in detect_events(y, sr):
            assert 0.0 <= e.confidence <= 1.0
            assert e.offset > e.onset

    def test_silence_yields_no_events(self, silence_wav):
        y, sr = sf.read(silence_wav)
        assert detect_events(y, sr) == []

    def test_noise_yields_no_events(self, noise_wav):
        y, sr = sf.read(noise_wav)
        events = detect_events(y, sr)
        assert events == [], f"noise produced {len(events)} spurious events"
