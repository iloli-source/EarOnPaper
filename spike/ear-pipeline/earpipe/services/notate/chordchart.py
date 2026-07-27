"""コード譜専用ビュー(#123, 可読化改修 #150): legend＋小節グリッド。

ユーザーテストで『TABよりコード譜派』の声があり、従来コード押さえ図は TAB の
コード帯にしか無かった。初版はコード＋押さえ図＋メロディ音名行を1行に詰めて
いたが、実曲ではラベルが衝突して判読不能だった(#150)。本改修で市販コード譜の
標準形に揃える:

- 冒頭 legend: 曲中に現れるユニークコードの押さえ図＋コード名を一覧表示。
  押さえ図はギター奏者向けのため diagrams=False で丸ごと省略できる
  (ヴォーカル＆コード用途ではコードネームだけが本体)
- 本体グリッド: 4小節/行の小節グリッドに、コードネームだけを大きく表示。
  コード変化は半小節単位に整理し、1小節あたり最大2スロット
- 拍子は明示指定 > estimate_meter 推定 > 4/4退避(五線譜側と同じ推定器)
- メロディ音名行は廃止(旋律は五線譜 PDF / MusicXML 側が担う)

正直な限界: 空欄の小節は「直前のコードの継続、または確信度不足(N.C.)」を
意味する(初版から同じ方針・脚注として紙面にも明記)。自動コード推定自体が
誤り得ることに変わりはない。
生成後は PDF を読み直して妥当性を検証する(偽レンダ禁止)。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.chord_shapes import diagram_svg, shape_for

_PAGE_W, _PAGE_H = 2100, 2970
_MARGIN = 130
_MEASURES_PER_SYS = 4
_DEFAULT_BEATS = 4      # beats_per_measure 未指定・推定不能時の退避値(4/4)
_HEADER_H = 210

# legend(押さえ図一覧)
_LEGEND_SCALE = 2.2
_LEGEND_ITEM_W = 230        # legend 1項目の横ピッチ
_LEGEND_ITEM_H = 190        # legend 1行の縦ピッチ(図＋コード名)
_LEGEND_GAP_BELOW = 60      # legend とグリッドの間隔

# 本体グリッド
_GRID_CHORD_FONT = 46       # グリッドのコードネーム
_SYS_H = 110                # 1行(コード行のみ)の高さ
_SYS_GAP = 55
_MEAS_NO_FONT = 20          # 行頭の小節番号
_FOOTNOTE_FONT = 22


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _dominant_chord(chords: Sequence[ChordSpan], lo: float, hi: float) -> ChordSpan | None:
    """区間 [lo, hi) を最も長く占める非 N.C. コードを返す(無ければ None)。"""
    best: ChordSpan | None = None
    best_overlap = 0.0
    for cs in chords:
        if cs.name == "N.C.":
            continue
        overlap = min(cs.end_beats, hi) - max(cs.start_beats, lo)
        if overlap > best_overlap:
            best, best_overlap = cs, overlap
    return best


def _measure_slots(
    chords: Sequence[ChordSpan], n_measures: int, beats: int
) -> list[list[tuple[float, ChordSpan]]]:
    """小節ごとのコードスロット(最大2: 小節頭/半小節)へ整理する(#150)。

    半小節単位の優勢コードを採用し、前半=後半なら1スロットへ統合、
    直前スロットと同名の連続は省略(空欄=継続)する。
    """
    half = beats / 2
    slots: list[list[tuple[float, ChordSpan]]] = []
    prev_name: str | None = None
    for m in range(n_measures):
        m_lo = float(m * beats)
        first = _dominant_chord(chords, m_lo, m_lo + half)
        second = _dominant_chord(chords, m_lo + half, m_lo + beats)
        measure: list[tuple[float, ChordSpan]] = []
        if first and second and first.name == second.name:
            second = None
        for beat_in, cs in ((0.0, first), (half, second)):
            if cs is None or cs.name == prev_name:
                continue
            measure.append((beat_in, cs))
            prev_name = cs.name
        slots.append(measure)
    return slots


def _unique_chords(chords: Sequence[ChordSpan]) -> list[ChordSpan]:
    """出現順のユニークコード(非 N.C.)。legend 用。"""
    seen: set[str] = set()
    out: list[ChordSpan] = []
    for cs in chords:
        if cs.name == "N.C." or cs.name in seen:
            continue
        seen.add(cs.name)
        out.append(cs)
    return out


def _draw_legend(chords: Sequence[ChordSpan], y: float) -> tuple[list[str], float]:
    """冒頭の押さえ図 legend を描き、(SVG断片, 消費後のy) を返す。"""
    unique = _unique_chords(chords)
    if not unique:
        return [], y
    per_row = max(1, int((_PAGE_W - 2 * _MARGIN) // _LEGEND_ITEM_W))
    parts: list[str] = []
    for i, cs in enumerate(unique):
        col, row = i % per_row, i // per_row
        x = _MARGIN + col * _LEGEND_ITEM_W
        top = y + row * _LEGEND_ITEM_H
        shape = shape_for(cs.root_pc, cs.quality)
        parts.append(diagram_svg(shape, "", x, top, scale=_LEGEND_SCALE))
        parts.append(
            f'<text x="{x + 50:.1f}" y="{top + 155:.1f}" font-size="30" font-weight="bold" '
            f'text-anchor="middle" fill="#111" class="legend-name">{_esc(cs.name)}</text>'
        )
    n_rows = (len(unique) + per_row - 1) // per_row
    return parts, y + n_rows * _LEGEND_ITEM_H + _LEGEND_GAP_BELOW


def _draw_system(
    m0: int,
    sys_top: float,
    meas_w: float,
    slots: Sequence[Sequence[tuple[float, ChordSpan]]],
    beats: int,
) -> list[str]:
    """1行(m0..m0+4小節)の小節線とコードネームを描く。"""
    base_y = sys_top + _SYS_H - 20
    parts: list[str] = [
        f'<text x="{_MARGIN - 14:.1f}" y="{sys_top + 24:.1f}" font-size="{_MEAS_NO_FONT}" '
        f'text-anchor="end" fill="#999">{m0 + 1}</text>'
    ]
    for mi in range(_MEASURES_PER_SYS + 1):
        x = _MARGIN + mi * meas_w
        parts.append(
            f'<line x1="{x:.1f}" y1="{sys_top:.1f}" x2="{x:.1f}" y2="{base_y:.1f}" '
            f'stroke="#999" stroke-width="2"/>'
        )
    parts.append(
        f'<line x1="{_MARGIN}" y1="{base_y:.1f}" x2="{_PAGE_W - _MARGIN}" '
        f'y2="{base_y:.1f}" stroke="#999" stroke-width="2"/>'
    )
    for mi in range(_MEASURES_PER_SYS):
        m = m0 + mi
        if m >= len(slots):
            break
        for beat_in, cs in slots[m]:
            x = _MARGIN + mi * meas_w + (beat_in / beats) * meas_w + 18
            parts.append(
                f'<text x="{x:.1f}" y="{sys_top + 66:.1f}" font-size="{_GRID_CHORD_FONT}" '
                f'font-weight="bold" fill="#111" class="grid-chord">{_esc(cs.name)}</text>'
            )
    return parts


def _resolve_beats(notes: Sequence[QuantizedNote], beats_per_measure: int | None) -> int:
    """拍子(1小節の拍数)を決める。明示指定 > 音符列から推定 > 4/4退避。"""
    if beats_per_measure and beats_per_measure > 0:
        return beats_per_measure
    if notes:
        from earpipe.services.rhythm.meter import estimate_meter

        est = estimate_meter(list(notes))
        if est > 0:
            return est
    return _DEFAULT_BEATS


def _render_chordchart_pages(
    notes: Sequence[QuantizedNote],
    chords: Sequence[ChordSpan],
    bpm: float,
    title: str | None = None,
    diagrams: bool = True,
    beats_per_measure: int | None = None,
) -> list[str]:
    """コード譜のSVGページ列を返す(1ページ=A4縦)。notes は小節数・拍子の推定にのみ使う。"""
    meas_w = (_PAGE_W - 2 * _MARGIN) / _MEASURES_PER_SYS
    beats = _resolve_beats(notes, beats_per_measure)

    last_beat = 0.0
    for n in notes:
        last_beat = max(last_beat, n.start_beats)
    for cs in chords:
        if cs.name != "N.C.":
            last_beat = max(last_beat, cs.start_beats)
    n_measures = int(last_beat // beats) + 1
    n_systems = (n_measures + _MEASURES_PER_SYS - 1) // _MEASURES_PER_SYS
    slots = _measure_slots(chords, n_measures, beats)

    sys_pitch = _SYS_H + _SYS_GAP
    pages: list[str] = []
    sys_idx = 0
    while sys_idx < n_systems or not pages:
        first = not pages
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_PAGE_W}" height="{_PAGE_H}" '
            f'viewBox="0 0 {_PAGE_W} {_PAGE_H}" '
            f'font-family="\'Arial Unicode MS\', \'Hiragino Sans\', \'Noto Sans CJK JP\', '
            f'Helvetica, Arial, sans-serif">',
            f'<rect width="{_PAGE_W}" height="{_PAGE_H}" fill="white"/>',
        ]
        y: float = _MARGIN
        if first:
            parts.append(
                f'<text x="{_PAGE_W / 2}" y="{y + 40}" font-size="48" '
                f'text-anchor="middle">{_esc(title or "Chord chart")}</text>'
            )
            parts.append(
                f'<text x="{_PAGE_W / 2}" y="{y + 92}" font-size="26" text-anchor="middle" '
                f'fill="#444">Chord chart | BPM {int(round(bpm))}</text>'
            )
            y += _HEADER_H
            if diagrams:
                legend_parts, y = _draw_legend(chords, y)
                parts.extend(legend_parts)
        while sys_idx < n_systems and y + _SYS_H <= _PAGE_H - _MARGIN:
            parts.extend(_draw_system(sys_idx * _MEASURES_PER_SYS, y, meas_w, slots, beats))
            y += sys_pitch
            sys_idx += 1
        # 脚注は全ページに置く(2ページ目以降の空欄小節にも説明が要る)
        parts.append(
            f'<text x="{_MARGIN}" y="{_PAGE_H - _MARGIN + 50:.1f}" '
            f'font-size="{_FOOTNOTE_FONT}" fill="#888">'
            f'{_esc("空欄の小節 = 直前のコードの継続、または推定確信度不足(N.C.)")}</text>'
        )
        parts.append("</svg>")
        pages.append("".join(parts))
    return pages


def render_chordchart_pdf(
    notes: Sequence[QuantizedNote],
    chords: Sequence[ChordSpan],
    bpm: float,
    out_path: str | Path,
    title: str | None = None,
    diagrams: bool = True,
    beats_per_measure: int | None = None,
) -> Path:
    """コード譜(legend＋小節グリッド)をPDFへ書き出す。

    diagrams=False で押さえ図legendを省略する(ヴォーカル＆コード用途 #150。
    押さえ図はギター奏者向けのオプトイン)。beats_per_measure 未指定時は
    音符列から拍子を推定する(五線譜側と同じ estimate_meter)。
    生成後にPDFを読み直して1ページ以上あることを検証する(偽レンダ禁止)。
    """
    import cairosvg
    import pypdf

    svgs = _render_chordchart_pages(
        notes, chords, bpm, title, diagrams=diagrams, beats_per_measure=beats_per_measure
    )
    writer = pypdf.PdfWriter()
    for svg in svgs:
        pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        writer.write(f)

    verify = pypdf.PdfReader(str(out_path))
    if len(verify.pages) < 1:
        raise RuntimeError(f"生成PDFのページが0です: {out_path}")
    return out_path
