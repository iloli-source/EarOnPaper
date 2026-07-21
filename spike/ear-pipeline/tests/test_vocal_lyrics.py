"""F-020 歌声採譜・歌詞同期(音節→音符割当・メリスマ)のテスト。

先行研究(F-020-grok / F-020-codex)の失敗例を回帰テスト化する:
- 1音節=1音符に潰さず、余剰音符をメリスマで吸収する(codex 1.2 / grok 3.8)
- 音節境界⇒音符境界の非対称制約(ROSVOT): 新規音節は melisma=False で始まる
- 悪い転写・空白・空音節(grok 3.6): 除去して落ちる
- 音符不足(音節>音符): 音節を黙って捨てず count_unassigned で可視化(grok BP6)
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.vocal_lyrics import (
    MELISMA_CONTINUATION,
    align_lyrics,
    count_unassigned,
)


def _note(start_beats: float, midi: int = 60) -> QuantizedNote:
    """テスト用の最小 QuantizedNote を作る補助。"""
    return QuantizedNote(
        start_beats=start_beats,
        dur_beats=1.0,
        midi=midi,
        confidence=0.9,
    )


def test_one_to_one_assignment_no_melisma() -> None:
    """音節数=音符数のとき、順次1対1割当・メリスマなし。"""
    # Arrange
    notes = [_note(0.0), _note(1.0), _note(2.0)]
    syllables = ["do", "re", "mi"]

    # Act
    result = align_lyrics(notes, syllables)

    # Assert
    assert [r["syllable"] for r in result] == ["do", "re", "mi"]
    assert [r["note_index"] for r in result] == [0, 1, 2]
    assert all(r["melisma"] is False for r in result)


def test_leftover_notes_become_melisma_of_last_syllable() -> None:
    """音符が余ると直前音節のメリスマ(継続)として吸収される(codex 1.2)。"""
    # Arrange: 2音節・4音符 -> 後半2音符は "re" のメリスマ
    notes = [_note(0.0), _note(1.0), _note(2.0), _note(3.0)]
    syllables = ["do", "re"]

    # Act
    result = align_lyrics(notes, syllables)

    # Assert
    assert result[0] == {"note_index": 0, "syllable": "do", "melisma": False}
    assert result[1] == {"note_index": 1, "syllable": "re", "melisma": False}
    assert result[2] == {
        "note_index": 2,
        "syllable": MELISMA_CONTINUATION,
        "melisma": True,
    }
    assert result[3]["melisma"] is True


def test_syllable_boundary_starts_new_note_not_melisma() -> None:
    """新規音節の頭は必ず melisma=False(音節境界⇒音符境界の非対称制約)。"""
    # Arrange
    notes = [_note(0.0), _note(1.0), _note(2.0)]
    syllables = ["a", "b", "c"]

    # Act
    result = align_lyrics(notes, syllables)

    # Assert: 全て新規音節なので melisma は立たない
    assert [r["melisma"] for r in result] == [False, False, False]


def test_more_syllables_than_notes_reports_unassigned() -> None:
    """音節>音符では取りこぼしを count_unassigned で可視化する(grok BP6)。"""
    # Arrange: 5音節・2音符
    notes = [_note(0.0), _note(1.0)]
    syllables = ["ku", "ru", "ma", "no", "iro"]

    # Act
    result = align_lyrics(notes, syllables)
    unassigned = count_unassigned(notes, syllables)

    # Assert: 出力は音符数と同数、あふれ3音節を報告
    assert len(result) == 2
    assert [r["syllable"] for r in result] == ["ku", "ru"]
    assert unassigned == 3


def test_blank_and_whitespace_syllables_are_dropped() -> None:
    """空文字・空白のみの音節は除去される(悪い転写対策・grok 3.6)。"""
    # Arrange
    notes = [_note(0.0), _note(1.0)]
    syllables = ["", "  ", " ha ", "\t"]

    # Act
    result = align_lyrics(notes, syllables)

    # Assert: 実体のある "ha"(前後空白除去)のみ割当、残り音符はメリスマ
    assert result[0]["syllable"] == "ha"
    assert result[0]["melisma"] is False
    assert result[1]["melisma"] is True


def test_empty_syllables_yields_empty_lyric_notes() -> None:
    """音節が皆無なら全音符 syllable=""・melisma=False。"""
    # Arrange
    notes = [_note(0.0), _note(1.0)]
    syllables: list[str] = []

    # Act
    result = align_lyrics(notes, syllables)

    # Assert
    assert [r["syllable"] for r in result] == ["", ""]
    assert all(r["melisma"] is False for r in result)
    assert count_unassigned(notes, syllables) == 0


def test_empty_notes_returns_empty_list() -> None:
    """音符が空なら空 list を返し、あふれ音節は全数報告。"""
    # Arrange
    notes: list[QuantizedNote] = []
    syllables = ["x", "y"]

    # Act
    result = align_lyrics(notes, syllables)

    # Assert
    assert result == []
    assert count_unassigned(notes, syllables) == 2


def test_records_are_note_indexed_and_complete() -> None:
    """戻り値は音符と同数・note_index は 0..n-1 で網羅する。"""
    # Arrange
    notes = [_note(float(i)) for i in range(6)]
    syllables = ["one", "two"]

    # Act
    result = align_lyrics(notes, syllables)

    # Assert
    assert len(result) == len(notes)
    assert [r["note_index"] for r in result] == list(range(6))
