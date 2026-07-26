"""notesjson エミッタのテスト(#147 剪定前提(a): confidence込みノート列の機械可読出力)。"""

from __future__ import annotations

import json
import math

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.notesjson import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _notes() -> list[QuantizedNote]:
    return [
        QuantizedNote(
            start_beats=0.0, dur_beats=1.0, midi=60,
            confidence=0.91, onset_sec=0.12, offset_sec=0.55,
        ),
        QuantizedNote(
            start_beats=1.0, dur_beats=0.5, midi=64,
            confidence=0.42, onset_sec=0.62, offset_sec=0.88,
        ),
    ]


def test_module_contract():
    # Arrange / Act / Assert
    assert KEY == "notesjson"
    assert EXT == "json"
    assert NEEDS_MUSICXML is False
    assert NEEDS_AUDIO is False


def test_emit_preserves_confidence_and_timing(tmp_path):
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=105.0, title="テスト")
    out = tmp_path / "notes.json"

    # Act
    result = emit(ctx, out)

    # Assert
    assert result == out
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bpm"] == 105.0
    assert payload["n_notes"] == 2
    first = payload["notes"][0]
    assert first["midi"] == 60
    assert first["confidence"] == 0.91
    assert first["onset_sec"] == 0.12
    assert first["offset_sec"] == 0.55
    assert first["start_beats"] == 0.0
    assert first["dur_beats"] == 1.0
    assert payload["notes"][1]["confidence"] == 0.42


def test_emit_nan_timing_becomes_null(tmp_path):
    # Arrange: 実タイミング未設定(NaN)のノートは JSON では null にする(strict JSON)
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=57, confidence=0.5)]
    ctx = EmitContext(notes=notes, bpm=120.0, title="未設定タイミング")
    out = tmp_path / "nan.json"

    # Act
    emit(ctx, out)

    # Assert
    raw = out.read_text(encoding="utf-8")
    assert "NaN" not in raw  # json.loads が通っても NaN リテラルは strict 違反
    payload = json.loads(raw)
    note = payload["notes"][0]
    assert note["onset_sec"] is None
    assert note["offset_sec"] is None
    assert not any(
        isinstance(v, float) and math.isnan(v) for v in note.values()
    )


def test_emit_empty_notes(tmp_path):
    # Arrange
    ctx = EmitContext(notes=[], bpm=120.0, title="空")
    out = tmp_path / "empty.json"

    # Act
    emit(ctx, out)

    # Assert
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["n_notes"] == 0
    assert payload["notes"] == []
