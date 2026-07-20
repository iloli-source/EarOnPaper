"""F-037 記譜形式相互変換ファサード(convert.py)のユニットテスト(Issue #85)。

staff_to_jianpu(既存 to_jianpu 委譲)・staff_to_tab_frets(既存 assign_frets 委譲)・
tab_to_staff(TabNote→QuantizedNote 逆写像)を AAA 形式で検証する。

先行研究(F-037-grok.md)の可逆性pitfallを反映した検証:
- 五線⇄TAB の音高・リズムの往復(round-trip)が保たれること
- 音域外音のオクターブ移動が復路で打ち消されること(情報復元)
- 縮退入力(空列)で例外を出さないこと
- 不正 string_index を黙って捨てず IndexError で表面化すること
"""

import math

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.convert import (
    staff_to_jianpu,
    staff_to_tab_frets,
    tab_to_staff,
)
from earpipe.services.notate.tab import TUNING_GUITAR, TabNote, assign_frets


def _note(midi: int, dur_beats: float = 1.0, start_beats: float = 0.0,
          confidence: float = 0.9) -> QuantizedNote:
    """テスト用 QuantizedNote 生成ヘルパ(実側 onset/offset は既定 NaN のまま)。"""
    return QuantizedNote(
        start_beats=start_beats, dur_beats=dur_beats, midi=midi, confidence=confidence
    )


class TestStaffToJianpu:
    """staff_to_jianpu が既存 to_jianpu に委譲していることを検証する。"""

    def test_c_major_scale_delegates_to_to_jianpu(self):
        # Arrange: ハ長調の1オクターブ音階(中音域・四分音符)
        notes = [_note(m) for m in (60, 62, 64, 65, 67, 69, 71)]
        # Act
        result = staff_to_jianpu(notes, key_tonic_pc=0)
        # Assert: 主音基準の音度 1-7
        assert result == "1 2 3 4 5 6 7"

    def test_accepts_sequence_not_only_list(self):
        # Arrange: tuple(Sequence)でも受理できること
        notes = (_note(60), _note(67))
        # Act
        result = staff_to_jianpu(notes, key_tonic_pc=0)
        # Assert
        assert result == "1 5"

    def test_empty_input_returns_empty_string(self):
        # Arrange
        notes: list[QuantizedNote] = []
        # Act
        result = staff_to_jianpu(notes, key_tonic_pc=0)
        # Assert: 縮退入力で例外を出さず空文字列
        assert result == ""


class TestStaffToTabFrets:
    """staff_to_tab_frets が既存 assign_frets に委譲していることを検証する。"""

    def test_delegates_to_assign_frets(self):
        # Arrange: 単音3つ(標準6弦で弾ける音域)
        notes = [_note(40), _note(45), _note(52)]
        # Act
        result = staff_to_tab_frets(notes)
        # Assert: assign_frets の直接呼び出しと同一結果(純委譲)
        assert result == assign_frets(notes)

    def test_returns_tabnote_instances(self):
        # Arrange
        notes = [_note(45)]  # 5弦(index0)開放 or 6弦5フレット等
        # Act
        result = staff_to_tab_frets(notes)
        # Assert
        assert result
        assert all(isinstance(t, TabNote) for t in result)

    def test_empty_input_returns_empty_list(self):
        # Arrange / Act
        result = staff_to_tab_frets([])
        # Assert
        assert result == []

    def test_custom_tuning_arg_does_not_crash(self):
        # Arrange: 非標準 tuning を渡しても(現行エンジンは標準6弦固定)例外を出さない
        notes = [_note(52)]
        # Act
        result = staff_to_tab_frets(notes, tuning=(40, 45, 50, 55, 59, 64))
        # Assert: 標準6弦として割当されること(委譲先と一致)
        assert result == assign_frets(notes)


class TestTabToStaff:
    """tab_to_staff の音高復元と逆写像を検証する。"""

    def test_open_string_recovers_open_midi(self):
        # Arrange: 6弦(index0)開放 = TUNING_GUITAR[0] = MIDI 40
        tab = TabNote(start_beats=0.0, dur_beats=1.0, string_index=0,
                      fret=0, octave_shift=0, confidence=0.8)
        # Act
        result = tab_to_staff([tab])
        # Assert
        assert len(result) == 1
        assert result[0].midi == TUNING_GUITAR[0]

    def test_fret_adds_to_open_string(self):
        # Arrange: 6弦5フレット = 40 + 5 = 45
        tab = TabNote(start_beats=1.0, dur_beats=0.5, string_index=0,
                      fret=5, octave_shift=0, confidence=0.7)
        # Act
        result = tab_to_staff([tab])
        # Assert: 音高・拍タイミング・confidence が引き継がれる
        note = result[0]
        assert note.midi == 45
        assert note.start_beats == 1.0
        assert note.dur_beats == 0.5
        assert note.confidence == 0.7

    def test_octave_shift_is_undone(self):
        # Arrange: 往路で1オクターブ上げた(shift=+1)音は、復路で 12 減算し元へ戻す。
        # 5弦3フレット = 45 + 3 = 48。shift=+1 なら元は 48 - 12 = 36。
        tab = TabNote(start_beats=0.0, dur_beats=1.0, string_index=1,
                      fret=3, octave_shift=1, confidence=0.9)
        # Act
        result = tab_to_staff([tab])
        # Assert
        assert result[0].midi == TUNING_GUITAR[1] + 3 - 12

    def test_empty_input_returns_empty_list(self):
        # Arrange / Act
        result = tab_to_staff([])
        # Assert
        assert result == []

    def test_out_of_range_string_index_raises(self):
        # Arrange: string_index=6 は標準6弦(0-5)の範囲外
        bad = TabNote(start_beats=0.0, dur_beats=1.0, string_index=6,
                      fret=0, octave_shift=0, confidence=0.5)
        # Act / Assert: 黙って捨てず IndexError で表面化する
        with pytest.raises(IndexError):
            tab_to_staff([bad])

    def test_onset_offset_left_nan(self):
        # Arrange: TAB には実側タイミングが無いため既定 NaN のまま
        tab = TabNote(start_beats=0.0, dur_beats=1.0, string_index=0,
                      fret=0, octave_shift=0, confidence=0.5)
        # Act
        result = tab_to_staff([tab])
        # Assert
        assert math.isnan(result[0].onset_sec)
        assert math.isnan(result[0].offset_sec)


class TestStaffTabRoundTrip:
    """五線⇄TAB の音高・リズム半可逆性(研究の段階的可逆性(A))を検証する。"""

    def test_in_range_pitches_round_trip_exactly(self):
        # Arrange: 標準6弦音域(40..83)内・単音のみ(同時発音なし)なら音高は往復一致
        midis = [40, 45, 50, 55, 59, 64, 52, 47]
        notes = [_note(m, start_beats=float(i)) for i, m in enumerate(midis)]
        # Act
        tabs = staff_to_tab_frets(notes)
        recovered = tab_to_staff(tabs)
        # Assert: ドロップなし(単音・音域内)で音高集合が保存される
        assert len(recovered) == len(notes)
        rec_by_start = {round(n.start_beats, 6): n.midi for n in recovered}
        for src in notes:
            assert rec_by_start[round(src.start_beats, 6)] == src.midi

    def test_out_of_range_pitch_recovered_via_octave_shift(self):
        # Arrange: 音域外の高音(MIDI 96)は往路でオクターブ移動され、復路で復元される
        note = _note(96, start_beats=0.0)
        # Act
        tabs = staff_to_tab_frets([note])
        recovered = tab_to_staff(tabs)
        # Assert: octave_shift が復路で打ち消され、元の音高に戻る
        assert recovered[0].midi == 96
