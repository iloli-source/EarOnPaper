"""F-016 相対強弱(velocity)推定と強弱記号化のテスト。

研究(docs/research/upcoming/F-016-*.md)の核心 pitfall を回帰固定する:
  - 返すのは「曲内の相対強弱(0-1)」であって絶対値ではない(録音レベル依存)。
  - 強い音のオンセットほど相対強弱が高く出る(順位保存)。
  - 録音ゲインで全体を定数倍しても相対順位は不変(ゲイン非依存性)。
  - 全音同一エネルギーなら順位を捏造せず一律 0.5。
  - to_dynamic_marks は絶対閾値ではなく分位点で pp..ff へ写像する。

AAA(Arrange-Act-Assert)形式で複数観点を検証する。
"""

import numpy as np
import pytest

from earpipe.contracts import PitchEvent
from earpipe.services.ear.velocity import (
    DYNAMIC_MARKS,
    estimate_velocities,
    to_dynamic_marks,
)

SR = 22050


def _tone(freq: float, dur: float, amp: float, sr: int = SR) -> np.ndarray:
    """指定振幅の正弦波トーンを生成する(振幅=相対的な強さの代理)。"""
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2.0 * np.pi * freq * t)).astype(np.float64)


def _event(onset: float, offset: float, midi: int = 60) -> PitchEvent:
    return PitchEvent(onset=onset, offset=offset, midi=midi, confidence=0.9)


def _build_signal(segments: list[tuple[float, float, float]], sr: int = SR) -> np.ndarray:
    """(onset, dur, amp) の列から連続音声を組み立てる(無音で埋める)。"""
    total = int(round(max(o + d for o, d, _ in segments) * sr)) + sr
    y = np.zeros(total, dtype=np.float64)
    for onset, dur, amp in segments:
        tone = _tone(440.0, dur, amp, sr)
        start = int(round(onset * sr))
        y[start:start + len(tone)] += tone
    return y


class TestEstimateVelocities:
    def test_returns_relative_strength_in_unit_range(self):
        # Arrange: 弱・中・強の3音(振幅で強さを表現)
        segments = [(0.0, 0.3, 0.1), (0.5, 0.3, 0.4), (1.0, 0.3, 0.9)]
        y = _build_signal(segments)
        events = [_event(0.0, 0.3), _event(0.5, 0.8), _event(1.0, 1.3)]

        # Act
        vels = estimate_velocities(y, SR, events)

        # Assert: 各ノートに 0-1 の相対強弱が付く
        assert len(vels) == 3
        assert all(0.0 <= v <= 1.0 for v in vels)

    def test_louder_onset_gets_higher_velocity(self):
        # Arrange: 振幅が単調増加する3音
        segments = [(0.0, 0.3, 0.1), (0.5, 0.3, 0.4), (1.0, 0.3, 0.9)]
        y = _build_signal(segments)
        events = [_event(0.0, 0.3), _event(0.5, 0.8), _event(1.0, 1.3)]

        # Act
        vels = estimate_velocities(y, SR, events)

        # Assert: 相対強弱も単調増加(順位保存)。最弱=0, 最強=1(min-max正規化)
        assert vels[0] < vels[1] < vels[2]
        assert vels[0] == pytest.approx(0.0, abs=1e-6)
        assert vels[2] == pytest.approx(1.0, abs=1e-6)

    def test_gain_invariance_recording_level(self):
        # Arrange: 同じ演奏を録音ゲインだけ変えて再測定(全体を定数倍)
        segments = [(0.0, 0.3, 0.1), (0.5, 0.3, 0.4), (1.0, 0.3, 0.9)]
        y = _build_signal(segments)
        events = [_event(0.0, 0.3), _event(0.5, 0.8), _event(1.0, 1.3)]

        # Act: 元とゲイン4倍(録音レベルを上げた)を比較
        vels = estimate_velocities(y, SR, events)
        vels_loud = estimate_velocities(y * 4.0, SR, events)

        # Assert: 曲内相対値なので録音ゲインに依存しない(F-016 の本質)
        assert vels == pytest.approx(vels_loud, abs=1e-6)

    def test_uniform_energy_returns_mid_value(self):
        # Arrange: 全音同一振幅(相対差なし)
        segments = [(0.0, 0.3, 0.5), (0.5, 0.3, 0.5), (1.0, 0.3, 0.5)]
        y = _build_signal(segments)
        events = [_event(0.0, 0.3), _event(0.5, 0.8), _event(1.0, 1.3)]

        # Act
        vels = estimate_velocities(y, SR, events)

        # Assert: 順位を捏造せず一律 0.5
        assert vels == pytest.approx([0.5, 0.5, 0.5])

    def test_empty_events_returns_empty(self):
        # Arrange
        y = _tone(440.0, 0.5, 0.5)

        # Act
        vels = estimate_velocities(y, SR, [])

        # Assert
        assert vels == []

    def test_stereo_input_is_reduced_to_mono(self):
        # Arrange: 2ch(ステレオ)入力でもクラッシュせず処理される
        mono = _build_signal([(0.0, 0.3, 0.3), (0.5, 0.3, 0.8)])
        stereo = np.stack([mono, mono], axis=1)
        events = [_event(0.0, 0.3), _event(0.5, 0.8)]

        # Act
        vels = estimate_velocities(stereo, SR, events)

        # Assert
        assert len(vels) == 2
        assert vels[0] < vels[1]

    def test_invalid_sr_raises(self):
        # Arrange
        y = _tone(440.0, 0.3, 0.5)

        # Act / Assert
        with pytest.raises(ValueError):
            estimate_velocities(y, 0, [_event(0.0, 0.3)])

    def test_negative_window_raises(self):
        # Arrange
        y = _tone(440.0, 0.3, 0.5)

        # Act / Assert
        with pytest.raises(ValueError):
            estimate_velocities(y, SR, [_event(0.0, 0.3)], pre_sec=-0.1)

    def test_empty_audio_with_events_raises(self):
        # Arrange: 測定対象があるのに音声が空 → 黙認しない
        # Act / Assert
        with pytest.raises(ValueError):
            estimate_velocities(np.array([], dtype=np.float64), SR, [_event(0.0, 0.3)])


class TestToDynamicMarks:
    def test_maps_relative_values_to_marks_monotonically(self):
        # Arrange: 0..1 を等間隔に並べる
        vels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

        # Act
        marks = to_dynamic_marks(vels)

        # Assert: 弱→強の順で pp..ff に単調写像される
        assert marks == ["pp", "p", "mp", "mf", "f", "ff"]

    def test_min_maps_to_softest_max_to_loudest(self):
        # Arrange
        vels = [0.0, 1.0]

        # Act
        marks = to_dynamic_marks(vels)

        # Assert: 曲内の最弱=pp, 最強=ff(相対段階)
        assert marks[0] == DYNAMIC_MARKS[0]
        assert marks[-1] == DYNAMIC_MARKS[-1]

    def test_value_one_clips_to_top(self):
        # Arrange: 上端 1.0 は最上段へクリップ(索引はみ出しを防ぐ)
        # Act
        marks = to_dynamic_marks([1.0])

        # Assert
        assert marks == ["ff"]

    def test_empty_returns_empty(self):
        # Act / Assert
        assert to_dynamic_marks([]) == []

    def test_out_of_range_value_raises(self):
        # Arrange / Act / Assert: 契約(0-1)を破る入力を黙認しない
        with pytest.raises(ValueError):
            to_dynamic_marks([1.5])

    def test_non_finite_value_raises(self):
        # Act / Assert
        with pytest.raises(ValueError):
            to_dynamic_marks([float("nan")])

    def test_empty_marks_raises(self):
        # Act / Assert
        with pytest.raises(ValueError):
            to_dynamic_marks([0.5], marks=())


class TestIntegrationVelocityToMarks:
    def test_estimate_then_mark_pipeline(self):
        # Arrange: 弱→強の3音を推定→記号化まで通す
        segments = [(0.0, 0.3, 0.1), (0.5, 0.3, 0.4), (1.0, 0.3, 0.9)]
        y = _build_signal(segments)
        events = [_event(0.0, 0.3), _event(0.5, 0.8), _event(1.0, 1.3)]

        # Act
        vels = estimate_velocities(y, SR, events)
        marks = to_dynamic_marks(vels)

        # Assert: 記号が全ノートに付き、最弱が最強より弱い段階
        assert len(marks) == 3
        assert DYNAMIC_MARKS.index(marks[0]) <= DYNAMIC_MARKS.index(marks[-1])
        assert all(m in DYNAMIC_MARKS for m in marks)
