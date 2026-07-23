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


def test_emit_jianpu_content_encodes_input_degrees(tmp_path: Path) -> None:
    # #115: 非空PDFだけでなく、簡譜の数字が入力音高(度数)を正しく表すことを検証。
    import pypdf

    # C長調のドレミファソ(midi 60..67, 同一オクターブ) = 度数 1 2 3 4 5
    notes = [
        QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=m, confidence=0.9)
        for i, m in enumerate([60, 62, 64, 65, 67])
    ]
    out = tmp_path / "deg.pdf"
    textpdf.emit(EmitContext(notes=notes, bpm=120.0, title="scale"), out)
    text = " ".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out)).pages)
    text_1line = text.replace("\n", " ")

    assert "Jianpu" in text  # 簡譜ヘッダ(結線)
    # 入力音高がそのまま度数列 1 2 3 4 5 として描画される(内容が入力に相関)
    assert "1 2 3 4 5" in text_1line


def test_emit_jianpu_content_differs_with_input(tmp_path: Path) -> None:
    # #115: 入力が変われば簡譜内容も変わる(固定テンプレの偽成功でない)。
    import pypdf

    def jianpu_text(midis: list[int]) -> str:
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=m, confidence=0.9)
            for i, m in enumerate(midis)
        ]
        out = tmp_path / f"j_{midis[0]}_{len(midis)}.pdf"
        textpdf.emit(EmitContext(notes=notes, bpm=120.0, title="x"), out)
        return " ".join(
            p.extract_text() or "" for p in pypdf.PdfReader(str(out)).pages
        ).replace("\n", " ")

    assert "1 2 3" in jianpu_text([60, 62, 64])   # ドレミ
    assert "5 4 3" in jianpu_text([67, 65, 64])   # ソファミ


def _chord_progression() -> list[QuantizedNote]:
    # C→F→G→C 和音進行(Cメジャー = 度数 I IV V I)
    prog = {0.0: (60, 64, 67), 4.0: (65, 69, 72), 8.0: (67, 71, 74), 12.0: (60, 64, 67)}
    return [
        QuantizedNote(start_beats=sb, dur_beats=4.0, midi=m, confidence=0.9)
        for sb, ms in prog.items()
        for m in ms
    ]


def _pdf_text(path: Path) -> str:
    import pypdf

    return " ".join(
        p.extract_text() or "" for p in pypdf.PdfReader(str(path)).pages
    ).replace("\n", " ")


def test_emit_roman_degrees_pdf(tmp_path: Path) -> None:
    # #122: 度数(ローマ数字)をPDF化。C→F→G→C = I IV V I が描画される。
    out = tmp_path / "roman.pdf"
    result = textpdf.emit(
        EmitContext(notes=_chord_progression(), bpm=120.0, title="R",
                    params={"format": "roman"}),
        out,
    )
    assert result == out
    assert out.read_bytes().startswith(b"%PDF")
    text = _pdf_text(out)
    assert "Roman numeral degrees" in text
    assert "I IV V" in text


def test_emit_nashville_degrees_pdf(tmp_path: Path) -> None:
    # #122: 度数(ナッシュビル番号)をPDF化。C→F→G→C = 1 4 5 1。
    out = tmp_path / "nash.pdf"
    textpdf.emit(
        EmitContext(notes=_chord_progression(), bpm=120.0, title="N",
                    params={"format": "nashville"}),
        out,
    )
    text = _pdf_text(out)
    assert "Nashville numbers" in text
    assert "1 4 5 1" in text


def test_emit_movable_do_pdf(tmp_path: Path) -> None:
    # #122: 移動ド階名をPDF化。C E G = Do Mi Sol が描画される。
    out = tmp_path / "solfege.pdf"
    textpdf.emit(
        EmitContext(notes=_chord_progression(), bpm=120.0, title="S",
                    params={"format": "movable_do"}),
        out,
    )
    assert out.read_bytes().startswith(b"%PDF")
    text = _pdf_text(out)
    assert "Movable-do solfege" in text
    for syll in ("Do", "Mi", "Sol"):
        assert syll in text


def test_emit_unknown_format_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError):
        textpdf.emit(
            EmitContext(notes=_notes(), bpm=120.0, title="x",
                        params={"format": "bogus"}),
            tmp_path / "x.pdf",
        )


def test_emitter_contract_attributes() -> None:
    # Arrange / Act / Assert
    assert textpdf.KEY == "textpdf"
    assert textpdf.EXT == "pdf"
    assert textpdf.NEEDS_MUSICXML is False
    assert textpdf.NEEDS_AUDIO is False
