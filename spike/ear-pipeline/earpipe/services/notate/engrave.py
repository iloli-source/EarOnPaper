"""五線譜のエングレービング: MusicXML → SVG/PDF（ADR-004: Verovio採択）。

パイプライン: MusicXML → verovio.toolkit（ページ毎SVG）
             → cairosvg（ページ毎PDF）→ pypdf（結合）。
完全ローカル処理（外部送信なし）。Verovio/cairosvg は LGPL-3.0（NF-029台帳登録済み）。
"""

import io
from pathlib import Path

# デフォルトのレンダリングオプション。A4縦・余白は控えめ（一次画面=五線のデフォルト表示に準拠）
_VEROVIO_OPTIONS = {
    "pageWidth": 2100,
    "pageHeight": 2970,
    "scale": 40,
    "adjustPageHeight": False,
    "footer": "none",
    "header": "auto",
}


def render_svg_pages(musicxml_path: str | Path) -> list[str]:
    """MusicXMLをページ毎のSVG文字列に描画する。"""
    import verovio

    tk = verovio.toolkit()
    tk.setOptions(_VEROVIO_OPTIONS)
    data = Path(musicxml_path).read_text(encoding="utf-8")
    if not tk.loadData(data):
        raise RuntimeError(f"Verovioが読み込めないMusicXML: {musicxml_path}")
    pages = tk.getPageCount()
    if pages < 1:
        raise RuntimeError(f"描画ページが0（空のスコア?）: {musicxml_path}")
    return [tk.renderToSVG(i) for i in range(1, pages + 1)]


def svg_note_count(svg: str) -> int:
    """SVG内の音符要素（notehead）の概数。テスト・健全性検査用の代理指標。"""
    return svg.count('class="note')


def write_pdf(musicxml_path: str | Path, out_pdf: str | Path) -> dict:
    """MusicXML → 複数ページPDF。生成結果のメタ情報を返す。"""
    import cairosvg
    from pypdf import PdfWriter

    svgs = render_svg_pages(musicxml_path)
    writer = PdfWriter()
    for svg in svgs:
        page_pdf = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(page_pdf))
        for page in reader.pages:
            writer.add_page(page)
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with out_pdf.open("wb") as f:
        writer.write(f)
    return {
        "pages": len(svgs),
        "notes_engraved": svg_note_count(svgs[0]) if svgs else 0,
        "pdf_path": str(out_pdf),
        "pdf_bytes": out_pdf.stat().st_size,
    }


def write_png_preview(musicxml_path: str | Path, out_png: str | Path, page: int = 1) -> str:
    """指定ページのPNGプレビューを生成する（確認・デモ用）。"""
    import cairosvg

    svgs = render_svg_pages(musicxml_path)
    idx = max(1, min(page, len(svgs))) - 1
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svgs[idx].encode("utf-8"), write_to=str(out_png))
    return str(out_png)
