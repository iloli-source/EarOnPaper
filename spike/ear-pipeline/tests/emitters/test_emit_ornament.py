"""ornament エミッタの結線テスト(F-082・#109 B-2)。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import ornament as ornament_emitter
from earpipe.services.emitters.base import EmitContext


def _note(start_beats, dur_beats, midi, confidence=0.9):
    return QuantizedNote(
        start_beats=start_beats,
        dur_beats=dur_beats,
        midi=midi,
        confidence=confidence,
    )


def test_emit_writes_non_empty_report_with_grace_candidate(tmp_path):
    # Arrange: 極短で隣接主音に近い微小音符(装飾候補)を含む列
    notes = [
        _note(0.0, 0.0625, 65),  # 極短・主音の直前 → grace/acciaccatura 候補
        _note(0.0625, 1.0, 64),  # 主音(隣接・音程1半音)
        _note(1.0, 1.0, 67),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="装飾テスト")
    out_path = tmp_path / "ornament.txt"

    # Act
    result = ornament_emitter.emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert text.strip() != ""
    assert "ornament_candidates: 1" in text
    assert "judgement=grace" in text


def test_emit_no_tiny_notes_still_writes_non_empty(tmp_path):
    # Arrange: 微小音符なし(全て本音符)
    notes = [_note(0.0, 1.0, 60), _note(1.0, 1.0, 62)]
    ctx = EmitContext(notes=notes, bpm=100.0, title="装飾なし")
    out_path = tmp_path / "ornament_none.txt"

    # Act
    ornament_emitter.emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert text.strip() != ""
    assert "ornament_candidates: 0" in text


def test_emitter_module_contract():
    # Arrange / Act / Assert: レジストリ発見に必要なモジュール契約
    assert ornament_emitter.KEY == "ornament"
    assert ornament_emitter.EXT == "txt"
    assert ornament_emitter.NEEDS_MUSICXML is False
    assert ornament_emitter.NEEDS_AUDIO is False
