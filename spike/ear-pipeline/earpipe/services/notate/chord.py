"""コード認識（クロマ・テンプレート相関方式）。

多声ノイズに強い定石: ピッチクラスヒストグラム（音価重み）を各コード
テンプレートと相関させ最良を選ぶ。music21の厳密なコードシンボル判定は
ノイズで転回形/識別不能になるため使わない。スコアが閾値未満は N.C.。

変化検出: 連続同一コードを統合し、短命コード（min_dur_beats未満）は隣に吸収。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.spelling import estimate_key

# quality -> ルートからの相対ピッチクラス集合
CHORD_TEMPLATES: dict[str, tuple[int, ...]] = {
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
    "dom7": (0, 4, 7, 10),
    "min7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11),
    "dim": (0, 3, 6),
    "sus4": (0, 5, 7),
}
_QUALITY_SUFFIX = {
    "major": "", "minor": "m", "dom7": "7", "min7": "m7",
    "maj7": "maj7", "dim": "dim", "sus4": "sus4",
}
# シャープ系/フラット系の音名（調で選ぶ）
_SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# コードと判定する最小スコア（テンプレート適合度）。これ未満は N.C.
_MIN_SCORE = 0.55
# テンプレート外の音への重みペナルティ係数
_OUTSIDE_PENALTY = 1.0


@dataclass(frozen=True)
class ChordSpan:
    start_beats: float
    end_beats: float
    name: str        # "C" / "Am" / "G7" / "N.C."
    root_pc: int     # 0-11。N.C.は -1
    quality: str     # "major" 等。N.C.は ""


def _use_flats(notes: Sequence[QuantizedNote]) -> bool:
    """調から音名の綴り（#/♭）を決める。フラット系の調は♭表記。"""
    try:
        key = estimate_key(notes)
        # music21 Key: sharps<0 ならフラット系
        return key.sharps < 0
    except Exception:
        return False


def _name(root_pc: int, quality: str, use_flats: bool) -> str:
    names = _FLAT_NAMES if use_flats else _SHARP_NAMES
    return names[root_pc % 12] + _QUALITY_SUFFIX[quality]


def _best_chord(hist: list[float]) -> tuple[int, str, float]:
    """12次元ヒストグラムに最も合うコードを返す (root_pc, quality, score)。"""
    total = sum(hist)
    if total <= 0:
        return -1, "", 0.0
    best = (-1, "", 0.0)
    for root in range(12):
        for quality, rel in CHORD_TEMPLATES.items():
            members = {(root + r) % 12 for r in rel}
            inside = sum(hist[pc] for pc in members)
            outside = total - inside
            # スコア: コード構成音のエネルギー比 − テンプレート外のペナルティ
            score = (inside - _OUTSIDE_PENALTY * outside) / total
            # 構成音がすべて鳴っているかの充足も加味（欠けを軽く罰する）
            present = sum(1 for pc in members if hist[pc] > 0) / len(members)
            score *= present
            if score > best[2]:
                best = (root, quality, score)
    return best


def _window_chord(win_notes: list[QuantizedNote]) -> tuple[int, str, float]:
    hist = [0.0] * 12
    for n in win_notes:
        hist[n.midi % 12] += max(n.dur_beats, 0.01) * max(n.confidence, 0.1)
    return _best_chord(hist)


def estimate_chords(
    notes: Sequence[QuantizedNote],
    bpm: float,
    window_beats: float = 0.5,
    min_dur_beats: float = 1.0,
) -> list[ChordSpan]:
    """音符列からコード進行を推定する。変化検出で連続同一を統合。"""
    if not notes:
        return []

    use_flats = _use_flats(notes)
    end = max(n.start_beats + n.dur_beats for n in notes)
    n_windows = max(1, int(round(end / window_beats)))

    # 各窓のコードを推定
    raw: list[tuple[float, int, str, float]] = []  # (win_start, root, quality, score)
    for w in range(n_windows):
        ws, we = w * window_beats, (w + 1) * window_beats
        win_notes = [n for n in notes if n.start_beats < we and n.start_beats + n.dur_beats > ws]
        root, quality, score = _window_chord(win_notes)
        if score < _MIN_SCORE:
            raw.append((ws, -1, "", 0.0))
        else:
            raw.append((ws, root, quality, score))

    # 連続同一コードを統合してスパン化
    spans: list[ChordSpan] = []
    i = 0
    while i < len(raw):
        ws, root, quality, _ = raw[i]
        j = i + 1
        while j < len(raw) and raw[j][1] == root and raw[j][2] == quality:
            j += 1
        span_end = raw[j][0] if j < len(raw) else end
        name = "N.C." if root < 0 else _name(root, quality, use_flats)
        spans.append(ChordSpan(ws, span_end, name, root, quality))
        i = j

    return _absorb_short(spans, min_dur_beats, end)


def _absorb_short(spans: list[ChordSpan], min_dur: float, end: float) -> list[ChordSpan]:
    """min_dur未満の短命コードを隣接（前優先）に吸収して統合する。"""
    if not spans:
        return spans
    # 短命スパンを除去し、隣接同名を再統合
    kept: list[ChordSpan] = []
    for s in spans:
        dur = s.end_beats - s.start_beats
        if dur < min_dur and kept:
            # 前のスパンを延長して吸収
            prev = kept[-1]
            kept[-1] = ChordSpan(prev.start_beats, s.end_beats, prev.name, prev.root_pc, prev.quality)
        else:
            kept.append(s)
    # 吸収後に隣接同名が生じたら再統合
    merged: list[ChordSpan] = []
    for s in kept:
        if merged and merged[-1].name == s.name:
            p = merged[-1]
            merged[-1] = ChordSpan(p.start_beats, s.end_beats, p.name, p.root_pc, p.quality)
        else:
            merged.append(s)
    return merged
