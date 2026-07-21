"""F-094 譜面差分ハイライト(diff_notes)のユニットテスト。

先行研究(F-094-grok / F-094-codex)の失敗例を回帰で固定する:
- 対応付けの失敗を「譜面差分」と誤表示しない(貪欲1対1・codex エグゼクティブ)
- 同音連打の対応入れ替わりを防ぐ安定タイブレーク(codex §2)
- 境界誤差(微小オンセットズレ)を timing_diff に化けさせない二段判定(codex §1.6)
- octave 違いは半音12の pitch_diff として素直に出る(整数MIDI限界・grok F6)
- split/merge の一方が only_in_* に落ちる原理的限界を明示(codex §2)
"""

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.score_diff import (
    DEFAULT_ONSET_TOL_BEATS,
    diff_notes,
)


def _note(start: float, midi: int, dur: float = 1.0, conf: float = 0.9) -> QuantizedNote:
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


class TestMatch:
    def test_identical_sequences_all_match(self):
        # Arrange
        a = [_note(0.0, 60), _note(1.0, 62), _note(2.0, 64)]
        b = [_note(0.0, 60), _note(1.0, 62), _note(2.0, 64)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert [r["type"] for r in result] == ["match", "match", "match"]
        assert all(r["a_index"] is not None and r["b_index"] is not None for r in result)

    def test_sub_threshold_onset_jitter_is_match_not_timing(self):
        # Arrange: 窓の半分未満のズレは境界誤差 → match(codex §1.6)
        a = [_note(1.0, 60)]
        b = [_note(1.0 + DEFAULT_ONSET_TOL_BEATS * 0.4, 60)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert len(result) == 1
        assert result[0]["type"] == "match"


class TestPitchDiff:
    def test_same_onset_different_pitch_is_pitch_diff(self):
        # Arrange
        a = [_note(0.0, 60)]
        b = [_note(0.0, 63)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert result[0]["type"] == "pitch_diff"
        assert result[0]["pitch_shift_semitones"] == 3

    def test_octave_error_surfaces_as_twelve_semitone_pitch_diff(self):
        # Arrange: 整数MIDI限界 — octave 違いは半音12(grok F6)
        a = [_note(0.0, 60)]
        b = [_note(0.0, 72)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert result[0]["type"] == "pitch_diff"
        assert result[0]["pitch_shift_semitones"] == 12


class TestTimingDiff:
    def test_significant_onset_shift_within_window_is_timing_diff(self):
        # Arrange: 同ピッチ・窓の半分超のズレ → timing_diff
        a = [_note(1.0, 60)]
        b = [_note(1.0 + DEFAULT_ONSET_TOL_BEATS * 0.9, 60)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert result[0]["type"] == "timing_diff"
        assert result[0]["onset_shift_beats"] == pytest.approx(
            DEFAULT_ONSET_TOL_BEATS * 0.9
        )

    def test_duration_mismatch_is_timing_diff(self):
        # Arrange: 開始拍同一・音価が大きく異なる(四分 vs 全音符)
        a = [_note(0.0, 60, dur=1.0)]
        b = [_note(0.0, 60, dur=4.0)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert result[0]["type"] == "timing_diff"


class TestOnlyIn:
    def test_extra_note_in_b_is_only_in_b(self):
        # Arrange: b に余分音(自動採譜のfalse positive・grok F4)
        a = [_note(0.0, 60), _note(2.0, 64)]
        b = [_note(0.0, 60), _note(1.0, 62), _note(2.0, 64)]

        # Act
        result = diff_notes(a, b)

        # Assert
        types = [r["type"] for r in result]
        assert types == ["match", "only_in_b", "match"]
        only = next(r for r in result if r["type"] == "only_in_b")
        assert only["b_midi"] == 62
        assert only["a_index"] is None

    def test_missing_note_in_b_is_only_in_a(self):
        # Arrange: b に欠落音(漏音・grok F4)
        a = [_note(0.0, 60), _note(1.0, 62), _note(2.0, 64)]
        b = [_note(0.0, 60), _note(2.0, 64)]

        # Act
        result = diff_notes(a, b)

        # Assert
        assert [r["type"] for r in result] == ["match", "only_in_a", "match"]


class TestGreedyOneToOne:
    def test_repeated_same_pitch_does_not_swap_correspondence(self):
        # Arrange: 同音連打 — 対応が隣に滑らないこと(codex §2)
        a = [_note(0.0, 60), _note(0.5, 60), _note(1.0, 60)]
        b = [_note(0.0, 60), _note(0.5, 60), _note(1.0, 60)]

        # Act
        result = diff_notes(a, b)

        # Assert: 各 a[i] は同拍の b[i] に対応し全て match
        assert [r["type"] for r in result] == ["match", "match", "match"]
        for r in result:
            assert r["a_index"] == r["b_index"]

    def test_split_one_to_two_leaves_extra_as_only_in_b(self):
        # Arrange: 1音→2音の split。片方が only_in_b に落ちる原理的限界(codex §2)
        a = [_note(0.0, 60, dur=1.0)]
        b = [_note(0.0, 60, dur=0.5), _note(0.1, 60, dur=0.5)]

        # Act
        result = diff_notes(a, b)

        # Assert: 最近傍(0.0)が確定し、もう一方(0.1)は only_in_b
        types = sorted(r["type"] for r in result)
        assert "only_in_b" in types
        assert sum(1 for r in result if r["a_index"] is not None) == 1


class TestOrderingAndValidation:
    def test_output_sorted_by_start_beats(self):
        # Arrange
        a = [_note(3.0, 67), _note(0.0, 60)]
        b = [_note(3.0, 67), _note(0.0, 60)]

        # Act
        result = diff_notes(a, b)

        # Assert
        starts = [
            r["a_start_beats"] if r["a_start_beats"] is not None else r["b_start_beats"]
            for r in result
        ]
        assert starts == sorted(starts)

    def test_empty_inputs_return_empty(self):
        # Arrange / Act
        result = diff_notes([], [])

        # Assert
        assert result == []

    def test_one_side_empty_all_only_in_a(self):
        # Arrange
        a = [_note(0.0, 60), _note(1.0, 62)]

        # Act
        result = diff_notes(a, [])

        # Assert
        assert [r["type"] for r in result] == ["only_in_a", "only_in_a"]

    def test_negative_tolerance_raises(self):
        # Arrange / Act / Assert
        with pytest.raises(ValueError):
            diff_notes([], [], onset_tol_beats=-0.1)

    def test_non_note_input_raises_typeerror(self):
        # Arrange / Act / Assert
        with pytest.raises(TypeError):
            diff_notes([_note(0.0, 60)], ["not a note"])  # type: ignore[list-item]
