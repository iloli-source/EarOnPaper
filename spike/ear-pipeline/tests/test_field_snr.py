"""#45 stem SNR推定器の攻撃回帰テスト(func-r1-fable-input S1/S2/S3/S4)。

旧実装はフレームRMSのp10/p90比 = 「無音率検出器」だった:
- S1: 連続純音(クリーン)を snr=0 → very_noisy と誤判定
- S2: 無音ギャップ付きで snr=182dB という物理不能値
本テストは実SNR推定(スペクトル雑音床分離)の挙動を固定する。
"""

import numpy as np
import pytest

from earpipe.services.stem import analyze_field
from tests.test_field_mode import mix_at_snr, white_noise

SR = 22050
_SNR_MAX_DB = 60.0  # 推定器の飽和上限(field.py と同期)


def continuous_tone(dur: float = 2.0, freq: float = 440.0, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t)


def gappy_tone(dur: float = 2.0, freq: float = 440.0, amp: float = 0.3) -> np.ndarray:
    """同エネルギーだが無音ギャップ付き(旧実装で182dBが出た攻撃S2)。"""
    y = continuous_tone(dur, freq, amp)
    n = len(y)
    seg = n // 8
    for k in range(1, 8, 2):  # 交互に無音化
        y[k * seg : (k + 1) * seg] = 0.0
    return y


class TestSnrEstimator:
    def test_s1_continuous_clean_tone_is_clean(self):
        """攻撃S1: クリーン連続純音は very_noisy ではなく clean。"""
        a = analyze_field(continuous_tone(), SR)
        assert a.noise_profile == "clean", f"snr={a.snr_db:.1f} profile={a.noise_profile}"
        assert a.snr_db >= 15.0

    def test_s2_gappy_tone_bounded_and_clean(self):
        """攻撃S2: 無音ギャップは物理不能値を出さない(上限で飽和)。"""
        a = analyze_field(gappy_tone(), SR)
        assert a.snr_db <= _SNR_MAX_DB + 1e-6
        assert a.noise_profile == "clean"

    @pytest.mark.parametrize("true_snr", [20.0, 10.0, 5.0])
    def test_known_snr_tracked_within_tolerance(self, true_snr):
        """既知SNRの混合で推定誤差が許容内(±6dB)。"""
        tone = continuous_tone(dur=3.0)
        mixed = mix_at_snr(tone, white_noise(len(tone)), true_snr)
        a = analyze_field(mixed, SR)
        assert abs(a.snr_db - true_snr) <= 6.0, f"true={true_snr} est={a.snr_db:.1f}"

    def test_known_snr_monotonic(self):
        """SNRを下げるほど推定値も単調に下がる。"""
        tone = continuous_tone(dur=3.0)
        estimates = []
        for snr in (20.0, 10.0, 5.0):
            mixed = mix_at_snr(tone, white_noise(len(tone)), snr)
            estimates.append(analyze_field(mixed, SR).snr_db)
        assert estimates[0] > estimates[1] > estimates[2], estimates

    def test_noise_only_is_very_noisy(self):
        y = white_noise(SR * 2) * 0.3
        a = analyze_field(y, SR)
        assert a.noise_profile == "very_noisy", f"snr={a.snr_db:.1f}"

    def test_s3_nan_input_does_not_crash(self):
        """攻撃S3: NaN混入でクラッシュしない(境界検証)。"""
        y = continuous_tone()
        y[100] = np.nan
        a = analyze_field(y, SR)
        assert np.isfinite(a.snr_db)

    def test_s4_inf_input_does_not_crash(self):
        """攻撃S4: Inf混入でクラッシュしない。"""
        y = continuous_tone()
        y[200] = np.inf
        a = analyze_field(y, SR)
        assert np.isfinite(a.snr_db)
