"""変換層: 区間別テンポ系列（テンポマップ・Issue #56 / C2受入条件）。

一定テンポ推定(estimate_tempo/estimate_grid)の上に載る区間分割:
イベント列を時間窓に切り、窓ごとに既存のテンポ推定を適用し、
近接テンポ(±5%以内)の隣接区間を併合する。一定テンポ曲は単一区間に退化する。

受入条件(C2): 緩急のある実録音で区間分割が破綻しない(クラッシュ・発散ゼロ)。
発散ゼロの構造保証: 各区間のBPMは estimate_tempo の戻り値(探索範囲内 or
BPM_DEFAULT)に限られ、NaN/inf は構造的に発生しない。

既知の限界(正直な記録):
- 窓内のイベントが少ない区間は前区間のテンポを引き継ぐ(独立推定しない)
- 記譜(quantize/notate)は現状も曲全体の単一テンポ格子を使う。テンポマップは
  分析出力(transcribe結果のtempo_map)として先行提供し、区間別格子での記譜は
  将来課題(ルバート記譜はスラー・フェルマータ等の表記問題を含むため)
"""

from dataclasses import dataclass

from earpipe.contracts import PitchEvent

from .quantize import BPM_DEFAULT, BPM_MAX, BPM_MIN, estimate_tempo

WINDOW_SEC = 10.0        # 区間推定の時間窓(テンポ推定に足るIOI数を確保できる長さ)
MIN_WINDOW_EVENTS = 8    # これ未満の窓は独立推定せず前区間を引き継ぐ
MERGE_TOL_RATIO = 0.05   # 隣接区間の併合閾値(±5% = テンポ受入条件と同じ粒度)


@dataclass(frozen=True)
class TempoSegment:
    """テンポマップの1区間。start_sec から次区間開始(または曲末)まで bpm。"""

    start_sec: float
    bpm: float


def estimate_tempo_map(
    events: list[PitchEvent],
    bpm_min: float = BPM_MIN,
    bpm_max: float = BPM_MAX,
    window_sec: float = WINDOW_SEC,
) -> list[TempoSegment]:
    """イベント列から区間別テンポ系列を推定する。

    - 空入力: [TempoSegment(0.0, BPM_DEFAULT)] を返す(呼び出し側の分岐を不要に)
    - 一定テンポ曲: 窓ごとの推定が±5%内に収まり単一区間に併合される
    - 緩急(ルバート)曲: テンポが5%超変わる境界で区間が分かれる
    """
    if window_sec <= 0:
        raise ValueError(f"window_sec must be positive, got {window_sec}")
    if not events:
        return [TempoSegment(0.0, BPM_DEFAULT)]

    span_end = max(e.offset for e in events)
    segments: list[TempoSegment] = []
    prev_bpm: float | None = None
    t = 0.0
    while t < span_end:
        window = [e for e in events if t <= e.onset < t + window_sec]
        if len(window) >= MIN_WINDOW_EVENTS:
            bpm = estimate_tempo(window, bpm_min, bpm_max)
        elif prev_bpm is not None:
            bpm = prev_bpm  # 疎な窓は前区間を引き継ぐ(限界としてdocstringに記録)
        else:
            bpm = estimate_tempo(events, bpm_min, bpm_max)  # 冒頭から疎: 全体推定
        segments.append(TempoSegment(start_sec=t, bpm=bpm))
        prev_bpm = bpm
        t += window_sec

    return _merge_adjacent(segments)


def _merge_adjacent(segments: list[TempoSegment]) -> list[TempoSegment]:
    """±5%以内で連続する隣接区間を先頭区間に併合する。"""
    merged: list[TempoSegment] = [segments[0]]
    for seg in segments[1:]:
        if abs(seg.bpm - merged[-1].bpm) / merged[-1].bpm <= MERGE_TOL_RATIO:
            continue
        merged.append(seg)
    return merged
