"""score_rhythm — 楽譜レベルのリズムKPI（第5指標。正解MIDIがある場合のみ算出可能）。

設計意図（Issue #33 / rhythm-autopsy §5.1）:
- ms単位の生タイミング一致は、楽譜化に必須の量子化を常に減点してしまう。
  逆に格子ベースの出だし指標は格子吸着を過大評価する。
- 楽譜製品にとってのリズム品質は「拍・小節に対する正しさ」であり、本指標は
  正解楽譜（MIDI）と採譜結果を **拍単位** で比較する。
- テンポの別名（2倍/半分の等価表記）は同じ音楽なので等価として扱う
  （スケール探索によるテンポ・オクターブ不変設計）。
- テンポメタが信用できない採譜（例: 実秒のままメタ120固定）にも、
  データ駆動のスケール候補（IOI中央値比）で整列する。

構成: total = 0.6*beat_f1 + 0.3*dur_agreement + 0.1*bar_consistency
- beat_f1: 音高+拍位置（許容 ±0.25拍）の貪欲マッチF1
- dur_agreement: 音価クラス（16分〜全音符・付点含む）一致率。分母は正解音符全数（未マッチ=不一致）
- bar_consistency: 総小節数の整合（構造が保存されているか）

限界（正直な記録）: 同一音高が反復する曲では、格子の整数倍だけずれた音符が
別の同音高音符と再マッチしうる（純粋な位置置換に甘い）。また単一の大域スケール+オフセットで整列するため、曲中の
テンポチェンジやルバートの局所ずれは吸収しない（それは意図的 — 局所の
ずれこそ測りたい対象）。声部・和音の重複音は音高一致でのみ区別する。
"""

from __future__ import annotations

import numpy as np
import pretty_midi

BEAT_TOL = 0.25  # 拍位置マッチの許容窓[拍]（16分音符相当）
DUR_CLASSES = np.array([0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0])
SCALE_OCTAVES = (0.5, 1.0, 2.0)
BEATS_PER_BAR_DEFAULT = 4.0

Note = tuple[float, float, int]  # (start, end, pitch) 単位は文脈依存（秒 or 拍）


def _notes_sec(pm: pretty_midi.PrettyMIDI) -> list[Note]:
    out: list[Note] = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            out.append((float(n.start), float(n.end), int(n.pitch)))
    return sorted(out)


def _initial_tempo(pm: pretty_midi.PrettyMIDI) -> float:
    _times, tempi = pm.get_tempo_changes()
    return float(tempi[0]) if len(tempi) else 120.0


def _to_beats(notes: list[Note], bpm: float) -> list[Note]:
    k = bpm / 60.0
    return [(s * k, e * k, p) for s, e, p in notes]


def _median_ioi(beats: list[Note]) -> float:
    if len(beats) < 3:
        return 0.0
    starts = np.array(sorted(b[0] for b in beats))
    iois = np.diff(starts)
    iois = iois[iois > 1e-6]
    return float(np.median(iois)) if len(iois) else 0.0


def _greedy_f1(gt: list[Note], est: list[Note], tol: float) -> tuple[float, list[tuple[Note, Note]]]:
    """音高一致+拍位置±tolの貪欲1対1マッチ。F1とマッチ対を返す。"""
    used: set[int] = set()
    pairs: list[tuple[Note, Note]] = []
    for e in sorted(est, key=lambda x: x[0]):
        best_i, best_d = None, tol
        for i, g in enumerate(gt):
            if i in used or g[2] != e[2]:
                continue
            d = abs(g[0] - e[0])
            if d <= best_d:
                best_i, best_d = i, d
        if best_i is not None:
            used.add(best_i)
            pairs.append((gt[best_i], e))
    tp = len(pairs)
    prec = tp / len(est) if est else 0.0
    rec = tp / len(gt) if gt else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return f1, pairs


def _offset_candidates(gt: list[Note], est: list[Note]) -> list[float]:
    """音高が一致するペア候補の開始差の分布から、大域オフセット候補を出す。"""
    diffs: list[float] = []
    by_pitch: dict[int, list[float]] = {}
    for s, _e, p in gt:
        by_pitch.setdefault(p, []).append(s)
    for s, _e, p in est[:200]:
        for g in by_pitch.get(p, [])[:20]:
            diffs.append(g - s)
    if not diffs:
        return [0.0]
    arr = np.array(diffs)
    med = float(np.median(arr))
    # ヒストグラム最頻ビンも候補に（中央値と離れている場合の保険）
    hist, edges = np.histogram(arr, bins=50)
    mode = float((edges[int(np.argmax(hist))] + edges[int(np.argmax(hist)) + 1]) / 2)
    return [0.0, med, mode]


def _duration_class(dur_beats: float) -> int:
    return int(np.argmin(np.abs(DUR_CLASSES - dur_beats)))


def score_rhythm(
    gt_pm: pretty_midi.PrettyMIDI,
    est_pm: pretty_midi.PrettyMIDI,
    beats_per_bar: float = BEATS_PER_BAR_DEFAULT,
) -> dict:
    """正解MIDIと採譜MIDIを拍単位で比較し、楽譜レベルのリズム品質を返す。"""
    gt_tempo = _initial_tempo(gt_pm)
    est_tempo = _initial_tempo(est_pm)
    gt_beats = _to_beats(_notes_sec(gt_pm), gt_tempo)
    est_sec = _notes_sec(est_pm)

    if not gt_beats or not est_sec:
        return {
            "beat_f1": 0.0,
            "dur_agreement": 0.0,
            "bar_consistency": 0.0,
            "total": 0.0,
            "scale": None,
            "offset": None,
            "explain": "正解または採譜の音符が空のため0点",
        }

    # スケール候補: オクターブ基本形 + テンポメタ比×オクターブ + データ駆動(IOI中央値比)×オクターブ
    est_beats_meta = _to_beats(est_sec, est_tempo)
    candidates: set[float] = set(SCALE_OCTAVES)
    meta_ratio = gt_tempo / est_tempo if est_tempo > 0 else 1.0
    for k in SCALE_OCTAVES:
        candidates.add(float(np.clip(meta_ratio * k, 0.1, 10.0)))
    gt_ioi = _median_ioi(gt_beats)
    est_ioi_meta = _median_ioi(est_beats_meta)
    if gt_ioi > 0 and est_ioi_meta > 0:
        data_ratio = gt_ioi / est_ioi_meta
        for k in SCALE_OCTAVES:
            candidates.add(float(np.clip(data_ratio * k, 0.1, 10.0)))

    best = {"f1": -1.0, "pairs": [], "scale": 1.0, "offset": 0.0, "est": est_beats_meta}
    for scale in sorted(candidates):
        scaled = [(s * scale, e * scale, p) for s, e, p in est_beats_meta]
        for off in _offset_candidates(gt_beats, scaled):
            shifted = [(s + off, e + off, p) for s, e, p in scaled]
            f1, pairs = _greedy_f1(gt_beats, shifted, BEAT_TOL)
            if f1 > best["f1"]:
                best = {"f1": f1, "pairs": pairs, "scale": scale, "offset": off, "est": shifted}

    beat_f1 = max(0.0, best["f1"])
    pairs = best["pairs"]

    # 音価一致は正解音符全数を分母にする（マッチしなかった正解音符=不一致扱い）。
    # マッチ対のみを分母にすると、リズム崩壊でマッチが激減しても音価成分が
    # 満点近くになり総合点に下駄を履かせるため。
    agree = sum(
        1
        for g, e in pairs
        if _duration_class(g[1] - g[0]) == _duration_class(e[1] - e[0])
    )
    dur_agreement = agree / len(gt_beats) if gt_beats else 0.0

    gt_span = max(g[1] for g in gt_beats)
    est_span = max(e[1] for e in best["est"]) if best["est"] else 0.0
    gt_bars = max(1.0, gt_span / beats_per_bar)
    est_bars = est_span / beats_per_bar
    bar_consistency = float(max(0.0, 1.0 - min(1.0, abs(est_bars - gt_bars) / gt_bars)))

    total = 0.6 * beat_f1 + 0.3 * dur_agreement + 0.1 * bar_consistency
    return {
        "beat_f1": round(beat_f1, 4),
        "dur_agreement": round(dur_agreement, 4),
        "bar_consistency": round(bar_consistency, 4),
        "total": round(float(total), 4),
        "scale": round(float(best["scale"]), 4),
        "offset": round(float(best["offset"]), 4),
        "explain": (
            "拍位置一致F1(0.6)+音価クラス一致(0.3)+小節数整合(0.1)。"
            "スケール探索によりテンポの等価表記・メタ誤りを吸収済み"
        ),
    }


def score_rhythm_paths(gt_path: str, est_path: str, beats_per_bar: float = BEATS_PER_BAR_DEFAULT) -> dict:
    return score_rhythm(
        pretty_midi.PrettyMIDI(str(gt_path)),
        pretty_midi.PrettyMIDI(str(est_path)),
        beats_per_bar=beats_per_bar,
    )
