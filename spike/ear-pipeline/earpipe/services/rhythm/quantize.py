"""変換層: 音程イベント → テンポ推定・16分格子への量子化 → 音符列。"""

import numpy as np

from earpipe.contracts import PitchEvent, QuantizedNote

BPM_MIN = 60.0
BPM_MAX = 180.0
BPM_DEFAULT = 120.0
GRID_PER_BEAT = 4        # 16分格子(2分系)
TRIPLET_GRID_PER_BEAT = 3  # 8分3連格子(3分系・Issue #39)
TRIPLET_PENALTY = 0.9    # 3分系のオッカム減点(2分系の方が音楽的に多数派)

# --- テンポ推定のパラメータ(Issue #34) ---
CLUSTER_WINDOW_SEC = 0.035   # 和音の弾きばらつきを1オンセットに束ねる窓
CONFIDENCE_FLOOR = 0.6       # 幽霊除けの信頼度下限(高信頼が十分残る場合のみ適用)
MIN_HI_CONF_EVENTS = 8       # 高信頼イベントがこの数以上なら低信頼を捨てる
IOI_MIN_SEC = 0.06           # これ未満の間隔はノイズ(クラスタ残渣)
IOI_MAX_SEC = 2.5            # これ超の間隔は休符跨ぎとして無視
FIT_BAND = 0.03              # 最良フィットとの許容差(この帯内を同点候補とみなす)
MIN_FIT = 0.35               # 全候補がこれ未満=格子で説明できない→デフォルトへ退避
PRIOR_CENTER_BPM = 108.0     # 音楽的テンポの事前分布中心(緩いガウス・log2空間)
PRIOR_SIGMA_LOG2 = 0.7
SUBDIV_SIGMA_LOG2 = 0.5



def _cluster_onsets(events: list[PitchEvent]) -> list[float]:
    """近接オンセット(和音の弾きばらつき)を1つの代表時刻に束ねる。"""
    onsets = sorted(e.onset for e in events)
    clusters: list[list[float]] = []
    for t in onsets:
        if clusters and t - clusters[-1][-1] <= CLUSTER_WINDOW_SEC:
            clusters[-1].append(t)
        else:
            clusters.append([t])
    return [float(np.mean(c)) for c in clusters]


def _grid_fit(iois: np.ndarray, bpm: float, grid_per_beat: int = GRID_PER_BEAT) -> float:
    """IOI列が指定格子で説明できる度合い(0-1の無次元スコア)。

    格子ずれの平均を「ランダムなら grid/4 になる」期待値で正規化する。
    秒単位の生誤差と違い、細かい格子(速いテンポ)が自動的に有利にならない
    — これが旧実装の145-150固着(幽霊混入時)の根治。
    """
    grid = 60.0 / bpm / grid_per_beat
    x = iois / grid
    dev = float(np.mean(np.abs(x - np.round(x))))  # 0(完全)〜0.25(ランダム期待値)
    return max(0.0, 1.0 - 4.0 * dev)


def _log2_gauss(x: float, center: float, sigma: float) -> float:
    d = np.log2(x / center)
    return float(np.exp(-(d * d) / (2.0 * sigma * sigma)))


def estimate_tempo(
    events: list[PitchEvent],
    bpm_min: float = BPM_MIN,
    bpm_max: float = BPM_MAX,
) -> float:
    """オンセット間隔(IOI)が16分格子に乗るテンポを、頑健化つきで推定する。

    旧実装の欠陥(Issue #34): 幽霊オンセット混入時に誤差が速いテンポほど単調に
    小さくなり、真のテンポと無関係に145-150帯へ固着。和音の非同時性で倍半誤りも発生。

    対策の三段構え:
    1. 幽霊除け: 高信頼イベントが十分あれば低信頼(confidence<0.6)を捨てる
    2. 和音束ね: 近接オンセットをクラスタ化し、IOIベースの無次元フィットで
       「細かい格子ほど有利」のバイアスを除去。説明できない場合はデフォルトへ退避
    3. 倍半処理: フィット同点帯の候補から、中央値IOIの音価妥当性(8分/4分を優先)
       と音楽的テンポ事前分布(log2ガウス)の積で選択

    限界: 一定テンポを仮定する。ルバート・テンポ変化曲は範囲外(READMEに記録)。
    """
    hi = [e for e in events if e.confidence >= CONFIDENCE_FLOOR]
    use = hi if len(hi) >= MIN_HI_CONF_EVENTS else events

    times = _cluster_onsets(use)
    if len(times) < 3:
        return BPM_DEFAULT
    diffs = np.diff(np.asarray(times))
    iois = diffs[(diffs >= IOI_MIN_SEC) & (diffs <= IOI_MAX_SEC)]
    if len(iois) < 2:
        return BPM_DEFAULT

    bpms = np.arange(bpm_min, bpm_max + 0.25, 0.5)
    fits = {float(b): _grid_fit(iois, float(b)) for b in bpms}
    best_fit = max(fits.values())
    if best_fit < MIN_FIT:
        return BPM_DEFAULT  # 格子で説明できない(幽霊の嵐等)→固着せず退避

    med_ioi = float(np.median(iois))
    band = [b for b, f in fits.items() if f >= best_fit - FIT_BAND]

    def total_score(bpm: float) -> float:
        spb = 60.0 / bpm
        ratio = med_ioi / spb  # 中央値IOIが何拍分か
        # 8分(0.5拍)・4分(1.0拍)を最尤の音価と見なす緩い事前分布
        subdiv = max(
            _log2_gauss(ratio, 0.5, SUBDIV_SIGMA_LOG2),
            _log2_gauss(ratio, 1.0, SUBDIV_SIGMA_LOG2),
        )
        prior = _log2_gauss(bpm, PRIOR_CENTER_BPM, PRIOR_SIGMA_LOG2)
        return fits[bpm] * subdiv * prior

    return max(band, key=total_score)


def _prep_iois(events: list[PitchEvent]) -> np.ndarray | None:
    """テンポ推定用のIOI列(幽霊除け・和音束ね込み)。推定不能ならNone。"""
    hi = [e for e in events if e.confidence >= CONFIDENCE_FLOOR]
    use = hi if len(hi) >= MIN_HI_CONF_EVENTS else events
    times = _cluster_onsets(use)
    if len(times) < 3:
        return None
    diffs = np.diff(np.asarray(times))
    iois = diffs[(diffs >= IOI_MIN_SEC) & (diffs <= IOI_MAX_SEC)]
    return iois if len(iois) >= 2 else None


def _system_total(
    iois: np.ndarray, bpm: float, grid_per_beat: int, subdiv_centers: tuple[float, ...]
) -> float:
    """格子系比較用の総合スコア: fit × 音価妥当性 × テンポ事前分布。

    2分系/3分系の比較では、各系の自然な音価(2分系=16分/8分/4分、
    3分系=3連8分/3連4分/4分)を対等に扱う必要があるため、
    estimate_tempo 内部(8分/4分のみ)より広い中心集合を使う。
    """
    med_ioi = float(np.median(iois))
    ratio = med_ioi / (60.0 / bpm)
    subdiv = max(_log2_gauss(ratio, c, SUBDIV_SIGMA_LOG2) for c in subdiv_centers)
    prior = _log2_gauss(bpm, PRIOR_CENTER_BPM, PRIOR_SIGMA_LOG2)
    return _grid_fit(iois, bpm, grid_per_beat) * subdiv * prior


def estimate_grid(
    events: list[PitchEvent],
    bpm_min: float = BPM_MIN,
    bpm_max: float = BPM_MAX,
) -> tuple[float, int]:
    """テンポと格子系(2分系=4/3分系=3)を同時推定する(Issue #39)。

    背景: 3連8分格子@T は 16分格子@1.5T と数学的に同一(エイリアシング)のため、
    格子系を固定したままでは三連符曲のテンポが1.5倍に化ける
    (Romanze: 正解96 → 旧実装144)。両系を候補にし、音価妥当性と
    テンポ事前分布(+3分系へのオッカム減点)で選択する。

    既知の限界(正直な記録): 一様な音符列では両系が完全に同点になるため、
    事前分布中心(108BPM)から遠い三連曲は2分系に倒れうる。
    ルバート・区間転換(曲中の系切替)はスコープ外。
    """
    iois = _prep_iois(events)
    if iois is None:
        return BPM_DEFAULT, GRID_PER_BEAT

    # 2分系: 既存 estimate_tempo の選択をそのまま使う(挙動不変)
    bpm_d = estimate_tempo(events, bpm_min, bpm_max)
    total_d = _system_total(iois, bpm_d, GRID_PER_BEAT, (0.25, 0.5, 1.0))

    # 3分系: 同じ機構を3連格子で探索
    bpms = np.arange(bpm_min, bpm_max + 0.25, 0.5)
    fits3 = {float(b): _grid_fit(iois, float(b), TRIPLET_GRID_PER_BEAT) for b in bpms}
    best3 = max(fits3.values())
    if best3 < MIN_FIT:
        return bpm_d, GRID_PER_BEAT
    band3 = [b for b, f in fits3.items() if f >= best3 - FIT_BAND]
    bpm_t = max(
        band3,
        key=lambda b: _system_total(
            iois, b, TRIPLET_GRID_PER_BEAT, (1.0 / 3.0, 2.0 / 3.0, 1.0)
        ),
    )
    total_t = TRIPLET_PENALTY * _system_total(
        iois, bpm_t, TRIPLET_GRID_PER_BEAT, (1.0 / 3.0, 2.0 / 3.0, 1.0)
    )

    if total_t > total_d:
        return bpm_t, TRIPLET_GRID_PER_BEAT
    return bpm_d, GRID_PER_BEAT


def quantize_events(
    events: list[PitchEvent],
    bpm: float,
    mono: bool = True,
    grid_per_beat: int = GRID_PER_BEAT,
) -> list[QuantizedNote]:
    """イベントを拍格子に吸着させ音符列にする(既定は16分格子、3=3連8分格子)。

    - 開始・長さとも最寄りの格子に丸める(最短は1格子)
    - mono=True: 次の音符の開始を越える長さは切り詰める(単旋律の前提)
    - mono=False(多声): 同時発音を許し、切り詰めは行わない
    - 同一開始・同一音高の重複は長い方を残す
    """
    if not events:
        return []
    grid = 60.0 / bpm / grid_per_beat

    raw: list[QuantizedNote] = []
    for e in sorted(events, key=lambda ev: ev.onset):
        start_q = int(round(e.onset / grid))
        dur_q = max(1, int(round((e.offset - e.onset) / grid)))
        raw.append(
            QuantizedNote(
                start_beats=start_q / grid_per_beat,
                dur_beats=dur_q / grid_per_beat,
                midi=e.midi,
                confidence=e.confidence,
                onset_sec=e.onset,
                offset_sec=e.offset,
            )
        )

    dedup: dict[tuple[float, int], QuantizedNote] = {}
    for n in raw:
        key = (n.start_beats, n.midi)
        if key not in dedup or n.dur_beats > dedup[key].dur_beats:
            dedup[key] = n

    notes = sorted(dedup.values(), key=lambda n: (n.start_beats, n.midi))
    if not mono:
        return notes
    clipped: list[QuantizedNote] = []
    for i, n in enumerate(notes):
        dur = n.dur_beats
        if i + 1 < len(notes):
            gap = notes[i + 1].start_beats - n.start_beats
            if gap > 0:
                dur = min(dur, gap)
        dur = max(dur, 1.0 / grid_per_beat)
        # 切り詰めは格子側のみ。実タイミング(onset_sec/offset_sec)は保持する(C3)
        clipped.append(
            QuantizedNote(
                n.start_beats, dur, n.midi, n.confidence, n.onset_sec, n.offset_sec
            )
        )
    return clipped
