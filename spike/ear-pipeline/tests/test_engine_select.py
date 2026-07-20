"""mono/poly エンジン自動選択(Issue #64)のテスト。

著作物音源に依存しないよう、合成波形(単一正弦=単旋律 / 複数正弦の同時発音=多声)で
ポリフォニー推定と選択ロジックを検証する。
"""

import numpy as np
import pytest

from earpipe.contracts import PitchEvent
from earpipe.services.ear.engine_select import (
    POLY_MIN,
    EngineChoice,
    choose_engine,
    estimate_polyphony,
)

SR = 22050
DUR = 2.0


def _sine(freq: float, sr: int = SR, dur: float = DUR) -> np.ndarray:
    t = np.linspace(0.0, dur, int(sr * dur), endpoint=False)
    return np.sin(2.0 * np.pi * freq * t)


def _mono_signal() -> np.ndarray:
    """単旋律相当: 単一正弦(基音のみ)。"""
    return _sine(440.0)


def _poly_signal() -> np.ndarray:
    """多声相当: 倍音関係にない6基音の同時発音。"""
    freqs = [261.6, 311.1, 392.0, 466.2, 587.3, 698.5]  # C4,Eb4,G4,Bb4,D5,F5
    y = np.zeros(int(SR * DUR))
    for f in freqs:
        y += _sine(f)
    return y / len(freqs)


class TestEstimatePolyphony:
    def test_single_sine_is_low(self):
        # Arrange
        y = _mono_signal()
        # Act
        p = estimate_polyphony(y, SR)
        # Assert
        assert p < POLY_MIN

    def test_dense_chord_is_high(self):
        # Arrange
        y = _poly_signal()
        # Act
        p = estimate_polyphony(y, SR)
        # Assert
        assert p >= POLY_MIN

    def test_silence_returns_zero(self):
        assert estimate_polyphony(np.zeros(SR), SR) == 0.0

    def test_noise_routes_to_mono_not_poly(self):
        # Arrange — 白色ノイズ。広帯域で多声と誤判定されやすいが音符化してはいけない
        rng = np.random.default_rng(0)
        noise = rng.standard_normal(int(SR * DUR))
        # Act — polyが使える環境でもノイズは mono に固定される(非調波ゲート)
        choice = choose_engine(noise, SR, mono_events=[], poly_available=True)
        # Assert
        assert choice.engine == "mono"
        assert "ノイズ" in choice.reason

    def test_mono_less_than_poly(self):
        assert estimate_polyphony(_mono_signal(), SR) < estimate_polyphony(_poly_signal(), SR)


class TestChooseEngine:
    def test_monophonic_selects_mono(self):
        # Arrange
        y = _mono_signal()
        # Act
        choice = choose_engine(y, SR, mono_events=None, poly_available=True)
        # Assert
        assert isinstance(choice, EngineChoice)
        assert choice.engine == "mono"
        assert not choice.fell_back

    def test_polyphonic_selects_poly_when_available(self):
        # Arrange
        y = _poly_signal()
        # Act
        choice = choose_engine(y, SR, mono_events=None, poly_available=True)
        # Assert
        assert choice.engine == "poly"
        assert not choice.fell_back

    def test_polyphonic_falls_back_to_mono_when_poly_unavailable(self):
        # Arrange
        y = _poly_signal()
        # Act
        choice = choose_engine(y, SR, mono_events=None, poly_available=False)
        # Assert — poly不能なら正直にmonoへ退避し、その旨を記録する
        assert choice.engine == "mono"
        assert choice.fell_back
        assert "basic-pitch" in choice.reason

    def test_low_mono_coverage_escalates_to_poly(self):
        # Arrange — ポリフォニーは低いが、有音なのにmonoがほぼ拾えない(取りこぼし)ケース
        y = _sine(220.0)  # エネルギーはあるが mono_events を空で渡す
        # Act
        choice = choose_engine(y, SR, mono_events=[], poly_available=True)
        # Assert
        assert choice.engine == "poly"
        assert choice.mono_coverage < 0.15

    def test_good_mono_coverage_stays_mono(self):
        # Arrange — 単旋律で mono が音源をよく覆っている
        y = _sine(220.0)
        events = [PitchEvent(onset=0.0, offset=DUR, midi=57, confidence=0.9)]
        # Act
        choice = choose_engine(y, SR, mono_events=events, poly_available=True)
        # Assert
        assert choice.engine == "mono"
        assert choice.mono_coverage >= 0.15
