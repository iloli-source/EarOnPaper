"""C3 リズム二重表現(Issue #38)のテスト。

設計の背景: PD15曲実測で「格子スナップが音符を正解タイミングから引き剥がす」
ことが確認された(results-pd.md)。解決は二重表現 — データモデルに
実タイミング(秒)と格子位置(拍)の両方を保持し、譜面は格子側・評価/エクスポートは
選択可能にする。
"""

import math

import pretty_midi
import pytest
from earpipe.contracts import PitchEvent, QuantizedNote
from earpipe.services.notate import write_midi_raw
from earpipe.services.rhythm import GRID_PER_BEAT, quantize_events

BPM = 120.0
SPB = 60.0 / BPM
GRID_SEC = SPB / GRID_PER_BEAT


def offgrid_events() -> list[PitchEvent]:
    """格子から意図的にズラしたイベント(±30ms)。実タイミングが保持されるべき素材。"""
    return [
        PitchEvent(onset=0.030, offset=SPB - 0.02, midi=60, confidence=0.9),
        PitchEvent(onset=SPB - 0.025, offset=2 * SPB - 0.02, midi=62, confidence=0.9),
        PitchEvent(onset=2 * SPB + 0.018, offset=3 * SPB, midi=64, confidence=0.9),
    ]


class TestDualRepresentation:
    def test_real_timing_preserved(self):
        # 量子化後も元イベントの実秒が保持される(格子に上書きされない)
        evs = offgrid_events()
        notes = sorted(quantize_events(evs, bpm=BPM), key=lambda n: n.start_beats)
        assert [n.onset_sec for n in notes] == pytest.approx([e.onset for e in evs])
        assert [n.offset_sec for n in notes] == pytest.approx([e.offset for e in evs])

    def test_grid_position_consistent_with_real(self):
        # 往復整合: 格子位置 = 実秒を格子に丸めたもの
        for n in quantize_events(offgrid_events(), bpm=BPM):
            expected = round(n.onset_sec / GRID_SEC) / GRID_PER_BEAT
            assert n.start_beats == pytest.approx(expected)

    def test_backward_compatible_construction(self):
        # 既存の4引数構築が有効のまま(実秒は未指定=NaN)
        n = QuantizedNote(0.0, 1.0, 60, 0.9)
        assert math.isnan(n.onset_sec) and math.isnan(n.offset_sec)

    def test_mono_clip_keeps_real_timing(self):
        # 単旋律の長さ切り詰めは格子側のみ。実秒は元のまま
        evs = [
            PitchEvent(onset=0.0, offset=1.9, midi=60, confidence=0.9),
            PitchEvent(onset=SPB, offset=2 * SPB, midi=62, confidence=0.9),
        ]
        notes = sorted(quantize_events(evs, bpm=BPM, mono=True), key=lambda n: n.start_beats)
        assert notes[0].dur_beats == pytest.approx(1.0)  # 格子側は切り詰め
        assert notes[0].offset_sec == pytest.approx(1.9)  # 実秒は保持


class TestRawExport:
    def test_write_midi_raw_uses_real_seconds(self, tmp_path):
        evs = offgrid_events()
        notes = quantize_events(evs, bpm=BPM)
        dest = tmp_path / "raw.mid"
        write_midi_raw(notes, dest)
        got = sorted(
            (n.start, n.pitch)
            for inst in pretty_midi.PrettyMIDI(str(dest)).instruments
            for n in inst.notes
        )
        for (start, pitch), e in zip(got, sorted(evs, key=lambda x: x.onset)):
            assert start == pytest.approx(e.onset, abs=2e-3)
            assert pitch == e.midi

    def test_write_midi_raw_falls_back_to_grid_when_nan(self, tmp_path):
        # 実秒を持たない旧型データはbpmから格子秒で書けるフォールバック
        notes = [QuantizedNote(1.0, 1.0, 60, 0.9)]
        dest = tmp_path / "fallback.mid"
        write_midi_raw(notes, dest, bpm=BPM)
        pm = pretty_midi.PrettyMIDI(str(dest))
        assert pm.instruments[0].notes[0].start == pytest.approx(SPB, abs=2e-3)

    def test_both_metrics_from_single_output(self, tmp_path):
        # 同一の量子化出力から: 実秒MIDI(F1@100ms用)と格子MIDI(score_rhythm用)が両方書ける
        evs = offgrid_events()
        notes = quantize_events(evs, bpm=BPM)
        raw = tmp_path / "raw.mid"
        write_midi_raw(notes, raw)
        # 格子側は従来経路(to_score→write_midi)が担う。ここでは実秒側が
        # 格子に吸着していないこと(=二重表現が実在すること)を確認する
        starts = [
            n.start
            for inst in pretty_midi.PrettyMIDI(str(raw)).instruments
            for n in inst.notes
        ]
        deviations = [abs(s - round(s / GRID_SEC) * GRID_SEC) for s in starts]
        assert max(deviations) > 0.01, "raw出力が格子に吸着している=二重表現になっていない"
