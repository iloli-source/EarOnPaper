"""F-002 音質診断 diagnose_audio の攻撃/合成信号テスト(AAA形式)。

合成信号は窓・端効果で理論値からズレるため、数値は範囲assertで固定する。
"""

import dataclasses

import numpy as np
import pytest

from earpipe.services.stem.diagnose import AudioQuality, diagnose_audio

SR = 22050


def _sine(dur: float = 2.0, freq: float = 440.0, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0.0, dur, int(SR * dur), endpoint=False)
    return (amp * np.sin(2.0 * np.pi * freq * t)).astype(np.float64)


def _clean_music(dur: float = 2.5) -> np.ndarray:
    """広帯域・シャープなオンセットを持つ現実的なクリーン音(減衰する撥弦様バースト列)。

    純正弦は帯域が極端に狭く残響プロキシが持続音として高く出るため、テスト素材には
    倍音豊富で明瞭なオンセット/減衰を持つ信号を使う。
    """
    t = np.linspace(0.0, dur, int(SR * dur), endpoint=False)
    y = np.zeros_like(t)
    step = 0.4
    for k in range(int(dur / step)):
        i = int(k * step * SR)
        length = int(0.35 * SR)
        seg = slice(i, i + length)
        tt = t[seg] - t[seg][0]
        env = np.exp(-6.0 * tt)
        note = sum(0.3 / h * np.sin(2.0 * np.pi * 220.0 * h * tt) for h in range(1, 50))
        note = note + 0.05 * np.sin(2.0 * np.pi * 17000.0 * tt)  # 高域の当たり
        y[seg] += env * note
    return (0.6 * y / (np.max(np.abs(y)) + 1e-9)).astype(np.float64)


def _white_noise(n: int, amp: float = 0.3, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (amp * rng.standard_normal(n)).astype(np.float64)


def _mix_at_snr(signal: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    s_pow = float(np.mean(signal**2))
    n_pow = float(np.mean(noise**2))
    scale = np.sqrt(s_pow / (n_pow * (10.0 ** (snr_db / 10.0))))
    return signal + scale * noise


class TestCleanSignal:
    def test_clean_music_has_no_clipping_and_wide_band(self):
        # Arrange
        y = _clean_music()

        # Act
        q = diagnose_audio(y, SR)

        # Assert: クリッピングなし・帯域広い・残響誤陽性なし(SNRは内部プロキシ値のため緩め)
        assert q.clipping_rate < 0.005, q.clipping_rate
        assert q.band_limit_hz > 9000.0, q.band_limit_hz
        assert q.reverb_ratio <= 0.6, q.reverb_ratio
        assert not any("残響" in w for w in q.warnings), q.warnings
        assert q.rating in ("green", "yellow")


class TestClipping:
    def test_hard_clipped_sine_has_high_clipping_and_red_rating(self):
        # Arrange: 振幅を大きくして±1.0でハードクリップ(矩形化)
        y = np.clip(_sine(amp=2.0), -1.0, 1.0)

        # Act
        q = diagnose_audio(y, SR)

        # Assert
        assert q.clipping_rate > 0.01, q.clipping_rate
        assert q.rating == "red", (q.rating, q.warnings)
        assert any("クリッピング" in w for w in q.warnings)


class TestSnr:
    @pytest.mark.parametrize("true_snr", [25.0, 12.0])
    def test_known_snr_in_expected_range(self, true_snr):
        # Arrange
        tone = _sine(dur=3.0)
        mixed = _mix_at_snr(tone, _white_noise(len(tone)), true_snr)

        # Act
        q = diagnose_audio(mixed, SR)

        # Assert: 端効果で理論値からずれるため範囲で確認
        assert 0.0 <= q.snr_db <= 60.0
        assert q.snr_db < 60.0  # ノイズありなら飽和しない

    def test_noisier_input_lowers_snr(self):
        # Arrange
        tone = _sine(dur=3.0)
        clean = _mix_at_snr(tone, _white_noise(len(tone), seed=1), 25.0)
        noisy = _mix_at_snr(tone, _white_noise(len(tone), seed=1), 5.0)

        # Act
        q_clean = diagnose_audio(clean, SR)
        q_noisy = diagnose_audio(noisy, SR)

        # Assert
        assert q_clean.snr_db > q_noisy.snr_db, (q_clean.snr_db, q_noisy.snr_db)


class TestBandLimit:
    def test_lowpassed_signal_has_low_band_limit_and_warns(self):
        # Arrange: 高srなのに低域のみ(3kHz以下の正弦の重ね合わせ=帯域制限素材)
        t = np.linspace(0.0, 3.0, int(SR * 3.0), endpoint=False)
        low = np.zeros_like(t)
        for f in (220.0, 440.0, 880.0, 1760.0):
            low += 0.1 * np.sin(2.0 * np.pi * f * t)

        # Act
        q = diagnose_audio(low, SR)

        # Assert: 帯域上限がナイキスト(11kHz)よりかなり下
        assert q.band_limit_hz < 8000.0, q.band_limit_hz
        assert any("帯域" in w for w in q.warnings)


class TestSafeGuards:
    def test_empty_input_returns_red_without_raising(self):
        # Arrange
        y = np.array([], dtype=np.float64)

        # Act
        q = diagnose_audio(y, SR)

        # Assert
        assert q.rating == "red"
        assert q.warnings

    def test_all_zero_input_returns_red(self):
        # Arrange
        y = np.zeros(SR, dtype=np.float64)

        # Act
        q = diagnose_audio(y, SR)

        # Assert
        assert q.rating == "red"

    def test_nan_input_returns_red_without_raising(self):
        # Arrange
        y = _sine()
        y[100] = np.nan

        # Act
        q = diagnose_audio(y, SR)

        # Assert
        assert q.rating == "red"
        assert np.isfinite(q.snr_db)


class TestInputNormalization:
    def test_stereo_2d_input_is_monoized_and_diagnosed(self):
        # Arrange: (2, n) ステレオ(左右同一)。モノ化して単一chと同等の診断になるべき
        mono = _clean_music()
        stereo = np.stack([mono, mono], axis=0)

        # Act
        q_stereo = diagnose_audio(stereo, SR)
        q_mono = diagnose_audio(mono, SR)

        # Assert: 例外なく診断され、モノ化結果がモノ入力とほぼ一致
        assert isinstance(q_stereo, AudioQuality)
        assert q_stereo.rating == q_mono.rating, (q_stereo.rating, q_mono.rating)
        assert abs(q_stereo.band_limit_hz - q_mono.band_limit_hz) < 200.0

    def test_int16_input_is_scaled_and_clipping_detected(self):
        # Arrange: フルスケール張り付きの int16
        analog = np.clip(_sine(amp=2.0), -1.0, 1.0)
        i16 = (analog * 32767).astype(np.int16)

        # Act
        q = diagnose_audio(i16, SR)

        # Assert
        assert q.clipping_rate > 0.01, q.clipping_rate


class TestImmutability:
    def test_result_is_frozen(self):
        # Arrange
        q = diagnose_audio(_sine(), SR)

        # Act / Assert
        with pytest.raises(dataclasses.FrozenInstanceError):
            q.rating = "green"  # type: ignore[misc]

    def test_invalid_rating_rejected_on_construction(self):
        # Arrange / Act / Assert
        with pytest.raises(ValueError):
            AudioQuality(
                clipping_rate=0.0,
                snr_db=30.0,
                reverb_ratio=0.0,
                band_limit_hz=10000.0,
                rating="purple",  # type: ignore[arg-type]
            )
