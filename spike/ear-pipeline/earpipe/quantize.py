"""変換層: 音程イベント → テンポ推定・16分格子への量子化 → 音符列。"""

from dataclasses import dataclass

import numpy as np

from earpipe.ear import PitchEvent

BPM_MIN = 60.0
BPM_MAX = 180.0
BPM_DEFAULT = 120.0
GRID_PER_BEAT = 4        # 16分格子
ERR_TOLERANCE_SEC = 0.005  # 最良誤差との許容差(秒)。同点なら遅いテンポを選ぶ


@dataclass(frozen=True)
class QuantizedNote:
    """拍格子に量子化された音符。start/dur は四分音符=1.0 の拍単位。"""

    start_beats: float
    dur_beats: float
    midi: int
    confidence: float


def estimate_tempo(
    events: list[PitchEvent],
    bpm_min: float = BPM_MIN,
    bpm_max: float = BPM_MAX,
) -> float:
    """オンセット列が16分格子に最もよく乗るテンポを探索する。

    誤差は秒単位で測る(格子単位だと粗い格子=遅いテンポほど見かけ上有利になるため)。
    テンポの整数倍(倍取り)も格子に乗るため、誤差が同水準なら最も遅い
    候補(=最も粗い格子で説明できるテンポ)を採用する。
    """
    onsets = sorted(e.onset for e in events)
    if len(onsets) < 3:
        return BPM_DEFAULT
    rel = np.asarray(onsets) - onsets[0]

    candidates: list[tuple[float, float]] = []
    for bpm in np.arange(bpm_min, bpm_max + 0.25, 0.5):
        grid = 60.0 / bpm / GRID_PER_BEAT
        pos = rel / grid
        err_sec = float(np.mean(np.abs(pos - np.round(pos)) * grid))
        candidates.append((err_sec, float(bpm)))

    min_err = min(err for err, _ in candidates)
    for err, bpm in sorted(candidates, key=lambda c: c[1]):  # 遅いテンポ優先
        if err <= min_err + ERR_TOLERANCE_SEC:
            return bpm
    return BPM_DEFAULT


def quantize_events(events: list[PitchEvent], bpm: float) -> list[QuantizedNote]:
    """イベントを16分格子に吸着させ音符列にする。

    - 開始・長さとも最寄りの16分格子に丸める(最短は16分)
    - 次の音符の開始を越える長さは切り詰める(単旋律v0の前提)
    - 同一開始・同一音高の重複は長い方を残す
    """
    if not events:
        return []
    grid = 60.0 / bpm / GRID_PER_BEAT

    raw: list[QuantizedNote] = []
    for e in sorted(events, key=lambda ev: ev.onset):
        start_q = int(round(e.onset / grid))
        dur_q = max(1, int(round((e.offset - e.onset) / grid)))
        raw.append(
            QuantizedNote(
                start_beats=start_q / GRID_PER_BEAT,
                dur_beats=dur_q / GRID_PER_BEAT,
                midi=e.midi,
                confidence=e.confidence,
            )
        )

    dedup: dict[tuple[float, int], QuantizedNote] = {}
    for n in raw:
        key = (n.start_beats, n.midi)
        if key not in dedup or n.dur_beats > dedup[key].dur_beats:
            dedup[key] = n

    notes = sorted(dedup.values(), key=lambda n: (n.start_beats, n.midi))
    clipped: list[QuantizedNote] = []
    for i, n in enumerate(notes):
        dur = n.dur_beats
        if i + 1 < len(notes):
            gap = notes[i + 1].start_beats - n.start_beats
            if gap > 0:
                dur = min(dur, gap)
        dur = max(dur, 1.0 / GRID_PER_BEAT)
        clipped.append(QuantizedNote(n.start_beats, dur, n.midi, n.confidence))
    return clipped
