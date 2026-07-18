"""変換層（テンポ推定・拍グリッド量子化）のユニットテスト。"""

import numpy as np
import pytest
from earpipe.ear import PitchEvent
from earpipe.quantize import BPM_DEFAULT, estimate_tempo, quantize_events

from tests.conftest import MELODY_DOTTED, MELODY_SIMPLE


def events_from_melody(melody, bpm, jitter=0.0):
    spb = 60.0 / bpm
    evs = []
    for i, (m, s, d) in enumerate(melody):
        j = jitter * (1 if i % 2 == 0 else -1)
        evs.append(PitchEvent(onset=s * spb + j, offset=(s + d) * spb - 0.03, midi=m, confidence=0.9))
    return evs


def dense_poly_events(bpm: float, seed: int = 7, n_bars: int = 8) -> list[PitchEvent]:
    """密な多声の合成: 8分メロディ+毎小節の16分走句+拍ベース+2拍ごとの三和音。

    和音は弾き手のばらつき(±18ms)で非同時、メロディ/ベースは±12msの揺れ。
    16分走句を含めるのは、倍テンポ解釈(8分→4分)を音価の妥当性で棄却できる
    よう、真のテンポでしか自然に説明できない最速音価を置くため。
    """
    rng = np.random.default_rng(seed)
    spb = 60.0 / bpm
    evs: list[PitchEvent] = []
    for bar in range(n_bars):
        base = bar * 4.0
        for k in np.arange(0.0, 3.0, 0.5):  # 8分メロディ(3拍目まで)
            t = (base + k) * spb + rng.normal(0, 0.012)
            evs.append(PitchEvent(max(0.0, t), max(0.0, t) + spb * 0.4, 72 + int(k * 2) % 7, 0.9))
        for k in np.arange(3.0, 4.0, 0.25):  # 4拍目は16分走句
            t = (base + k) * spb + rng.normal(0, 0.012)
            evs.append(PitchEvent(max(0.0, t), max(0.0, t) + spb * 0.2, 76 + int(k * 4) % 5, 0.85))
        for k in range(4):  # ベース(毎拍)
            t = (base + k) * spb + rng.normal(0, 0.012)
            evs.append(PitchEvent(max(0.0, t), max(0.0, t) + spb * 0.9, 36 + k, 0.85))
        for k in (0.0, 2.0):  # 三和音(2拍ごと・非同時)
            for m in (48, 52, 55):
                t = (base + k) * spb + rng.normal(0, 0.018)
                evs.append(PitchEvent(max(0.0, t), max(0.0, t) + spb * 1.8, m, 0.8))
    return evs


def ghosty_events(bpm: float, ghost_ratio: float = 2.0, seed: int = 3, n_bars: int = 8) -> list[PitchEvent]:
    """実測のBasic Pitch出力風: 密な多声(高confidence)に、ほぼランダムな
    幽霊オンセット(低confidence)を混入させる。rhythm-autopsy.md で観測された
    precision 0.23-0.40 の状況を模す。"""
    rng = np.random.default_rng(seed)
    evs = dense_poly_events(bpm, seed=seed, n_bars=n_bars)
    total = n_bars * 4.0 * (60.0 / bpm)
    for _ in range(int(len(evs) * ghost_ratio)):
        t = float(rng.uniform(0, total))
        evs.append(PitchEvent(t, t + 0.08, 60 + int(rng.integers(0, 24)), 0.3))
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


class TestEstimateTempoRobust:
    """Issue #34: 密な多声・幽霊混入でのテンポ推定の頑健性(固着・倍半誤りの回帰テスト)。"""

    @pytest.mark.parametrize("bpm", [60, 90, 100, 120, 150])
    def test_mono_matrix(self, bpm):
        # 単音メロディ(16分走句・シンコペーション含む)で誤差±5%以内
        evs = events_from_melody(MELODY_SIMPLE, bpm, jitter=0.008)
        est = estimate_tempo(evs)
        assert abs(est - bpm) <= bpm * 0.05, f"true={bpm}, got {est}"

    @pytest.mark.parametrize("bpm", [60, 90, 100, 120, 150])
    def test_dense_poly_matrix(self, bpm):
        # 密な多声(和音の非同時・揺れ込み)で誤差±5%以内。
        # 旧実装は 120→60, 150→75 の倍半誤りを起こしていた
        est = estimate_tempo(dense_poly_events(bpm))
        assert abs(est - bpm) <= bpm * 0.05, f"true={bpm}, got {est}"

    @pytest.mark.parametrize("bpm", [90, 150])
    def test_ghosts_with_confidence(self, bpm):
        # 低confidenceの幽霊が2倍量混入しても、confidence重み付けで正しい帯に入る
        est = estimate_tempo(ghosty_events(bpm, ghost_ratio=2.0))
        assert abs(est - bpm) <= bpm * 0.05, f"true={bpm}, got {est}"

    def test_ghost_storm_returns_default_not_fixation(self):
        # 全部が低confidenceのランダムオンセット(格子で説明できない)なら、
        # 旧実装のように145-155帯へ張り付かず、素直にデフォルトへ退避する
        rng = np.random.default_rng(11)
        evs = [
            PitchEvent(t, t + 0.08, 60 + int(rng.integers(0, 24)), 0.3)
            for t in sorted(rng.uniform(0, 20, size=120))
        ]
        est = estimate_tempo(evs)
        assert est == BPM_DEFAULT, f"expected default {BPM_DEFAULT}, got {est}"


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
