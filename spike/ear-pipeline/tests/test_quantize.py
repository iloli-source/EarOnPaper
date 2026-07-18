"""変換層（テンポ推定・拍グリッド量子化）のユニットテスト。"""

from earpipe.ear import PitchEvent
from earpipe.quantize import estimate_tempo, quantize_events

from tests.conftest import MELODY_DOTTED, MELODY_SIMPLE


def events_from_melody(melody, bpm, jitter=0.0):
    spb = 60.0 / bpm
    evs = []
    for i, (m, s, d) in enumerate(melody):
        j = jitter * (1 if i % 2 == 0 else -1)
        evs.append(PitchEvent(onset=s * spb + j, offset=(s + d) * spb - 0.03, midi=m, confidence=0.9))
    return evs


class TestEstimateTempo:
    def test_clean_120(self):
        evs = events_from_melody(MELODY_SIMPLE, 120)
        bpm = estimate_tempo(evs)
        assert abs(bpm - 120) <= 2, f"expected ~120, got {bpm}"

    def test_clean_100(self):
        evs = events_from_melody(MELODY_DOTTED, 100)
        bpm = estimate_tempo(evs)
        assert abs(bpm - 100) <= 2, f"expected ~100, got {bpm}"

    def test_jittered_onsets(self):
        # ±15ms の揺れがあっても正しいテンポ帯を選ぶ
        evs = events_from_melody(MELODY_SIMPLE, 120, jitter=0.015)
        bpm = estimate_tempo(evs)
        assert abs(bpm - 120) <= 4

    def test_too_few_events_returns_default(self):
        evs = [PitchEvent(onset=0.0, offset=0.5, midi=60, confidence=0.9)]
        assert estimate_tempo(evs) == 120.0


class TestQuantizeEvents:
    def test_grid_alignment(self):
        evs = events_from_melody(MELODY_SIMPLE, 120)
        notes = quantize_events(evs, bpm=120)
        # zip+ソートは順序前提が崩れると誤マッチする(レビューLOW-4)ため集合で完全一致を検証
        got = {(n.midi, n.start_beats, n.dur_beats) for n in notes}
        want = {(m, s, d) for m, s, d in MELODY_SIMPLE}
        assert got == want

    def test_min_duration_is_16th(self):
        evs = [PitchEvent(onset=0.0, offset=0.02, midi=60, confidence=0.9)]
        notes = quantize_events(evs, bpm=120)
        assert len(notes) == 1
        assert notes[0].dur_beats == 0.25  # 16分未満は16分に切上げ

    def test_snap_off_grid_onset(self):
        # 格子から20msズレたオンセットが最寄り格子に吸着する
        spb = 60.0 / 120
        evs = [
            PitchEvent(onset=0.0 + 0.02, offset=spb - 0.03, midi=60, confidence=0.9),
            PitchEvent(onset=spb - 0.02, offset=2 * spb - 0.03, midi=62, confidence=0.9),
        ]
        notes = sorted(quantize_events(evs, bpm=120), key=lambda n: n.start_beats)
        assert notes[0].start_beats == 0.0
        assert notes[1].start_beats == 1.0

    def test_empty_input(self):
        assert quantize_events([], bpm=120) == []
