"""F-091 度数表記(ローマ数字 / ナッシュビル)写像 roman_nashville.py のテスト。

test_chord.py / test_leadsheet.py の span ヘルパに倣い、ChordSpan を直接構築して
to_roman / to_nashville を AAA(Arrange-Act-Assert)形式で検証する。

方針(実装 docstring に整合):
- 変化記号は Unicode の ♭/♯ を前置。7th は ASCII の '7'。
- 短調は key_tonic_pc を主音として扱い平行長調変換をしない。
- トライトーンは #4 固定。
"""

import pytest

from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.roman_nashville import to_nashville, to_roman


def span(root_pc: int, quality: str, name: str = "X") -> ChordSpan:
    """ChordSpan を1つ作るヘルパ(start/end は本テストでは無関係)。"""
    return ChordSpan(
        start_beats=0.0, end_beats=1.0, name=name, root_pc=root_pc, quality=quality
    )


NC = ChordSpan(start_beats=0.0, end_beats=1.0, name="N.C.", root_pc=-1, quality="")


class TestToRomanMajor:
    def test_diatonic_triads_in_c_major(self) -> None:
        # Arrange: C長調(主音pc=0)の I..vii°
        chords = [
            span(0, "major"),   # C  -> I
            span(2, "minor"),   # Dm -> ii
            span(4, "minor"),   # Em -> iii
            span(5, "major"),   # F  -> IV
            span(7, "major"),   # G  -> V
            span(9, "minor"),   # Am -> vi
            span(11, "dim"),    # B° -> vii°
        ]

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["I", "ii", "iii", "IV", "V", "vi", "vii°"]

    def test_seventh_suffixes_preserve_case(self) -> None:
        # Arrange: dom7 は大文字+7、min7 は小文字+7、maj7 は大文字+maj7
        chords = [
            span(7, "dom7"),   # G7    -> V7
            span(2, "min7"),   # Dm7   -> ii7
            span(0, "maj7"),   # Cmaj7 -> Imaj7
        ]

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["V7", "ii7", "Imaj7"]

    def test_sus4_is_uppercase(self) -> None:
        # Arrange: sus4 は3度を持たないため慣例で大文字
        chords = [span(7, "sus4")]  # Gsus4 -> Vsus4

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["Vsus4"]

    def test_chromatic_flat_seven_in_c_major(self) -> None:
        # Arrange: C長調の B♭(root_pc=10, major)は借用の ♭VII
        chords = [span(10, "major")]

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="major")

        # Assert: 変化記号はローマ数字の前、本体は大文字のまま
        assert result == ["♭VII"]

    def test_tritone_defaults_to_sharp_four(self) -> None:
        # Arrange: C長調の F#(root_pc=6)。トライトーンは #4 固定
        chords = [span(6, "major")]

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["♯IV"]


class TestToRomanMinor:
    def test_tonic_minor_diatonic_qualities(self) -> None:
        # Arrange: イ短調(主音pc=9)。i(Am) / iv(Dm) / V(E:和声的短音階)
        chords = [
            span(9, "minor"),  # Am -> i
            span(2, "minor"),  # Dm -> iv
            span(4, "major"),  # E  -> V(和声的短音階の長V)
        ]

        # Act
        result = to_roman(chords, key_tonic_pc=9, mode="minor")

        # Assert
        assert result == ["i", "iv", "V"]

    def test_flat_sixth_is_not_accidental_in_minor(self) -> None:
        # Arrange: ハ短調(主音pc=0)の A♭(root_pc=8, major)は ♭VI ではなく VI
        chords = [span(8, "major")]

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="minor")

        # Assert: 短調の第6度は正規の度数なので変化記号を付けない
        assert result == ["VI"]


class TestToNashville:
    def test_major_progression(self) -> None:
        # Arrange: C長調 I-vi-IV-V を数字で
        chords = [
            span(0, "major"),   # C  -> 1
            span(9, "minor"),   # Am -> 6-
            span(5, "major"),   # F  -> 4
            span(7, "dom7"),    # G7 -> 57
        ]

        # Act
        result = to_nashville(chords, key_tonic_pc=0, mode="major")

        # Assert: minor は '-'、dim は '°'、7th は ASCII '7'
        assert result == ["1", "6-", "4", "57"]

    def test_diminished_and_min7_and_maj7(self) -> None:
        # Arrange: dim/min7/maj7 の修飾
        chords = [
            span(11, "dim"),    # B°   -> 7°
            span(2, "min7"),    # Dm7  -> 2-7
            span(0, "maj7"),    # Cmaj7-> 1maj7
        ]

        # Act
        result = to_nashville(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["7°", "2-7", "1maj7"]

    def test_chromatic_flat_seven(self) -> None:
        # Arrange: C長調の B♭(root_pc=10)は ♭7
        chords = [span(10, "major")]

        # Act
        result = to_nashville(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["♭7"]

    def test_minor_tonic_based_numbering(self) -> None:
        # Arrange: イ短調(主音pc=9)。トニック基準で 1-/4-/5
        chords = [
            span(9, "minor"),  # Am -> 1-
            span(2, "minor"),  # Dm -> 4-
            span(4, "major"),  # E  -> 5
        ]

        # Act
        result = to_nashville(chords, key_tonic_pc=9, mode="minor")

        # Assert
        assert result == ["1-", "4-", "5"]


class TestEdgeCases:
    def test_no_chord_passes_through_roman(self) -> None:
        # Arrange: N.C.(root_pc<0, quality="")
        # Act
        result = to_roman([NC], key_tonic_pc=0, mode="major")
        # Assert
        assert result == ["N.C."]

    def test_no_chord_passes_through_nashville(self) -> None:
        # Arrange / Act
        result = to_nashville([NC], key_tonic_pc=0, mode="major")
        # Assert
        assert result == ["N.C."]

    def test_negative_root_pc_treated_as_no_chord(self) -> None:
        # Arrange: root_pc<0 は quality があっても N.C. 扱い(早期return)
        weird = ChordSpan(
            start_beats=0.0, end_beats=1.0, name="?", root_pc=-1, quality="major"
        )
        # Act
        roman = to_roman([weird], key_tonic_pc=0, mode="major")
        nash = to_nashville([weird], key_tonic_pc=0, mode="major")
        # Assert
        assert roman == ["N.C."]
        assert nash == ["N.C."]

    def test_empty_input_returns_empty_list(self) -> None:
        # Arrange / Act
        # Assert
        assert to_roman([], key_tonic_pc=0, mode="major") == []
        assert to_nashville([], key_tonic_pc=0, mode="minor") == []

    def test_invalid_mode_raises(self) -> None:
        # Arrange: 'major'/'minor' 以外は黙って長調フォールバックせず明示エラー
        chords = [span(0, "major")]

        # Act / Assert
        with pytest.raises(ValueError):
            to_roman(chords, key_tonic_pc=0, mode="dorian")
        with pytest.raises(ValueError):
            to_nashville(chords, key_tonic_pc=0, mode="dorian")

    def test_order_and_length_preserved(self) -> None:
        # Arrange: 出力は入力と同順・同数
        chords = [span(0, "major"), NC, span(7, "dom7")]

        # Act
        result = to_roman(chords, key_tonic_pc=0, mode="major")

        # Assert
        assert result == ["I", "N.C.", "V7"]
