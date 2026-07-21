"""共有用ビジュアルカード(visual_card.py / F-109 Issue #93)のテスト。

波形+抽出音符を重畳したSNS共有用PNGを端末内生成する機能を検証する。
描画系は「PNGが生成され再読込でファイルが妥当(固定比率・非空・PNG署名)」までを見る
(OCR/目視は親が別途)。研究(F-109-grok/codex)の失敗例に対応する挙動も検証する。
"""

from pathlib import Path

import numpy as np
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.visual_card import (
    CARD_H,
    CARD_W,
    CardLayout,
    card_layout,
    downsample_peaks,
    render_visual_card,
)


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


def sine(freq: float, dur: float, sr: int = 22050, amp: float = 0.5) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _png_dimensions(path: Path) -> tuple[int, int]:
    """PILでPNGを再読込し (width, height) を返す(ファイル妥当性の検証)。"""
    from PIL import Image

    with Image.open(path) as im:
        im.load()  # 実デコードして破損していないことを保証
        return im.size


# ============================ downsample_peaks ============================


class TestDownsamplePeaks:
    def test_returns_requested_length(self):
        # Arrange
        y = sine(440, 1.0)
        # Act
        peaks = downsample_peaks(y, n_peaks=200)
        # Assert
        assert peaks.shape == (200,)

    def test_values_in_unit_range(self):
        # Arrange: クリップ寸前の大音量
        y = (np.random.default_rng(0).uniform(-3.0, 3.0, 44100)).astype(np.float32)
        # Act
        peaks = downsample_peaks(y)
        # Assert: 高パーセンタイル正規化でも0..1に収まる(codex 1.2)
        assert peaks.min() >= 0.0
        assert peaks.max() <= 1.0

    def test_tiny_amplitude_does_not_blow_up(self):
        # Arrange: 極小音源(ベタ平坦になりやすい)
        y = sine(220, 0.5, amp=1e-4)
        # Act
        peaks = downsample_peaks(y)
        # Assert: 破綻せず値域内
        assert np.all(peaks >= 0.0) and np.all(peaks <= 1.0)

    def test_empty_input_returns_zeros(self):
        peaks = downsample_peaks(np.zeros(0, dtype=np.float32), n_peaks=64)
        assert peaks.shape == (64,)
        assert np.all(peaks == 0.0)

    def test_stereo_is_mixed_to_mono(self):
        # Arrange: 2ch(ch, samples)
        stereo = np.stack([sine(440, 0.5), sine(441, 0.5)])
        # Act
        peaks = downsample_peaks(stereo, n_peaks=100)
        # Assert: モノ化して1次元で返る
        assert peaks.ndim == 1 and peaks.shape == (100,)

    def test_invalid_n_peaks_raises(self):
        with pytest.raises(ValueError):
            downsample_peaks(sine(440, 0.2), n_peaks=0)


# ============================ card_layout(ピッチ窓/尺) ============================


class TestCardLayout:
    def test_pitch_window_zooms_to_note_range(self):
        # Arrange: C4(60)〜E4(64)の狭い音域
        notes = [qn(0, 1, 60), qn(1, 1, 64)]
        # Act
        lay = card_layout(sine(440, 2.0), 22050, notes, bpm=120)
        # Assert: 全音域ではなく検出音域周辺に窓が寄る(codex 2.1 自動ズーム)
        assert isinstance(lay, CardLayout)
        assert lay.pitch_lo <= 60
        assert lay.pitch_hi >= 64
        assert lay.pitch_hi - lay.pitch_lo <= 24  # 狭い素材で広く開きすぎない

    def test_single_note_gets_minimum_span(self):
        # Arrange: 1音だけ → 巨大化しないよう最小スパンを確保
        lay = card_layout(sine(440, 1.0), 22050, [qn(0, 1, 60)], bpm=120)
        assert lay.pitch_hi - lay.pitch_lo >= 12

    def test_empty_notes_still_valid_window(self):
        lay = card_layout(sine(440, 1.0), 22050, [], bpm=120)
        assert lay.pitch_lo < lay.pitch_hi
        assert lay.notes_drawn == 0

    def test_duration_uses_max_of_audio_and_notes(self):
        # Arrange: 音声0.5s、音符は拍換算で後ろまで伸びる
        notes = [qn(0, 4, 60)]  # 4拍 @120bpm = 2.0s
        lay = card_layout(sine(440, 0.5), 22050, notes, bpm=120)
        assert lay.duration_sec >= 2.0

    def test_notes_outside_window_not_counted(self):
        # 極端に離れた外れ値は窓に入らずカウントされない場合がある
        notes = [qn(0, 1, 60), qn(0, 1, 62)]
        lay = card_layout(sine(440, 1.0), 22050, notes, bpm=120)
        assert lay.notes_drawn == 2  # 近接音は両方描かれる


# ============================ render_visual_card(PNG生成) ============================


class TestRenderVisualCard:
    def test_png_created_and_valid(self, tmp_path: Path):
        # Arrange
        notes = [qn(i, 1, m) for i, m in enumerate([60, 62, 64, 65, 64, 62, 60])]
        y = sine(440, 3.0)
        out = tmp_path / "card.png"
        # Act
        result = render_visual_card(y, 22050, notes, out, title="テスト曲")
        # Assert: 生成され、再読込で妥当なPNG
        assert result.exists() and result.stat().st_size > 0
        assert result.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # PNG署名
        w, h = _png_dimensions(result)
        assert (w, h) == (CARD_W, CARD_H)

    def test_fixed_sns_aspect_ratio(self, tmp_path: Path):
        # SNS共有向けの固定比率(1.91:1)であること
        out = render_visual_card(sine(440, 1.0), 22050, [qn(0, 1, 60)], tmp_path / "a.png")
        w, h = _png_dimensions(out)
        assert abs(w / h - 1.91) < 0.05

    def test_empty_notes_still_makes_card(self, tmp_path: Path):
        # 音符ゼロでも妥当なカードを生成する(堅牢性)
        out = render_visual_card(sine(440, 1.0), 22050, [], tmp_path / "empty.png")
        assert out.exists()
        assert _png_dimensions(out) == (CARD_W, CARD_H)

    def test_silent_audio_still_makes_card(self, tmp_path: Path):
        # 無音音声でも波形平坦線で破綻しない(codex checklist)
        out = render_visual_card(
            np.zeros(22050, dtype=np.float32), 22050, [qn(0, 1, 60)], tmp_path / "sil.png"
        )
        assert _png_dimensions(out) == (CARD_W, CARD_H)

    def test_empty_audio_uses_notes_for_duration(self, tmp_path: Path):
        # 空音声でも音符から尺を決めて生成できる
        out = render_visual_card(
            np.zeros(0, dtype=np.float32), 0, [qn(0, 2, 60)], tmp_path / "na.png"
        )
        assert out.exists() and out.stat().st_size > 0

    def test_stereo_audio_accepted(self, tmp_path: Path):
        stereo = np.stack([sine(440, 1.0), sine(660, 1.0)])
        out = render_visual_card(stereo, 22050, [qn(0, 1, 69)], tmp_path / "st.png")
        assert _png_dimensions(out) == (CARD_W, CARD_H)

    def test_suffix_normalized_to_png(self, tmp_path: Path):
        # 拡張子が.png以外でも.pngへ正規化して返す
        out = render_visual_card(sine(440, 0.5), 22050, [qn(0, 1, 60)], tmp_path / "x.jpg")
        assert out.suffix == ".png"
        assert out.exists()

    def test_dense_chord_does_not_crash(self, tmp_path: Path):
        # 和音密集・半音差でも生成が破綻しない(codex 2.1)
        notes = [qn(0, 1, m) for m in range(60, 73)]  # C4..C5半音全部
        out = render_visual_card(sine(440, 1.0), 22050, notes, tmp_path / "chord.png")
        assert _png_dimensions(out) == (CARD_W, CARD_H)

    def test_real_seconds_notes_render(self, tmp_path: Path):
        # onset_sec/offset_sec を持つ音符(実タイミング)でも描ける
        notes = [
            QuantizedNote(start_beats=0, dur_beats=1, midi=60, confidence=0.8,
                          onset_sec=0.1, offset_sec=0.6),
            QuantizedNote(start_beats=1, dur_beats=1, midi=64, confidence=0.5,
                          onset_sec=0.8, offset_sec=1.4),
        ]
        out = render_visual_card(sine(440, 2.0), 22050, notes, tmp_path / "sec.png")
        assert _png_dimensions(out) == (CARD_W, CARD_H)

    def test_negative_bpm_raises(self, tmp_path: Path):
        with pytest.raises(ValueError):
            render_visual_card(sine(440, 0.5), 22050, [qn(0, 1, 60)],
                               tmp_path / "b.png", bpm=-1)

    def test_low_confidence_notes_still_render(self, tmp_path: Path):
        # 低信頼度でも完全には消さず描く(冗長表現・codex 2.2)
        notes = [qn(0, 1, 60, conf=0.05), qn(1, 1, 62, conf=0.1)]
        out = render_visual_card(sine(440, 2.0), 22050, notes, tmp_path / "lc.png")
        assert out.exists() and out.stat().st_size > 0
