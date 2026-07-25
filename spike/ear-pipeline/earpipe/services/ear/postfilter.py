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
        run_end = pitch_events[0].offset
        for e in pitch_events[1:]:
            # 包含イベントがあるためrun終端は逐次maxで追跡する(レビュー#40 M8)
            if e.onset - run_end <= max_gap:
                run.append(e)
                run_end = max(run_end, e.offset)
            else:
                merged.append(_merge_run(run))
                run = [e]
                run_end = e.offset
        merged.append(_merge_run(run))
    return sorted(merged, key=lambda e: (e.onset, e.midi))


def _merge_run(run: list[PitchEvent]) -> PitchEvent:
    if len(run) == 1:
        return run[0]
    return PitchEvent(
        onset=run[0].onset,
        # 包含イベント(長い音の中に短い再トリガー)ではrun末尾のoffsetが
        # 最大とは限らないためmaxを取る(レビュー#40 M8)
        offset=max(e.offset for e in run),
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


# #144実測(夢見る・正解付き)で導入。多曲較正(2026-07-25)でオフラインは0.9/0.5が
# 良く見えたが、パイプライン実測ではposterior補完との相互作用で夢見る0.752→0.699に
# 退行したため0.75/0.3を維持(オフライン予測とパイプラインの乖離を正直に記録)。
# 強化版(0.9/0.5)はG-TECHS 4声和音では有効(DI 0.512→0.558) — 将来の適応切替候補。
# +12は本物の構成音と分離不能のため対象外。
CLEANUP_INTERVALS = frozenset({19, 24, 28})
CLEANUP_RATIO = 0.75
CLEANUP_CONF_CAP = 0.3


def cleanup_upper_harmonics(events: list[PitchEvent]) -> list[PitchEvent]:
    """+19/+24/+28の弱い上方倍音だけを除去する軽量クリーンアップ(#144・常時ON用)。

    条件: より低い音に重なり、confidence が基音の CLEANUP_RATIO 未満かつ
    CLEANUP_CONF_CAP 未満。+12(オクターブ)は本物の構成音と分離不能のため触らない。
    """
    def ov(a: PitchEvent, b: PitchEvent) -> float:
        return min(a.offset, b.offset) - max(a.onset, b.onset)

    def valid_base(b: PitchEvent) -> bool:
        # サブオクターブ疑いの音は基音として無効(#144実測バグ: C#2幽霊が
        # +19の本物G#3を殺した)。+12上に同等信頼度の音があれば疑う。
        return not any(
            c.midi == b.midi + 12 and ov(b, c) > 0.05
            and c.confidence >= 0.8 * b.confidence
            for c in events
            if c is not b
        )

    out = []
    for e in events:
        is_ghost = any(
            e.midi - b.midi in CLEANUP_INTERVALS and ov(b, e) > 0.05
            and e.confidence < CLEANUP_RATIO * b.confidence
            and e.confidence < CLEANUP_CONF_CAP
            and valid_base(b)
            for b in events
            if b is not e
        )
        if not is_ghost:
            out.append(e)
    return out


def apply_postfilter(events: list[PitchEvent]) -> list[PitchEvent]:
    """#31の標準後処理: 分裂マージ → 倍音幽霊除去。

    きれいな入力は素通し(非破壊・冪等)。高感度検出(#32)と組で使うと
    「低閾値で拾い、幽霊だけ捨てる」両輪になる。
    """
    if not events:
        return []
    return filter_harmonic_ghosts(merge_splits(events))
