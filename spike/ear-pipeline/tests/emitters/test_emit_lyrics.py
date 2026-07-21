"""lyrics エミッタのスモーク: notes+音節→歌詞同期レポートを非空で出す。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.lyrics import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _notes() -> list[QuantizedNote]:
    """MELODY_SIMPLE 先頭の上行音型に対応する最小ノート。"""
    specs = [
        (60, 0.0, 1.0),
        (62, 1.0, 1.0),
        (64, 2.0, 0.5),
        (65, 2.5, 0.5),
        (67, 3.0, 1.0),
    ]
    return [
        QuantizedNote(start_beats=s, dur_beats=d, midi=m, confidence=0.9)
        for m, s, d in specs
    ]


def test_module_contract():
    # Arrange / Act / Assert
    assert KEY == "lyrics"
    assert EXT == "txt"
    assert NEEDS_AUDIO is False
    assert NEEDS_MUSICXML is False


def test_emit_writes_non_empty_report(tmp_path):
    # Arrange: 音節5個を音符5個へ1対1で割り当て
    ctx = EmitContext(
        notes=_notes(),
        bpm=120.0,
        title="test",
        params={"syllables": "ら,ら,ら,ら,ら"},
    )
    out_path = tmp_path / "lyrics.txt"

    # Act
    result = emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "note_count: 5" in text
    assert "unassigned_syllables: 0" in text
    assert "melisma=False" in text


def test_emit_marks_melisma_when_syllables_run_out(tmp_path):
    # Arrange: 音節2個・音符5個 → 音節が尽きた後はメリスマ継続
    ctx = EmitContext(
        notes=_notes(),
        bpm=120.0,
        title="melisma",
        params={"syllables": "は,な"},
    )
    out_path = tmp_path / "lyrics_melisma.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "syllable_input: 2" in text
    assert "melisma=True" in text  # 余剰音符が直前音節の継続になる


def test_emit_reports_unassigned_when_notes_short(tmp_path):
    # Arrange: 音節7個・音符5個 → 2音節あふれる
    ctx = EmitContext(
        notes=_notes(),
        bpm=120.0,
        title="overflow",
        params={"syllables": "a,b,c,d,e,f,g"},
    )
    out_path = tmp_path / "lyrics_overflow.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "unassigned_syllables: 2" in text


def test_emit_no_lyrics_produces_empty_syllables(tmp_path):
    # Arrange: 歌詞なし(既定) → 全音符 syllable 空・melisma=False
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="none")
    out_path = tmp_path / "lyrics_none.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "note_count: 5" in text
    assert "syllable_input: 0" in text
    assert "melisma=True" not in text
