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
    """音域外のMIDIをオクターブ単位で 40..83 に収める。(収めたmidi, 移動オクターブ数)。

    必要オクターブ数を算術で一度に求めて定数時間で補正する(デバッグEOP-DEBUG 3.11:
    旧実装は1オクターブずつのwhileループで、巨大MIDI値(±10^12級)で約833億回反復し
    実用時間内に終了しないDoSになっていた)。
    """
    lo, hi = TUNING_GUITAR[0], TUNING_GUITAR[-1] + MAX_FRET
    m = midi
    shift = 0
    if m < lo:
        steps = (lo - m + 11) // 12
        m += 12 * steps
        shift += steps
    elif m > hi:
        steps = (m - hi + 11) // 12
        m -= 12 * steps
        shift -= steps
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


# 主旋律選択で倍音/幽霊を除外する信頼度比。グループ最大信頼度に対しこの比
# 未満の音は主旋律候補から外す(#119: 低信頼の高音倍音へ跳ねて音が飛ぶのを抑制)。
_MELODY_GHOST_RATIO = 0.5


def _reduce_to_melody(notes: Sequence[QuantizedNote]) -> list[QuantizedNote]:
    """各オンセット群から最高音(スカイライン=主旋律)1音だけ残して単旋律化する。

    多声ステム(other等)をpoly検出した音符列は和音を含み、そのままだと物理的に
    押さえられないTAB配置が出る。各拍で最高音(同点は高信頼度)を主旋律として選ぶと、
    同時発音が常に1音になり、TABは必ず演奏可能になる。

    ただし無条件スカイラインは、弱く検出された高音倍音(幽霊)に跳ねて主旋律が
    高フレットへ飛ぶ(#119)。グループ最大信頼度に対し極端に弱い音は候補から除外
    してからスカイラインを採ることで、可読性の高い連続した主旋律にする。
    """
    if not notes:
        return []
    melody: list[QuantizedNote] = []
    for group in _group_by_start(notes):
        cmax = max(n.confidence for n in group)
        # 幽霊/倍音除去。全音が弱い(=cmax自体が低い)場合は全候補を残し欠落を防ぐ。
        strong = [n for n in group if n.confidence >= cmax * _MELODY_GHOST_RATIO]
        candidates = strong or list(group)
        melody.append(max(candidates, key=lambda n: (n.midi, n.confidence)))
    return melody


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

# GP風リズム帯(#127): TAB最下線の下に符尾/連桁/付点を描く(Guitar Pro慣行)
_RHY_GAP = 10            # 最下線→符尾開始の距離
_STEM_LEN = 30           # 4分以下の符尾長
_STEM_LEN_HALF = 15      # 2分音符の短い符尾長
_EPS = 1e-6


def _note_x(mi: int, beat_in: float, meas_w: float) -> float:
    """小節内拍位置→X座標。数字・符尾・休符・楕円の全描画で共有する。"""
    return _MARGIN + mi * meas_w + 26 + (beat_in / _BEATS_PER_MEASURE) * (meas_w - 44)


def _is_dotted(dur: float) -> bool:
    return any(abs(dur - d) < _EPS for d in (0.75, 1.5, 3.0))


def _rhythm_marks(by_measure: dict[int, list["TabNote"]], m0: int, top: float,
                  meas_w: float, n_measures: int) -> list[str]:
    """システム分のリズム帯(符尾・連桁・付点)を描く(#127)。

    オンセットグループごとに1本の符尾。全音符=符尾なし / 2分=短い符尾 /
    4分以下=通常符尾。8分以下は同一拍内の隣接オンセットを連桁で結ぶ。
    付点(0.75/1.5/3.0拍)は符尾脇に点を打つ。
    """
    parts: list[str] = []
    y0 = top + _SYS_H + _RHY_GAP
    for mi in range(_MEASURES_PER_SYS):
        m = m0 + mi
        if m >= n_measures:
            continue
        onsets: dict[float, float] = {}
        for t in by_measure.get(m, ()):
            b = round(t.start_beats - m * _BEATS_PER_MEASURE, 6)
            onsets[b] = max(onsets.get(b, 0.0), t.dur_beats)
        items = sorted(onsets.items())
        for b, dur in items:
            x = _note_x(mi, b, meas_w)
            if dur < 4.0 - _EPS:  # 全音符は符尾なし(GP慣行)
                ln = _STEM_LEN_HALF if dur >= 2.0 - _EPS else _STEM_LEN
                parts.append(
                    f'<line class="stem" x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" '
                    f'y2="{y0 + ln}" stroke="#222" stroke-width="2.4"/>')
            if _is_dotted(dur):
                ln = _STEM_LEN_HALF if dur >= 2.0 - _EPS else _STEM_LEN
                parts.append(
                    f'<circle class="dot" cx="{x + 8:.1f}" cy="{y0 + ln - 3}" '
                    f'r="2.8" fill="#222"/>')
        # 連桁: 8分以下が隙間なく続き同一拍に収まるペアを結ぶ(連続すれば視覚上1本に繋がる)
        for (b1, d1), (b2, d2) in zip(items, items[1:]):
            if d1 > 0.5 + _EPS or d2 > 0.5 + _EPS:
                continue
            if abs((b1 + d1) - b2) > _EPS or int(b1 + _EPS) != int(b2 + _EPS):
                continue  # 隙間あり、または拍をまたぐペアは結ばない
            x1, x2 = _note_x(mi, b1, meas_w), _note_x(mi, b2, meas_w)
            yb = y0 + _STEM_LEN
            parts.append(
                f'<line class="beam" x1="{x1:.1f}" y1="{yb}" x2="{x2:.1f}" y2="{yb}" '
                f'stroke="#222" stroke-width="5"/>')
            if d1 <= 0.25 + _EPS and d2 <= 0.25 + _EPS:  # 16分は2本目
                parts.append(
                    f'<line class="beam2" x1="{x1:.1f}" y1="{yb - 7}" x2="{x2:.1f}" '
                    f'y2="{yb - 7}" stroke="#222" stroke-width="5"/>')
    return parts


def _rest_svg(kind: float, x: float, top: float) -> str:
    """休符1個のSVG(全て自前プリミティブ・SMuFLフォント非依存)。"""
    ya = top + _LINE_GAP  # 第2線
    if kind >= 4.0 - _EPS:   # 全休符: 第2線からぶら下がる矩形
        return (f'<rect class="rest" x="{x - 11:.1f}" y="{ya}" width="22" height="8" '
                f'fill="#222"/>')
    if kind >= 2.0 - _EPS:   # 2分休符: 第3線の上に載る矩形
        return (f'<rect class="rest" x="{x - 11:.1f}" y="{top + 2 * _LINE_GAP - 8}" '
                f'width="22" height="8" fill="#222"/>')
    if kind >= 1.0 - _EPS:   # 4分休符: 簡略ジグザグ
        return (f'<path class="rest" d="M{x - 4:.1f},{ya} l8,10 -8,10 8,10" '
                f'stroke="#222" stroke-width="3.2" fill="none"/>')
    # 8分休符: 玉つき斜線
    ym = top + 1.6 * _LINE_GAP
    return (f'<path class="rest" d="M{x + 4:.1f},{ym} l-8,18 M{x + 4:.1f},{ym} '
            f'a4,4 0 1 1 -7.5,2.5" stroke="#222" stroke-width="2.6" fill="none"/>')


def _rest_marks(by_measure: dict[int, list["TabNote"]], m0: int, top: float,
                meas_w: float, n_measures: int) -> list[str]:
    """音のない区間を休符記号で埋める(#127)。空小節は全休符。

    小節内の占有区間(音の開始〜終了)を合成し、隙間を0.25拍格子に丸めて
    全→2分→4分→8分の貪欲分解で休符化する。
    """
    parts: list[str] = []
    for mi in range(_MEASURES_PER_SYS):
        m = m0 + mi
        if m >= n_measures:
            continue
        m_start = m * _BEATS_PER_MEASURE
        spans = []
        for t in by_measure.get(m, ()):
            s = max(0.0, t.start_beats - m_start)
            e = min(float(_BEATS_PER_MEASURE), t.start_beats - m_start + t.dur_beats)
            if e > s:
                spans.append((s, e))
        spans.sort()
        merged: list[list[float]] = []
        for s, e in spans:
            if merged and s <= merged[-1][1] + _EPS:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        gaps = []
        cur = 0.0
        for s, e in merged:
            if s - cur > 0.25:
                gaps.append((cur, s))
            cur = max(cur, e)
        if _BEATS_PER_MEASURE - cur > 0.25:
            gaps.append((cur, float(_BEATS_PER_MEASURE)))
        for gs, ge in gaps:
            b = round(gs * 4) / 4  # 0.25拍格子へ
            rem = round((ge - b) * 4) / 4
            while rem >= 0.5 - _EPS:
                for size in (4.0, 2.0, 1.0, 0.5):
                    if rem >= size - _EPS:
                        parts.append(_rest_svg(size, _note_x(mi, b, meas_w), top))
                        b += size
                        rem -= size
                        break
    return parts


def _chord_ellipses(by_measure: dict[int, list["TabNote"]], m0: int, top: float,
                    meas_w: float) -> list[str]:
    """同一オンセットに2音以上ある和音を楕円で囲む(#127・参考動画準拠)。"""
    parts: list[str] = []
    for mi in range(_MEASURES_PER_SYS):
        groups: dict[float, list[TabNote]] = {}
        for t in by_measure.get(m0 + mi, ()):
            groups.setdefault(round(t.start_beats, 6), []).append(t)
        for start, g in groups.items():
            if len(g) < 2:
                continue
            beat_in = start - (m0 + mi) * _BEATS_PER_MEASURE
            x = _note_x(mi, beat_in, meas_w)
            ys = [top + (5 - t.string_index) * _LINE_GAP for t in g]
            cy = (min(ys) + max(ys)) / 2
            ry = (max(ys) - min(ys)) / 2 + 15
            rx = 15 + 4 * max(len(str(t.fret)) for t in g)
            parts.append(
                f'<ellipse class="chord-ellipse" cx="{x:.1f}" cy="{cy:.1f}" '
                f'rx="{rx}" ry="{ry:.1f}" stroke="#666" stroke-width="1.4" fill="none"/>')
    return parts


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
            # cairosvgは候補リストのフォールバックをせず先頭の実在フォントで全描画するため、
            # 日本語/韓国語タイトルの豆腐化を防ぐにはCJK対応フォントを先頭に置く必要がある。
            # Arial Unicode MS(macOS標準・pan-Unicode)がJP/KR/CN/ラテンを網羅。
            f'viewBox="0 0 {_PAGE_W} {_PAGE_H}" '
            f'font-family="\'Arial Unicode MS\', \'Hiragino Sans\', \'Noto Sans CJK JP\', Helvetica, Arial, sans-serif">',
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
            # 小節線と小節番号(#127: GP風に全小節へ番号を振る)
            for mi in range(_MEASURES_PER_SYS + 1):
                mx = _MARGIN + mi * meas_w
                parts.append(f'<line x1="{mx}" y1="{top}" x2="{mx}" y2="{top+_SYS_H}" stroke="#333" stroke-width="1.6"/>')
            for mi in range(_MEASURES_PER_SYS):
                if m0 + mi >= n_measures:
                    break
                mx = _MARGIN + mi * meas_w
                parts.append(f'<text class="mnum" x="{mx+5}" y="{top-8}" font-size="17" fill="#555">{m0+mi+1}</text>')
            # リズム帯(符尾/連桁/付点)・休符(#127)
            parts.extend(_rhythm_marks(by_measure, m0, top, meas_w, n_measures))
            parts.extend(_rest_marks(by_measure, m0, top, meas_w, n_measures))
            # フレット数字: 白背景(TAB線マスク)を全部先に描き、数字は後で全部描く。
            # こうしないと、密な箇所で後の数字の白背景が前の数字を消してしまう。
            rects: list[str] = []
            texts: list[str] = []
            for mi in range(_MEASURES_PER_SYS):
                for t in by_measure.get(m0 + mi, ()):
                    beat_in = t.start_beats - (m0 + mi) * _BEATS_PER_MEASURE
                    nx = _note_x(mi, beat_in, meas_w)
                    ny = top + (5 - t.string_index) * _LINE_GAP
                    label = str(t.fret)
                    bw = 18 + 11 * len(label)
                    rects.append(f'<rect x="{nx-bw/2}" y="{ny-13}" width="{bw}" height="26" fill="white"/>')
                    texts.append(f'<text x="{nx}" y="{ny+8}" font-size="24" font-weight="bold" text-anchor="middle">{label}</text>')
                    if t.octave_shift:
                        texts.append(f'<text x="{nx}" y="{ny-16}" font-size="17" text-anchor="middle" fill="#b05050">*</text>')
            parts.extend(rects)
            parts.extend(texts)
            # 和音の楕円囲み(#127): 数字の上に細線で重ねる
            parts.extend(_chord_ellipses(by_measure, m0, top, meas_w))
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
    return system, t.string_index, _note_x(mi, beat_in, meas_w)


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
                  chord_diagrams: bool = True, monophonic: bool = False) -> dict:
    """QuantizedNote列をギターTAB譜PDFにする。

    chord_diagrams: Trueならコード帯にコードネーム＋押さえ図、Falseならコードネームのみ。
    monophonic: Trueなら各オンセットの最高音(主旋律)1音だけ残して単音TAB化する
        (多声ステムをpoly検出した音源を、常に演奏可能な単旋律TABにするため)。
    戻り値: {"pages", "n_octave_shifted", "n_dropped", "n_notes_placed", "n_overlaps", "n_chords"}
    """
    import cairosvg
    import pypdf

    # コード帯は原音(多声)から推定する。monophonic の単旋律化は TAB 運指を
    from earpipe.services.notate.chord import estimate_chords

    # 演奏可能にするための間引きであって、その単音を estimate_chords に渡すと
    # 和音が判定できずコード帯が消える(EOP tab-mono 回帰)。フレット割当だけ
    # 単旋律化し、コード推定は元の notes を使う。
    tab_notes = _reduce_to_melody(notes) if monophonic else notes
    tabs = assign_frets(tab_notes)
    chord_spans = estimate_chords(notes, bpm)
    n_shifted = sum(1 for t in tabs if t.octave_shift)
    n_dropped = len(list(tab_notes)) - len(tabs) if tab_notes else 0
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
