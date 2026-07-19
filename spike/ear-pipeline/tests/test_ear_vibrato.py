"""#46 ear ビブラート断片化の攻撃回帰テスト(func-r1-fable-input E1/E7)。

旧実装はフレームのMIDI整数値が変わるたびにセグメントを切るため、
ビブラート(f0の連続上下)で全セグメントがmin_dur未満に断片化し音符が消えた。
本テストは中心音高±許容幅のセグメント統合による音符保存を固定する。
"""

import numpy as np

from earpipe.services.ear import detect_events

SR = 22050


def vibrato_tone(
    dur: float = 2.0,
    center_hz: float = 440.0,
    depth_semitones: float = 0.5,
    rate_hz: float = 6.0,
    amp: float = 0.3,
) -> np.ndarray:
    """中心音高の周りを正弦的に揺れるビブラート音(位相連続のFM合成)。"""
    n = int(SR * dur)
    t = np.arange(n) / SR
    # 瞬時周波数: center * 2^(depth*sin(2πrt)/12)
    inst_freq = center_hz * 2.0 ** (depth_semitones * np.sin(2 * np.pi * rate_hz * t) / 12.0)
    phase = 2 * np.pi * np.cumsum(inst_freq) / SR
    return amp * np.sin(phase)


def two_note_melody(freqs: tuple[float, float], note_dur: float = 0.6, amp: float = 0.3) -> np.ndarray:
    segs = []
    for f in freqs:
        n = int(SR * note_dur)
        t = np.arange(n) / SR
        seg = amp * np.sin(2 * np.pi * f * t)
        fade = int(0.01 * SR)
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        segs.append(seg)
    return np.concatenate(segs)


class TestVibratoPreservation:
    def test_boundary_centered_vibrato_single_note(self):
        """本物のE1再現: 半音境界(midi69.5=452.9Hz)中心のビブラートは
        旧実装で20断片(69/70交互)に砕けた。1音として統合されること。"""
        events = detect_events(vibrato_tone(center_hz=452.9, depth_semitones=0.3), SR)
        assert len(events) == 1, f"events={[(e.midi, round(e.onset,2)) for e in events]}"
        assert events[0].midi in (69, 70)

    def test_near_boundary_same_note_not_fragmented(self):
        """本物のE1再現: 境界寄り中心(450Hz)のビブラートは旧実装で
        同じ音高69が12断片化した。1音として統合されること。"""
        events = detect_events(vibrato_tone(center_hz=450.0, depth_semitones=0.4), SR)
        assert len(events) == 1, f"events={[(e.midi, round(e.onset,2)) for e in events]}"
        assert events[0].midi == 69

    def test_e1_shallow_vibrato_preserved(self):
        """攻撃E1: ビブラート±0.25半音で音符が保存される(旧実装は0イベント)。"""
        events = detect_events(vibrato_tone(depth_semitones=0.25), SR)
        assert len(events) == 1, f"events={[(e.midi, round(e.onset,2)) for e in events]}"
        assert events[0].midi == 69  # A4

    def test_e1_half_semitone_vibrato_preserved(self):
        """攻撃E1: ビブラート±0.5半音でも音符が保存される。"""
        events = detect_events(vibrato_tone(depth_semitones=0.5), SR)
        assert len(events) == 1, f"events={[(e.midi, round(e.onset,2)) for e in events]}"
        assert events[0].midi == 69

    def test_deep_vibrato_documented_limit(self):
        """深いビブラート(±1半音超)は1音への統合を保証しない(正直な限界:
        局所シフト検出が半サイクル毎に反応し断片化する。実測±1.5で8前後)。
        ここでの要求は「幽霊の洪水を出さない」— サイクル数(2s×6Hz=24半周期)を
        超える断片は出さないこと。"""
        events = detect_events(vibrato_tone(depth_semitones=1.5), SR)
        assert len(events) <= 24, f"deep vibrato flooded: {len(events)} events"

    def test_no_overmerge_two_semitone_step(self):
        """過統合の防止: 2半音差の2音(A4→B4)は2イベントのまま。"""
        events = detect_events(two_note_melody((440.0, 493.88)), SR)
        midis = [e.midi for e in events]
        assert midis == [69, 71], f"midis={midis}"

    def test_no_overmerge_adjacent_semitone(self):
        """過統合の防止: 半音差の2音(A4→A#4)も分離される。"""
        events = detect_events(two_note_melody((440.0, 466.16)), SR)
        midis = [e.midi for e in events]
        assert midis == [69, 70], f"midis={midis}"

    def test_steady_tone_unchanged(self):
        """回帰: 揺れのない持続音は従来どおり1イベント。"""
        events = detect_events(vibrato_tone(depth_semitones=0.0), SR)
        assert len(events) == 1
        assert events[0].midi == 69
