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

    def test_silence_yields_no_events(self, silence_wav_path):
        y, sr = sf.read(silence_wav_path)
        assert detect_events(y, sr) == []

    def test_noise_yields_no_events(self, noise_wav_path):
        y, sr = sf.read(noise_wav_path)
        events = detect_events(y, sr)
        assert events == [], f"noise produced {len(events)} spurious events"


class TestRepeatedNoteSplit:
    """同一音高の反復音がエネルギー再アタックで分割される回帰(根治 2026-07-23)。
    旧mono実装はピッチ変化のみで音符を切り、反復8分(唱歌の「けろけろ…」等)を
    1音にマージして速い音を取りこぼし→リズムが曖昧になり三連符へ誤爆していた。"""

    def test_repeated_same_pitch_notes_are_split(self):
        import numpy as np

        from earpipe.services.ear.mono import detect_events as mono_detect

        sr = 22050
        note_dur = 0.25  # 8分@120bpm
        n = 8
        t = np.linspace(0, note_dur, int(sr * note_dur), endpoint=False)
        note = np.sin(2 * np.pi * 440.0 * t) * np.exp(-t * 6.0)  # 減衰=音間に谷
        y = np.tile(note, n)

        events = mono_detect(y, sr)
        # 反復8音が概ね分割される(旧実装は1〜2音にマージ)。多少の欠けは許容。
        assert len(events) >= n - 2, f"reps merged: expected ~{n}, got {len(events)}"
        assert all(e.midi == 69 for e in events)  # A4
