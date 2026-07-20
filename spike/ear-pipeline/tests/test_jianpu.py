"""F-033 簡譜(jianpu / 数字譜)テキスト出力(Issue #70)のユニットテスト。

ハ長調(key_tonic_pc=0)を主に、音度写像・オクターブ点・臨時記号・音価近似・
縮退入力(空/休符/未正規化 key)を AAA 形式で検証する。
本関数はテキスト近似であり厳密な簡譜組版ではない(限界はモジュール docstring 参照)。
"""

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.jianpu import to_jianpu


def _note(midi: int, dur_beats: float = 1.0, start_beats: float = 0.0) -> QuantizedNote:
    """テスト用 QuantizedNote 生成ヘルパ(実側 onset/offset は既定 NaN のまま)。"""
    return QuantizedNote(
        start_beats=start_beats, dur_beats=dur_beats, midi=midi, confidence=0.9
    )


class TestDegreeMapping:
    """ハ長調での音度写像(主音基準 1-7)を検証する。"""

    def test_c4_maps_to_degree_1(self):
        # Arrange
        notes = [_note(60)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1"

    def test_g4_maps_to_degree_5(self):
        # Arrange
        notes = [_note(67)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "5"

    def test_full_c_major_scale(self):
        # Arrange: C4 D4 E4 F4 G4 A4 B4(全て中音域・四分音符)
        notes = [_note(m) for m in (60, 62, 64, 65, 67, 69, 71)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1 2 3 4 5 6 7"

    def test_g_major_tonic_g_maps_to_degree_1(self):
        # Arrange: G4 を主音とする調(key_tonic_pc=7)では 5 ではなく 1
        notes = [_note(67)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=7)
        # Assert
        assert result == "1"


class TestOctaveDots:
    """オクターブ点(高=' / 低=,)の ASCII サフィックスを検証する。"""

    def test_c5_gets_upper_dot(self):
        # Arrange
        notes = [_note(72)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1'"

    def test_c3_gets_lower_dot(self):
        # Arrange
        notes = [_note(48)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1,"

    def test_c6_gets_two_upper_dots(self):
        # Arrange: 中音域(C4-B4)から2オクターブ上
        notes = [_note(84)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1''"

    def test_middle_octave_has_no_dot(self):
        # Arrange: B4=71 は中音域(点なし)の上端
        notes = [_note(71)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "7"


class TestAccidentals:
    """長音階外の半音(臨時記号)を "#" 前置で近似することを検証する。"""

    def test_c_sharp_maps_to_sharp_1(self):
        # Arrange: C#4=61(主音からの半音差1)
        notes = [_note(61)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "#1"

    def test_f_sharp_maps_to_sharp_4(self):
        # Arrange: F#4=66(主音からの半音差6 → 直下の音度4に#)
        notes = [_note(66)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "#4"


class TestDurationApproximation:
    """音価近似(増時線 " -" / 減時線 "_" / 付点 ".")を検証する。"""

    def test_quarter_note_plain_number(self):
        # Arrange: 四分音符(1拍)は素の数字
        notes = [_note(60, dur_beats=1.0)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1"

    def test_half_note_gets_dash(self):
        # Arrange: 二分音符(2拍)は増時線1本
        notes = [_note(60, dur_beats=2.0)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1 -"

    def test_eighth_note_gets_underscore(self):
        # Arrange: 8分音符(0.5拍)は減時線1本
        notes = [_note(60, dur_beats=0.5)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1_"

    def test_sixteenth_note_gets_two_underscores(self):
        # Arrange: 16分音符(0.25拍)は減時線2本
        notes = [_note(60, dur_beats=0.25)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1__"

    def test_dotted_quarter_gets_dot(self):
        # Arrange: 付点四分(1.5拍)は付点
        notes = [_note(60, dur_beats=1.5)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1."


class TestRestAndDegenerate:
    """休符・空入力・未正規化 key・不正 dur などの縮退入力を検証する。"""

    def test_empty_returns_empty_string(self):
        # Arrange
        notes: list[QuantizedNote] = []
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == ""

    def test_negative_midi_is_rest_zero(self):
        # Arrange: midi<0 は休符 "0"
        notes = [_note(-1, dur_beats=1.0)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "0"

    def test_unnormalized_key_tonic_pc_is_wrapped(self):
        # Arrange: key_tonic_pc=12 は %12 で 0(ハ長調)に正規化される
        notes = [_note(60)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=12)
        # Assert
        assert result == "1"

    def test_negative_key_tonic_pc_is_wrapped(self):
        # Arrange: key_tonic_pc=-12 も %12 で 0
        notes = [_note(60)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=-12)
        # Assert
        assert result == "1"

    def test_non_positive_duration_falls_back_to_quarter(self):
        # Arrange: dur_beats=0.0 でもクラッシュせず素の数字にする
        notes = [_note(60, dur_beats=0.0)]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1"

    def test_nan_duration_falls_back_to_quarter(self):
        # Arrange: NaN の dur でもクラッシュしない
        notes = [_note(60, dur_beats=float("nan"))]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1"


class TestCombined:
    """音度・オクターブ・音価の組み合わせ(実務に近い並び)を検証する。"""

    def test_melody_with_octave_and_duration(self):
        # Arrange: C5(高8度・二分) → G4(四分) → C4(付点四分)
        notes = [
            _note(72, dur_beats=2.0),
            _note(67, dur_beats=1.0),
            _note(60, dur_beats=1.5),
        ]
        # Act
        result = to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1' - 5 1."
