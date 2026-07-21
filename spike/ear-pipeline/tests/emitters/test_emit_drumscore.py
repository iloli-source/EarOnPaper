"""test: drumscore エミッタ(F-036/Issue #89・#109 B-2 結線)。"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import drumscore
from earpipe.services.emitters.base import EmitContext


def _ctx(notes, **params):
    return EmitContext(
        notes=notes,
        bpm=120.0,
        title="test drums",
        params={k: str(v) for k, v in params.items()},
    )


def test_emit_writes_nonempty_musicxml(tmp_path: Path):
    # Arrange
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.8),
        QuantizedNote(start_beats=2.0, dur_beats=0.5, midi=64, confidence=0.7),
    ]
    ctx = _ctx(notes)
    out = tmp_path / "drums.musicxml"

    # Act
    result = drumscore.emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "score-partwise" in text


def test_emit_uses_kit_param_and_injects_midi_unpitched(tmp_path: Path):
    # Arrange: kick は GM 36 → midi-unpitched 37 が注入されるはず
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9)]
    ctx = _ctx(notes, kit="kick")
    out = tmp_path / "kick.musicxml"

    # Act
    drumscore.emit(ctx, out)

    # Assert
    text = out.read_text(encoding="utf-8")
    assert "<midi-unpitched>37</midi-unpitched>" in text


def test_emit_handles_empty_notes(tmp_path: Path):
    # Arrange
    ctx = _ctx([])
    out = tmp_path / "empty.musicxml"

    # Act
    drumscore.emit(ctx, out)

    # Assert
    assert out.read_text(encoding="utf-8").strip() != ""


def test_module_contract():
    # Arrange / Act / Assert
    assert drumscore.KEY == "drumscore"
    assert drumscore.EXT == "musicxml"
    assert drumscore.NEEDS_MUSICXML is False
    assert drumscore.NEEDS_AUDIO is False
