"""F-059 テンポ変更再生(Issue #107)のユニットテスト。

先行研究(F-059-grok / F-059-codex)の失敗例を回帰で固定する:
- 減速でピッチが動かない(チップマンク事故の回避・grok クラスタE / codex §5)
- 減速で長さが伸びる(rate<1 で 1/rate 倍・ピッチ維持タイムストレッチ)
- アーティファクト注意ゾーン(rate<0.5)を明示判定できる(codex §1・§3)
- A-Bループの継ぎ目でクロスフェードし境界クリックを抑える(codex §6)
- 極端/不正な rate・区間・回数は例外で弾く(誤用防止・grok クラスタA)
"""

import librosa
import numpy as np
import pytest

from earpipe.services.notate.tempo_playback import (
    ARTIFACT_WARNING_RATE,
    is_artifact_prone,
    loop_region,
    time_stretch,
)

_SR = 22050


def _sine(freq_hz: float, dur_sec: float, sr: int = _SR) -> np.ndarray:
    """検証用の単一正弦波(モノラル float32)を生成する。"""
    t = np.arange(int(dur_sec * sr), dtype=np.float32) / sr
    return (0.5 * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)


class TestTimeStretch:
    def test_slowdown_lengthens_audio(self):
        # Arrange
        y = _sine(440.0, 1.0)

        # Act
        slow = time_stretch(y, _SR, 0.5)

        # Assert: 半速なら概ね2倍の長さ(phase vocoder の丸めで完全一致はしない)
        assert slow.size > y.size
        assert abs(slow.size / y.size - 2.0) < 0.1

    def test_speedup_shortens_audio(self):
        # Arrange
        y = _sine(440.0, 1.0)

        # Act
        fast = time_stretch(y, _SR, 2.0)

        # Assert
        assert fast.size < y.size
        assert abs(fast.size / y.size - 0.5) < 0.1

    def test_pitch_is_preserved_on_slowdown(self):
        # Arrange: 440Hz を減速してもピッチ(推定f0)が保たれること
        y = _sine(440.0, 1.0)

        # Act
        slow = time_stretch(y, _SR, 0.5)
        f0_orig = librosa.yin(y, fmin=200, fmax=800, sr=_SR)
        f0_slow = librosa.yin(slow, fmin=200, fmax=800, sr=_SR)

        # Assert: 中央値の周波数が半音(約6%)以内で一致=ピッチ維持
        assert abs(np.median(f0_slow) - np.median(f0_orig)) / 440.0 < 0.06

    def test_rate_one_is_identity_copy(self):
        # Arrange
        y = _sine(330.0, 0.3)

        # Act
        out = time_stretch(y, _SR, 1.0)

        # Assert: 値は同一だが別配列(入力を破壊しない)
        assert np.array_equal(out, y)
        assert out is not y

    def test_does_not_mutate_input(self):
        # Arrange
        y = _sine(440.0, 0.5)
        before = y.copy()

        # Act
        time_stretch(y, _SR, 0.7)

        # Assert
        assert np.array_equal(y, before)

    @pytest.mark.parametrize("bad_rate", [0.0, -1.0, 0.1, 10.0, float("nan"), float("inf")])
    def test_rejects_out_of_range_rate(self, bad_rate):
        # Arrange
        y = _sine(440.0, 0.2)

        # Act / Assert
        with pytest.raises(ValueError):
            time_stretch(y, _SR, bad_rate)

    def test_rejects_non_ndarray(self):
        # Act / Assert
        with pytest.raises(TypeError):
            time_stretch([0.0, 1.0, 0.0], _SR, 0.5)

    def test_rejects_empty_and_multichannel(self):
        # Act / Assert
        with pytest.raises(ValueError):
            time_stretch(np.array([], dtype=np.float32), _SR, 0.5)
        with pytest.raises(ValueError):
            time_stretch(np.zeros((2, 100), dtype=np.float32), _SR, 0.5)

    def test_rejects_non_positive_sr(self):
        # Arrange
        y = _sine(440.0, 0.2)

        # Act / Assert
        with pytest.raises(ValueError):
            time_stretch(y, 0, 0.5)


class TestArtifactWarning:
    def test_strong_slowdown_is_flagged(self):
        # 0.5 未満の強い減速は transient smearing が顕著=注意(codex §1・§3)
        assert is_artifact_prone(0.4) is True
        assert is_artifact_prone(ARTIFACT_WARNING_RATE - 0.01) is True

    def test_mild_slowdown_is_not_flagged(self):
        # 実務スイートスポット(0.70〜0.85 付近)は注意ゾーン外(grok クラスタI)
        assert is_artifact_prone(0.8) is False
        assert is_artifact_prone(1.0) is False


class TestLoopRegion:
    def test_single_time_returns_the_segment(self):
        # Arrange
        y = _sine(440.0, 1.0)

        # Act: 0.2〜0.6 秒を1回
        out = loop_region(y, _SR, 0.2, 0.6, 1)

        # Assert: 区間長ぶんのサンプル、かつ入力の部分列と一致
        start, end = int(round(0.2 * _SR)), int(round(0.6 * _SR))
        assert np.array_equal(out, y[start:end])

    def test_repeat_length_matches_crossfade_model(self):
        # Arrange
        y = _sine(440.0, 1.0)
        start, end, times = 0.2, 0.6, 3
        seg_len = int(round(end * _SR)) - int(round(start * _SR))
        fade = min(int(round(0.005 * _SR)), seg_len // 2)

        # Act
        out = loop_region(y, _SR, start, end, times)

        # Assert: 継ぎ目でのみ fade 分だけ短縮される長さモデル
        expected = times * seg_len - (times - 1) * fade
        assert out.size == expected

    def test_crossfade_suppresses_boundary_discontinuity(self):
        # Arrange: 末尾 +0.9 / 先頭 -0.9 と段差のある区間を作る。素朴連結だと
        # 継ぎ目でサンプルが +0.9→-0.9 と飛び、これがクリックの正体(codex §6)。
        sr = 1000
        n = 400
        seg = np.linspace(0.9, -0.9, n, dtype=np.float32)  # 末尾-先頭に大きな段差
        y = np.tile(seg, 3).astype(np.float32)             # 区間を取り出せる長さの音源
        start, end, times = 0.0, n / sr, 4

        # Act
        looped = loop_region(y, sr, start, end, times)
        naive = np.tile(seg, times)

        # Assert: クロスフェード後の継ぎ目付近の最大サンプル飛びが、
        # 素朴連結の段差(約1.8)より明確に小さい=クリックが抑えられている
        smooth_jump = float(np.max(np.abs(np.diff(looped))))
        naive_jump = float(np.max(np.abs(np.diff(naive))))
        assert naive_jump > 1.5           # 素朴連結には大きな段差が存在する
        assert smooth_jump < naive_jump * 0.5  # クロスフェードで半分未満に抑制

    def test_does_not_mutate_input(self):
        # Arrange
        y = _sine(440.0, 0.8)
        before = y.copy()

        # Act
        loop_region(y, _SR, 0.1, 0.5, 3)

        # Assert
        assert np.array_equal(y, before)

    def test_rejects_reversed_or_out_of_bounds_region(self):
        # Arrange
        y = _sine(440.0, 0.5)

        # Act / Assert
        with pytest.raises(ValueError):
            loop_region(y, _SR, 0.4, 0.2, 2)   # 逆順
        with pytest.raises(ValueError):
            loop_region(y, _SR, 0.1, 5.0, 2)   # 範囲外(音源長超え)
        with pytest.raises(ValueError):
            loop_region(y, _SR, -0.1, 0.2, 2)  # 負の開始

    def test_rejects_bad_times(self):
        # Arrange
        y = _sine(440.0, 0.5)

        # Act / Assert
        with pytest.raises(ValueError):
            loop_region(y, _SR, 0.1, 0.3, 0)
        with pytest.raises(TypeError):
            loop_region(y, _SR, 0.1, 0.3, 2.5)

    def test_rejects_non_ndarray(self):
        # Act / Assert
        with pytest.raises(TypeError):
            loop_region([0.0, 1.0], _SR, 0.0, 0.1, 2)
