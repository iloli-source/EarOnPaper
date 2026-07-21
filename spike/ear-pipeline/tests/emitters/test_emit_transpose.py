"""transpose エミッタのスモーク/結線テスト(#109 B-2)。"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import transpose as transpose_emitter
from earpipe.services.emitters.base import EmitContext


def _notes() -> list[QuantizedNote]:
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=1.0),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=67, confidence=1.0),
    ]


def test_emit_writes_non_empty_musicxml(tmp_path: Path) -> None:
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="テスト曲",
                      params={"semitones": "3"})
    out = tmp_path / f"out.{transpose_emitter.EXT}"

    # Act
    result = transpose_emitter.emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0
    assert "<note" in out.read_text(encoding="utf-8")


def test_emit_transposes_pitch(tmp_path: Path) -> None:
    # Arrange: +2半音で C(60) は D(62) へ上がる。MusicXMLに D が現れる。
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="T",
                      params={"semitones": "2"})
    out = tmp_path / "out.musicxml"

    # Act
    transpose_emitter.emit(ctx, out)

    # Assert
    xml = out.read_text(encoding="utf-8")
    assert "<step>D</step>" in xml


def test_emit_default_semitones(tmp_path: Path) -> None:
    # Arrange: paramなしでも既定 semitones=2 で非空出力
    ctx = EmitContext(notes=_notes(), bpm=100.0, title="既定")
    out = tmp_path / "out.musicxml"

    # Act
    result = transpose_emitter.emit(ctx, out)

    # Assert
    assert result.stat().st_size > 0
