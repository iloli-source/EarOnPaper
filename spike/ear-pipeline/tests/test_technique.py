"""F-078(Issue #73) detect_techniques の合成f0による受入テスト(AAA形式)。

各奏法を1本ずつ合成f0で用意し、kind・上行/下行・区間境界・confidence範囲を検証。
実装の正直な限界(bend/slideの曖昧さ等)は過信しない範囲で固定する。
"""

from __future__ import annotations

import numpy as np

from earpipe.services.notate.technique import (
    LEAP_MAX_DUR_SEC,
    Technique,
    detect_techniques,
)

# 合成に使う共通の分析フレームレート(Hz)。100フレーム/秒。
FRAME_RATE_HZ = 100.0


def _times(n: int) -> np.ndarray:
    """n点・等間隔(FRAME_RATE_HZ)の時刻軸を作る。"""
    return np.arange(n, dtype=np.float64) / FRAME_RATE_HZ


def _hz_from_cents(cents: np.ndarray, ref_hz: float = 440.0) -> np.ndarray:
    """centオフセット列を基準周波数refからのHz列へ戻す。"""
    return ref_hz * 2.0 ** (cents / 1200.0)


class TestGlide:
    def test_ascending_ramp_is_glide_upward(self):
        # Arrange: 0.5秒で0→300cents(3半音)へ直線上昇するグライド。
        n = 50
        t = _times(n)
        cents = np.linspace(0.0, 300.0, n)
        f0 = _hz_from_cents(cents)

        # Act
        techs = detect_techniques(t, f0)

        # Assert: bend/slideのいずれかが1件、区間境界が入力端に一致。
        glides = [x for x in techs if x.kind in ("bend", "slide")]
        assert len(glides) == 1
        g = glides[0]
        assert g.kind in ("bend", "slide")
        assert g.onset_sec == t[0]
        assert g.offset_sec == t[-1]
        assert 0.0 <= g.confidence <= 1.0

    def test_descending_ramp_is_glide(self):
        # Arrange: 0→-250cents へ下降する連続グライド。
        n = 50
        t = _times(n)
        cents = np.linspace(0.0, -250.0, n)
        f0 = _hz_from_cents(cents)

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        glides = [x for x in techs if x.kind in ("bend", "slide")]
        assert len(glides) == 1
        assert 0.0 <= glides[0].confidence <= 1.0

    def test_bend_holds_after_reaching_target(self):
        # Arrange: 上昇後に定常保持(=bend寄り)。前半上昇、後半フラット。
        t = _times(60)
        rise = np.linspace(0.0, 200.0, 30)
        hold = np.full(30, 200.0)
        f0 = _hz_from_cents(np.concatenate([rise, hold]))

        # Act
        techs = detect_techniques(t, f0)

        # Assert: 到達後定常のためbendに寄る。
        glides = [x for x in techs if x.kind in ("bend", "slide")]
        assert len(glides) == 1
        assert glides[0].kind == "bend"


class TestVibrato:
    def test_sinusoidal_modulation_is_vibrato(self):
        # Arrange: 6Hz・±40cents(peak-to-peak80cents)の正弦変調を1秒。
        n = 100
        t = _times(n)
        cents = 40.0 * np.sin(2 * np.pi * 6.0 * t)
        f0 = _hz_from_cents(cents)

        # Act
        techs = detect_techniques(t, f0)

        # Assert: vibratoが検出され、区間・confidence範囲が妥当。
        vibs = [x for x in techs if x.kind == "vibrato"]
        assert len(vibs) == 1
        v = vibs[0]
        assert v.onset_sec == t[0]
        assert v.offset_sec == t[-1]
        assert 0.0 <= v.confidence <= 1.0

    def test_slow_wide_swing_not_vibrato(self):
        # Arrange: 1Hz(帯域外)のゆっくりした揺れはvibratoにしない。
        n = 100
        t = _times(n)
        cents = 60.0 * np.sin(2 * np.pi * 1.0 * t)
        f0 = _hz_from_cents(cents)

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        assert [x for x in techs if x.kind == "vibrato"] == []


class TestLeap:
    def _stair(self, low_c: float, high_c: float) -> tuple[np.ndarray, np.ndarray]:
        """1フレームで low_c→high_c へ跳ぶ階段状f0(再アタック無し)を作る。"""
        seg = 20
        t = _times(seg * 2)
        cents = np.concatenate([np.full(seg, low_c), np.full(seg, high_c)])
        return t, _hz_from_cents(cents)

    def test_step_up_is_hammer_on(self):
        # Arrange: 0→200cents(2半音)の離散上行ジャンプ。
        t, f0 = self._stair(0.0, 200.0)

        # Act
        techs = detect_techniques(t, f0)

        # Assert: hammer_onが1件、境界秒が跳躍点周辺、confidence範囲内。
        leaps = [x for x in techs if x.kind in ("hammer_on", "pull_off")]
        assert len(leaps) == 1
        assert leaps[0].kind == "hammer_on"
        assert leaps[0].offset_sec - leaps[0].onset_sec <= LEAP_MAX_DUR_SEC + 1e-9
        assert 0.0 <= leaps[0].confidence <= 1.0

    def test_step_down_is_pull_off(self):
        # Arrange: 0→-200cents の離散下行ジャンプ。
        t, f0 = self._stair(0.0, -200.0)

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        leaps = [x for x in techs if x.kind in ("hammer_on", "pull_off")]
        assert len(leaps) == 1
        assert leaps[0].kind == "pull_off"

    def test_leap_over_physical_limit_not_detected(self):
        # Arrange: 500cents(5半音, 物理限界超)の段差は跳躍としない。
        t, f0 = self._stair(0.0, 500.0)

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        assert [x for x in techs if x.kind in ("hammer_on", "pull_off")] == []


class TestNegativeAndBoundaries:
    def test_steady_tone_yields_nothing(self):
        # Arrange: 完全な定常音(揺れも遷移も無し)。
        n = 100
        t = _times(n)
        f0 = _hz_from_cents(np.zeros(n))

        # Act
        techs = detect_techniques(t, f0)

        # Assert: 何も検出しない。
        assert techs == []

    def test_nan_gap_splits_two_notes(self):
        # Arrange: 有声0.3秒 → 無声0.2秒(NaN) → 有声0.3秒 の2音。
        seg = 30
        gap = 20
        t = _times(seg * 2 + gap)
        voiced = np.zeros(seg)
        f0 = np.concatenate([
            _hz_from_cents(voiced),
            np.full(gap, np.nan),
            _hz_from_cents(voiced),
        ])

        # Act: 定常2音なので奏法は出ないが、NaN境界で例外なく処理されること。
        techs = detect_techniques(t, f0)

        # Assert
        assert techs == []
        assert all(isinstance(x, Technique) for x in techs)

    def test_empty_array_returns_empty(self):
        # Arrange
        t = np.array([], dtype=np.float64)
        f0 = np.array([], dtype=np.float64)

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        assert techs == []

    def test_all_nan_returns_empty(self):
        # Arrange
        n = 50
        t = _times(n)
        f0 = np.full(n, np.nan)

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        assert techs == []

    def test_too_short_segment_returns_empty(self):
        # Arrange: 0.05秒(MIN_SEG_SEC未満)のグライドは破棄される。
        n = 5
        t = _times(n)
        f0 = _hz_from_cents(np.linspace(0.0, 300.0, n))

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        assert techs == []

    def test_mismatched_lengths_returns_empty(self):
        # Arrange: times と f0 の長さ不一致(頑健性)。
        t = _times(10)
        f0 = _hz_from_cents(np.zeros(8))

        # Act
        techs = detect_techniques(t, f0)

        # Assert
        assert techs == []

    def test_octave_spike_is_ignored(self):
        # Arrange: 定常音の途中に1フレームだけ+1200centsのオクターブ誤り。
        n = 60
        t = _times(n)
        cents = np.zeros(n)
        cents[30] = 1200.0
        f0 = _hz_from_cents(cents)

        # Act: スパイクは境界化されて偽のhammer/大bendを生まない。
        techs = detect_techniques(t, f0)

        # Assert
        assert techs == []

    def test_confidence_always_in_unit_range(self):
        # Arrange: 複数奏法が混在する信号(グライド→跳躍)。
        t = _times(80)
        cents = np.concatenate([np.linspace(0.0, 200.0, 40), np.full(40, 400.0)])
        f0 = _hz_from_cents(cents)

        # Act
        techs = detect_techniques(t, f0)

        # Assert: すべてのconfidenceが0-1に収まる。
        assert all(0.0 <= x.confidence <= 1.0 for x in techs)
