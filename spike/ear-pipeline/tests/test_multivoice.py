"""多声部一括採譜の声部分離(F-019)のユニットテスト。

先行研究(F-019-grok.md / F-019-codex.md)の失敗例を回帰テストとして固定する:
- 失敗4/§4.3(同音ユニゾンが1音に潰れる・Melodyne 単一blob): 同時刻・同高の
  重複は幻の声部を作らず1音へ統合されることを検証。
- 失敗C(メロディが声部間を飛ぶ): 声部内の音高連続性が保たれる(貪欲法で近い音を
  引き継ぐ)ことを検証。
- skyline=上声の割り切り: voices[0] が各時刻の最高音を含むことを検証。
- 非破壊・不変(density.py と同方針): 入力インスタンスを改変せず、timing/pitch を
  一切変えずに振り分けることを検証。
"""

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.multivoice import separate_voices


def note(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    """テスト用の QuantizedNote ファクトリ(実側は既定NaNのまま)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


class TestBasics:
    def test_empty_input_returns_empty(self):
        # Arrange
        notes: list[QuantizedNote] = []

        # Act
        result = separate_voices(notes)

        # Assert
        assert result == []

    def test_single_note_single_voice(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act
        result = separate_voices(notes, max_voices=2)

        # Assert: 音のある声部だけ返る(空声部は落とす)
        assert len(result) == 1
        assert result[0] == [notes[0]]

    def test_pure_monophonic_stays_one_voice(self):
        # Arrange: 時間的に重ならない単旋律(各時刻1音)
        notes = [note(float(i), 1.0, 60 + i) for i in range(4)]

        # Act
        result = separate_voices(notes, max_voices=3)

        # Assert: 単旋律は上声1本に収まる(下声を捏造しない)
        assert len(result) == 1
        assert [n.midi for n in result[0]] == [60, 61, 62, 63]


class TestMaxVoicesValidation:
    def test_max_voices_one_raises(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act / Assert: 小編成限定(2〜3)。1 は範囲外
        with pytest.raises(ValueError):
            separate_voices(notes, max_voices=1)

    def test_max_voices_four_raises(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act / Assert: 4 以上は対象外(フルオーケストラ非対応)
        with pytest.raises(ValueError):
            separate_voices(notes, max_voices=4)


class TestSkylineTopVoice:
    def test_top_note_goes_to_first_voice(self):
        # Arrange: 同時刻に高・中・低の3音
        hi = note(0.0, 1.0, 76)
        mid = note(0.0, 1.0, 67)
        lo = note(0.0, 1.0, 55)
        notes = [lo, hi, mid]  # 入力順は意図的にバラす

        # Act
        result = separate_voices(notes, max_voices=3)

        # Assert: 上声(voices[0])が最高音を持つ(skyline=上声)
        assert 76 in [n.midi for n in result[0]]
        # 3声部すべてに1音ずつ割り当たる
        assert len(result) == 3
        all_midis = sorted(n.midi for v in result for n in v)
        assert all_midis == [55, 67, 76]


class TestUnisonCollapse:
    def test_same_pitch_same_time_collapses_to_one(self):
        # Arrange: 2楽器が同じ A4(69) を同時に鳴らす(音声上分離不能)
        a = note(0.0, 1.0, 69, conf=0.9)
        b = note(0.0, 1.0, 69, conf=0.8)  # 別ソースの同音ユニゾン
        notes = [a, b]

        # Act
        result = separate_voices(notes, max_voices=3)

        # Assert: 幻の第2声部を作らず1音へ統合(codex §4.3 / grok 失敗4)
        total = sum(len(v) for v in result)
        assert total == 1
        assert len(result) == 1  # 1声部のみ

    def test_unison_does_not_inflate_voice_count(self):
        # Arrange: 各時刻に「同音ユニゾン + 別の高音」= 実質2声部
        notes = [
            note(0.0, 1.0, 72),  # 上声
            note(0.0, 1.0, 60),  # 下声
            note(0.0, 1.0, 60),  # 60 のユニゾン(統合されるべき)
        ]

        # Act
        result = separate_voices(notes, max_voices=3)

        # Assert: 60 は1音に統合され、声部は2本(72 と 60)
        total = sum(len(v) for v in result)
        assert total == 2
        assert len(result) == 2


class TestVoiceContinuity:
    def test_voices_keep_pitch_continuity(self):
        # Arrange: 2声部が並行進行。上声は高域、下声は低域を一貫して保つべき。
        notes = [
            note(0.0, 1.0, 72), note(0.0, 1.0, 60),
            note(1.0, 1.0, 74), note(1.0, 1.0, 62),
            note(2.0, 1.0, 76), note(2.0, 1.0, 64),
        ]

        # Act
        result = separate_voices(notes, max_voices=2)

        # Assert: 2声部に分かれ、上声は常に下声より高い(交差しない並行進行)
        assert len(result) == 2
        top, bottom = result[0], result[1]
        assert [n.midi for n in top] == [72, 74, 76]
        assert [n.midi for n in bottom] == [60, 62, 64]

    def test_voice_avoids_large_leap_when_continuation_exists(self):
        # Arrange: 上声が滑らかに動き、下声も滑らか。跳躍で取り違えないこと。
        notes = [
            note(0.0, 1.0, 70), note(0.0, 1.0, 50),
            note(1.0, 1.0, 71), note(1.0, 1.0, 51),
        ]

        # Act
        result = separate_voices(notes, max_voices=2)

        # Assert: 上声 70→71、下声 50→51(声部内で近接音を引き継ぐ)
        assert len(result) == 2
        assert [n.midi for n in result[0]] == [70, 71]
        assert [n.midi for n in result[1]] == [50, 51]


class TestNonDestructive:
    def test_does_not_mutate_input_list(self):
        # Arrange
        notes = [note(0.0, 1.0, 72), note(0.0, 1.0, 60), note(1.0, 1.0, 64)]
        original = list(notes)

        # Act
        separate_voices(notes, max_voices=3)

        # Assert: 元 list は不変
        assert notes == original

    def test_returned_notes_are_original_instances(self):
        # Arrange
        notes = [note(0.0, 1.0, 72), note(0.0, 1.0, 60)]

        # Act
        result = separate_voices(notes, max_voices=2)

        # Assert: 声部に入る音は元インスタンスそのまま(timing/pitch 改変なし)
        for v in result:
            for n in v:
                assert n in notes

    def test_all_notes_preserved_except_unison_dedup(self):
        # Arrange: ユニゾン重複なしなら全音符が保存される
        notes = [
            note(0.0, 1.0, 72), note(0.0, 1.0, 64), note(0.0, 1.0, 55),
            note(1.0, 1.0, 74), note(1.0, 1.0, 62),
        ]

        # Act
        result = separate_voices(notes, max_voices=3)

        # Assert: 入出力の音符集合が一致(欠落・捏造なし)
        out_notes = [n for v in result for n in v]
        assert len(out_notes) == len(notes)
        assert sorted(n.midi for n in out_notes) == sorted(n.midi for n in notes)


class TestVoiceOrdering:
    def test_each_voice_sorted_by_start_beats(self):
        # Arrange: 入力順をバラして与える
        notes = [
            note(2.0, 1.0, 76), note(0.0, 1.0, 72), note(1.0, 1.0, 74),
            note(0.0, 1.0, 60), note(2.0, 1.0, 64), note(1.0, 1.0, 62),
        ]

        # Act
        result = separate_voices(notes, max_voices=2)

        # Assert: 各声部内は start_beats 昇順
        for v in result:
            starts = [n.start_beats for n in v]
            assert starts == sorted(starts)

    def test_deterministic_same_input_same_output(self):
        # Arrange
        notes = [
            note(0.0, 1.0, 72), note(0.0, 1.0, 60),
            note(1.0, 0.5, 74), note(1.0, 0.5, 62),
            note(1.5, 0.5, 71),
        ]

        # Act
        a = separate_voices(notes, max_voices=3)
        b = separate_voices(notes, max_voices=3)

        # Assert: 決定的(同一入力は完全一致)
        assert a == b


class TestOverflowFolding:
    def test_more_simultaneous_than_voices_folds_into_chords(self):
        # Arrange: 4同時音 vs max_voices=2 → 超過分は最寄り声部へ畳み込み(声部内和音)
        notes = [
            note(0.0, 1.0, 80), note(0.0, 1.0, 72),
            note(0.0, 1.0, 64), note(0.0, 1.0, 55),
        ]

        # Act
        result = separate_voices(notes, max_voices=2)

        # Assert: 声部数は 2 を超えず、全4音は保存される(欠落なし)
        assert len(result) <= 2
        total = sum(len(v) for v in result)
        assert total == 4
