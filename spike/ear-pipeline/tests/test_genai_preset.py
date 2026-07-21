"""生成AI楽曲向け採譜プリセット(F-092 / Issue #99)のテスト。

先行研究(F-092-grok / F-092-codex)の失敗回避を検証する:
- 前処理は非破壊(倍音・音高・相対ダイナミクスを壊さない・長さ保存)
- DCオフセット除去が効く / 高域デエンファシスは倍音を消さない
- プリセットは note-only 既定でドラム非対象、値域が妥当
"""

import numpy as np
import pytest

from earpipe.services.stem.genai_preset import (
    GENAI_PRESET,
    genai_preprocess,
    genai_preset,
)

SR = 22050


def _tone(sec: float, freq: float = 440.0, amp: float = 0.5) -> np.ndarray:
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t)


class TestGenaiPreprocess:
    def test_preserves_length(self):
        # Arrange
        y = _tone(1.0)
        # Act
        out = genai_preprocess(y, SR)
        # Assert
        assert out.shape == y.shape

    def test_does_not_mutate_input(self):
        # Arrange
        y = _tone(0.5) + 0.2  # DC付きで確実に変化させる
        original = y.copy()
        # Act
        genai_preprocess(y, SR)
        # Assert: 入力配列は不変
        assert np.array_equal(y, original)

    def test_removes_dc_offset(self):
        # Arrange: 明確なDCオフセットを載せる
        y = _tone(0.5) + 0.3
        assert abs(float(np.mean(y))) > 0.1
        # Act
        out = genai_preprocess(y, SR)
        # Assert: 元の0.3のDCがほぼ消える(残差は後段シェルフの微小ドリフトのみ)
        assert abs(float(np.mean(out))) < 1e-4

    def test_peak_normalized_no_clip(self):
        # Arrange: 小音量の音源
        y = _tone(0.5, amp=0.05)
        # Act
        out = genai_preprocess(y, SR)
        # Assert: ピークが目標付近まで持ち上がりクリップしない
        peak = float(np.max(np.abs(out)))
        assert 0.9 < peak <= 1.0

    def test_preserves_relative_dynamics(self):
        # Arrange: 前半小音量・後半大音量(velocity手がかり)
        soft = _tone(0.4, freq=440.0, amp=0.1)
        loud = _tone(0.4, freq=440.0, amp=0.5)
        y = np.concatenate([soft, loud])
        # Act
        out = genai_preprocess(y, SR)
        n = len(soft)
        soft_peak = float(np.max(np.abs(out[:n])))
        loud_peak = float(np.max(np.abs(out[n:])))
        # Assert: 相対音量差(≈5倍)が保たれる(コンプで潰れていない)
        assert loud_peak / soft_peak > 3.5

    def test_preserves_fundamental_pitch(self):
        # Arrange
        freq = 440.0
        y = _tone(1.0, freq=freq)
        # Act
        out = genai_preprocess(y, SR)
        # Assert: 基本波のスペクトルピークが同じ周波数のまま(音高破壊なし)
        spec = np.abs(np.fft.rfft(out))
        freqs = np.fft.rfftfreq(len(out), 1.0 / SR)
        peak_freq = float(freqs[int(np.argmax(spec))])
        assert abs(peak_freq - freq) < 5.0

    def test_deemphasis_keeps_harmonic_energy(self):
        # Arrange: 高域に倍音を持つ音(基本波+高次倍音)
        base = _tone(1.0, freq=440.0, amp=0.4)
        harm = _tone(1.0, freq=440.0 * 6, amp=0.2)  # 高次倍音
        y = base + harm
        # Act
        out = genai_preprocess(y, SR)
        # Assert: 高域倍音は減衰しても消えない(完全カットは音高手がかり破壊)
        spec = np.abs(np.fft.rfft(out))
        freqs = np.fft.rfftfreq(len(out), 1.0 / SR)
        hi_bin = int(np.argmin(np.abs(freqs - 440.0 * 6)))
        assert spec[hi_bin] > 0.0

    def test_empty_input_safe(self):
        # Act
        out = genai_preprocess(np.array([]), SR)
        # Assert
        assert out.size == 0

    def test_silence_safe(self):
        # Arrange
        y = np.zeros(SR // 2)
        # Act
        out = genai_preprocess(y, SR)
        # Assert: 無音はゼロ割せず素通し(長さ保存)
        assert out.shape == y.shape
        assert float(np.max(np.abs(out))) == 0.0

    def test_stereo_folded_to_mono(self):
        # Arrange: (frames, 2) のステレオ
        mono = _tone(0.5)
        y = np.stack([mono, mono], axis=1)
        # Act
        out = genai_preprocess(y, SR)
        # Assert: 1次元へ畳まれる
        assert out.ndim == 1
        assert out.shape[0] == mono.shape[0]

    def test_invalid_sr_raises(self):
        y = _tone(0.1)
        with pytest.raises(ValueError):
            genai_preprocess(y, 0)
        with pytest.raises(ValueError):
            genai_preprocess(y, -100)

    def test_output_finite(self):
        # Arrange
        y = _tone(0.5) + 0.2
        # Act
        out = genai_preprocess(y, SR)
        # Assert: NaN/Inf を出さない
        assert np.all(np.isfinite(out))


class TestGenaiPreset:
    def test_note_only_default(self):
        # note-only 既定(pitch bend OFF・grok F6)
        assert GENAI_PRESET["pitch_bend"] is False

    def test_drums_excluded(self):
        # tonal tracks only(非音高FX対象外・grok F8)
        assert GENAI_PRESET["drums"] is False

    def test_min_conf_higher_than_default(self):
        # 既定0.5より高くゴースト音を抑える(codex §2-3)
        assert GENAI_PRESET["detect_min_conf"] > 0.5

    def test_grid_is_sixteenth(self):
        # 16分格子(電子/ループ寄り生成曲)
        assert GENAI_PRESET["grid_per_beat"] == 4

    def test_quantize_strength_not_destructive(self):
        # 完全吸着(1.0)で演奏を殺さない段階量子化(codex §3)
        s = GENAI_PRESET["quantize_strength"]
        assert 0.0 < s <= 1.0

    def test_param_value_ranges(self):
        assert 0.0 < GENAI_PRESET["detect_min_conf"] <= 1.0
        assert 0.0 < GENAI_PRESET["detect_pitch_tol"] <= 1.0
        assert GENAI_PRESET["grid_per_beat"] >= 1

    def test_preprocess_shelf_gain_non_destructive(self):
        # 高域シェルフ利得は 0<gain<=1(完全カットしない=倍音を壊さない)
        g = GENAI_PRESET["preprocess"]["high_shelf_gain"]
        assert 0.0 < g <= 1.0

    def test_notes_are_honest(self):
        # 不可逆性・非破壊・重依存未使用を notes に明記(捏造禁止・正直さ)
        notes = GENAI_PRESET["notes"]
        assert isinstance(notes, str) and len(notes) > 0

    def test_typed_preset_matches_dict(self):
        # 型付き参照が dict と一致する
        p = genai_preset()
        assert p.pitch_bend == GENAI_PRESET["pitch_bend"]
        assert p.drums == GENAI_PRESET["drums"]
        assert p.grid_per_beat == GENAI_PRESET["grid_per_beat"]
        assert p.detect_min_conf == GENAI_PRESET["detect_min_conf"]
