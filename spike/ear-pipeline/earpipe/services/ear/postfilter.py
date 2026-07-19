"""後処理フィルタ(#31): 幽霊オンセット除去。

解剖(docs/research/rhythm-autopsy.md)の実測に基づく:
- precision 0.23-0.40 の主因 = 倍音誤検出・ペダル再トリガーによる同一音高の分裂・密集ゴミ
- 対策は (a)分裂マージ (b)倍音整合フィルタ。confidence閾値の適応化は
  「recall救済(#32)と併用したときだけ意味を持つ」ため apply_postfilter に内蔵する。

すべて純関数(イベント列 → 新しいイベント列)。エンジン層に楽器固有の分岐は持たない(NF-050)。
"""

from earpipe.contracts import PitchEvent

MERGE_GAP_SEC = 0.08          # 同一音高がこのギャップ以下で連続したら分裂とみなす
GHOST_CONF_MAX = 0.4          # これ以下の確信度のみ倍音幽霊の候補になる
GHOST_SUPPORT_RATIO = 1.5     # 基音の確信度が幽霊候補の1.5倍以上あること
GHOST_OVERLAP_FRAC = 0.5      # 幽霊候補の時間の半分以上が基音に覆われていること
# 倍音列の音程差(半音)。2f=+12, 3f=+19, 4f=+24, 5f=+28, 6f=+31, 7f=+34, 8f=+36
HARMONIC_INTERVALS = frozenset({12, 19, 24, 28, 31, 34, 36})


def merge_splits(
    events: list[PitchEvent], max_gap: float = MERGE_GAP_SEC
) -> list[PitchEvent]:
    """同一音高の極短ギャップ連続(分裂ノート)を1音に統合する。

    ペダル残響・トレモロ誤検出による再トリガーが対象。確信度は最大値を保持する。
    """
    by_pitch: dict[int, list[PitchEvent]] = {}
    for e in sorted(events, key=lambda x: x.onset):
        by_pitch.setdefault(e.midi, []).append(e)

    merged: list[PitchEvent] = []
    for pitch_events in by_pitch.values():
        run = [pitch_events[0]]
        for e in pitch_events[1:]:
            if e.onset - run[-1].offset <= max_gap:
                run.append(e)
            else:
                merged.append(_merge_run(run))
                run = [e]
        merged.append(_merge_run(run))
    return sorted(merged, key=lambda e: (e.onset, e.midi))


def _merge_run(run: list[PitchEvent]) -> PitchEvent:
    if len(run) == 1:
        return run[0]
    return PitchEvent(
        onset=run[0].onset,
        offset=run[-1].offset,
        midi=run[0].midi,
        confidence=max(e.confidence for e in run),
    )


def _overlap(a: PitchEvent, b: PitchEvent) -> float:
    """b の時間のうち a と重なる割合(0-1)。"""
    inter = min(a.offset, b.offset) - max(a.onset, b.onset)
    dur = b.offset - b.onset
    return max(0.0, inter) / dur if dur > 0 else 0.0


def filter_harmonic_ghosts(
    events: list[PitchEvent],
    conf_max: float = GHOST_CONF_MAX,
    support_ratio: float = GHOST_SUPPORT_RATIO,
    overlap_frac: float = GHOST_OVERLAP_FRAC,
) -> list[PitchEvent]:
    """倍音位置の低確信度音を幽霊として除去する。

    除去条件(すべて満たす場合のみ):
    - 候補の確信度が conf_max 以下
    - より低い音に、確信度が候補の support_ratio 倍以上の「基音」が存在
    - 候補と基音の音程差が倍音列(HARMONIC_INTERVALS)に一致
    - 候補の時間の overlap_frac 以上が基音に覆われている
    条件を欠く音は消さない(取りこぼし側に倒す=recall非劣化の設計)。
    """
    keep: list[PitchEvent] = []
    for cand in events:
        if cand.confidence > conf_max:
            keep.append(cand)
            continue
        is_ghost = any(
            (cand.midi - base.midi) in HARMONIC_INTERVALS
            and base.confidence >= cand.confidence * support_ratio
            and _overlap(base, cand) >= overlap_frac
            for base in events
            if base.midi < cand.midi
        )
        if not is_ghost:
            keep.append(cand)
    return keep


def apply_postfilter(events: list[PitchEvent]) -> list[PitchEvent]:
    """#31の標準後処理: 分裂マージ → 倍音幽霊除去。

    きれいな入力は素通し(非破壊・冪等)。高感度検出(#32)と組で使うと
    「低閾値で拾い、幽霊だけ捨てる」両輪になる。
    """
    if not events:
        return []
    return filter_harmonic_ghosts(merge_splits(events))
