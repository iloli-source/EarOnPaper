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

import os

import numpy as np

from earpipe.contracts import PitchEvent

# 裁定パラメータ。多曲較正(2026-07-25): 夢見る単曲調律のsub=0.4はGuitar-TECHS
# 4声和音で逆効果だった。パイプライン実測A/Bで sub=0.3 が全ベンチのパレート改善
# (夢見る0.739→0.752 / G-TECHS DI 0.508→0.512 / mic 0.470→0.475)となり採用。
MIN_HITS = 3          # クラスタリングに必要な同一ルートの最小ヒット数
SPLIT_RATIO = 1.5     # 高/低クラスタ中心比がこれ以上なら「分離あり」とみなす
FIFTH_OV_SEC = 0.05   # 5度(+7)の同時性判定の最小重なり秒
SUB_OCTAVE_RATIO = 0.3   # f0がX+12帯のこの比未満ならサブオクターブ幽霊(旧0.4)
DOWN_COMPLETE_RATIO = 0.8  # X-12帯がこの比以上なら下方実在として補完
SIBLING_BETA = 0.6       # 兄弟音補完: 典型エネルギーのこの比以上で欠けメンバー実在と判定
SIBLING_MIN_TEMPLATE = 2  # テンプレ採用に必要な同一ピッチ集合の出現回数
# クラスタ補完の絶対ゲート(#144 gt-muzyx実測 2026-07-26): 相対分離(SPLIT_RATIO)だけだと
# 2声パワーコード曲で+12幽霊を量産(E3×10/A3×5)。highクラスタ中心が偶数優勢の絶対水準
# (0.8)に届かない場合は+12実在の証拠なしとして補完しない。2正解ベンチのパレート点
# (muzyx 0.756→0.830 / 夢見る0.767維持。1.0は夢見るのC#4補完を殺し0.748に退行)。
CLUSTER_COMPLETE_MIN_EVEN = 0.8
_CQT_BINS = 84        # C1..B7
_CQT_FMIN_MIDI = 24   # C1


# 5度補完の物理ゲート(#144 夢見る実測 2026-07-26: 落ちた5度4/4件で
# E(+7)/E(root)=0.31〜0.94, E(+26)/E(root)=0.20〜0.62, 対照ビン比1.3〜2.2)。
# 較正(2026-07-26): 3ベンチ全候補ログ(yume44/muzyx57/octave114件)を正解ラベル付けし
# 合同掃引した最適点。初期値(0.25/0.12/1.15)は幽霊過多で夢見る0.767→0.757と退行、
# 本値で夢見る+0.006/muzyx+0.013/octave±0(幽霊0)の全ベンチ・パレート改善。
FIFTH_F0_RATIO = 0.40    # E(+7) ≥ この比 × E(root f0) (5度の基音1.5f0=非重複)
FIFTH_P3_RATIO = 0.10    # E(+26) ≥ この比 × E(root f0) (5度の第3倍音4.5f0=非重複)
FIFTH_CTRL_MARGIN = 1.4   # E(+7) が隣接ビン(±1半音)の最大よりこの倍数以上
# 下方ルート補完: 検出音Xが5度で、下のルートR=X-7が落ちているケース。
# Rのf0(X-7)とRの第2倍音(X+5)はどちらもXの倍音系列(+12,+19,+24...)と重ならない。
# 較正(2026-07-26): 3ベンチ下方候補218件の正解ラベル合同掃引の最適点。
# 上方(0.40/1.4)より緩いのは、ルートが5度より強く弾かれ偽陽性余地が小さいため
# (掃引でFP=0のまま: 夢見る+5/muzyx+2/octave±0)
ROOT_F0_RATIO = 0.25     # E(X-7) ≥ この比 × E(X)
ROOT_H2_RATIO = 0.10     # E(X+5) ≥ この比 × E(X) (ルートの第2倍音=非重複)
ROOT_CTRL_MARGIN = 1.1    # E(X-7) が隣接ビン最大よりこの倍数以上
# 運用点の選定(2026-07-26実走3点比較): 1.4=夢見る0.786/縦0.815・muzyx0.832 /
# 1.1=夢見る0.788/縦0.852・muzyx0.828 / 1.2=両損(0.786/0.815・0.828)。
# 要件ゲート(縦積み再現率)を優先し1.1を採用(muzyx縦積みは0.735で不変)


def complete_fifths(events: list[PitchEvent], y: np.ndarray, sr: int) -> list[PitchEvent]:
    """5度(+7)構成音を非重複倍音の直接測定で補完する(検出器の縦積み実績に依存しない)。

    パワーコードの5度は偶数次倍音が全てルートと共有され検出器に落とされやすいが、
    奇数次(基音1.5f0=+7・第3倍音4.5f0=+26)はルートのどの倍音とも一致しない。
    この2帯の同時成立+隣接ビン対照で「ルートの響き」と「実在する2本目の弦」を
    分離する(Klapuri 2003のスペクトル平滑性原理の局所適用)。
    """
    if not events or y is None or len(y) == 0:
        return list(events)
    import librosa

    C = np.abs(librosa.cqt(np.asarray(y, dtype=np.float32), sr=sr,
                           fmin=librosa.midi_to_hz(_CQT_FMIN_MIDI),
                           n_bins=_CQT_BINS, bins_per_octave=12))
    times = librosa.times_like(C, sr=sr)

    def e(midi: int, t0: float, t1: float) -> float:
        b = midi - _CQT_FMIN_MIDI
        if not 0 <= b < C.shape[0]:
            return 0.0
        i0, i1 = np.searchsorted(times, t0), np.searchsorted(times, t1)
        return float(np.median(C[b, i0:i1])) if i1 > i0 else 0.0

    def ov(a: PitchEvent, t0: float, t1: float) -> float:
        return min(a.offset, t1) - max(a.onset, t0)

    out = list(events)
    for r in events:
        if any(x.midi == r.midi + 7 and ov(x, r.onset, r.offset) > 0.03 for x in out):
            continue
        e_root = e(r.midi, r.onset, r.offset)
        if e_root <= 0:
            continue
        e_f = e(r.midi + 7, r.onset, r.offset)
        e_p3 = e(r.midi + 26, r.onset, r.offset)
        ctrl = max(e(r.midi + 6, r.onset, r.offset), e(r.midi + 8, r.onset, r.offset))
        _log = os.environ.get("EARPIPE_FIFTH_LOG")
        if _log:  # 較正用計測(ゲート判定前の生値を全候補で記録)
            import json as _json
            with open(_log, "a") as f:
                f.write(_json.dumps({"midi": r.midi, "onset": round(r.onset, 3),
                                     "rf": round(e_f / e_root, 4), "r3": round(e_p3 / e_root, 4),
                                     "rc": round(e_f / max(ctrl, 1e-9), 4)}) + "\n")
        if (e_f >= FIFTH_F0_RATIO * e_root
                and e_p3 >= FIFTH_P3_RATIO * e_root
                and e_f > FIFTH_CTRL_MARGIN * ctrl):
            out.append(PitchEvent(onset=r.onset, offset=r.offset, midi=r.midi + 7,
                                  confidence=round(r.confidence * 0.5, 4)))

    # 下方ルート補完: 検出音Xの-7半音(=Xを5度とするルート)を同じ非重複倍音論理で裁定
    for r in events:
        if any(x.midi == r.midi - 7 and ov(x, r.onset, r.offset) > 0.03 for x in out):
            continue
        e_x = e(r.midi, r.onset, r.offset)
        if e_x <= 0:
            continue
        e_rf = e(r.midi - 7, r.onset, r.offset)
        e_h2 = e(r.midi + 5, r.onset, r.offset)
        ctrl = max(e(r.midi - 6, r.onset, r.offset), e(r.midi - 8, r.onset, r.offset))
        _log = os.environ.get("EARPIPE_FIFTH_LOG")
        if _log:
            import json as _json
            with open(_log, "a") as f:
                f.write(_json.dumps({"dir": "down", "midi": r.midi, "onset": round(r.onset, 3),
                                     "rf": round(e_rf / e_x, 4), "r3": round(e_h2 / e_x, 4),
                                     "rc": round(e_rf / max(ctrl, 1e-9), 4)}) + "\n")
        if (e_rf >= ROOT_F0_RATIO * e_x
                and e_h2 >= ROOT_H2_RATIO * e_x
                and e_rf > ROOT_CTRL_MARGIN * ctrl):
            out.append(PitchEvent(onset=r.onset, offset=r.offset, midi=r.midi - 7,
                                  confidence=round(r.confidence * 0.5, 4)))
    return sorted(out, key=lambda x: (x.onset, x.midi))


# 一打まるごと欠落の復元(#144): 検出器が完全に落としたストロークを、
# 音声のオンセット(演奏の物理事実)+曲内和音語彙(その曲で実在した打の型)で復元する。
# 単発の音符プローブでは届かない"whole-event miss"(夢見る実測5件)への対処
STROKE_ONSET_TOL = 0.10   # 検出イベントとみなすオンセット近傍(秒)
STROKE_BETA = 0.6         # 語彙メンバー実在判定: 典型エネルギーのこの比以上
# gt-octave実測の幽霊対策: 伴奏ベースのbleed単音が第2倍音でオクターブペア語彙の
# 上声を偽装する(βゲートも立ち上がりゲートも通ってしまう=本物の打だから)。
# ペア語彙{m, m+12}の上声は偶奇倍音比の絶対ゲートで「重ねが実在する打」だけを通す。
# 0.8では伴奏ベースbleedの偶数優勢音色が2件通過(gt-octave実測) → 過去実測の
# 「重ねなし単音帯の上限1.04」(0.38〜1.04 vs 重ねあり0.98〜4.8)を超える1.05に設定
STROKE_PAIR_MIN_EVEN = 1.05
# 既知トレードオフ(2026-07-26採用時): gt-octaveで参照休符位置に語彙一打を1回誤補完
# (13.13s {55,67}: 伴奏bleedの強オンセット+本物同様の倍音構成でゲート分離不能)。
# 3ベンチ総合: 夢見るF1+0.014/縦積み+7.4pt, muzyx+0.001/+2.0pt, octave-0.007/縦積み±0
# → 要件ゲート(縦積み)優先で採用。GuitarSet(#147)拡充後に再較正する
STROKE_MIN_TEMPLATE = 2   # 語彙採用に必要な同一ピッチ集合の出現回数
STROKE_MEMBER_PASS = 1.0  # 語彙セットの全メンバーが実在判定を通ること(1.0=全員)


def complete_missed_strokes(events: list[PitchEvent], y: np.ndarray, sr: int) -> list[PitchEvent]:
    """検出器がまるごと落とした一打を、実測オンセット+曲内語彙で復元する。

    1. 検出イベントの無い音声オンセット(孤児オンセット)を列挙
    2. 曲内で2回以上出現した2声以上のピッチ集合を語彙とする
    3. 孤児オンセットで語彙セットの全メンバーのf0帯に典型比0.6以上の
       エネルギーが実在すれば、そのセットの一打として補完
    """
    if not events or y is None or len(y) == 0:
        return list(events)
    import librosa
    from collections import Counter

    C = np.abs(librosa.cqt(np.asarray(y, dtype=np.float32), sr=sr,
                           fmin=librosa.midi_to_hz(_CQT_FMIN_MIDI),
                           n_bins=_CQT_BINS, bins_per_octave=12))
    times = librosa.times_like(C, sr=sr)

    def e(midi: int, t0: float, t1: float) -> float:
        b = midi - _CQT_FMIN_MIDI
        if not 0 <= b < C.shape[0]:
            return 0.0
        i0, i1 = np.searchsorted(times, t0), np.searchsorted(times, t1)
        return float(np.median(C[b, i0:i1])) if i1 > i0 else 0.0

    # 1. 孤児オンセット
    onsets = librosa.onset.onset_detect(y=np.asarray(y, dtype=np.float32), sr=sr,
                                        units="time", backtrack=False)
    ev_onsets = np.array(sorted(x.onset for x in events))
    orphans = [float(t) for t in onsets
               if not (np.abs(ev_onsets - t) < STROKE_ONSET_TOL).any()]
    if not orphans:
        return sorted(events, key=lambda x: (x.onset, x.midi))

    # 2. 曲内語彙(2声以上×2回以上)と各ピッチの典型エネルギー・典型長
    clusters: list[list] = []
    for x in sorted(events, key=lambda x: (x.onset, x.midi)):
        if clusters and x.onset - clusters[-1][0] < 0.08:
            clusters[-1][1].append(x)
        else:
            clusters.append([x.onset, [x]])
    sets = Counter(frozenset(x.midi for x in c[1]) for c in clusters if len(c[1]) >= 2)
    vocab = [set(fs) for fs, n in sets.items() if n >= STROKE_MIN_TEMPLATE]
    if not vocab:
        return sorted(events, key=lambda x: (x.onset, x.midi))
    typ: dict[int, list[float]] = {}
    durs: list[float] = []
    for t0, mem in clusters:
        for x in mem:
            typ.setdefault(x.midi, []).append(e(x.midi, t0, t0 + 0.3))
            durs.append(x.offset - x.onset)
    typm = {k: float(np.median(v)) for k, v in typ.items()}
    dur = float(np.clip(np.median(durs), 0.1, 0.6)) if durs else 0.3

    # 3. 孤児オンセットごとに語彙を照合(全メンバー実在のセットのみ・最大集合を採用)
    out = list(events)
    for t in orphans:
        passing = []
        for V in vocab:
            def member_ok(m: int) -> bool:
                if typm.get(m, 0.0) <= 0 or e(m, t, t + 0.3) < STROKE_BETA * typm[m]:
                    return False
                if m - 12 in V:  # オクターブペアの上声: 偶奇比の絶対ゲートで裁定
                    ratio = _even_odd_ratio(C, times, m - 12, t, t + 0.3)
                    if ratio < STROKE_PAIR_MIN_EVEN:
                        return False
                return True

            ok = [m for m in V if member_ok(m)]
            if len(ok) >= STROKE_MEMBER_PASS * len(V):
                passing.append(V)
        if not passing:
            continue
        best = max(passing, key=len)
        for m in best:
            out.append(PitchEvent(onset=t, offset=t + dur, midi=m, confidence=0.35))
    return sorted(out, key=lambda x: (x.onset, x.midi))


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


def arbitrate_octaves(events: list[PitchEvent], y: np.ndarray, sr: int,
                      context_events: list[PitchEvent] | None = None) -> list[PitchEvent]:
    """パワーコード文脈(+7同時)のルートについて+12構成音を証拠ベースで裁定する。

    context_events: 文脈判定(どのルートがパワーコードか)に使う集合。既定は events。
    complete_fifths の補完5度で新規文脈を作らないよう、パイプラインは検出器
    ネイティブの集合を渡す(補完5度が文脈になると2声曲で+12幽霊が量産される)。
    """
    if not events or y is None or len(y) == 0:
        return sorted(events, key=lambda e: (e.onset, e.midi))
    import librosa

    def ov(a: PitchEvent, b: PitchEvent) -> float:
        return min(a.offset, b.offset) - max(a.onset, b.onset)

    # パワーコード文脈のルートヒットを収集(文脈はネイティブ検出に限定可)
    ctx_src = context_events if context_events is not None else events
    contexts: list[PitchEvent] = [
        r for r in ctx_src
        if any(f.midi - r.midi == 7 and ov(r, f) > FIFTH_OV_SEC for f in ctx_src)
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
        if _energy(e.midi, e.onset, e.offset) < SUB_OCTAVE_RATIO * _energy(e.midi + 12, e.onset, e.offset):
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
        if below >= DOWN_COMPLETE_RATIO * here and below > 0:
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
        can_complete = np.mean(high) >= CLUSTER_COMPLETE_MIN_EVEN  # 補完のみ絶対ゲート
        for h, ratio in zip(hits, ratios):
            oct_events = [e for e in events if e.midi == root_midi + 12 and ov(h, e) > 0.03]
            if ratio > thr and not oct_events and can_complete:
                # 重ねあり判定なのに+12が無い → 補完(検出器の見落とし回復)
                out.append(PitchEvent(
                    onset=h.onset, offset=h.offset, midi=root_midi + 12,
                    confidence=round(h.confidence * 0.6, 4),
                ))
            elif ratio <= thr:
                for e in oct_events:
                    removed.add(id(e))  # 重ねなし判定の+12検出 → 幽霊として除去
    # 兄弟音トリガーの和音メンバー補完(#144 2026-07-26): 同一テンプレ(頻出ピッチ集合)の
    # 打で欠けたメンバーを、そのピッチの「検出済みヒットの典型CQTエネルギー」との比で
    # 裁定して補完する。実測: 欠落メンバーの大半は兄弟音の時刻に典型比≈1.0で実在
    # (検出器が落としているだけ)。比が低い打(2声版など)には足さない。
    cur = sorted([e for e in out if id(e) not in removed], key=lambda e: (e.onset, e.midi))
    from collections import Counter

    clusters: list[list] = []
    for e in cur:
        if clusters and e.onset - clusters[-1][0] < 0.08:
            clusters[-1][1].append(e)
        else:
            clusters.append([e.onset, [e]])
    sets = Counter(frozenset(x.midi for x in c[1]) for c in clusters if len(c[1]) >= 2)
    vocab = [set(fs) for fs, n in sets.items() if n >= SIBLING_MIN_TEMPLATE]
    typ: dict[int, list[float]] = {}
    for t0, mem in clusters:
        for x in mem:
            typ.setdefault(x.midi, []).append(_energy(x.midi, t0, t0 + 0.3))
    typm = {k: float(np.median(v)) for k, v in typ.items()}
    for t0, mem in clusters:
        mset = {x.midi for x in mem}
        t1 = min(max(x.offset for x in mem), t0 + 0.35)
        cands = [V for V in vocab if mset & V and mset <= V and len(V - mset) <= 2]
        if not cands:
            continue
        V = min(cands, key=lambda v: len(v - mset))
        for miss in V - mset:
            e_typ = typm.get(miss, 0.0)
            if e_typ > 0 and _energy(miss, t0, t0 + 0.3) >= SIBLING_BETA * e_typ:
                cur.append(PitchEvent(onset=t0, offset=t1, midi=miss, confidence=0.4))
    return sorted(cur, key=lambda e: (e.onset, e.midi))
