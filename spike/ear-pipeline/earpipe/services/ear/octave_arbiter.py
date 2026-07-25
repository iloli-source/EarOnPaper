"""オクターブ構成音の裁定(#144): 偶数/奇数倍音比の同一ルート内クラスタリング。

パワーコードのオクターブ重ね(+12)の有無は、検出器の信頼度では分離できない
(正解付き実曲の実測: 本物と幽霊の信頼度分布が重なる)。一方、ルート音の
偶数倍音エネルギー比 [E(2f0)+E(4f0)] / [E(f0)+E(3f0)] は物理的に分離できる
(実測: 重ねあり0.98〜4.8 vs なし0.38〜1.04。2f0の音が実在すると偶数側が持ち上がる)。

同一ルートの全ヒットの比を2クラスタに分け、明確に分離する場合のみ:
- 高クラスタのヒットに+12が無ければ補完(検出器の見落とし回復)
- 低クラスタのヒットの+12検出を除去(倍音幽霊の抑制)
分離が不明瞭(単峰)なら検出器の判断を尊重して何もしない。楽器分岐なし(NF-050)。
"""

from __future__ import annotations

import numpy as np

from earpipe.contracts import PitchEvent

# 裁定パラメータ(#144の正解付き実曲で調律)
MIN_HITS = 3          # クラスタリングに必要な同一ルートの最小ヒット数
SPLIT_RATIO = 1.5     # 高/低クラスタ中心比がこれ以上なら「分離あり」とみなす
FIFTH_OV_SEC = 0.05   # 5度(+7)の同時性判定の最小重なり秒
_CQT_BINS = 84        # C1..B7
_CQT_FMIN_MIDI = 24   # C1


def _even_odd_ratio(C: np.ndarray, times: np.ndarray, root: int,
                    t0: float, t1: float) -> float:
    """ルートの偶数倍音(2f0,4f0=+12,+24) / 奇数側(f0,3f0≈+19) エネルギー比。"""
    def e(midi: int) -> float:
        b = midi - _CQT_FMIN_MIDI
        if not 0 <= b < C.shape[0]:
            return 0.0
        i0, i1 = np.searchsorted(times, t0), np.searchsorted(times, t1)
        if i1 <= i0:
            return 0.0
        return float(np.median(C[b, i0:i1]))

    even = e(root + 12) + e(root + 24)
    odd = e(root) + e(root + 19)
    return even / max(odd, 1e-9)


def arbitrate_octaves(events: list[PitchEvent], y: np.ndarray, sr: int) -> list[PitchEvent]:
    """パワーコード文脈(+7同時)のルートについて+12構成音を証拠ベースで裁定する。"""
    if not events or y is None or len(y) == 0:
        return sorted(events, key=lambda e: (e.onset, e.midi))
    import librosa

    def ov(a: PitchEvent, b: PitchEvent) -> float:
        return min(a.offset, b.offset) - max(a.onset, b.onset)

    # パワーコード文脈のルートヒットを収集
    contexts: list[PitchEvent] = [
        r for r in events
        if any(f.midi - r.midi == 7 and ov(r, f) > FIFTH_OV_SEC for f in events)
    ]
    by_root: dict[int, list[PitchEvent]] = {}
    for r in contexts:
        by_root.setdefault(r.midi, []).append(r)
    if not any(len(v) >= MIN_HITS for v in by_root.values()):
        return sorted(events, key=lambda e: (e.onset, e.midi))

    C = np.abs(librosa.cqt(np.asarray(y, dtype=np.float32), sr=sr,
                           fmin=librosa.midi_to_hz(_CQT_FMIN_MIDI),
                           n_bins=_CQT_BINS, bins_per_octave=12))
    times = librosa.times_like(C, sr=sr)

    out = list(events)
    removed: set[int] = set()

    def _energy(midi: int, t0: float, t1: float) -> float:
        b = midi - _CQT_FMIN_MIDI
        if not 0 <= b < C.shape[0]:
            return 0.0
        i0, i1 = np.searchsorted(times, t0), np.searchsorted(times, t1)
        return float(np.median(C[b, i0:i1])) if i1 > i0 else 0.0

    # サブオクターブ幽霊の一般除去(#144実測: E5根音のE3がE2として検出される)。
    # 物理: X−12帯のf0エネルギーはXの倍音では作れない(倍音はXより上にしか出ない)。
    # 逆にXのf0帯はX−12の第2倍音で埋まる。よって「Xのf0がX+12帯より明確に弱い」
    # 検出Xはサブオクターブ幽霊 → X+12へ置換する。
    for e in list(out):
        if id(e) in removed:
            continue
        if _energy(e.midi, e.onset, e.offset) < 0.4 * _energy(e.midi + 12, e.onset, e.offset):
            removed.add(id(e))
            if not any(x.midi == e.midi + 12 and ov(e, x) > 0.03 for x in out):
                out.append(PitchEvent(onset=e.onset, offset=e.offset,
                                      midi=e.midi + 12, confidence=e.confidence))

    # 下方オクターブ補完(#144実測: G#2がG#3として上方誤検出される)。
    # X−12帯に本物同等のf0エネルギーがあれば、下の音が実在する(上の倍音では説明不能)。
    # 検出Xのf0がX−12の第2倍音由来で弱い場合は置換、独立に強ければ両方実在として追加。
    for e in list(out):
        if id(e) in removed:
            continue
        below = _energy(e.midi - 12, e.onset, e.offset)
        here = _energy(e.midi, e.onset, e.offset)
        if below >= 0.8 * here and below > 0:
            if not any(x.midi == e.midi - 12 and ov(e, x) > 0.03 for x in out):
                out.append(PitchEvent(onset=e.onset, offset=e.offset,
                                      midi=e.midi - 12, confidence=e.confidence))
    for root_midi, hits in by_root.items():
        if len(hits) < MIN_HITS:
            continue
        ratios = [_even_odd_ratio(C, times, root_midi, h.onset, h.offset) for h in hits]
        order = np.argsort(ratios)
        # 1次元2クラスタ: 最大ギャップで分割し、中心比で分離判定
        sorted_r = [ratios[i] for i in order]
        gaps = [sorted_r[i + 1] / max(sorted_r[i], 1e-9) for i in range(len(sorted_r) - 1)]
        if not gaps:
            continue
        k = int(np.argmax(gaps))
        low, high = sorted_r[: k + 1], sorted_r[k + 1:]
        if not high or np.mean(high) / max(np.mean(low), 1e-9) < SPLIT_RATIO:
            continue  # 単峰=分離なし → 検出器を尊重
        thr = (max(low) + min(high)) / 2
        for h, ratio in zip(hits, ratios):
            oct_events = [e for e in events if e.midi == root_midi + 12 and ov(h, e) > 0.03]
            if ratio > thr and not oct_events:
                # 重ねあり判定なのに+12が無い → 補完(検出器の見落とし回復)
                out.append(PitchEvent(
                    onset=h.onset, offset=h.offset, midi=root_midi + 12,
                    confidence=round(h.confidence * 0.6, 4),
                ))
            elif ratio <= thr:
                for e in oct_events:
                    removed.add(id(e))  # 重ねなし判定の+12検出 → 幽霊として除去
    result = [e for e in out if id(e) not in removed]
    return sorted(result, key=lambda e: (e.onset, e.midi))


# #144 選択的抽出v1: 和音テンプレート多数決 + 生事後確率ゲートの補完。
# 同一ルートのヒット群で過半数出現するメンバーは「そのコードの形」— 個別ヒットで
# 検出器が落としても、note/onset事後確率が床値以上残っていれば実在として補完する。
# (実測: 欠けメンバーのnote事後確率0.10-0.21は閾値未満だがゼロではなく、
#  onset headは0.2-0.43で発火している)
TPL_MAJORITY = 0.5
TPL_TAU_NOTE = 0.08
TPL_TAU_ONSET = 0.08


def complete_with_posterior(events: list[PitchEvent], posterior_path,
                            total_dur: float) -> list[PitchEvent]:
    """テンプレート多数決の欠けメンバーを事後確率ゲートで補完する(#144)。"""
    try:
        import numpy as _np

        d = _np.load(str(posterior_path))
        note_p, onset_p = d["note"], d["onset"]
    except Exception:
        return events
    if note_p is None or note_p.ndim != 2 or total_dur <= 0:
        return events
    fps = note_p.shape[0] / total_dur

    def post(midi: int, t0: float, t1: float, mat) -> float:
        k = midi - 21
        if not 0 <= k < mat.shape[1]:
            return 0.0
        i0 = int(t0 * fps)
        i1 = max(i0 + 1, int(t1 * fps))
        return float(mat[i0:i1, k].max()) if i1 <= mat.shape[0] else 0.0

    evs = sorted(events, key=lambda e: e.onset)
    clusters: list[list] = []
    for e in evs:
        if clusters and e.onset - clusters[-1][0] < 0.08:
            clusters[-1][1].append(e)
        else:
            clusters.append([e.onset, [e]])
    from collections import Counter

    by_root: dict[int, list] = {}
    for t0, mem in clusters:
        by_root.setdefault(min(x.midi for x in mem), []).append((t0, mem))
    out = list(events)
    for root, hits in by_root.items():
        if len(hits) < 3:
            continue
        cnt: Counter = Counter()
        for _, mem in hits:
            for m in {x.midi for x in mem}:
                cnt[m] += 1
        template = {m for m, n in cnt.items() if n / len(hits) >= TPL_MAJORITY}
        for t0, mem in hits:
            mset = {x.midi for x in mem}
            t1 = min(max(x.offset for x in mem), t0 + 0.35)
            for miss in template - mset:
                if (post(miss, t0, t1, note_p) >= TPL_TAU_NOTE
                        and post(miss, t0, t0 + 0.15, onset_p) >= TPL_TAU_ONSET):
                    out.append(PitchEvent(t0, t1, miss, 0.35))
    return sorted(out, key=lambda e: (e.onset, e.midi))
