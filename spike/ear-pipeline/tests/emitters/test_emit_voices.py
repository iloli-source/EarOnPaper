"""test: voices エミッタ(F-019 声部分離・#109 B-2 結線)。"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import voices
from earpipe.services.emitters.base import EmitContext


def _ctx(notes, **params):
    return EmitContext(
        notes=notes,
        bpm=120.0,
        title="test voices",
        params={k: str(v) for k, v in params.items()},
    )


def test_module_contract():
    # Arrange / Act / Assert
    assert voices.KEY == "voices"
    assert voices.EXT == "musicxml"
    assert voices.NEEDS_MUSICXML is False
    assert voices.NEEDS_AUDIO is False


def test_emit_writes_nonempty_musicxml(tmp_path: Path):
    # Arrange: 三和音を含む多声部入力(声部分離が働く)
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=72, confidence=0.8),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=69, confidence=0.8),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=65, confidence=0.8),
    ]
    ctx = _ctx(notes)
    out = tmp_path / "voices.musicxml"

    # Act
    result = voices.emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "score-partwise" in text


def test_emit_produces_multiple_parts(tmp_path: Path):
    # Arrange: 明確に分離可能な三和音の連続
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=60, confidence=0.9),
    ]
    ctx = _ctx(notes, max_voices=3)
    out = tmp_path / "multi.musicxml"

    # Act
    voices.emit(ctx, out)

    # Assert: 複数パート(声部)が MusicXML に現れる
    text = out.read_text(encoding="utf-8")
    assert text.count("<score-part ") >= 2


def test_emit_handles_empty_notes(tmp_path: Path):
    # Arrange
    ctx = _ctx([])
    out = tmp_path / "empty.musicxml"

    # Act
    voices.emit(ctx, out)

    # Assert: 空入力でも非空ファイル(全休符1パート)を出す
    assert out.read_text(encoding="utf-8").strip() != ""
