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

    def _repeated(self, sr: int, n: int = 8, note_dur: float = 0.25):
        import numpy as np

        t = np.linspace(0, note_dur, int(sr * note_dur), endpoint=False)
        note = np.sin(2 * np.pi * 440.0 * t) * np.exp(-t * 6.0)
        return np.tile(note, n)

    def test_repeated_notes_split_is_sr_invariant(self):
        """#138: 分割窓が22050Hz前提のフレーム定数で、ネイティブsr(48k)では
        実時間窓が半減し連打・段差の分割が壊れていた。srに依らず同等に分割される。"""
        from earpipe.services.ear.mono import detect_events as mono_detect

        n = 8
        for sr in (22050, 48000):
            events = mono_detect(self._repeated(sr), sr)
            assert len(events) >= n - 2, f"sr={sr}: expected ~{n}, got {len(events)}"
            assert all(e.midi == 69 for e in events)

    def test_semitone_step_with_glide_splits_at_48k(self):
        """#138: F→E型の半音段差(pYIN滑走つき)がsr=48000でも2音に分割される
        (かえるのうた実測: 窓37msでは滑走が窓を覆い best_gap 0.6<0.8 で失敗)。"""
        import numpy as np

        from earpipe.services.ear.mono import detect_events as mono_detect

        sr = 48000
        dur = 0.7
        glide = 0.06  # 60msの滑走
        t1 = np.arange(int(sr * dur)) / sr
        f_hi, f_lo = 349.23, 329.63  # F4 → E4 (1半音)
        seg1 = 0.3 * np.sin(2 * np.pi * f_hi * t1)
        tg = np.arange(int(sr * glide)) / sr
        fg = f_hi + (f_lo - f_hi) * tg / glide
        segg = 0.3 * np.sin(2 * np.pi * np.cumsum(fg) / sr)
        seg2 = 0.3 * np.sin(2 * np.pi * f_lo * t1)
        y = np.concatenate([seg1, segg, seg2])
        events = mono_detect(y, sr)
        midis = sorted({e.midi for e in events})
        assert midis == [64, 65], f"got {[(e.midi, round(e.onset,2)) for e in events]}"

    def test_kaeru_regression_local(self):
        """#138統合回帰(ローカル実音源・存在時のみ): 23→25音以上・誤音0。

        正解29音との編集距離≤4を固定(残るレガート連打の取りこぼしは#114領域と
        して正直に記録・偽分割ゼロを優先した0.15採用の実測水準)。"""
        from pathlib import Path

        import pytest

        src = Path(__file__).resolve().parents[1] / "usertest" / "input" / "かえるのうた mp3.m4a"
        if not src.exists():
            pytest.skip("ローカル実音源なし")
        from earpipe.services.ear.mono import detect_events as mono_detect
        from earpipe.services.stem import load_audio

        y, sr = load_audio(src)
        evs = mono_detect(y, sr)
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        seq = [names[e.midi % 12] for e in evs]
        expected = "C D E F E D C E F G A G F E C C C C C C D D E E F F E D C".split()
        assert len(seq) >= 25, f"n={len(seq)}: {seq}"
        assert set(seq) <= set(expected), f"誤音混入: {sorted(set(seq) - set(expected))}"
        dp = list(range(len(expected) + 1))
        for i, ca in enumerate(seq, 1):
            prev, dp[0] = dp[0], i
            for j, cb in enumerate(expected, 1):
                prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
        assert dp[-1] <= 4, f"編集距離={dp[-1]}"

    def test_vibrato_preserved_at_48k(self):
        """#138過剰分割ガード: ±0.4半音ビブラートは48kでも1音のまま。"""
        import numpy as np

        from earpipe.services.ear.mono import detect_events as mono_detect

        sr = 48000
        t = np.arange(int(sr * 2.0)) / sr
        inst = 450.0 * 2.0 ** (0.4 * np.sin(2 * np.pi * 6.0 * t) / 12.0)
        y = 0.3 * np.sin(2 * np.pi * np.cumsum(inst) / sr)
        events = mono_detect(y, sr)
        assert len(events) == 1, f"got {[(e.midi, round(e.onset,2)) for e in events]}"
