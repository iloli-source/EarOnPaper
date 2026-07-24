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

# #142 慣用ヴォイシングボーナス(DS-04東スポ氏指摘・docs/research/tab-fingering-idiom-research.md)。
# 同じ音高集合の複数運指から、ギタリストが実際に使う形を優先する(音高は変えない)。
# _MOVE_COST=1.0 に対し小さく保ち、ポジション慣性を壊さない(Tuohy&Potter 2005以来の定石)。
_IDIOM_POWER = 0.35    # 隣接弦で+7半音 = root+5th(パワーコード形)
_IDIOM_OCTAVE = 0.15   # 2弦スキップで+12半音(オクターブ形)
_IDIOM_BARRE = 0.1     # 隣接弦の同一フレット(1F以上・バレー形)
_ENUM_MAX_NOTES = 4    # 全列挙するグループサイズ上限(超過は従来の貪欲割当)

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


def _idiom_bonus(assign: Sequence[tuple[int, int]], midis: Sequence[int]) -> float:
    """慣用形(パワーコード/オクターブ/バレー)への一致ボーナス(#142・純関数)。

    弦番号昇順の全ペアについて: 隣接弦+7半音=パワーコード形 /
    2弦スキップ+12半音=オクターブ形 / 隣接弦の同一フレット(1F以上)=バレー形。
    """
    items = sorted(zip(assign, midis), key=lambda x: x[0][0])
    bonus = 0.0
    for a in range(len(items)):
        (si, fi), mi = items[a]
        for b in range(a + 1, len(items)):
            (sj, fj), mj = items[b]
            if sj - si == 1 and mj - mi == 7:
                bonus += _IDIOM_POWER
            elif sj - si == 2 and mj - mi == 12:
                bonus += _IDIOM_OCTAVE
            elif sj - si == 1 and fi == fj and fi >= 1:
                bonus += _IDIOM_BARRE
    return bonus


def _assign_group_at(midis: list[int], pos: int) -> list[tuple[int, int]] | None:
    """ポジションposで全音を割当てる。開放弦(f0)またはpos..pos+WINDOW内のみ許可。

    2〜_ENUM_MAX_NOTES音は全組合せを列挙し、フレットコスト−慣用形ボーナス最小の
    割当を選ぶ(#142: 貪欲最低フレットでは慣用形候補を生成できない)。
    単音・上限超は従来の貪欲割当(候補が少ない音から・同一弦の重複禁止)。
    """
    def cands(m: int) -> list[tuple[int, int]]:
        return [
            (si, f) for si, f in _candidates(m)
            if f == 0 or pos <= f <= pos + _WINDOW
        ]

    if 2 <= len(midis) <= _ENUM_MAX_NOTES:
        from itertools import product

        cand_lists = [cands(m) for m in midis]
        if any(not c for c in cand_lists):
            return None
        best_combo = None
        best_cost = float("inf")
        for combo in product(*cand_lists):
            if len({si for si, _ in combo}) != len(combo):
                continue  # 同一弦の重複禁止
            cost = (_FRET_COST * sum(f for _, f in combo)
                    - _idiom_bonus(combo, midis))
            if cost < best_cost:
                best_combo, best_cost = combo, cost
        return list(best_combo) if best_combo is not None else None

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

    def local_cost(p: int, assign: list[tuple[int, int]], midis: list[int]) -> float:
        return (_HEIGHT_COST * p + _FRET_COST * sum(f for _, f in assign)
                - _idiom_bonus(assign, midis))

    for gi in range(n_groups):
        table = assigns[gi]
        if not table:  # フォールバック対象（後段処理）。ポジションは前を維持
            dp[gi] = dp[gi - 1] if gi else {p: 0.0 for p in _POSITIONS}
            back[gi] = {p: p for p in dp[gi]}
            continue
        for p, a in table.items():
            lc = local_cost(p, a, prepared[gi][1])
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
_MEASURES_PER_SYS = 4    # 段あたり小節数の上限(#139: 密度により1〜4で可変)
_HEADER_H = 170

# コード帯(#143: 図の実寸から幾何的に確保しTAB上線との衝突を根絶)
_DIAGRAM_TOTAL_H = 70    # diagram_svg実寸: コード名14 + 図44 + フレットラベル余白12
_CHORD_BAND_H = _DIAGRAM_TOTAL_H + 10
_SYS_GAP = _CHORD_BAND_H + 78  # リズム帯(符尾+旗+三連括弧)ぶんを含む段間隔

# GP風リズム帯(#127): TAB最下線の下に符尾/連桁/付点を描く(Guitar Pro慣行)
_RHY_GAP = 10            # 最下線→符尾開始の距離
_STEM_LEN = 30           # 4分以下の符尾長
_STEM_LEN_HALF = 15      # 2分音符の短い符尾長
_EPS = 1e-6

# #139 簡易spring-rod(調査 docs/research/tab-spacing-research.md):
# 拍比例(spring=理想間隔)を保ちつつ、隣接オンセットに数字幅+余白の最小間隔(rod)を
# 保証する。小節の必要幅に応じて段あたり小節数も1〜4で可変にする。
_X_PAD_L = 26            # 小節左の内側パディング(従来の描画式と同値)
_X_PAD_R = 18            # 小節右の内側パディング
_ROD_PAD = 4.0           # 隣接数字間の最小余白
_TS_PAD = 52             # 拍子記号ぶんの第1小節左パディング追加(#143)


def _digit_w(fret: int) -> float:
    """フレット数字の描画幅(白背景マスクと同じ幅モデル)。"""
    return 18 + 11 * len(str(fret))


def _label_w(label: str) -> float:
    return 18 + 11 * len(label)


def _nominal_inner_width() -> float:
    """従来レイアウト(4小節/段)での小節内側幅。拍比例の理想間隔の基準。"""
    return (_PAGE_W - 2 * _MARGIN) / _MEASURES_PER_SYS - _X_PAD_L - _X_PAD_R


def _display_segments(tabs: Sequence[TabNote], beats: int) -> list[dict]:
    """小節線を越える音を表示用に分割する(#143タイ)。

    各要素: {"b": 開始拍, "dur": 拍, "string": 弦, "fret": フレット,
    "label": 表示文字列(継続は括弧数字), "w": 表示幅, "cont": 継続か, "src": 元音ID}
    継続小節が占有扱いになり、跨ぎ音の続き小節へ誤って休符が出る旧バグも直る。
    """
    segs: list[dict] = []
    for t in tabs:
        s, d = t.start_beats, t.dur_beats
        first = True
        while d > _EPS:
            m_end = (int(s // beats) + 1) * beats
            take = min(d, m_end - s)
            label = str(t.fret) if first else f"({t.fret})"
            segs.append({
                "b": s, "dur": take, "string": t.string_index, "fret": t.fret,
                "label": label, "w": _label_w(label), "cont": not first,
                "src": id(t), "shift": t.octave_shift if first else 0,
            })
            s += take
            d -= take
            first = False
    # 同弦・同拍で新音と衝突する継続(タイ先)は落とす: 同弦の持続は次の押弦で
    # 物理的に消えるため記譜的にも新音優先が正しい(重なり再発の防止・#143)。
    occupied = {(g["string"], round(g["b"], 6)) for g in segs if not g["cont"]}
    seen: set[tuple[int, float]] = set()
    cleaned: list[dict] = []
    for g in segs:
        key = (g["string"], round(g["b"], 6))
        if g["cont"]:
            if key in occupied or key in seen:
                continue
            seen.add(key)
        cleaned.append(g)
    return cleaned


def _measure_onsets(msegs: Sequence[dict], m_start: float) -> list[tuple[float, float]]:
    """小節内のオンセット(拍位置)→その位置の最大表示幅。"""
    groups: dict[float, float] = {}
    for g in msegs:
        b = round(g["b"] - m_start, 6)
        groups[b] = max(groups.get(b, 0.0), g["w"])
    return sorted(groups.items())


def _rods_and_ideals(
    onsets: Sequence[tuple[float, float]], width: float, beats: int
) -> tuple[list[float], list[float]]:
    """区間列[左端→o0, o0→o1, …, oN→右端]の rod(最小)と ideal(拍比例)を返す。"""
    rods = [onsets[0][1] / 2]
    ideals = [onsets[0][0] / beats * width]
    for (b1, w1), (b2, w2) in zip(onsets, onsets[1:]):
        rods.append((w1 + w2) / 2 + _ROD_PAD)
        ideals.append((b2 - b1) / beats * width)
    rods.append(onsets[-1][1] / 2)
    ideals.append((beats - onsets[-1][0]) / beats * width)
    return rods, ideals


def _natural_inner_width(onsets: Sequence[tuple[float, float]], beats: int) -> float:
    """rodを満たすのに必要な小節内側幅(拍比例のnominalとの大きい方)。"""
    w_nom = _nominal_inner_width()
    if not onsets:
        return w_nom
    rods, ideals = _rods_and_ideals(onsets, w_nom, beats)
    return max(w_nom, sum(max(r, i) for r, i in zip(rods, ideals)))


def _solve_anchors(
    onsets: Sequence[tuple[float, float]], width: float, beats: int = 4
) -> list[tuple[float, float]]:
    """1次元spring-rod解: (拍位置, 小節内側左端からのx) のアンカー列を返す。

    gap = rod + slack×spring比(spring=max(0, 拍比例−rod))。幅がrod合計に足りない
    病的ケース(1小節がページ幅超)でもrodは破らない(はみ出しは正直に許容)。
    """
    if not onsets:
        return []
    rods, ideals = _rods_and_ideals(onsets, width, beats)
    springs = [max(0.0, i - r) for i, r in zip(ideals, rods)]
    slack = width - sum(rods)
    if slack <= 0:
        gaps = list(rods)  # rod死守(重なりを出さない)。幅超過は正直に許容
    else:
        s_total = sum(springs)
        if s_total <= 1e-9:
            gaps = [r + slack / len(rods) for r in rods]
        else:
            gaps = [r + slack * sp / s_total for r, sp in zip(rods, springs)]
    anchors: list[tuple[float, float]] = []
    acc = 0.0
    for g, (b, _w) in zip(gaps, onsets):
        acc += g
        anchors.append((b, acc))
    return anchors


def _pack_measures(naturals: Sequence[float], page_w: float) -> list[list[int]]:
    """必要幅ベースの貪欲段組(GP auto方式)。1〜_MEASURES_PER_SYS小節/段。"""
    rows: list[list[int]] = []
    cur: list[int] = []
    acc = 0.0
    for i, w in enumerate(naturals):
        if cur and (acc + w > page_w or len(cur) >= _MEASURES_PER_SYS):
            rows.append(cur)
            cur, acc = [], 0.0
        cur.append(i)
        acc += w
    if cur:
        rows.append(cur)
    return rows


def _layout_rows(tabs: Sequence[TabNote], beats: int = 4,
                 segs: Sequence[dict] | None = None) -> list[list[dict]]:
    """全小節をレイアウトし、段(row)ごとの小節レイアウト辞書を返す。

    各辞書: {"m", "x0", "w", "anchors", "beats", "pad_l"}。第1小節は拍子記号ぶん
    左パディングを拡張(#143)。
    """
    if segs is None:
        segs = _display_segments(tabs, beats)
    by_measure: dict[int, list[dict]] = {}
    for g in segs:
        by_measure.setdefault(int(g["b"] // beats + _EPS), []).append(g)
    n_measures = (max(by_measure) + 1) if by_measure else 1
    page_w = _PAGE_W - 2 * _MARGIN
    measures = []
    for m in range(n_measures):
        pad_l = _X_PAD_L + (_TS_PAD if m == 0 else 0)
        onsets = _measure_onsets(by_measure.get(m, []), m * beats)
        nat = _natural_inner_width(onsets, beats) + pad_l + _X_PAD_R
        measures.append((m, onsets, nat, pad_l))
    rows_idx = _pack_measures([nat for _, _, nat, _ in measures], page_w)
    rows: list[list[dict]] = []
    for row in rows_idx:
        total = sum(measures[i][2] for i in row)
        scale = page_w / total  # 段内はnatural幅比で配分(通常≥1のstretch)
        x = float(_MARGIN)
        out = []
        for i in row:
            m, onsets, nat, pad_l = measures[i]
            w = nat * scale
            anchors = _solve_anchors(onsets, w - pad_l - _X_PAD_R, beats)
            out.append({"m": m, "x0": x, "w": w, "anchors": anchors,
                        "beats": beats, "pad_l": pad_l})
            x += w
        rows.append(out)
    return rows


def _mx(ml: dict, beat_in: float) -> float:
    """小節レイアウト上の拍位置→x。オンセットはアンカー・中間は区分線形補間。"""
    beats = ml["beats"]
    inner_l = ml["x0"] + ml["pad_l"]
    inner_w = ml["w"] - ml["pad_l"] - _X_PAD_R
    pts = list(ml["anchors"])
    if not pts or pts[0][0] > _EPS:
        pts = [(0.0, 0.0)] + pts
    if pts[-1][0] < beats - _EPS:
        pts = pts + [(float(beats), max(inner_w, pts[-1][1]))]
    for (b1, x1), (b2, x2) in zip(pts, pts[1:]):
        if beat_in <= b2 + _EPS:
            if b2 - b1 <= _EPS:
                return inner_l + x2
            frac = (beat_in - b1) / (b2 - b1)
            return inner_l + x1 + frac * (x2 - x1)
    return inner_l + pts[-1][1]


def _is_dotted(dur: float) -> bool:
    return any(abs(dur - d) < _EPS for d in (0.75, 1.5, 3.0))


def _flag_svg(x: float, y_tip: float, second: bool = False) -> str:
    """単独8分/16分の旗(#143)。符幹下端から右向きのカーブ(SMuFL形状を模す)。"""
    y = y_tip - (9 if second else 0)
    return (f'<path class="flag" d="M{x:.1f},{y:.1f} c 9,-3 13,-9 11,-17 '
            f'c 5,7 3,13 -11,17 z" fill="#222"/>')


def _rhythm_marks(msegs: Sequence[dict], ml: dict, top: float,
                  grid_per_beat: int = 4) -> list[str]:
    """小節ぶんのリズム帯(符尾・連桁・旗・付点・三連括弧)を描く(#127/#143)。"""
    parts: list[str] = []
    y0 = top + _SYS_H + _RHY_GAP
    beats = ml["beats"]
    m_start = ml["m"] * beats
    onsets: dict[float, float] = {}
    for g in msegs:
        b = round(g["b"] - m_start, 6)
        onsets[b] = max(onsets.get(b, 0.0), g["dur"])
    items = sorted(onsets.items())
    # 連桁: 8分以下が隙間なく続き同一拍に収まるペア(旗の要否判定にも使う)
    beamed: set[int] = set()
    beam_parts: list[str] = []
    for k, ((b1, d1), (b2, d2)) in enumerate(zip(items, items[1:])):
        if d1 > 0.5 + _EPS or d2 > 0.5 + _EPS:
            continue
        if abs((b1 + d1) - b2) > _EPS or int(b1 + _EPS) != int(b2 + _EPS):
            continue
        x1, x2 = _mx(ml, b1), _mx(ml, b2)
        yb = y0 + _STEM_LEN
        beam_parts.append(
            f'<line class="beam" x1="{x1:.1f}" y1="{yb}" x2="{x2:.1f}" y2="{yb}" '
            f'stroke="#222" stroke-width="5"/>')
        if d1 <= 0.25 + _EPS and d2 <= 0.25 + _EPS:  # 16分は2本目
            beam_parts.append(
                f'<line class="beam2" x1="{x1:.1f}" y1="{yb - 7}" x2="{x2:.1f}" '
                f'y2="{yb - 7}" stroke="#222" stroke-width="5"/>')
        beamed.add(k)
        beamed.add(k + 1)
    for k, (b, dur) in enumerate(items):
        x = _mx(ml, b)
        if dur < 4.0 - _EPS:  # 全音符は符尾なし(GP慣行)
            ln = _STEM_LEN_HALF if dur >= 2.0 - _EPS else _STEM_LEN
            parts.append(
                f'<line class="stem" x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" '
                f'y2="{y0 + ln}" stroke="#222" stroke-width="2.4"/>')
            # #143: 連桁が組めない単独8分/16分は旗(旗なし=4分と区別不能は誤り)
            if k not in beamed and dur <= 0.5 + _EPS:
                parts.append(_flag_svg(x, y0 + _STEM_LEN))
                if dur <= 0.25 + _EPS:
                    parts.append(_flag_svg(x, y0 + _STEM_LEN, second=True))
        if _is_dotted(dur):
            ln = _STEM_LEN_HALF if dur >= 2.0 - _EPS else _STEM_LEN
            parts.append(
                f'<circle class="dot" cx="{x + 8:.1f}" cy="{y0 + ln - 3}" '
                f'r="2.8" fill="#222"/>')
    parts.extend(beam_parts)
    # #143: 三連格子(grid_per_beat=3)ではオンセットを含む拍に角括弧+中央の3
    if grid_per_beat == 3:
        yb3 = y0 + _STEM_LEN + 12
        for beat in range(beats):
            in_beat = [b for b, _d in items if beat - _EPS <= b < beat + 1 - _EPS]
            if len(in_beat) < 2:
                continue
            x1, x2 = _mx(ml, in_beat[0]) - 4, _mx(ml, in_beat[-1]) + 4
            xm = (x1 + x2) / 2
            parts.append(
                f'<g class="tuplet3">'
                f'<path d="M{x1:.1f},{yb3 + 5} v-5 H{xm - 8:.1f} M{xm + 8:.1f},{yb3} '
                f'H{x2:.1f} v5" stroke="#222" stroke-width="1.6" fill="none"/>'
                f'<text x="{xm:.1f}" y="{yb3 + 5}" font-size="15" '
                f'text-anchor="middle" fill="#222">3</text></g>')
    return parts


def _rest_svg(kind: float, x: float, top: float) -> str:
    """休符1個のSVG(自前プリミティブ・SMuFL形状を模す)。

    全休符=第2線からぶら下がる/2分休符=第3線に載る(上下を逆にするのが世界最頻の
    誤り・調査 tab-rhythm-notation-research.md)。4分は現代標準の稲妻型。
    """
    ya = top + _LINE_GAP  # 第2線
    if kind >= 4.0 - _EPS:   # 全休符
        return (f'<rect class="rest" x="{x - 11:.1f}" y="{ya}" width="22" height="8" '
                f'fill="#222"/>')
    if kind >= 2.0 - _EPS:   # 2分休符
        return (f'<rect class="rest" x="{x - 11:.1f}" y="{top + 2 * _LINE_GAP - 8}" '
                f'width="22" height="8" fill="#222"/>')
    if kind >= 1.0 - _EPS:   # 4分休符: 稲妻型(#143でSMuFL形状に接近)
        y = top + 0.8 * _LINE_GAP
        return (f'<path class="rest" d="M{x - 5:.1f},{y:.1f} l9,10 -7,7 8,9 '
                f'c -8,-4 -12,-1 -9,7 c -7,-7 -6,-13 2,-14 l-8,-9 7,-7 z" '
                f'fill="#222"/>')
    # 8分休符: 玉つき斜線
    ym = top + 1.6 * _LINE_GAP
    return (f'<path class="rest" d="M{x + 4:.1f},{ym} l-8,18 M{x + 4:.1f},{ym} '
            f'a4,4 0 1 1 -7.5,2.5" stroke="#222" stroke-width="2.6" fill="none"/>')


def _rest_marks(msegs: Sequence[dict], ml: dict, top: float) -> list[str]:
    """音のない区間を休符記号で埋める(#127)。空小節は全休符。

    #143: タイ分割済みセグメントで占有を判定するため、小節跨ぎ音の続き小節に
    誤って休符が出る旧バグは構造的に発生しない。
    """
    parts: list[str] = []
    beats = ml["beats"]
    m_start = ml["m"] * beats
    spans = []
    for g in msegs:
        s = max(0.0, g["b"] - m_start)
        e = min(float(beats), g["b"] - m_start + g["dur"])
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
    if beats - cur > 0.25:
        gaps.append((cur, float(beats)))
    for gs, ge in gaps:
        b = round(gs * 4) / 4  # 0.25拍格子へ
        rem = round((ge - b) * 4) / 4
        while rem >= 0.5 - _EPS:
            for size in (4.0, 2.0, 1.0, 0.5):
                if rem >= size - _EPS:
                    parts.append(_rest_svg(size, _mx(ml, b), top))
                    b += size
                    rem -= size
                    break
    return parts


def _chord_ellipses(msegs: Sequence[dict], ml: dict, top: float) -> list[str]:
    """同一オンセットに2音以上ある和音を楕円で囲む(#127・参考動画準拠)。"""
    parts: list[str] = []
    groups: dict[float, list[dict]] = {}
    for g in msegs:
        if g["cont"]:
            continue  # タイ継続の括弧数字は囲まない
        groups.setdefault(round(g["b"], 6), []).append(g)
    beats = ml["beats"]
    m_start = ml["m"] * beats
    for start, gg in groups.items():
        if len(gg) < 2:
            continue
        x = _mx(ml, start - m_start)
        ys = [top + (5 - g["string"]) * _LINE_GAP for g in gg]
        cy = (min(ys) + max(ys)) / 2
        ry = (max(ys) - min(ys)) / 2 + 15
        rx = 15 + 4 * max(len(str(g["fret"])) for g in gg)
        parts.append(
            f'<ellipse class="chord-ellipse" cx="{x:.1f}" cy="{cy:.1f}" '
            f'rx="{rx}" ry="{ry:.1f}" stroke="#666" stroke-width="1.4" fill="none"/>')
    return parts


def _draw_chord_band(chord_spans: list, row: list[dict], top: float,
                     chord_diagrams: bool) -> list[str]:
    """段の上部にコード帯を描く。コード変化点にネーム＋図。"""
    parts: list[str] = []
    by_m = {ml["m"]: ml for ml in row}
    for cs in chord_spans:
        if cs.name == "N.C.":
            continue
        beats = row[0]["beats"] if row else 4
        m = int(cs.start_beats // beats)
        ml = by_m.get(m)
        if ml is None:
            continue
        cx = _mx(ml, cs.start_beats - m * beats)
        if chord_diagrams:
            shape = shape_for(cs.root_pc, cs.quality)
            parts.append(diagram_svg(shape, cs.name, cx - 22, top - _CHORD_BAND_H + 14, scale=1.0))
        else:
            parts.append(f'<text x="{cx}" y="{top - 12}" font-size="22" '
                         f'text-anchor="middle" font-weight="bold" fill="#222">{_esc(cs.name)}</text>')
    return parts


def _timesig_svg(beats: int, x: float, top: float) -> list[str]:
    """拍子記号(#143): 第1小節左にL/4の数字スタックをスタッフ上に描く。"""
    cx = x + _TS_PAD / 2
    return [
        f'<text class="timesig" x="{cx:.1f}" y="{top + 2.1 * _LINE_GAP}" font-size="52" '
        f'font-weight="bold" text-anchor="middle" fill="#222">{beats}</text>',
        f'<text class="timesig" x="{cx:.1f}" y="{top + 4.6 * _LINE_GAP}" font-size="52" '
        f'font-weight="bold" text-anchor="middle" fill="#222">4</text>',
    ]


def _render_pages(tabs: list[TabNote], bpm: float, title: str | None,
                  n_shifted: int, n_dropped: int,
                  chord_spans: list, chord_diagrams: bool,
                  beats_per_measure: int = 4, grid_per_beat: int = 4) -> list[str]:
    beats = beats_per_measure
    segs = _display_segments(tabs, beats)
    by_measure: dict[int, list[dict]] = {}
    for g in segs:
        by_measure.setdefault(int(g["b"] // beats + _EPS), []).append(g)
    rows = _layout_rows(tabs, beats, segs=segs)

    sys_per_page_first = int((_PAGE_H - 2 * _MARGIN - _HEADER_H) // (_SYS_H + _SYS_GAP))
    sys_per_page = int((_PAGE_H - 2 * _MARGIN) // (_SYS_H + _SYS_GAP))

    pages: list[str] = []
    row_idx = 0
    last_pos: dict[int, tuple[int, float, float]] = {}  # src -> (row, x, y) タイ弧用
    while row_idx < len(rows) or not pages:
        first = not pages
        cap = sys_per_page_first if first else sys_per_page
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_PAGE_W}" height="{_PAGE_H}" '
            # cairosvgは候補リストのフォールバックをせず先頭の実在フォントで全描画するため、
            # 日本語/韓国語タイトルの豆腐化を防ぐにはCJK対応フォントを先頭に置く必要がある。
            f'viewBox="0 0 {_PAGE_W} {_PAGE_H}" '
            f'font-family="\'Arial Unicode MS\', \'Hiragino Sans\', \'Noto Sans CJK JP\', Helvetica, Arial, sans-serif">',
            f'<rect width="{_PAGE_W}" height="{_PAGE_H}" fill="white"/>',
        ]
        y = _MARGIN
        if first:
            t = _esc(title or "TAB")
            parts.append(f'<text x="{_PAGE_W/2}" y="{y+40}" font-size="48" text-anchor="middle">{t}</text>')
            sub = (f"Guitar TAB | BPM {int(round(bpm))} | {beats}/4 | "
                   f"Tuning: E A D G B E")
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
        while drawn < cap and (row_idx < len(rows) or (first and drawn == 0)):
            top = y
            row = rows[row_idx] if row_idx < len(rows) else []
            parts.extend(_draw_chord_band(chord_spans, row, top, chord_diagrams))
            row_x0 = row[0]["x0"] if row else _MARGIN
            row_x1 = (row[-1]["x0"] + row[-1]["w"]) if row else _PAGE_W - _MARGIN
            for li in range(6):
                ly = top + li * _LINE_GAP
                parts.append(f'<line x1="{row_x0}" y1="{ly}" x2="{row_x1:.1f}" y2="{ly}" stroke="#333" stroke-width="1.6"/>')
            for ch, frac in zip("TAB", (0.16, 0.5, 0.84)):
                parts.append(f'<text x="{_MARGIN-34}" y="{top+_SYS_H*frac+8}" font-size="26" fill="#333">{ch}</text>')
            for ml in row:
                parts.append(f'<line x1="{ml["x0"]:.1f}" y1="{top}" x2="{ml["x0"]:.1f}" y2="{top+_SYS_H}" stroke="#333" stroke-width="1.6"/>')
                parts.append(f'<text class="mnum" x="{ml["x0"]+5:.1f}" y="{top-8}" font-size="17" fill="#555">{ml["m"]+1}</text>')
                if ml["m"] == 0:
                    parts.extend(_timesig_svg(beats, ml["x0"], top))
            parts.append(f'<line x1="{row_x1:.1f}" y1="{top}" x2="{row_x1:.1f}" y2="{top+_SYS_H}" stroke="#333" stroke-width="1.6"/>')
            rects: list[str] = []
            texts: list[str] = []
            ties: list[str] = []
            for ml in row:
                msegs = by_measure.get(ml["m"], [])
                parts.extend(_rhythm_marks(msegs, ml, top, grid_per_beat))
                parts.extend(_rest_marks(msegs, ml, top))
                m_start = ml["m"] * beats
                for g in msegs:
                    nx = _mx(ml, g["b"] - m_start)
                    ny = top + (5 - g["string"]) * _LINE_GAP
                    bw = g["w"]
                    cls = ' class="tie-digit"' if g["cont"] else ""
                    fill = "#666" if g["cont"] else "#000"
                    rects.append(f'<rect x="{nx-bw/2:.1f}" y="{ny-13}" width="{bw:.0f}" height="26" fill="white"/>')
                    texts.append(f'<text{cls} x="{nx:.1f}" y="{ny+8}" font-size="24" font-weight="bold" '
                                 f'text-anchor="middle" fill="{fill}">{g["label"]}</text>')
                    if g["shift"]:
                        texts.append(f'<text x="{nx:.1f}" y="{ny-16}" font-size="17" text-anchor="middle" fill="#b05050">*</text>')
                    if g["cont"]:
                        prev = last_pos.get(g["src"])
                        if prev and prev[0] == row_idx:
                            # タイ弧: 数字の上側外周(数字を遮らない・調査の失敗例回避)
                            x1, y1 = prev[1], prev[2]
                            ties.append(
                                f'<path class="tie" d="M{x1:.1f},{y1 - 15} '
                                f'Q{(x1 + nx) / 2:.1f},{y1 - 30} {nx:.1f},{ny - 15}" '
                                f'stroke="#444" stroke-width="1.8" fill="none"/>')
                    last_pos[g["src"]] = (row_idx, nx, ny)
            parts.extend(rects)
            parts.extend(texts)
            parts.extend(ties)
            for ml in row:
                parts.extend(_chord_ellipses(by_measure.get(ml["m"], []), ml, top))
            y += _SYS_H + _SYS_GAP
            drawn += 1
            row_idx += 1
        parts.append(f'<text x="{_PAGE_W/2}" y="{_PAGE_H-56}" font-size="18" text-anchor="middle" fill="#999">- {len(pages)+1} -</text>')
        parts.append("</svg>")
        pages.append("".join(parts))
        if row_idx >= len(rows):
            break
    return pages


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def count_overlaps(tabs: list[TabNote], beats: int = 4) -> int:
    """視覚的に数字が重なるペア数を数える（可読性の実測検証）。

    #139以降は実レイアウト(spring-rod)基準・タイ分割込みで判定する。同一段・
    同一弦で、隣接表示の中心間隔が表示幅平均の8割未満なら「重なって読めない」。
    0なら全数字が判読可能。
    """
    segs = _display_segments(tabs, beats)
    rows = _layout_rows(tabs, beats, segs=segs)
    m_to_row: dict[int, int] = {}
    m_to_ml: dict[int, dict] = {}
    for ri, row in enumerate(rows):
        for ml in row:
            m_to_row[ml["m"]] = ri
            m_to_ml[ml["m"]] = ml
    by_key: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for g in segs:
        m = int(g["b"] // beats + _EPS)
        ml = m_to_ml.get(m)
        if ml is None:
            continue
        nx = _mx(ml, g["b"] - m * beats)
        by_key.setdefault((m_to_row[m], g["string"]), []).append((nx, g["w"]))
    overlaps = 0
    for xs in by_key.values():
        xs.sort()
        for (x1, w1), (x2, w2) in zip(xs, xs[1:]):
            if x2 - x1 < (w1 + w2) / 2 * 0.8:
                overlaps += 1
    return overlaps


def write_tab_pdf(notes: Sequence[QuantizedNote], bpm: float,
                  out_pdf: str | Path, title: str | None = None,
                  chord_diagrams: bool = True, monophonic: bool = False,
                  beats_per_measure: int | None = None,
                  grid_per_beat: int = 4) -> dict:
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
    # #143: 拍子は五線譜(score.py)と同一推定器で一致させる。上書きがあれば尊重
    if beats_per_measure is None:
        from earpipe.services.rhythm.meter import estimate_meter

        beats_per_measure = estimate_meter(list(notes))
    chord_spans = estimate_chords(notes, bpm)
    n_shifted = sum(1 for t in tabs if t.octave_shift)
    n_dropped = len(list(tab_notes)) - len(tabs) if tab_notes else 0
    # 同時7音以上の切り捨て等もドロップに含まれる（assign_fretsの上限6音）
    n_dropped = max(0, n_dropped)

    svgs = _render_pages(tabs, bpm, title, n_shifted, n_dropped, chord_spans,
                         chord_diagrams, beats_per_measure=beats_per_measure,
                         grid_per_beat=grid_per_beat)
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
    # #142: 慣用形(パワーコード/オクターブ/バレー)が発動した同時発音グループ数
    groups: dict[float, list[TabNote]] = {}
    for t in tabs:
        groups.setdefault(round(t.start_beats, 6), []).append(t)
    n_idiom = sum(
        1 for g in groups.values() if len(g) >= 2 and _idiom_bonus(
            [(t.string_index, t.fret) for t in g],
            [TUNING_GUITAR[t.string_index] + t.fret for t in g],
        ) > 0
    )
    return {
        "pages": len(svgs),
        "n_octave_shifted": n_shifted,
        "n_dropped": n_dropped,
        "n_notes_placed": len(tabs),
        "n_overlaps": count_overlaps(tabs, beats=beats_per_measure),
        "beats_per_measure": beats_per_measure,
        "n_idiom_shapes": n_idiom,
        "n_chords": sum(1 for c in chord_spans if c.name != "N.C."),
    }
