"""F-RENDER テキスト記譜(簡譜/リードシート)のPDF/PNG描画層(Issue #88)。

`to_jianpu`(jianpu.py)/`to_leadsheet`(leadsheet.py)が生成する monospace の
テキスト記譜を、自前SVG → cairosvg → pypdf の描画スタック(tab.py と同方式・
Verovio非依存)で PDF / PNG に組版する。五線譜(engrave.py)は Verovio を使うが、
テキスト記譜はグリフではなく等幅文字の桁揃えが本体なので、五線譜スタックに
乗せず単純な `<text>` ベースの自前SVGで描く。

設計方針(先行研究 RENDER-grok / RENDER-codex の失敗例を反映):

1. CJK豆腐化の防止(codex「PDFでは出るがSVG/browserで豆腐(□)」/ grok 3.5-C):
   cairosvg はフォント未指定テキストを CJK 非対応フォントで描き日本語が □ 化する。
   engrave.py の `cjk_safe_header_svg` 方式に倣い、全 `<text>` に CJK 対応フォント
   スタック(等幅→CJK フォールバック)を明示注入する。等幅字形が桁揃えの前提。

2. SVG インジェクション/壊れSVGの防止(grok 3.9 SVG経由XSS / codex「SVG text」):
   タイトルや記譜テキストは必ず XML エスケープしてから `<text>` に載せる。
   `<`, `>`, `&`, 引用符を素通しすると SVG が壊れる/注入経路になる。

3. 行あふれの防止(codex「line break: overflow」/ grok 改行後ずれ):
   長い1行はページ幅で強制折り返しする。等幅前提の桁数(_MAX_COLS)で機械的に
   折り返し、簡譜/リードシートの列構造(桁揃え)を崩さない。複数ページにも対応。

4. 偽レンダの禁止・実レンダ検証(grok 3.8「偽SVGスクショ」/ 3.10 実レンダ検証):
   本モジュールは生成後に PDF を pypdf で再読込し、少なくとも1ページを持つことを
   assert してから返す。テストはこの再読込妥当性まで検証する(OCR/目視は親の別工程)。

正直な限界:
- テキスト近似の限界(上下点・減時線・増時線の厳密な段組不可)は上流の
  jianpu.py / leadsheet.py が負う。本層はその文字列を忠実に等幅組版するだけで、
  組版で意味を補正しない(渡された文字列を唯一の真実とする)。
- 折り返しは「桁数での機械折り返し」であり、簡譜のフレーズ境界やリードシートの
  小節境界(`|`)を意味的に尊重しない。桁数を十分広く取り実用上の破綻を避けるが、
  極端に長い1小節では小節が途中で折れ得る(表示のみ・データは不変)。
- フォント埋め込みは cairosvg 既定に従う。環境により字形は変わり得るが、等幅+CJK
  フォールバックの明示でグリフ欠落(豆腐)は避ける。ピクセル一致は保証しない。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.jianpu import to_jianpu
from earpipe.services.notate.leadsheet import to_leadsheet
from earpipe.services.notate.movable_do import to_movable_do
from earpipe.services.notate.roman_nashville import to_nashville, to_roman

# A4縦(engrave.py / tab.py と同一ページ寸法)。
_PAGE_W: int = 2100
_PAGE_H: int = 2970
_MARGIN: int = 130

# 等幅本文の字送り・行送り(px)。_CHAR_W は monospace の1文字幅の近似で、
# 折り返し桁数の算定と字送りに使う(font-size と整合させて桁が揃うよう調整)。
_FONT_SIZE: int = 30
_CHAR_W: float = 18.0     # 等幅1文字の水平送り(font-size=30 の実測近似)
_LINE_H: float = 46.0     # 本文の行送り
_TITLE_SIZE: int = 48
_TITLE_H: float = 96.0    # タイトル行が占める縦幅
_SUBHEAD_SIZE: int = 26

# ページ幅に収まる等幅桁数。これを超える1行は機械的に折り返す(行あふれ防止)。
_MAX_COLS: int = int((_PAGE_W - 2 * _MARGIN) / _CHAR_W)

# engrave.py と同一の CJK 対応フォントスタック。先頭を等幅にして桁揃えを保ちつつ、
# CJK グリフは Hiragino / Noto にフォールバックさせ豆腐化を避ける。
_MONO_CJK_FONT_STACK: str = (
    "DejaVu Sans Mono, Menlo, Consolas, "
    "Hiragino Sans, Hiragino Kaku Gothic ProN, Noto Sans CJK JP, monospace"
)


def _esc(text: str) -> str:
    """SVG `<text>` に載せる前の XML エスケープ(注入・壊れSVGの防止)。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wrap_line(line: str, max_cols: int) -> list[str]:
    """1論理行を等幅桁数 max_cols で機械折り返しする(空行は空行として残す)。"""
    if max_cols < 1:
        max_cols = 1
    if line == "":
        return [""]
    return [line[i : i + max_cols] for i in range(0, len(line), max_cols)]


def _layout_rows(text: str, max_cols: int) -> list[str]:
    """記譜テキスト全体を、折り返し済みの描画行リストに展開する。"""
    rows: list[str] = []
    for logical in text.split("\n"):
        rows.extend(_wrap_line(logical, max_cols))
    return rows or [""]


def _paginate(rows: Sequence[str], rows_first: int, rows_rest: int) -> list[list[str]]:
    """描画行を、先頭ページ(タイトル分だけ少ない)と後続ページに分割する。"""
    rows_first = max(1, rows_first)
    rows_rest = max(1, rows_rest)
    pages: list[list[str]] = []
    idx = 0
    n = len(rows)
    first = True
    while idx < n or not pages:
        cap = rows_first if first else rows_rest
        chunk = list(rows[idx : idx + cap])
        pages.append(chunk)
        idx += cap
        first = False
        if idx >= n:
            break
    return pages


def _render_svg_pages(
    text: str, title: str | None, subhead: str
) -> list[str]:
    """記譜テキストを等幅組版した複数ページSVG文字列を返す。

    先頭ページ上部にタイトル(任意)とサブヘッダ(記譜種別・BPM等)を置き、
    以降は等幅本文を行ごとに `<text>` で描く。全 `<text>` に CJK 対応の等幅
    フォントスタックを明示して豆腐化を防ぐ。
    """
    rows = _layout_rows(text, _MAX_COLS)
    body_top_first = _MARGIN + _TITLE_H + _SUBHEAD_SIZE + 20
    body_top_rest = _MARGIN
    usable_h = _PAGE_H - _MARGIN
    rows_first = int((usable_h - body_top_first) // _LINE_H)
    rows_rest = int((usable_h - body_top_rest) // _LINE_H)
    page_rows = _paginate(rows, rows_first, rows_rest)

    svgs: list[str] = []
    for pi, chunk in enumerate(page_rows):
        first = pi == 0
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_PAGE_W}" '
            f'height="{_PAGE_H}" viewBox="0 0 {_PAGE_W} {_PAGE_H}" '
            f'font-family="{_MONO_CJK_FONT_STACK}">',
            f'<rect width="{_PAGE_W}" height="{_PAGE_H}" fill="white"/>',
        ]
        y = _MARGIN + _TITLE_SIZE
        if first:
            if title:
                parts.append(
                    f'<text x="{_PAGE_W / 2}" y="{y}" font-size="{_TITLE_SIZE}" '
                    f'text-anchor="middle" font-family="{_MONO_CJK_FONT_STACK}">'
                    f"{_esc(title)}</text>"
                )
            parts.append(
                f'<text x="{_MARGIN}" y="{y + _SUBHEAD_SIZE + 20}" '
                f'font-size="{_SUBHEAD_SIZE}" fill="#444" '
                f'font-family="{_MONO_CJK_FONT_STACK}">{_esc(subhead)}</text>'
            )
            by = _MARGIN + _TITLE_H + _SUBHEAD_SIZE + 20 + _LINE_H
        else:
            by = _MARGIN + _LINE_H
        for row in chunk:
            parts.append(
                f'<text x="{_MARGIN}" y="{by}" font-size="{_FONT_SIZE}" '
                f'xml:space="preserve" font-family="{_MONO_CJK_FONT_STACK}" '
                f'fill="#111">{_esc(row)}</text>'
            )
            by += _LINE_H
        parts.append(
            f'<text x="{_PAGE_W / 2}" y="{_PAGE_H - 56}" font-size="20" '
            f'text-anchor="middle" fill="#999" '
            f'font-family="{_MONO_CJK_FONT_STACK}">- {pi + 1} -</text>'
        )
        parts.append("</svg>")
        svgs.append("".join(parts))
    return svgs


def render_degrees_pdf(
    chords: list[ChordSpan],
    key_tonic_pc: int,
    mode: str,
    out_path: str | Path,
    title: str | None = None,
    style: str = "roman",
) -> Path:
    """コード進行の度数(ローマ数字/ナッシュビル)をPDFに描画する(#122)。

    簡譜/リードシートと同じ text→SVG→PDF 経路で、五線譜/TABと並ぶ視覚出力に
    する。style='roman' でローマ数字度数、'nashville' でナッシュビル番号。
    どの調基準かを隠さないよう主音を subhead に明記する。
    """
    if style == "nashville":
        symbols = to_nashville(chords, key_tonic_pc, mode)
        label = "Nashville numbers"
    else:
        symbols = to_roman(chords, key_tonic_pc, mode)
        label = "Roman numeral degrees"
    text = " ".join(symbols) if symbols else "(no chords)"
    subhead = f"{label} | tonic pc={key_tonic_pc % 12} {mode}"
    svgs = _render_svg_pages(text, title, subhead)
    return _write_pdf_from_svgs(svgs, Path(out_path))


def render_movable_do_pdf(
    notes: list[QuantizedNote],
    key_tonic_pc: int,
    out_path: str | Path,
    title: str | None = None,
) -> Path:
    """移動ド階名(do re mi …)をPDFに描画する(#122)。

    簡譜/リードシートと同じ text→SVG→PDF 経路。何調基準の階名かを隠さない
    よう主音を subhead に明記する。
    """
    syllables = to_movable_do(notes, key_tonic_pc)
    text = " ".join(syllables) if syllables else "(no notes)"
    subhead = f"Movable-do solfege | tonic pc={key_tonic_pc % 12}"
    svgs = _render_svg_pages(text, title, subhead)
    return _write_pdf_from_svgs(svgs, Path(out_path))


def _write_pdf_from_svgs(svgs: Sequence[str], out_path: Path) -> Path:
    """SVG列を cairosvg→pypdf で1つのPDFに結合し、再読込妥当性を検証して返す。

    偽レンダ防止(grok 3.8/3.10): 書き出したPDFを pypdf で読み直し、1ページ以上
    あることを確認してからパスを返す。生成に失敗していれば例外で止まる。
    """
    import cairosvg
    import pypdf

    if not svgs:
        raise ValueError("描画対象のSVGが空です(記譜テキストが生成できていない)")

    writer = pypdf.PdfWriter()
    for svg in svgs:
        pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        writer.write(f)

    # 実レンダ検証: 書いたPDFを読み直して妥当性を確認する(偽レンダ禁止)。
    verify = pypdf.PdfReader(str(out_path))
    if len(verify.pages) < 1:
        raise RuntimeError(f"生成PDFのページが0です: {out_path}")
    return out_path


def render_jianpu_pdf(
    notes: list[QuantizedNote],
    key_tonic_pc: int,
    out_path: str | Path,
    title: str | None = None,
) -> Path:
    """量子化音符列を簡譜(数字譜)テキストとして組版し、PDFに書き出す。

    `to_jianpu`(jianpu.py)で生成した簡譜テキストを等幅+CJK 安全フォントで
    自前SVG化し、cairosvg→pypdf で PDF にする。長い1行はページ幅で折り返し、
    複数ページにも対応する。生成後にPDFを再読込して妥当性を検証する。

    Args:
        notes: 量子化済み音符列(QuantizedNote)。空なら空の簡譜として1ページ出力。
        key_tonic_pc: 主音のピッチクラス(0-11 前提。to_jianpu 側で % 12 正規化)。
        out_path: 出力PDFパス。親ディレクトリは自動作成する。
        title: 譜面タイトル(任意)。CJK タイトルも豆腐化しないよう明示フォント注入。

    Returns:
        書き出した PDF の Path(再読込で 1 ページ以上を確認済み)。
    """
    text = to_jianpu(notes, key_tonic_pc)
    subhead = f"Jianpu (numbered notation) | tonic pc={key_tonic_pc % 12}"
    svgs = _render_svg_pages(text, title, subhead)
    return _write_pdf_from_svgs(svgs, Path(out_path))


def render_leadsheet_pdf(
    notes: list[QuantizedNote],
    chords: list[ChordSpan],
    bpm: float,
    out_path: str | Path,
    title: str | None = None,
) -> Path:
    """音符列＋コード進行をリードシートテキストとして組版し、PDFに書き出す。

    `to_leadsheet`(leadsheet.py)で生成した2段(コード行/メロディ行)テキストを
    等幅+CJK 安全フォントで自前SVG化し、cairosvg→pypdf で PDF にする。等幅前提の
    桁揃え(小節 `|` 区切り)を保つため本文は monospace で描く。生成後にPDFを
    再読込して妥当性を検証する。

    Args:
        notes: 量子化済み音符列(拍単位 start_beats/dur_beats を使う)。
        chords: 推定済みコード進行(ChordSpan 列)。
        bpm: テンポ(ヘッダ・to_leadsheet の表示に使用)。
        out_path: 出力PDFパス。親ディレクトリは自動作成する。
        title: 譜面タイトル(任意)。

    Returns:
        書き出した PDF の Path(再読込で 1 ページ以上を確認済み)。
    """
    text = to_leadsheet(notes, chords, bpm)
    subhead = f"Lead sheet | BPM {bpm:g}"
    svgs = _render_svg_pages(text, title, subhead)
    return _write_pdf_from_svgs(svgs, Path(out_path))


def render_png_preview(
    text: str, out_path: str | Path, title: str | None = None, subhead: str = ""
) -> Path:
    """記譜テキストの先頭ページPNGプレビューを生成する(確認・デモ用)。

    PDF と同じ自前SVGの1ページ目を cairosvg で PNG 化する。テキストは呼び出し側
    (to_jianpu / to_leadsheet の出力等)から渡す汎用プレビュー。

    Args:
        text: 等幅前提の記譜テキスト(改行区切り)。
        out_path: 出力PNGパス。親ディレクトリは自動作成する。
        title: 譜面タイトル(任意)。
        subhead: サブヘッダ(記譜種別など。任意)。

    Returns:
        書き出した PNG の Path。
    """
    import cairosvg

    svgs = _render_svg_pages(text, title, subhead)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svgs[0].encode("utf-8"), write_to=str(out_path))
    return out_path
