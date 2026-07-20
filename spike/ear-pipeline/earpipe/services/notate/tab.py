"""TAB譜出力プロファイル（ギター6弦標準EADGBE・NF-045プラグイン型出力層の実例）。

弦・フレット割当は「手の移動最小化」を主目的とした動的計画法:
ハンドポジション（人差し指の基準フレット、4フレット幅＋開放弦）を状態とし、
グループ間のポジション移動量を主コストに最適化する。ローコード偏重で
G→A→Bm→C のような進行のたびに手が飛ぶ割当を避ける（ユーザー要望 2026-07-20）。

音域外の音はオクターブ移動で収め、移動数を譜面と戻り値に正直に注記する。
描画は自前SVG（Verovio非依存）→ cairosvg → pypdf 結合（engrave.pyと同パターン）。
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import estimate_chords
from earpipe.services.notate.chord_shapes import diagram_svg, shape_for

TUNING_GUITAR = (40, 45, 50, 55, 59, 64)  # 6弦(低E)→1弦(高E) のMIDI
MAX_FRET = 19
_WINDOW = 3  # ハンドポジション幅: p〜p+3 の4フレット＋開放弦
_POSITIONS = tuple(range(1, MAX_FRET - _WINDOW + 1))
_MOVE_COST = 1.0     # ポジション移動1フレットあたり（主コスト）
_HEIGHT_COST = 0.05  # ハイポジション微ペナルティ（同コストなら低い方）
_FRET_COST = 0.02    # 押弦フレット合計の微ペナルティ

_BEATS_PER_MEASURE = 4  # 現行エンジンは4/4固定（score.pyと同前提）


@dataclass(frozen=True)
class TabNote:
    """TAB上の1音。string_index: 0=6弦(低E)〜5=1弦(高E)。"""

    start_beats: float
    dur_beats: float
    string_index: int
    fret: int
    octave_shift: int  # 音域に収めるため移動したオクターブ数（+上げ/-下げ、0=なし）
    confidence: float


def fold_to_range(midi: int) -> tuple[int, int]:
    """音域外のMIDIをオクターブ単位で 40..83 に収める。(収めたmidi, 移動オクターブ数)。"""
    lo, hi = TUNING_GUITAR[0], TUNING_GUITAR[-1] + MAX_FRET
    shift = 0
    m = midi
    while m < lo:
        m += 12
        shift += 1
    while m > hi:
        m -= 12
        shift -= 1
    return m, shift


def _candidates(midi: int) -> list[tuple[int, int]]:
    """弾ける (string_index, fret) の全候補。"""
    out = []
    for si, open_midi in enumerate(TUNING_GUITAR):
        fret = midi - open_midi
        if 0 <= fret <= MAX_FRET:
            out.append((si, fret))
    return out


def _group_by_start(notes: Sequence[QuantizedNote]) -> list[list[QuantizedNote]]:
    groups: dict[float, list[QuantizedNote]] = {}
    for n in sorted(notes, key=lambda n: n.start_beats):
        key = round(n.start_beats, 6)
        groups.setdefault(key, []).append(n)
    return [groups[k] for k in sorted(groups)]


def _assign_group_at(midis: list[int], pos: int) -> list[tuple[int, int]] | None:
    """ポジションposで全音を割当てる。開放弦(f0)またはpos..pos+WINDOW内のみ許可。

    候補が少ない音から貪欲に割当（同一弦の重複禁止）。不能ならNone。
    """
    def cands(m: int) -> list[tuple[int, int]]:
        return [
            (si, f) for si, f in _candidates(m)
            if f == 0 or pos <= f <= pos + _WINDOW
        ]

    order = sorted(range(len(midis)), key=lambda i: len(cands(midis[i])))
    used: set[int] = set()
    result: list[tuple[int, int] | None] = [None] * len(midis)
    for i in order:
        best = None
        for si, f in cands(midis[i]):
            if si in used:
                continue
            if best is None or f < best[1]:
                best = (si, f)
        if best is None:
            return None
        used.add(best[0])
        result[i] = best
    return result  # type: ignore[return-value]


def assign_frets(notes: Sequence[QuantizedNote]) -> list[TabNote]:
    """手の移動最小化DPで弦・フレットを割当てる。

    同時7音以上は信頼度の高い6音を残す。どのポジションでも割当不能な
    グループはポジション制約なしの貪欲割当にフォールバックし、それでも
    載らない音は正直にドロップする（戻り値に含めない）。
    """
    if not notes:
        return []

    groups = _group_by_start(notes)
    prepared: list[tuple[list[QuantizedNote], list[int], list[int]]] = []
    for g in groups:
        g = sorted(g, key=lambda n: (-n.confidence, -n.midi))[:6]  # 6弦上限
        folded = [fold_to_range(n.midi) for n in g]
        prepared.append((g, [m for m, _ in folded], [s for _, s in folded]))

    # DP: dp[p] = (累計コスト, 経路)。各グループ×各ポジションの割当をメモ化
    assigns: list[dict[int, list[tuple[int, int]]]] = []
    for _, midis, _ in prepared:
        table: dict[int, list[tuple[int, int]]] = {}
        for p in _POSITIONS:
            a = _assign_group_at(midis, p)
            if a is not None:
                table[p] = a
        assigns.append(table)

    INF = float("inf")
    n_groups = len(prepared)
    dp: list[dict[int, float]] = [dict() for _ in range(n_groups)]
    back: list[dict[int, int]] = [dict() for _ in range(n_groups)]

    def local_cost(p: int, assign: list[tuple[int, int]]) -> float:
        return _HEIGHT_COST * p + _FRET_COST * sum(f for _, f in assign)

    prev_ps: list[int] = []
    for gi in range(n_groups):
        table = assigns[gi]
        if not table:  # フォールバック対象（後段処理）。ポジションは前を維持
            dp[gi] = dp[gi - 1] if gi else {p: 0.0 for p in _POSITIONS}
            back[gi] = {p: p for p in dp[gi]}
            continue
        for p, a in table.items():
            lc = local_cost(p, a)
            if gi == 0 or not dp[gi - 1]:
                dp[gi][p] = lc
                back[gi][p] = p
            else:
                best_q, best_c = None, INF
                for q, cq in dp[gi - 1].items():
                    c = cq + _MOVE_COST * abs(p - q) + lc
                    if c < best_c:
                        best_q, best_c = q, c
                dp[gi][p] = best_c
                back[gi][p] = best_q  # type: ignore[assignment]

    # バックトラック
    chosen: list[int | None] = [None] * n_groups
    if dp[-1]:
        cur = min(dp[-1], key=lambda p: dp[-1][p])
        for gi in range(n_groups - 1, -1, -1):
            chosen[gi] = cur
            cur = back[gi].get(cur, cur)

    out: list[TabNote] = []
    for gi, (g, midis, shifts) in enumerate(prepared):
        p = chosen[gi]
        assign = assigns[gi].get(p) if p is not None else None
        if assign is None:
            assign = _fallback_assign(midis)
        for note, (si_f), midi, shift in zip(g, assign, midis, shifts):
            if si_f is None:
                continue  # 正直にドロップ
            si, f = si_f
            out.append(TabNote(
                start_beats=note.start_beats, dur_beats=note.dur_beats,
                string_index=si, fret=f, octave_shift=shift,
                confidence=note.confidence,
            ))
    return out


def _fallback_assign(midis: list[int]) -> list[tuple[int, int] | None]:
    """ポジション制約なしの貪欲割当（最低フレット優先・弦重複禁止）。"""
    used: set[int] = set()
    result: list[tuple[int, int] | None] = [None] * len(midis)
    order = sorted(range(len(midis)), key=lambda i: len(_candidates(midis[i])))
    for i in order:
        best = None
        for si, f in _candidates(midis[i]):
            if si in used:
                continue
            if best is None or f < best[1]:
                best = (si, f)
        if best is not None:
            used.add(best[0])
            result[i] = best
    return result


# ================= SVG描画（自前エングレーバー・Verovio非依存） =================

_PAGE_W, _PAGE_H = 2100, 2970
_MARGIN = 130
_LINE_GAP = 26           # TAB線間隔
_SYS_H = _LINE_GAP * 5   # 6本線の高さ
_SYS_GAP = 138           # システム間隔（コード帯ぶんを含む）
_MEASURES_PER_SYS = 4
_HEADER_H = 170
_CHORD_BAND_H = 64       # 各システム上部のコード帯の高さ


def _draw_chord_band(chord_spans: list, m0: int, top: float, meas_w: float,
                     chord_diagrams: bool) -> list[str]:
    """システム(m0..m0+3小節)の上部にコード帯を描く。コード変化点にネーム＋図。"""
    parts: list[str] = []
    sys_start = m0 * _BEATS_PER_MEASURE
    sys_end = (m0 + _MEASURES_PER_SYS) * _BEATS_PER_MEASURE
    for cs in chord_spans:
        if cs.name == "N.C." or not (sys_start <= cs.start_beats < sys_end):
            continue
        mi = int(cs.start_beats // _BEATS_PER_MEASURE) - m0
        beat_in = cs.start_beats - (m0 + mi) * _BEATS_PER_MEASURE
        cx = _MARGIN + mi * meas_w + 26 + (beat_in / _BEATS_PER_MEASURE) * (meas_w - 44)
        if chord_diagrams:
            shape = shape_for(cs.root_pc, cs.quality)
            parts.append(diagram_svg(shape, cs.name, cx - 22, top - _CHORD_BAND_H + 14, scale=1.0))
        else:
            parts.append(f'<text x="{cx}" y="{top - 12}" font-size="22" '
                         f'text-anchor="middle" font-weight="bold" fill="#222">{_esc(cs.name)}</text>')
    return parts


def _render_pages(tabs: list[TabNote], bpm: float, title: str | None,
                  n_shifted: int, n_dropped: int,
                  chord_spans: list, chord_diagrams: bool) -> list[str]:
    width = _PAGE_W - 2 * _MARGIN
    meas_w = width / _MEASURES_PER_SYS
    n_measures = 1
    if tabs:
        last = max(t.start_beats for t in tabs)
        n_measures = int(last // _BEATS_PER_MEASURE) + 1
    n_systems = (n_measures + _MEASURES_PER_SYS - 1) // _MEASURES_PER_SYS

    sys_per_page_first = int((_PAGE_H - 2 * _MARGIN - _HEADER_H) // (_SYS_H + _SYS_GAP))
    sys_per_page = int((_PAGE_H - 2 * _MARGIN) // (_SYS_H + _SYS_GAP))

    by_measure: dict[int, list[TabNote]] = {}
    for t in tabs:
        by_measure.setdefault(int(t.start_beats // _BEATS_PER_MEASURE), []).append(t)

    pages: list[str] = []
    sys_idx = 0
    while sys_idx < n_systems or not pages:
        first = not pages
        cap = sys_per_page_first if first else sys_per_page
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_PAGE_W}" height="{_PAGE_H}" '
            f'viewBox="0 0 {_PAGE_W} {_PAGE_H}" font-family="Helvetica, Arial, sans-serif">',
            f'<rect width="{_PAGE_W}" height="{_PAGE_H}" fill="white"/>',
        ]
        y = _MARGIN
        if first:
            t = _esc(title or "TAB")
            parts.append(f'<text x="{_PAGE_W/2}" y="{y+40}" font-size="48" text-anchor="middle">{t}</text>')
            sub = f"Guitar TAB | BPM {int(round(bpm))} | Tuning: E A D G B E"
            parts.append(f'<text x="{_PAGE_W/2}" y="{y+92}" font-size="26" text-anchor="middle" fill="#444">{sub}</text>')
            notes_txt = []
            if n_shifted:
                notes_txt.append(f"* = octave-shifted to fit guitar range ({n_shifted} notes)")
            if n_dropped:
                notes_txt.append(f"{n_dropped} notes dropped (unplayable)")
            if notes_txt:
                parts.append(f'<text x="{_PAGE_W/2}" y="{y+128}" font-size="20" text-anchor="middle" fill="#888">{_esc(" / ".join(notes_txt))}</text>')
            y += _HEADER_H
        drawn = 0
        while drawn < cap and (sys_idx < n_systems or (first and drawn == 0)):
            top = y
            m0 = sys_idx * _MEASURES_PER_SYS
            # コード帯（システム上部）
            parts.extend(_draw_chord_band(chord_spans, m0, top, meas_w, chord_diagrams))
            # TAB縦ラベルと6本線
            for li in range(6):
                ly = top + li * _LINE_GAP
                parts.append(f'<line x1="{_MARGIN}" y1="{ly}" x2="{_MARGIN+width}" y2="{ly}" stroke="#333" stroke-width="1.6"/>')
            for ch, frac in zip("TAB", (0.16, 0.5, 0.84)):
                parts.append(f'<text x="{_MARGIN-34}" y="{top+_SYS_H*frac+8}" font-size="26" fill="#333">{ch}</text>')
            # 小節線と小節番号
            for mi in range(_MEASURES_PER_SYS + 1):
                mx = _MARGIN + mi * meas_w
                parts.append(f'<line x1="{mx}" y1="{top}" x2="{mx}" y2="{top+_SYS_H}" stroke="#333" stroke-width="1.6"/>')
            parts.append(f'<text x="{_MARGIN}" y="{top-14}" font-size="18" fill="#999">{m0+1}</text>')
            # フレット数字: 白背景(TAB線マスク)を全部先に描き、数字は後で全部描く。
            # こうしないと、密な箇所で後の数字の白背景が前の数字を消してしまう。
            rects: list[str] = []
            texts: list[str] = []
            for mi in range(_MEASURES_PER_SYS):
                for t in by_measure.get(m0 + mi, ()):
                    beat_in = t.start_beats - (m0 + mi) * _BEATS_PER_MEASURE
                    nx = _MARGIN + mi * meas_w + 26 + (beat_in / _BEATS_PER_MEASURE) * (meas_w - 44)
                    ny = top + (5 - t.string_index) * _LINE_GAP
                    label = str(t.fret)
                    bw = 18 + 11 * len(label)
                    rects.append(f'<rect x="{nx-bw/2}" y="{ny-13}" width="{bw}" height="26" fill="white"/>')
                    texts.append(f'<text x="{nx}" y="{ny+8}" font-size="24" text-anchor="middle">{label}</text>')
                    if t.octave_shift:
                        texts.append(f'<text x="{nx}" y="{ny-16}" font-size="17" text-anchor="middle" fill="#b05050">*</text>')
            parts.extend(rects)
            parts.extend(texts)
            y += _SYS_H + _SYS_GAP
            drawn += 1
            sys_idx += 1
        parts.append(f'<text x="{_PAGE_W/2}" y="{_PAGE_H-56}" font-size="18" text-anchor="middle" fill="#999">- {len(pages)+1} -</text>')
        parts.append("</svg>")
        pages.append("".join(parts))
        if sys_idx >= n_systems:
            break
    return pages


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _digit_x(t: TabNote, meas_w: float) -> tuple[int, int, float]:
    """描画時の (system, string, x中心) を _render_pages と同じ式で再現する。"""
    measure = int(t.start_beats // _BEATS_PER_MEASURE)
    system = measure // _MEASURES_PER_SYS
    mi = measure % _MEASURES_PER_SYS
    beat_in = t.start_beats - measure * _BEATS_PER_MEASURE
    nx = _MARGIN + mi * meas_w + 26 + (beat_in / _BEATS_PER_MEASURE) * (meas_w - 44)
    return system, t.string_index, nx


def count_overlaps(tabs: list[TabNote]) -> int:
    """視覚的に数字が重なるペア数を数える（可読性の実測検証）。

    同一システム・同一弦で、隣接する数字の中心間隔が数字幅平均の8割未満なら
    「重なって読めない」と判定する。0なら全数字が判読可能。
    """
    width = _PAGE_W - 2 * _MARGIN
    meas_w = width / _MEASURES_PER_SYS
    by_key: dict[tuple[int, int], list[tuple[float, int]]] = {}
    for t in tabs:
        system, string, nx = _digit_x(t, meas_w)
        by_key.setdefault((system, string), []).append((nx, len(str(t.fret))))
    overlaps = 0
    for xs in by_key.values():
        xs.sort()
        for (x1, l1), (x2, l2) in zip(xs, xs[1:]):
            w_avg = ((18 + 11 * l1) + (18 + 11 * l2)) / 2
            if x2 - x1 < w_avg * 0.8:
                overlaps += 1
    return overlaps


def write_tab_pdf(notes: Sequence[QuantizedNote], bpm: float,
                  out_pdf: str | Path, title: str | None = None,
                  chord_diagrams: bool = True) -> dict:
    """QuantizedNote列をギターTAB譜PDFにする。

    chord_diagrams: Trueならコード帯にコードネーム＋押さえ図、Falseならコードネームのみ。
    戻り値: {"pages", "n_octave_shifted", "n_dropped", "n_notes_placed", "n_overlaps", "n_chords"}
    """
    import cairosvg
    import pypdf

    tabs = assign_frets(notes)
    chord_spans = estimate_chords(notes, bpm)
    n_shifted = sum(1 for t in tabs if t.octave_shift)
    n_dropped = len(list(notes)) - len(tabs) if notes else 0
    # 同時7音以上の切り捨て等もドロップに含まれる（assign_fretsの上限6音）
    n_dropped = max(0, n_dropped)

    svgs = _render_pages(tabs, bpm, title, n_shifted, n_dropped, chord_spans, chord_diagrams)
    writer = pypdf.PdfWriter()
    for svg in svgs:
        pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pdf, "wb") as f:
        writer.write(f)
    return {
        "pages": len(svgs),
        "n_octave_shifted": n_shifted,
        "n_dropped": n_dropped,
        "n_notes_placed": len(tabs),
        "n_overlaps": count_overlaps(tabs),
        "n_chords": sum(1 for c in chord_spans if c.name != "N.C."),
    }
