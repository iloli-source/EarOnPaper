"""移動ド階名付け(F-100・Issue #75)のユニットテスト。

合成メロディで「調主音基準の相対階名」を AAA 形式で検証する。
半音の上行/下行綴りは旋律方向ヒューリスティックに依存するため、上行/下行の
両文脈を分けて確認する。限界(方向の曖昧さ)は movable_do.py の docstring 参照。
"""

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.movable_do import to_movable_do


def _mel(midis: list[int]) -> list[QuantizedNote]:
    """MIDI列を入力list順の量子化音符列にする(旋律順=list順)。"""
    return [
        QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=m, confidence=0.9)
        for i, m in enumerate(midis)
    ]


class TestDiatonicSolfege:
    def test_ascending_c_major_scale_gives_do_to_ti(self):
        # Arrange
        notes = _mel([60, 62, 64, 65, 67, 69, 71])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert
        assert result == ["Do", "Re", "Mi", "Fa", "Sol", "La", "Ti"]

    def test_descending_c_major_scale_gives_same_diatonic_names(self):
        # Arrange
        notes = _mel([71, 69, 67, 65, 64, 62, 60])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert
        assert result == ["Ti", "La", "Sol", "Fa", "Mi", "Re", "Do"]


class TestChromaticDirection:
    def test_ascending_chromatic_uses_raised_spellings(self):
        # Arrange: C C# D D# E は上行なので raised(Di/Ri)
        notes = _mel([60, 61, 62, 63, 64])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert
        assert result == ["Do", "Di", "Re", "Ri", "Mi"]

    def test_descending_chromatic_uses_lowered_spellings(self):
        # Arrange: E Eb D Db C は下行なので lowered(Me/Ra)
        notes = _mel([64, 63, 62, 61, 60])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert
        assert result == ["Mi", "Me", "Re", "Ra", "Do"]

    def test_first_note_semitone_defaults_to_raised(self):
        # Arrange: 先頭が半音(C#)。直前が無いので raised(Di)既定
        notes = _mel([61, 60])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert
        assert result[0] == "Di"

    def test_octave_leap_up_is_treated_as_ascending(self):
        # Arrange: C(60)→C#上行→半音を跨ぐ跳躍でも生midi差で方向判定
        # 72(高いC)の直後の73(C#)は上行なので Di になるはず
        notes = _mel([60, 72, 73])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert: 73はpc1(半音)、直前72より高いのでraised=Di
        assert result == ["Do", "Do", "Di"]


class TestNumericStyle:
    def test_ascending_diatonic_numeric(self):
        # Arrange
        notes = _mel([60, 62, 64, 65, 67, 69, 71])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="numeric")

        # Assert
        assert result == ["1", "2", "3", "4", "5", "6", "7"]

    def test_ascending_semitone_numeric_uses_sharp_prefix(self):
        # Arrange: C C# D は上行 → "1" "#1" "2"
        notes = _mel([60, 61, 62])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="numeric")

        # Assert
        assert result == ["1", "#1", "2"]

    def test_descending_semitone_numeric_uses_flat_prefix(self):
        # Arrange: E Eb D は下行 → "3" "b3" "2"
        notes = _mel([64, 63, 62])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="numeric")

        # Assert
        assert result == ["3", "b3", "2"]


class TestNonCTonic:
    def test_g_tonic_scale_is_relative_to_g(self):
        # Arrange: G major 上行音階(G A B C D E F#)。主音pc=7。
        # 相対度数は主音基準なので全音階の 1..7 相当 → Do..Ti
        notes = _mel([67, 69, 71, 72, 74, 76, 78])

        # Act
        result = to_movable_do(notes, key_tonic_pc=7, style="solfege")

        # Assert
        assert result == ["Do", "Re", "Mi", "Fa", "Sol", "La", "Ti"]

    def test_g_tonic_numeric_starts_at_one(self):
        # Arrange: G主音でGの音(pc7)は首調の "1"
        notes = _mel([67, 74, 79])  # G, D, G

        # Act
        result = to_movable_do(notes, key_tonic_pc=7, style="numeric")

        # Assert: G=1, D=5, G=1
        assert result == ["1", "5", "1"]

    def test_key_tonic_pc_is_normalized_mod_12(self):
        # Arrange: 主音pc=19(=7 mod12)でもG主音と同じ結果になる
        notes = _mel([67, 69, 71])

        # Act
        result = to_movable_do(notes, key_tonic_pc=19, style="solfege")

        # Assert
        assert result == ["Do", "Re", "Mi"]


class TestBoundaries:
    def test_empty_notes_returns_empty_list(self):
        # Arrange
        notes: list[QuantizedNote] = []

        # Act
        result = to_movable_do(notes, key_tonic_pc=0, style="solfege")

        # Assert
        assert result == []

    def test_invalid_style_raises_value_error(self):
        # Arrange
        notes = _mel([60])

        # Act / Assert
        with pytest.raises(ValueError):
            to_movable_do(notes, key_tonic_pc=0, style="jazz")

    def test_default_style_is_solfege(self):
        # Arrange
        notes = _mel([60, 62])

        # Act
        result = to_movable_do(notes, key_tonic_pc=0)

        # Assert
        assert result == ["Do", "Re"]
