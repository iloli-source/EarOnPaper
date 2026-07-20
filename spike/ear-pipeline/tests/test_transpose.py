"""F-060 移調・キー変更(Issue #87)のユニットテスト。

先行研究(F-060-grok / F-060-codex)の失敗例を回帰で固定する:
- music21 の素朴な整数/chromatic 移調が調号だらけの調へ飛ぶ問題(§1.2/§1.6)
- MIDI移調で音高を厳密に保つ(綴りは後段責務・§1.8)
- 実タイミング(C3二重表現)を移調で壊さない
- 移調でTAB音域外に出る音を色付けでなく明示検出(§2.4-2.6)
"""

import math

import music21
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.transpose import (
    TAB_MIDI_HIGH,
    TAB_MIDI_LOW,
    spell_transposed_key,
    transpose_key,
    transpose_notes,
    transpose_tab_out_of_range,
)

_NOTES = [
    QuantizedNote(0.0, 1.0, 60, 0.9, onset_sec=0.10, offset_sec=0.60),
    QuantizedNote(1.0, 0.5, 64, 0.8, onset_sec=0.62, offset_sec=0.90),
    QuantizedNote(1.5, 0.5, 67, 0.7, onset_sec=0.91, offset_sec=1.20),
]


class TestTransposeNotes:
    def test_shifts_all_midi_by_semitones(self):
        # Arrange
        notes = _NOTES

        # Act
        up = transpose_notes(notes, 2)

        # Assert
        assert [n.midi for n in up] == [62, 66, 69]

    def test_downward_transpose_uses_negative_semitones(self):
        # Arrange / Act
        down = transpose_notes(_NOTES, -3)

        # Assert
        assert [n.midi for n in down] == [57, 61, 64]

    def test_zero_is_identity_on_pitch(self):
        # Arrange / Act
        same = transpose_notes(_NOTES, 0)

        # Assert
        assert [n.midi for n in same] == [n.midi for n in _NOTES]

    def test_preserves_beats_and_real_timing(self):
        # 移調は音高のみ。拍と実タイミング(C3二重表現)を壊さない(codex §0 二層モデル)
        # Arrange / Act
        out = transpose_notes(_NOTES, 5)

        # Assert
        for src, dst in zip(_NOTES, out):
            assert dst.start_beats == src.start_beats
            assert dst.dur_beats == src.dur_beats
            assert dst.onset_sec == src.onset_sec
            assert dst.offset_sec == src.offset_sec
            assert dst.confidence == src.confidence

    def test_does_not_mutate_input(self):
        # Arrange
        before = [n.midi for n in _NOTES]

        # Act
        transpose_notes(_NOTES, 7)

        # Assert
        assert [n.midi for n in _NOTES] == before

    def test_empty_list_returns_empty(self):
        # Arrange / Act / Assert
        assert transpose_notes([], 4) == []

    def test_preserves_nan_real_timing_by_default_construction(self):
        # 実側未設定(既定NaN)の音符も破壊せずNaNのまま運ぶ
        # Arrange
        notes = [QuantizedNote(0.0, 1.0, 60, 0.9)]

        # Act
        out = transpose_notes(notes, 1)

        # Assert
        assert out[0].midi == 61
        assert math.isnan(out[0].onset_sec)

    def test_non_int_semitones_raises(self):
        # Arrange / Act / Assert
        with pytest.raises(TypeError):
            transpose_notes(_NOTES, 2.5)  # type: ignore[arg-type]


class TestTransposeKey:
    def test_up_wraps_pitch_class(self):
        # Arrange / Act / Assert
        assert transpose_key(0, 2) == 2       # C -> D
        assert transpose_key(11, 2) == 1      # B -> C# (pc1), wraps mod12

    def test_down_wraps_pitch_class(self):
        # Arrange / Act / Assert
        assert transpose_key(0, -1) == 11     # C -> B
        assert transpose_key(2, -3) == 11     # D -> B

    def test_zero_is_identity(self):
        # Arrange / Act / Assert
        assert transpose_key(7, 0) == 7

    def test_full_octave_is_identity(self):
        # Arrange / Act / Assert
        assert transpose_key(5, 12) == 5

    def test_out_of_range_pc_raises(self):
        # Arrange / Act / Assert
        with pytest.raises(ValueError):
            transpose_key(12, 1)

    def test_non_int_raises(self):
        # Arrange / Act / Assert
        with pytest.raises(TypeError):
            transpose_key(0, 1.0)  # type: ignore[arg-type]


class TestSpellTransposedKey:
    def test_result_has_expected_tonic_pitch_class(self):
        # D major を +2 -> E major (pc4)
        # Arrange
        key = music21.key.Key("D")

        # Act
        out = spell_transposed_key(key, 2)

        # Assert
        assert out.tonic.pitchClass == 4
        assert out.mode == "major"

    def test_avoids_accidental_spam_on_tritone_transpose(self):
        # 先行研究の中核: D major を +6 すると素朴実装は G# major(8#)を返し
        # 譜面が調号だらけになる(codex §1.2/§1.6・grok F.5)。最少調号の
        # 異名同音(F#/Gb=6)を選ぶことを固定する。
        # Arrange
        key = music21.key.Key("D")
        naive = key.transpose(music21.interval.Interval(6))

        # Act
        out = spell_transposed_key(key, 6)

        # Assert
        assert abs(naive.sharps) >= 8            # 素朴実装は調号だらけ
        assert abs(out.sharps) <= 6              # 我々の実装は最少化
        assert out.tonic.pitchClass == (key.tonic.pitchClass + 6) % 12

    def test_minus_one_avoids_seven_sharps(self):
        # D major -1 -> pc1。素朴実装は C# major(7#)。Db(-5)を選び臨時記号を減らす。
        # Arrange
        key = music21.key.Key("D")

        # Act
        out = spell_transposed_key(key, -1)

        # Assert
        assert out.tonic.pitchClass == 1
        assert abs(out.sharps) <= 5

    def test_upward_tritone_prefers_sharp_side(self):
        # F#/Gb は同数(6)。上行は#系を選ぶ(方向一貫性・spelling.pyの向き優先と同思想)
        # Arrange
        key = music21.key.Key("C")

        # Act
        out = spell_transposed_key(key, 6)

        # Assert
        assert out.sharps == 6                   # F# major(6#), not Gb(-6)

    def test_downward_tritone_prefers_flat_side(self):
        # 下行は b系を選ぶ
        # Arrange
        key = music21.key.Key("C")

        # Act
        out = spell_transposed_key(key, -6)

        # Assert
        assert out.sharps == -6                  # Gb major(6b)

    def test_preserves_minor_mode(self):
        # Arrange
        key = music21.key.Key("a")  # a minor

        # Act
        out = spell_transposed_key(key, 3)

        # Assert
        assert out.mode == "minor"
        assert out.tonic.pitchClass == 0         # a(pc9) +3 -> c(pc0)


class TestTransposeTabOutOfRange:
    def test_in_range_notes_report_empty(self):
        # 60/64/67 を +2 -> 62/66/69。すべて 40..83 内
        # Arrange / Act
        flagged = transpose_tab_out_of_range(_NOTES, 2)

        # Assert
        assert flagged == []

    def test_flags_notes_pushed_above_high_bound(self):
        # 83境界の1弦最高フレット。+2で音域外に出る音を検出
        # Arrange
        notes = [QuantizedNote(0.0, 1.0, TAB_MIDI_HIGH - 1, 0.9)]  # 82

        # Act
        flagged = transpose_tab_out_of_range(notes, 3)  # 82 -> 85 > 83

        # Assert
        assert len(flagged) == 1
        assert flagged[0].midi == TAB_MIDI_HIGH + 2

    def test_flags_notes_pushed_below_low_bound(self):
        # 40境界(6弦開放E)より下に落ちる音を検出
        # Arrange
        notes = [QuantizedNote(0.0, 1.0, TAB_MIDI_LOW + 1, 0.9)]  # 41

        # Act
        flagged = transpose_tab_out_of_range(notes, -3)  # 41 -> 38 < 40

        # Assert
        assert len(flagged) == 1
        assert flagged[0].midi == TAB_MIDI_LOW - 2

    def test_reports_shifted_midi_not_original(self):
        # 返す音は移調後(midi加算済み)であることを固定
        # Arrange
        notes = [QuantizedNote(0.0, 1.0, 30, 0.9)]  # 元から音域外

        # Act
        flagged = transpose_tab_out_of_range(notes, 1)

        # Assert
        assert flagged[0].midi == 31
