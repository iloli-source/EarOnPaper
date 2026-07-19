"""#51 stem R2-P0の攻撃回帰テスト(func-r2-input R2-S1)。

R1修正(#45)の雑音床推定「全ビン中央値」は白色雑音専用だった:
- 褐色雑音はエネルギーが低域ビンに集中し大半のビンが静か
  → ビン中央値≈0 → 雑音床を激しく過小評価
  → 純褐色雑音(信号ゼロ)を est_snr=44dB / clean と誤報(R2実測)。
実環境の雑音(空調・交通・ハム・残響尾)はほぼ全て低域偏重=有色であり、
白色専用の推定器は実環境で降噪の起動判断を誤る。

本テストは有色雑音(ピンク/褐色)でも雑音床が成立することを固定する。
"""

import numpy as np
import pytest

from earpipe.services.stem import analyze_field
from tests.test_field_mode import mix_at_snr, white_noise
from tests.test_field_snr import continuous_tone

SR = 22050
_SNR_NOISY_DB = 10.0  # field.py の noisy/very_noisy 境界と同期


def _colored_noise(n: int, exponent: float, seed: int = 7) -> np.ndarray:
    """1/f^exponent 雑音をFFT整形で生成(exponent: 1=ピンク, 2=褐色)。"""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / SR)
    # DCを除き 1/f^(exponent/2) を振幅に適用(パワーで1/f^exponent)
    scale = np.ones_like(freqs)
    scale[1:] = freqs[1:] ** (-exponent / 2.0)
    scale[0] = 0.0
    y = np.fft.irfft(spec * scale, n=n)
    return (y / (np.max(np.abs(y)) + 1e-12) * 0.3).astype(np.float64)


def pink_noise(n: int, seed: int = 7) -> np.ndarray:
    return _colored_noise(n, exponent=1.0, seed=seed)


def brown_noise(n: int, seed: int = 7) -> np.ndarray:
    return _colored_noise(n, exponent=2.0, seed=seed)


class TestPureColoredNoise:
    """攻撃R2-S1の核心: 信号ゼロの純雑音を clean と誤報しない。"""

    def test_pure_brown_noise_is_not_clean(self):
        a = analyze_field(brown_noise(SR * 2), SR)
        assert a.noise_profile != "clean", f"純褐色雑音がclean誤報: snr={a.snr_db:.1f}"
        assert a.snr_db <= _SNR_NOISY_DB, f"純雑音のsnrが高すぎ: {a.snr_db:.1f}"

    def test_pure_pink_noise_is_not_clean(self):
        a = analyze_field(pink_noise(SR * 2), SR)
        assert a.noise_profile != "clean", f"純ピンク雑音がclean誤報: snr={a.snr_db:.1f}"
        assert a.snr_db <= _SNR_NOISY_DB, f"純雑音のsnrが高すぎ: {a.snr_db:.1f}"

    def test_pure_white_noise_regression(self):
        """R1から効いていた白色は退行しない。"""
        a = analyze_field(white_noise(SR * 2) * 0.3, SR)
        assert a.noise_profile != "clean"
        assert a.snr_db <= _SNR_NOISY_DB


class TestColoredKnownSnr:
    """既知SNRの有色混合でも推定誤差±6dB(白色と同じ受入条件)。"""

    @pytest.mark.parametrize("true_snr", [20.0, 10.0, 5.0])
    def test_pink_mix_tracked(self, true_snr):
        tone = continuous_tone(dur=3.0)
        mixed = mix_at_snr(tone, pink_noise(len(tone)), true_snr)
        a = analyze_field(mixed, SR)
        assert abs(a.snr_db - true_snr) <= 6.0, f"pink true={true_snr} est={a.snr_db:.1f}"

    @pytest.mark.parametrize("true_snr", [20.0, 10.0, 5.0])
    def test_brown_mix_tracked(self, true_snr):
        tone = continuous_tone(dur=3.0)
        mixed = mix_at_snr(tone, brown_noise(len(tone)), true_snr)
        a = analyze_field(mixed, SR)
        assert abs(a.snr_db - true_snr) <= 6.0, f"brown true={true_snr} est={a.snr_db:.1f}"

    def test_brown_monotonic(self):
        """褐色でもSNRを下げるほど推定値が単調に下がる。"""
        tone = continuous_tone(dur=3.0)
        estimates = []
        for snr in (20.0, 10.0, 5.0):
            mixed = mix_at_snr(tone, brown_noise(len(tone)), snr)
            estimates.append(analyze_field(mixed, SR).snr_db)
        assert estimates[0] > estimates[1] > estimates[2], f"非単調: {estimates}"


class TestCleanRegression:
    """クリーン純音の判定はR1のまま退行しない。"""

    def test_clean_tone_stays_clean(self):
        a = analyze_field(continuous_tone(), SR)
        assert a.noise_profile == "clean"
        assert a.snr_db >= 15.0
