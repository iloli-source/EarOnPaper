"""convert エミッタのテスト(F-037/Issue #85 結線スモーク)。

staff->jianpu / staff->tab / tab->staff の3変換を1レポートに束ねる convert
エミッタが、実ノートから非空ファイルを生成することを検証する。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.convert import EXT, KEY, emit


def _notes() -> list[QuantizedNote]:
    # C長調スケール断片。TAB/簡譜/往復いずれも中身が出るよう複数音を並べる。
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=67, confidence=0.9),
    ]


def test_key_and_ext_are_wired():
    # Arrange / Act / Assert: レジストリ発見に必要な定数が担当KEYで定義済み。
    assert KEY == "convert"
    assert EXT == "txt"


def test_emit_writes_non_empty_report(tmp_path: Path):
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="テスト旋律")
    out_path = tmp_path / f"convert.{EXT}"

    # Act
    result = emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert text.strip() != ""
    # 3変換すべての節が出ていることで結線を確認する。
    assert "staff->jianpu" in text
    assert "staff->tab" in text
    assert "tab->staff" in text
    assert "note_count: 4" in text


def test_emit_empty_notes_still_writes(tmp_path: Path):
    # Arrange: 空入力でも例外を出さず非空レポートを書く(縮退の堅牢性)。
    ctx = EmitContext(notes=[], bpm=100.0, title="空")
    out_path = tmp_path / f"convert.{EXT}"

    # Act
    emit(ctx, out_path)

    # Assert
    assert out_path.read_text(encoding="utf-8").strip() != ""
