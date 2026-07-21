"""fingering エミッタのスモーク: notes→運指(指番号・手)レポートを非空で出す。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.fingering import (
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
    assert KEY == "fingering"
    assert EXT == "txt"
    assert NEEDS_AUDIO is False
    assert NEEDS_MUSICXML is False


def test_emit_writes_non_empty_report(tmp_path):
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="test")
    out_path = tmp_path / "fingering.txt"

    # Act
    result = emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "note_count: 5" in text
    # 各実音に指番号(1-5)が付く
    assert any(f"finger={f}" in text for f in (1, 2, 3, 4, 5))


def test_emit_auto_hand_splits_left_and_right(tmp_path):
    # Arrange: 低域と高域を混在させ auto 割当で両手が現れることを確認
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=48, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=50, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=72, confidence=0.9),
        QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=74, confidence=0.9),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="auto", params={"hand": "auto"})
    out_path = tmp_path / "fingering_auto.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "hand: auto" in text
    assert "right" in text
    assert "left" in text


def test_emit_skips_rest_notes(tmp_path):
    # Arrange: 休符(midi<0)は運指対象外として結果に含めない
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=-1, confidence=0.0),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=64, confidence=0.9),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="rest")
    out_path = tmp_path / "fingering_rest.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "note_count: 2" in text
