"""変換層: 拍子推定(小節長の推定・Issue #57/#59の帰結)。

4/4固定の記譜では正解が3拍子系の曲で小節数が構造的にずれる(C5-2不合格)ため、
量子化済み音符列のアクセント周期から小節長L(4分音符ベース、2/3/4/5拍)を推定する。

信号: 整数拍ごとのオンセット強度(同時発音数 + 低音の重み + 音価の重み)。
小節長Lと位相pの全候補について「downbeat拍の平均強度がその他の拍をどれだけ
上回るか」を標準偏差で正規化して採点し、オッカム事前分布(4拍を最優先)を掛けて選ぶ。
確証が弱い(prominence < 閾値)場合は4/4に退避する — 合成テストの安定性と
「わからないときは最多数派」の正直な既定。

正直な限界:
- 複合拍子(6/8)は3/4と小節長が同じ(4分3つぶん)ため区別しない(小節数は一致する)。
- 8分音符基準の拍子(3/8等)はテンポ推定の拍単位に依存する。
- 判定パラメータはPD15曲ベンチ(bench_score_checks.py)で調律した値であり、
  コーパス外での汎化は未検証。
"""

import numpy as np

from earpipe.contracts import QuantizedNote

BAR_CANDIDATES = (4, 3, 2, 5)  # 優先順(同点時は先勝ち)
OCCAM_PRIOR = {4: 1.00, 3: 0.97, 2: 0.90, 5: 0.85}
MIN_PROMINENCE = 0.12   # これ未満は「確証なし」として4/4へ退避
# 小節長推定に必要な最小の拍スパン。短い断片(数小節)ではアクセント統計が
# 不安定で誤選択しうる(e2e合成4小節で3/4誤選択を実測)ため、証拠不足は4/4既定
MIN_BEATS = 24
BASS_MIDI = 55          # これ未満の音は低音(小節頭に置かれやすい)として加点
BASS_BONUS = 1.0
DUR_WEIGHT_CAP = 2.0    # 音価の重み上限(全音符が支配しないように)


def _beat_strengths(notes: list[QuantizedNote]) -> np.ndarray:
    """整数拍ごとのオンセット強度列。"""
    end = max(int(n.start_beats) for n in notes) + 1
    s = np.zeros(end)
    for n in notes:
        b = int(n.start_beats)
        # 拍頭(±1/8拍)に立つオンセットのみアクセント候補として数える
        if abs(n.start_beats - round(n.start_beats)) > 0.125:
            continue
        b = int(round(n.start_beats))
        if b >= end:
            continue
        w = 1.0 + min(float(n.dur_beats), DUR_WEIGHT_CAP) * 0.5
        if n.midi < BASS_MIDI:
            w += BASS_BONUS
        s[b] += w
    return s


def estimate_meter(notes: list[QuantizedNote]) -> int:
    """音符列から小節長(4分音符ベースの拍数)を推定する。既定退避は4。"""
    if not notes:
        return 4
    s = _beat_strengths(notes)
    if len(s) < MIN_BEATS:
        return 4
    std = float(np.std(s))
    if std <= 1e-9:
        return 4  # 全拍が同強度(一様列) → 判別不能を正直に4/4へ

    best_l, best_score = 4, -np.inf
    for length in BAR_CANDIDATES:
        if len(s) < 2 * length:
            continue
        prom = max(
            (float(np.mean(s[p::length])) - float(np.mean(s))) / std
            for p in range(length)
        )
        score = prom * OCCAM_PRIOR[length]
        if score > best_score + 1e-9:
            best_l, best_score = length, score

    if best_score < MIN_PROMINENCE:
        return 4
    return best_l
