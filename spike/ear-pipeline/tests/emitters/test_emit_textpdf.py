"""textpdf エミッタのテスト(#109 B-2 結線: render_text の PDF 層を到達可能化)。

notes→PDF の副次成果物生成を、jianpu(既定)/leadsheet 両 format で検証する。
render_jianpu_pdf / render_leadsheet_pdf が内部で PDF を再読込妥当性検証するため、
ここでは emit が非空 PDF ファイルを書き出すことを assert すれば結線を確認できる。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import textpdf
from earpipe.services.emitters.base import EmitContext


def _notes() -> list[QuantizedNote]:
    # ドレミソ相当の最小旋律(調・コード推定が成立する最小限)。
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=72, confidence=0.9),
    ]


def test_emit_jianpu_writes_nonempty_pdf(tmp_path: Path) -> None:
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="テスト曲")
    out = tmp_path / "out.pdf"

    # Act
    result = textpdf.emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.read_bytes().startswith(b"%PDF")


def test_emit_leadsheet_writes_nonempty_pdf(tmp_path: Path) -> None:
    # Arrange
    ctx = EmitContext(
        notes=_notes(), bpm=120.0, title="LS", params={"format": "leadsheet"}
    )
    out = tmp_path / "ls.pdf"

    # Act
    result = textpdf.emit(ctx, out)

    # Assert
    assert result == out
    assert out.stat().st_size > 0
    assert out.read_bytes().startswith(b"%PDF")


def test_emitter_contract_attributes() -> None:
    # Arrange / Act / Assert
    assert textpdf.KEY == "textpdf"
    assert textpdf.EXT == "pdf"
    assert textpdf.NEEDS_MUSICXML is False
    assert textpdf.NEEDS_AUDIO is False
