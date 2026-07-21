"""midiclean エミッタのスモーク+結線テスト(F-084 結線)。

cleanup_notes / RemovedNote が実採譜フロー(EmitContext)から到達可能になり、
非空のレポートファイルを出力できることを確認する。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.midiclean import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def test_module_contract() -> None:
    # Arrange / Act / Assert: モジュールレベル契約(レジストリ発見に必要)
    assert KEY == "midiclean"
    assert EXT == "txt"
    assert NEEDS_MUSICXML is False
    assert NEEDS_AUDIO is False


def test_emit_writes_nonempty_report(tmp_path) -> None:
    # Arrange: 本物の単音 + 完全重複(統合される)を含む最小ノート列
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.6),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.9),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="test")
    out_path = tmp_path / f"cleanup.{EXT}"

    # Act
    result = emit(ctx, out_path)

    # Assert: 非空ファイルが出力され、レポートに結線の痕跡がある
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert text.strip() != ""
    assert "input_count: 3" in text
    # 完全重複が1件統合され RemovedNote が可視化されている
    assert "exact_duplicate" in text


def test_emit_empty_notes(tmp_path) -> None:
    # Arrange: 空でも非空レポート(0件)を出す
    ctx = EmitContext(notes=[], bpm=120.0, title="empty")
    out_path = tmp_path / f"cleanup.{EXT}"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "input_count: 0" in text
    assert "removed_count: 0" in text
