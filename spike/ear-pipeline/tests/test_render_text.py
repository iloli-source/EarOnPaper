"""テキスト記譜PDF/PNG描画層(render_text.py・F-RENDER/Issue #88)のテスト。

先行研究(RENDER-grok / RENDER-codex)の失敗例を回帰項目に固定する:
- 偽レンダ禁止 → 生成PDFを pypdf で再読込し妥当性(1ページ以上・非空)まで検証。
- 行あふれ防止 → 長い記譜テキストが複数ページに折り返されることを検証。
- 豆腐化防止 → SVG に CJK 対応フォントスタックが明示注入されることを検証。
- SVG注入/壊れSVG防止 → タイトル中の '<' 等が XML エスケープされることを検証。

AAA(Arrange-Act-Assert)形式。描画の正しさ(OCR/目視)は親の別工程で担保する。
"""

from pathlib import Path

import pypdf
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.render_text import (
    _MONO_CJK_FONT_STACK,
    _esc,
    _layout_rows,
    _render_svg_pages,
    _wrap_line,
    render_jianpu_pdf,
    render_leadsheet_pdf,
    render_png_preview,
)


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    """量子化音符を1つ作るヘルパ。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


def span(start: float, end: float, name: str, root_pc: int, quality: str) -> ChordSpan:
    """ChordSpan を1つ作るヘルパ。"""
    return ChordSpan(
        start_beats=start, end_beats=end, name=name, root_pc=root_pc, quality=quality
    )


def _valid_pdf_page_count(path: Path) -> int:
    """PDFを読み直してページ数を返す(妥当性=非破損の代理)。"""
    reader = pypdf.PdfReader(str(path))
    return len(reader.pages)


class TestEscape:
    def test_escapes_xml_special_chars(self) -> None:
        # Arrange: SVG を壊す/注入し得る文字列
        raw = '<title> & "q"'
        # Act
        out = _esc(raw)
        # Assert: 生の < > & " が残らない
        assert "<" not in out
        assert ">" not in out
        assert "&amp;" in out
        assert "&quot;" in out


class TestWrapAndLayout:
    def test_wrap_line_splits_by_columns(self) -> None:
        # Arrange: 10文字を桁幅4で折り返す
        # Act
        rows = _wrap_line("0123456789", 4)
        # Assert: 4,4,2 の3行
        assert rows == ["0123", "4567", "89"]

    def test_wrap_line_keeps_empty_line(self) -> None:
        # Arrange/Act/Assert: 空行は空行として保持
        assert _wrap_line("", 4) == [""]

    def test_layout_rows_preserves_newlines(self) -> None:
        # Arrange: 2論理行(各短い)
        # Act
        rows = _layout_rows("ab\ncd", 80)
        # Assert: 折り返し不要でそのまま2行
        assert rows == ["ab", "cd"]


class TestRenderSvgPages:
    def test_injects_cjk_font_stack(self) -> None:
        # Arrange: 日本語タイトルを含む描画
        # Act
        svgs = _render_svg_pages("1 2 3", title="テスト曲", subhead="Jianpu")
        # Assert: CJK 対応フォントスタックが明示注入されている(豆腐化防止)
        assert _MONO_CJK_FONT_STACK in svgs[0]
        assert "テスト曲" in svgs[0]

    def test_title_special_chars_escaped(self) -> None:
        # Arrange: SVG を壊し得るタイトル
        # Act
        svgs = _render_svg_pages("1", title="a<b>c", subhead="")
        # Assert: 生タグが混入せずエスケープ済み
        assert "a<b>c" not in svgs[0]
        assert "a&lt;b&gt;c" in svgs[0]

    def test_long_text_paginates(self) -> None:
        # Arrange: 1ページに収まらない大量行
        text = "\n".join(f"line {i}" for i in range(400))
        # Act
        svgs = _render_svg_pages(text, title="長い譜", subhead="")
        # Assert: 複数ページに分割される(行あふれ防止)
        assert len(svgs) >= 2


class TestRenderJianpuPdf:
    def test_creates_valid_pdf(self, tmp_path: Path) -> None:
        # Arrange: C長調(tonic_pc=0)のドレミファソ
        notes = [qn(i, 1, 60 + p) for i, p in enumerate([0, 2, 4, 5, 7])]
        out = tmp_path / "jianpu.pdf"
        # Act
        result = render_jianpu_pdf(notes, key_tonic_pc=0, out_path=out, title="音階")
        # Assert: パスが返り、再読込で妥当(1ページ以上)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        assert _valid_pdf_page_count(out) >= 1

    def test_empty_notes_still_valid_pdf(self, tmp_path: Path) -> None:
        # Arrange: 空の音符列
        out = tmp_path / "empty.pdf"
        # Act
        render_jianpu_pdf([], key_tonic_pc=0, out_path=out)
        # Assert: 空でも壊れないPDFが出る
        assert _valid_pdf_page_count(out) >= 1

    def test_long_input_multipage_pdf(self, tmp_path: Path) -> None:
        # Arrange: 折り返し・改ページを誘発する長い音符列
        notes = [qn(i, 0.25, 48 + (i % 36)) for i in range(2000)]
        out = tmp_path / "long.pdf"
        # Act
        render_jianpu_pdf(notes, key_tonic_pc=0, out_path=out, title="長い簡譜")
        # Assert: 複数ページで妥当
        assert _valid_pdf_page_count(out) >= 2


class TestRenderLeadsheetPdf:
    def test_creates_valid_pdf(self, tmp_path: Path) -> None:
        # Arrange: C-Am-F-G の4小節進行＋各小節頭の単音メロディ
        chords = [
            span(0, 4, "C", 0, "major"),
            span(4, 8, "Am", 9, "minor"),
            span(8, 12, "F", 5, "major"),
            span(12, 16, "G", 7, "major"),
        ]
        notes = [qn(0, 1, 60), qn(4, 1, 69), qn(8, 1, 65), qn(12, 1, 67)]
        out = tmp_path / "leadsheet.pdf"
        # Act
        result = render_leadsheet_pdf(
            notes, chords, bpm=120.0, out_path=out, title="リードシート"
        )
        # Assert
        assert result == out
        assert out.exists()
        assert _valid_pdf_page_count(out) >= 1

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        # Arrange: 未作成のネストしたパス
        out = tmp_path / "nested" / "deep" / "ls.pdf"
        notes = [qn(0, 1, 60)]
        chords = [span(0, 4, "C", 0, "major")]
        # Act
        render_leadsheet_pdf(notes, chords, bpm=90.0, out_path=out)
        # Assert: 親ディレクトリが自動作成され妥当なPDF
        assert out.exists()
        assert _valid_pdf_page_count(out) >= 1


class TestRenderPngPreview:
    def test_creates_png_file(self, tmp_path: Path) -> None:
        # Arrange
        out = tmp_path / "preview.png"
        # Act
        result = render_png_preview("1 2 3 5", out_path=out, title="プレビュー", subhead="Jianpu")
        # Assert: PNG が出力される(先頭が PNG シグネチャ)
        assert result == out
        assert out.exists()
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
