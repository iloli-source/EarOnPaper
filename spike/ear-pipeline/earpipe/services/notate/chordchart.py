"""コード譜専用ビュー(#123): コードネーム＋押さえ図＋メロディ音名行。

ユーザーテストで『TABよりコード譜派』の声があり、従来コード押さえ図は TAB の
コード帯にしか無かった。本モジュールは TAB/五線譜とは独立に、各小節へ
コードネーム＋横向き押さえ図を並べ、その下にメロディを音名で表示する
『コード譜』PDF を出力する。

レイアウトは五線譜/TAB と同じ A4 縦・4小節/システムに揃える。図(押さえ図)は
chord_shapes.diagram_svg を再利用し、TAB のコード帯と同じ見た目に保つ。
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
_BEATS_PER_MEASURE = 4
_HEADER_H = 210
_SYS_H = 250            # 1システム(押さえ図帯＋メロディ行)の高さ
_SYS_GAP = 70
_DIAGRAM_SCALE = 2.0    # 押さえ図の拡大率(可読性)
_DIAGRAM_Y = 70         # システム上端からの押さえ図Yオフセット
_MELODY_Y = 210         # システム上端からのメロディ音名Yオフセット

_SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _note_name(midi: int) -> str:
    """MIDIノート番号を音名(オクターブ付き)へ。60→'C4'(中央ハ)。"""
    return f"{_SHARP_NAMES[midi % 12]}{midi // 12 - 1}"


def _melody_line(notes: Sequence[QuantizedNote]) -> list[tuple[float, int]]:
    """各オンセットの最高音(スカイライン=主旋律)を (start_beats, midi) で返す。"""
    by_start: dict[float, int] = {}
    for n in notes:
        cur = by_start.get(n.start_beats)
        if cur is None or n.midi > cur:
            by_start[n.start_beats] = n.midi
    return sorted(by_start.items())


def _x_of(mi: int, beat_in: float, meas_w: float) -> float:
    return _MARGIN + mi * meas_w + (beat_in / _BEATS_PER_MEASURE) * meas_w


def _draw_system(
    m0: int,
    sys_top: float,
    meas_w: float,
    chords: Sequence[ChordSpan],
    melody: Sequence[tuple[float, int]],
) -> list[str]:
    """1システム(m0..m0+4小節)のコード帯＋メロディ行＋小節線を描く。"""
    sys_start = m0 * _BEATS_PER_MEASURE
    sys_end = (m0 + _MEASURES_PER_SYS) * _BEATS_PER_MEASURE
    parts: list[str] = []

    # 小節線(縦の薄い区切り) + ベースライン
    base_y = sys_top + _MELODY_Y + 16
    for mi in range(_MEASURES_PER_SYS + 1):
        x = _MARGIN + mi * meas_w
        parts.append(
            f'<line x1="{x:.1f}" y1="{sys_top + _DIAGRAM_Y - 30:.1f}" '
            f'x2="{x:.1f}" y2="{base_y:.1f}" stroke="#ccc" stroke-width="1"/>'
        )
    parts.append(
        f'<line x1="{_MARGIN}" y1="{base_y:.1f}" x2="{_PAGE_W - _MARGIN}" '
        f'y2="{base_y:.1f}" stroke="#999" stroke-width="1.2"/>'
    )

    # コードネーム＋押さえ図
    for cs in chords:
        if cs.name == "N.C." or not (sys_start <= cs.start_beats < sys_end):
            continue
        mi = int(cs.start_beats // _BEATS_PER_MEASURE) - m0
        beat_in = cs.start_beats - (m0 + mi) * _BEATS_PER_MEASURE
        cx = _x_of(mi, beat_in, meas_w) + 30
        shape = shape_for(cs.root_pc, cs.quality)
        parts.append(diagram_svg(shape, cs.name, cx, sys_top + _DIAGRAM_Y, scale=_DIAGRAM_SCALE))

    # メロディ音名
    for start_beats, midi in melody:
        if not (sys_start <= start_beats < sys_end):
            continue
        mi = int(start_beats // _BEATS_PER_MEASURE) - m0
        beat_in = start_beats - (m0 + mi) * _BEATS_PER_MEASURE
        mx = _x_of(mi, beat_in, meas_w) + 30
        parts.append(
            f'<text x="{mx:.1f}" y="{sys_top + _MELODY_Y:.1f}" font-size="30" '
            f'text-anchor="middle" fill="#222">{_esc(_note_name(midi))}</text>'
        )
    return parts


def _render_chordchart_pages(
    notes: Sequence[QuantizedNote],
    chords: Sequence[ChordSpan],
    bpm: float,
    title: str | None = None,
) -> list[str]:
    """コード譜のSVGページ列を返す(1ページ=A4縦)。"""
    meas_w = (_PAGE_W - 2 * _MARGIN) / _MEASURES_PER_SYS
    melody = _melody_line(notes)

    last_beat = 0.0
    if melody:
        last_beat = max(last_beat, melody[-1][0])
    for cs in chords:
        if cs.name != "N.C.":
            last_beat = max(last_beat, cs.start_beats)
    n_measures = int(last_beat // _BEATS_PER_MEASURE) + 1
    n_systems = (n_measures + _MEASURES_PER_SYS - 1) // _MEASURES_PER_SYS

    sys_pitch = _SYS_H + _SYS_GAP
    sys_per_page_first = max(1, int((_PAGE_H - 2 * _MARGIN - _HEADER_H) // sys_pitch))
    sys_per_page = max(1, int((_PAGE_H - 2 * _MARGIN) // sys_pitch))

    pages: list[str] = []
    sys_idx = 0
    while sys_idx < n_systems or not pages:
        first = not pages
        cap = sys_per_page_first if first else sys_per_page
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_PAGE_W}" height="{_PAGE_H}" '
            f'viewBox="0 0 {_PAGE_W} {_PAGE_H}" '
            f'font-family="\'Arial Unicode MS\', \'Hiragino Sans\', \'Noto Sans CJK JP\', '
            f'Helvetica, Arial, sans-serif">',
            f'<rect width="{_PAGE_W}" height="{_PAGE_H}" fill="white"/>',
        ]
        y = _MARGIN
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
        for _ in range(cap):
            if sys_idx >= n_systems:
                break
            m0 = sys_idx * _MEASURES_PER_SYS
            parts.extend(_draw_system(m0, y, meas_w, chords, melody))
            y += sys_pitch
            sys_idx += 1
        parts.append("</svg>")
        pages.append("".join(parts))
    return pages


def render_chordchart_pdf(
    notes: Sequence[QuantizedNote],
    chords: Sequence[ChordSpan],
    bpm: float,
    out_path: str | Path,
    title: str | None = None,
) -> Path:
    """コード譜(コードネーム＋押さえ図＋メロディ音名)をPDFへ書き出す。

    生成後にPDFを読み直して1ページ以上あることを検証する(偽レンダ禁止)。
    """
    import cairosvg
    import pypdf

    svgs = _render_chordchart_pages(notes, chords, bpm, title)
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
