"""F-102 サステインペダル区間候補推定のテスト。

研究(docs/research/upcoming/F-102-*.md)の核心 pitfall を回帰固定する:
  - ペダルは音価を伸ばさない(3層分離: 物理note_off/音響sound_off/記譜音価)
  - 返すのは「候補」であって CC64 真値ではない
  - audio 直検出は honest に未実装(NotImplementedError)

AAA(Arrange-Act-Assert)形式で複数観点を検証する。
"""

import math

import numpy as np
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.ear.pedal import (
    DEFAULT_MIN_OVERLAP_SEC,
    SustainSpan,
    detect_sustain,
    detect_sustain_audio,
)


def _note(onset: float, offset: float, midi: int = 60) -> QuantizedNote:
    """実タイミング付きの量子化ノートを作るヘルパ(格子側は仮値)。"""
    return QuantizedNote(
        start_beats=0.0,
        dur_beats=1.0,
        midi=midi,
        confidence=0.9,
        onset_sec=onset,
        offset_sec=offset,
    )


class TestDetectSustainOverlap:
    def test_detects_span_when_tail_overlaps_next_onset(self):
        # Arrange: 1音目の尾(0.0-1.0)が2音目の打鍵(0.5)を大きく越える
        notes = [_note(0.0, 1.0, 60), _note(0.5, 1.5, 62)]

        # Act
        spans = detect_sustain(notes)

        # Assert: 候補が1区間、区間は[次打鍵0.5, 尾の終わり1.0]近傍
        assert len(spans) == 1
        assert spans[0]["start_sec"] == pytest.approx(0.5)
        assert spans[0]["end_sec"] == pytest.approx(1.0)
        assert spans[0]["note_count"] == 1

    def test_no_span_when_notes_do_not_overlap(self):
        # Arrange: 尾が次の打鍵前に消える(重なりゼロ)
        notes = [_note(0.0, 0.4, 60), _note(0.5, 0.9, 62)]

        # Act
        spans = detect_sustain(notes)

        # Assert
        assert spans == []

    def test_tiny_overlap_below_threshold_ignored(self):
        # Arrange: 重なりが min_overlap_sec 未満(誤検出防止の下限)
        overlap = DEFAULT_MIN_OVERLAP_SEC / 2.0
        notes = [_note(0.0, 0.5, 60), _note(0.5 - overlap, 1.0, 62)]

        # Act
        spans = detect_sustain(notes)

        # Assert: 微小重なりはペダルと誤認しない
        assert spans == []


class TestNoteValueNotStretched:
    """3層分離の核心: ペダル候補を出しても音符の音価を伸ばさない。"""

    def test_input_notes_are_not_mutated(self):
        # Arrange
        notes = [_note(0.0, 1.0, 60), _note(0.5, 1.5, 62)]
        before = [(n.dur_beats, n.offset_sec) for n in notes]

        # Act
        detect_sustain(notes)

        # Assert: 音価(dur_beats)も実オフセットも不変(共鳴を音価にしない)
        after = [(n.dur_beats, n.offset_sec) for n in notes]
        assert after == before

    def test_span_is_sound_off_layer_not_notated(self):
        # Arrange
        notes = [_note(0.0, 1.0, 60), _note(0.5, 1.5, 62)]

        # Act
        spans = detect_sustain(notes)

        # Assert: 返り値は音響層(sound_off)であると明示され、音価ではない
        assert spans[0]["layer"] == "sound_off"


class TestSpanMerging:
    def test_adjacent_overlaps_merge_into_one_span(self):
        # Arrange: 連続してペダルの尾が重なる(踏みっぱなし)
        notes = [
            _note(0.0, 1.0, 60),
            _note(0.5, 1.5, 62),
            _note(1.0, 2.0, 64),
        ]

        # Act
        spans = detect_sustain(notes)

        # Assert: 1つの連続ペダル区間に併合、複数ノートが関与。
        # 区間は「尾が後続打鍵に食い込んだ範囲」= [0.5, 1.5]。
        # 最終音(尾2.0)は後続打鍵が無いため候補に寄与しない(重なりベースの定義)。
        assert len(spans) == 1
        assert spans[0]["note_count"] >= 2
        assert spans[0]["start_sec"] == pytest.approx(0.5)
        assert spans[0]["end_sec"] == pytest.approx(1.5)

    def test_large_gap_splits_into_two_spans(self):
        # Arrange: 前半ペア(0-1台)と後半ペア(遠く離れた3秒台)
        notes = [
            _note(0.0, 1.0, 60),
            _note(0.5, 1.5, 62),
            _note(3.0, 4.0, 65),
            _note(3.5, 4.5, 67),
        ]

        # Act
        spans = detect_sustain(notes)

        # Assert: 踏み直し相当で2区間に分かれる
        assert len(spans) == 2
        assert spans[0]["end_sec"] < spans[1]["start_sec"]

    def test_confidence_in_unit_range(self):
        # Arrange
        notes = [_note(0.0, 2.0, 60), _note(0.2, 2.2, 62)]

        # Act
        spans = detect_sustain(notes)

        # Assert: confidence は 0-1(粗い代理値であり真値ではない)
        assert len(spans) == 1
        assert 0.0 <= spans[0]["confidence"] <= 1.0


class TestEdgeCases:
    def test_empty_returns_empty(self):
        # Arrange / Act / Assert
        assert detect_sustain([]) == []

    def test_single_note_returns_empty(self):
        # Arrange: 1音では重なりが定義できない
        notes = [_note(0.0, 1.0, 60)]

        # Act / Assert
        assert detect_sustain(notes) == []

    def test_notes_without_real_timing_ignored(self):
        # Arrange: 実タイミング未設定(NaN)のノートは音響層判定に使えない
        grid_only = QuantizedNote(0.0, 1.0, 60, 0.9)  # onset/offset は既定NaN
        assert math.isnan(grid_only.onset_sec)

        # Act
        spans = detect_sustain([grid_only, grid_only])

        # Assert
        assert spans == []

    def test_zero_duration_notes_ignored(self):
        # Arrange: offset <= onset の退化ノートは無視
        notes = [_note(1.0, 1.0, 60), _note(1.0, 0.5, 62)]

        # Act / Assert
        assert detect_sustain(notes) == []


class TestInputValidation:
    def test_negative_min_overlap_raises(self):
        with pytest.raises(ValueError):
            detect_sustain([_note(0.0, 1.0)], min_overlap_sec=-0.1)

    def test_non_finite_merge_gap_raises(self):
        with pytest.raises(ValueError):
            detect_sustain([_note(0.0, 1.0)], merge_gap_sec=float("inf"))


class TestDetectSustainAudioHonest:
    """audio 直検出は原理的に脆弱 → honest に未実装で拒否する。"""

    def test_audio_detection_not_implemented(self):
        # Arrange
        y = np.zeros(1000, dtype=np.float32)

        # Act / Assert: 黙って空を返さず明示的に拒否
        with pytest.raises(NotImplementedError):
            detect_sustain_audio(y, 22050)

    def test_invalid_sr_raises_value_error(self):
        with pytest.raises(ValueError):
            detect_sustain_audio(np.zeros(10), 0)

    def test_empty_audio_raises_value_error(self):
        with pytest.raises(ValueError):
            detect_sustain_audio(np.array([]), 22050)


class TestSustainSpanDataclass:
    def test_span_is_frozen(self):
        # Arrange
        span = SustainSpan(start_sec=0.0, end_sec=1.0, confidence=0.5, note_count=1)

        # Act / Assert: frozen dataclass は代入不可
        with pytest.raises(Exception):
            span.start_sec = 2.0  # type: ignore[misc]
