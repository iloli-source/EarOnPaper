"""C2 三連符対応(Issue #39)のテスト。

#34の既知限界: 16分格子しかなく、三連符曲(Romanze 3/4・正解96BPM)を
1.5倍の144BPMと誤答していた(三連8分格子@96 ≡ 16分格子@144 のエイリアシング)。
格子系(2分系/3分系)をテンポと同時推定して解消する。

既知の理論限界(正直な記録): 一様な音符列では三連@T と 16分@1.5T が数学的に
同一のため、事前分布(テンポ中心108)から遠いテンポの三連曲は2分系に倒れうる。
本テストは事前分布の有効域(90-110近傍)と実曲Romanzeを受入範囲とする。
"""

from pathlib import Path

import pretty_midi
import pytest
from earpipe.contracts import PitchEvent
from earpipe.services.rhythm import estimate_grid, estimate_tempo, quantize_events

CORPUS = Path(__file__).resolve().parents[3] / "tools" / "ai-ears" / "testdata" / "pd-corpus"
ROMANZE = CORPUS / "user-samples" / "Romanze_Castellana_G-Em.mid"
TURKISH = CORPUS / "user-samples" / "Turkish_March_K331_C-Am.mid"


def midi_to_events(path: Path, clip_sec: float = 60.0) -> list[PitchEvent]:
    pm = pretty_midi.PrettyMIDI(str(path))
    evs = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            if n.start < clip_sec:
                evs.append(PitchEvent(n.start, min(n.end, clip_sec), n.pitch, 0.9))
    return sorted(evs, key=lambda e: e.onset)


def triplet_melody_events(bpm: float, n_bars: int = 8) -> list[PitchEvent]:
    """3/4拍子・8分3連の連続アルペジオ(Romanze型)の合成。"""
    spb = 60.0 / bpm
    step = spb / 3.0
    evs = []
    t = 0.0
    for bar in range(n_bars):
        for k in range(9):  # 3拍 × 3連
            evs.append(PitchEvent(t, t + step * 0.9, 64 + (k % 3) * 4, 0.9))
            t += step
    return evs


class TestTripletGrid:
    @pytest.mark.parametrize("bpm", [96, 100, 108])
    def test_synthetic_triplet_selects_triplet_grid(self, bpm):
        # 事前分布の有効域では三連格子(gpb=3)が選ばれ、テンポも±5%
        est_bpm, gpb = estimate_grid(triplet_melody_events(bpm))
        assert gpb == 3, f"expected triplet grid, got gpb={gpb} (bpm={est_bpm})"
        assert abs(est_bpm - bpm) <= bpm * 0.05, f"true={bpm}, got {est_bpm}"

    def test_duple_melody_keeps_duple_grid(self):
        # 16分走句を含む2分系メロディは従来どおり gpb=4
        from tests.test_quantize import events_from_melody
        from tests.conftest import MELODY_SIMPLE

        est_bpm, gpb = estimate_grid(events_from_melody(MELODY_SIMPLE, 120))
        assert gpb == 4
        assert abs(est_bpm - 120) <= 6

    def test_quantize_on_triplet_grid(self):
        # 三連格子での量子化: start/dur が 1/3 拍の倍数になる
        evs = triplet_melody_events(96, n_bars=2)
        notes = quantize_events(evs, bpm=96, mono=True, grid_per_beat=3)
        for n in notes:
            assert round(n.start_beats * 3) == pytest.approx(n.start_beats * 3, abs=1e-9)
            assert n.dur_beats >= 1.0 / 3.0 - 1e-9


class TestRealSongs:
    @pytest.mark.skipif(not ROMANZE.exists(), reason="pd-corpus未取得環境")
    def test_romanze_tempo_within_5pct(self):
        # 固着の再現→解消: 正解96BPM(旧実装は144と誤答)
        est_bpm, gpb = estimate_grid(midi_to_events(ROMANZE))
        assert gpb == 3, f"Romanzeは三連格子のはず, got gpb={gpb} (bpm={est_bpm})"
        assert abs(est_bpm - 96) <= 96 * 0.05, f"true=96, got {est_bpm}"

    @pytest.mark.skipif(not TURKISH.exists(), reason="pd-corpus未取得環境")
    def test_turkish_march_regression(self):
        # トルコ行進曲(2分系・#34で121達成)がリグレッションしない
        est_bpm, gpb = estimate_grid(midi_to_events(TURKISH))
        assert gpb == 4, f"トルコ行進曲は2分系のはず, got gpb={gpb} (bpm={est_bpm})"
        assert abs(est_bpm - 120) <= 120 * 0.05, f"true=120, got {est_bpm}"


class TestBackwardCompat:
    def test_estimate_tempo_unchanged_interface(self):
        # 既存API estimate_tempo は従来どおり bpm(float) を返す
        from tests.test_quantize import events_from_melody
        from tests.conftest import MELODY_SIMPLE

        bpm = estimate_tempo(events_from_melody(MELODY_SIMPLE, 120))
        assert isinstance(bpm, float)
        assert abs(bpm - 120) <= 2
