"""outprofile エミッタのテスト(F-103 結線スモーク)。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.outprofile import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _notes() -> list[QuantizedNote]:
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=1.0),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=67, confidence=1.0),
    ]


def test_module_contract():
    # Arrange / Act / Assert
    assert KEY == "outprofile"
    assert EXT == "musicxml"
    assert NEEDS_MUSICXML is False
    assert NEEDS_AUDIO is False


def test_emit_writes_nonempty_generic(tmp_path):
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="テスト")
    out = tmp_path / "out.musicxml"

    # Act
    result = emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert content.strip()
    assert "score-partwise" in content or "score-timewise" in content


def test_emit_dorico_target_produces_valid_xml(tmp_path):
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=100.0, title="Dorico", params={"target": "dorico"})
    out = tmp_path / "dorico.musicxml"

    # Act
    emit(ctx, out)

    # Assert
    import xml.etree.ElementTree as ET

    content = out.read_text(encoding="utf-8")
    assert content.strip()
    # Dorico プロファイル後も音符が壊れず XML としてパース可能であること。
    root = ET.fromstring(content)
    assert root.iter("note")
