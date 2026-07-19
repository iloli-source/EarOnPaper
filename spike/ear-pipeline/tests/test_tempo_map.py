"""区間別テンポ系列(テンポマップ・Issue #56 / C2受入条件)のテスト。

合成イベント列で分割・退化・頑健性を固定し、real-audio(緩急のある実演奏)で
「区間分割が破綻しない(クラッシュ・発散ゼロ)」の受入条件を検証する。
"""

import math
from pathlib import Path

import pytest

from earpipe.contracts import PitchEvent
from earpipe.services.rhythm import (
    BPM_DEFAULT,
    TempoSegment,
    estimate_tempo_map,
)
from earpipe.services.rhythm.tempo_map import MERGE_TOL_RATIO

REAL_AUDIO = (
    Path(__file__).resolve().parents[3]
    / "tools" / "ai-ears" / "testdata" / "pd-corpus" / "real-audio"
)


def _steady_events(bpm: float, start: float, end: float, midi: int = 60) -> list[PitchEvent]:
    """指定テンポの8分音符列(IOI = 30/bpm 秒)。"""
    ioi = 30.0 / bpm
    events = []
    t = start
    while t < end:
        events.append(PitchEvent(onset=t, offset=t + ioi * 0.9, midi=midi, confidence=0.9))
        t += ioi
    return events


def _assert_no_divergence(segments: list[TempoSegment]):
    """発散ゼロ: 全区間が有限・正のBPMで、開始時刻が単調増加。"""
    assert segments, "テンポマップが空"
    for seg in segments:
        assert math.isfinite(seg.bpm) and seg.bpm > 0
    starts = [s.start_sec for s in segments]
    assert starts == sorted(starts)


class TestTempoMapSynthetic:
    def test_constant_tempo_collapses_to_single_segment(self):
        segments = estimate_tempo_map(_steady_events(120.0, 0.0, 40.0))
        assert len(segments) == 1
        assert segments[0].bpm == pytest.approx(120.0, rel=0.05)

    def test_tempo_change_splits_segments(self):
        # 前半100BPM→後半140BPM(5%超の変化): 2区間に分かれ両方のテンポを捉える
        events = _steady_events(100.0, 0.0, 30.0) + _steady_events(140.0, 30.0, 60.0)
        segments = estimate_tempo_map(events)
        _assert_no_divergence(segments)
        assert len(segments) >= 2
        assert segments[0].bpm == pytest.approx(100.0, rel=0.05)
        assert segments[-1].bpm == pytest.approx(140.0, rel=0.05)

    def test_gradual_accelerando_no_divergence(self):
        # 連続的な加速(96→150BPM線形): 破綻せず、区間テンポが単調に上がる
        events = []
        t = 0.0
        while t < 60.0:
            bpm_now = 96.0 + (150.0 - 96.0) * (t / 60.0)
            ioi = 30.0 / bpm_now
            events.append(PitchEvent(onset=t, offset=t + ioi * 0.9, midi=64, confidence=0.9))
            t += ioi
        segments = estimate_tempo_map(events)
        _assert_no_divergence(segments)
        assert len(segments) >= 2
        # テンポの倍半曖昧性(一様音符列の理論限界・quantize.py docstring)があるため
        # オクターブ折り畳み([90,180)に正規化)後の単調増加で加速追従を確認する
        def fold(bpm: float) -> float:
            while bpm < 90.0:
                bpm *= 2.0
            while bpm >= 180.0:
                bpm /= 2.0
            return bpm

        folded = [fold(s.bpm) for s in segments]
        assert folded == sorted(folded)

    def test_empty_events_returns_default(self):
        assert estimate_tempo_map([]) == [TempoSegment(0.0, BPM_DEFAULT)]

    def test_sparse_tail_inherits_previous_tempo(self):
        # 後半が疎(イベント僅少)でも独立推定で暴れず前区間を引き継ぐ
        events = _steady_events(120.0, 0.0, 30.0) + [
            PitchEvent(onset=45.0, offset=45.5, midi=60, confidence=0.9)
        ]
        segments = estimate_tempo_map(events)
        _assert_no_divergence(segments)
        assert len(segments) == 1  # 引き継ぎ→±5%内→併合で単一区間

    def test_merge_tolerance_matches_c2_criterion(self):
        # 併合閾値は受入条件と同じ±5%
        assert MERGE_TOL_RATIO == 0.05

    def test_invalid_window_rejected(self):
        with pytest.raises(ValueError):
            estimate_tempo_map(_steady_events(120.0, 0.0, 10.0), window_sec=0.0)


@pytest.mark.skipif(not REAL_AUDIO.exists(), reason="real-audioコーパス不在")
class TestTempoMapRealAudio:
    """C2受入条件: 緩急のある実録音でテンポ系列の区間分割が破綻しない。"""

    @pytest.mark.parametrize("name", ["turkish_march.wav", "romanze.wav"])
    def test_real_recording_no_crash_no_divergence(self, name):
        from earpipe.services.ear import bp_python_path, detect_events_poly

        if bp_python_path() is None:
            pytest.skip("basic-pitch実行環境なし")
        events = detect_events_poly(REAL_AUDIO / name)
        segments = estimate_tempo_map(events)
        _assert_no_divergence(segments)
