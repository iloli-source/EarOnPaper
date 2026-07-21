"""F-101 鍵盤運指推定(指番号自動付与・右手/左手割当)(Issue #92)。

量子化済み音符列(QuantizedNote)に対し、各音へ指番号(1-5)を付与し、
どちらの手(right/left)で弾くかを割り当てる。指番号は「隣接音の音程 →
指遷移コスト」の動的計画法(Viterbi 型の最小コスト経路探索)で決める。
左右手割当は音高の中央値で分割する簡易版である。

設計方針(先行研究 F-101-grok / F-101-codex の失敗例を反映):

- 動的計画法(DP): Parncutt らのエルゴノミックコストモデル(指間スパン・弱指・
  親指くぐり・逆行運指のペナルティ)を単純化した遷移コストを定義し、隣接する
  2音に対する (前指, 次指) のコストを最小化する経路を DP で解く。ノート単位の
  独立分類は系列一貫性を壊す(codex(2)「単純NNがHMMに負ける」)ため採らない。

- 物理的到達不能の除外(grok 失敗類型E / pianoplayer): 音程が片手で届く上限
  (MAX_HAND_SPAN_SEMITONES)を超える遷移は「同一手内で連続して押さえられない」
  として巨大コストを課す。解剖学的に不可能な運指を第一候補にしない。

- 逆行運指の抑制(grok 失敗類型E, codex Guan IFR): 音高が上がるのに指番号が
  下がる/その逆、といった手を動かさないと弾けない運指にペナルティを課す。
  ただし親指くぐり・小指またぎは実在するため禁止ではなくコストで表現する。

- 左右手割当は「簡易版」と明記(grok 失敗類型C / codex(3)「ピッチ閾値分割は
  危険」): 音高中央値で二分するだけで、手交差・内声・伴奏跳躍は正しく割れない。
  これは意図的な割り切りであり、本モジュールの原理的限界として docstring と
  戻り値の hand フィールドに正直に残す(交差手・声部分離は将来 joint inference)。

- 複数正解が本質(grok 失敗類型H / codex(2)「人間同士でも 71.4」): 出力は
  唯一の正解ではなく「編集可能な提案」。同点経路が複数あり得るため、決定的な
  タイブレーク(小さい指番号優先)で安定化するが、他の運指も等しく妥当たり得る。

限界(正直な記録):
- 単一の QuantizedNote 列を前提とし、和音(同一 start_beats の同時音)の縦制約
  (同時に異なる指を割り当てる)は本 DP では厳密に扱わない。同時音は入力順に
  逐次処理され、遷移コストで近似的に散らすのみ(codex(2)「和音・polyphony」)。
- 手のサイズ・実テンポ・ペダル・フレージング・保持音は未考慮。MAX_HAND_SPAN は
  平均的な手の概算固定値で、ユーザー手スパン設定は本簡易版では受けない
  (grok ベストプラクティス「手スパンを入力」は将来拡張)。
- 採譜誤差(オクターブ誤り・ゴーストノート)は運指探索を歪めるが、本関数は
  入力音列を信頼する。誤譜検知は前段の責務(grok 失敗類型D)。
"""

from __future__ import annotations

import math
from typing import Final, Literal

from earpipe.contracts import QuantizedNote

# 指番号の値域(1=親指 .. 5=小指)。片手はこの5本のみ。
MIN_FINGER: Final[int] = 1
MAX_FINGER: Final[int] = 5
_FINGERS: Final[tuple[int, ...]] = (1, 2, 3, 4, 5)

# 片手が無理なく届く音程の概算上限(半音)。おおよそ1オクターブ(12)強を想定。
# これを超える隣接音は同一手内では連続で押さえられない扱いにする
# (grok 失敗類型E: 14鍵に届かない/pianoplayer の到達不能除外に対応)。
MAX_HAND_SPAN_SEMITONES: Final[int] = 14

# 同一手内で連続音が MAX_HAND_SPAN を超えるときに課す禁止的コスト。
# 有限の大きな値にして DP を破綻させない(inf は経路比較で全経路等価になり得る)。
_UNREACHABLE_COST: Final[float] = 1e6

# 遷移コストの重み(Parncutt 系ルールコストの単純化。単位は無次元の相対値)。
# 音高が動いたのに同じ指を使い回すペナルティ(手を大きく動かす必要が出る)。
_SAME_FINGER_MOVE_COST: Final[float] = 2.5
# 逆行運指(音高↑なのに指↓ / 音高↓なのに指↑)のペナルティ。親指くぐり等で
# 実在はするため禁止せずコスト化(codex: finger crossing を消し切れない問題)。
_CONTRARY_MOTION_COST: Final[float] = 1.5
# 弱指(4,5)を跳躍で使うことへの軽いペナルティ(Parncutt の weak-finger rule)。
_WEAK_FINGER_LEAP_COST: Final[float] = 0.6
# 指の隣接性と音程の乖離ペナルティ係数。理想は「音程の半音数に見合う指移動」。
_SPAN_MISMATCH_COST: Final[float] = 0.35
# 大きな跳躍(1オクターブ近く)で親指(1)/小指(5)以外を端に置くことの軽い抑制。
_LEAP_PIVOT_COST: Final[float] = 0.4
# 跳躍とみなす音程しきい値(半音)。
_LEAP_THRESHOLD_SEMITONES: Final[int] = 7

Hand = Literal["right", "left"]


def _safe_midi(note: QuantizedNote) -> int:
    """QuantizedNote から int の MIDI ノート番号を安全に取り出す。

    midi は int 想定だが、float 混入や休符(midi<0)もあり得るため int 化する。
    休符判定は呼び出し側で行う(ここでは値をそのまま int で返すのみ)。
    """
    return int(note.midi)


def _initial_cost(finger: int, hand_note_count: int) -> float:
    """系列先頭音に対する指ごとの初期コスト。

    先頭は文脈が無いため、中指(3)を最安・親指/小指をやや高くする軽い事前分布。
    これは決定的タイブレークのための微小バイアスであり、音楽的必然ではない。
    """
    # 中央(3)からの距離に比例する微小コスト。単音列でも安定した既定運指にする。
    base = abs(finger - 3) * 0.05
    return base


def _transition_cost(
    prev_finger: int,
    prev_midi: int,
    cur_finger: int,
    cur_midi: int,
) -> float:
    """隣接2音(同一手内)の (前指→次指) 遷移コスト。

    Parncutt 系ルールを単純化: 到達不能の除外、逆行運指ペナルティ、弱指跳躍、
    音程と指移動量の乖離ペナルティを合算する。値が小さいほど自然な運指。

    引数はいずれも int(前後の指番号 1-5、前後の MIDI ノート番号)。
    """
    interval = cur_midi - prev_midi          # 符号付き音程(半音)
    abs_interval = abs(interval)

    # 到達不能: 同一手で連続して届かない音程は禁止的コスト。
    if abs_interval > MAX_HAND_SPAN_SEMITONES:
        return _UNREACHABLE_COST

    cost = 0.0
    finger_delta = cur_finger - prev_finger  # 符号付き指移動

    # 同一指で音高が動く: 手全体を移動する必要があり負担。同音反復のみ許容。
    if cur_finger == prev_finger and abs_interval > 0:
        cost += _SAME_FINGER_MOVE_COST

    # 逆行運指: 音高の向きと指番号の向きが逆(親指くぐり等で実在するため軽め)。
    # interval>0(上行)なら指は増える方が自然、interval<0(下行)なら減る方が自然。
    if interval > 0 and finger_delta < 0:
        cost += _CONTRARY_MOTION_COST
    elif interval < 0 and finger_delta > 0:
        cost += _CONTRARY_MOTION_COST

    # 弱指(4,5)で跳躍: 跳躍を弱指で担うと不安定(Parncutt weak-finger)。
    if abs_interval >= _LEAP_THRESHOLD_SEMITONES and cur_finger in (4, 5):
        cost += _WEAK_FINGER_LEAP_COST

    # 音程と指移動量の乖離: 理想は音程(半音)に見合う指の開き。
    # 1半音あたりおよそ指1本分を目安に、乖離の絶対値へ比例ペナルティ。
    ideal_finger_span = abs_interval / 2.0
    cost += abs(abs(finger_delta) - ideal_finger_span) * _SPAN_MISMATCH_COST

    # 大跳躍で端の指(親指/小指)以外を軸にすると次の展開が窮屈になりやすい。
    if abs_interval >= _LEAP_THRESHOLD_SEMITONES and cur_finger not in (MIN_FINGER, MAX_FINGER):
        cost += _LEAP_PIVOT_COST

    return cost


def _optimal_fingers_for_hand(midis: list[int]) -> list[int]:
    """片手に割り当てられた MIDI 列に対し、DP で最小コストの指番号列を返す。

    Viterbi 型 DP: dp[i][f] = i 番目の音を指 f で弾くときの先頭からの最小累積
    コスト。遷移は _transition_cost で評価し、逆ポインタで最良経路を復元する。
    同点は小さい指番号を優先する決定的タイブレーク(複数正解の安定化)。

    空入力には空 list を返す。単音には初期コスト最小の指を返す。
    """
    n = len(midis)
    if n == 0:
        return []

    # dp[f] = 現在音までの、指 f で終える最小累積コスト(f は 0..4 で指1..5)。
    dp: list[float] = [_initial_cost(f, n) for f in _FINGERS]
    # back[i][f] = i 番目の音を指 f で弾くときの、直前音の最良指インデックス。
    back: list[list[int]] = [[-1] * len(_FINGERS) for _ in range(n)]

    for i in range(1, n):
        prev_dp = dp
        cur_dp: list[float] = [math.inf] * len(_FINGERS)
        for cf_idx, cur_finger in enumerate(_FINGERS):
            best_cost = math.inf
            best_prev = 0
            for pf_idx, prev_finger in enumerate(_FINGERS):
                trans = _transition_cost(
                    prev_finger, midis[i - 1], cur_finger, midis[i]
                )
                total = prev_dp[pf_idx] + trans
                # < で比較し、同点は先に走査した小さい指番号を残す(決定的)。
                if total < best_cost:
                    best_cost = total
                    best_prev = pf_idx
            cur_dp[cf_idx] = best_cost
            back[i][cf_idx] = best_prev
        dp = cur_dp

    # 終端で最小コストの指を選ぶ(同点は小さい指番号)。
    end_idx = min(range(len(_FINGERS)), key=lambda f_idx: dp[f_idx])

    # 逆ポインタで経路復元。
    fingers_idx: list[int] = [0] * n
    fingers_idx[n - 1] = end_idx
    for i in range(n - 1, 0, -1):
        fingers_idx[i - 1] = back[i][fingers_idx[i]]

    return [_FINGERS[idx] for idx in fingers_idx]


def _split_hands_by_median(playable: list[tuple[int, int]]) -> dict[int, Hand]:
    """(元index, midi) の並びを音高中央値で右手/左手に二分する簡易割当。

    中央値以上を right、未満を left とする。中央値ちょうどの同点は right に寄せる
    (境界の恣意性。手交差・内声はここでは正しく割れない= 簡易版の限界)。

    戻り値は 元index -> Hand の写像。空入力には空 dict。
    """
    if not playable:
        return {}
    sorted_midis = sorted(m for _, m in playable)
    n = len(sorted_midis)
    # 中央値(偶数個は下側中央=低い方を採り、境界を right 寄りにする)。
    median = sorted_midis[(n - 1) // 2]
    return {idx: ("right" if midi >= median else "left") for idx, midi in playable}


def assign_fingering(
    notes: list[QuantizedNote],
    hand: str = "right",
) -> list[dict]:
    """音符列に指番号(1-5)と手(right/left)を割り当てる(F-101)。

    処理の流れ:
      1. 休符(midi<0)や非有限は運指対象外として除外し、実音のみ抽出する。
      2. hand の指定に応じて手を決める:
         - "right"/"left": 全実音を単一手に固定して DP 運指(手割当は固定)。
         - "auto": 音高中央値で右手/左手へ二分し(簡易版・限界あり)、各手ごとに
           独立に DP で運指を最適化する。
      3. 各手内で「隣接音の音程 → 指遷移コスト」を最小化する DP で指番号を決める。

    Args:
        notes: 量子化済み音符列(QuantizedNote)。空リストなら空リストを返す。
            入力の list 順を旋律順として信頼する(onset_sec は NaN 既定でソート
            根拠に使えない。contracts.py 参照)。
        hand: "right"(既定)/"left"/"auto" のいずれか。"auto" は音高中央値で
            左右へ二分する簡易版(手交差・内声・伴奏跳躍は正しく割れない)。

    Returns:
        各対象音に対応する dict の list。要素は:
          - "note_index": 入力 notes 内での元インデックス(int)。
          - "finger": 指番号 1-5(int)。
          - "hand": "right" または "left"(str)。
        休符・非有限音は結果に含めない(拾えないものは正直に落とす)。
        結果は note_index の昇順に整列して返す。

    Raises:
        ValueError: hand が "right"/"left"/"auto" 以外のとき(静かに失敗しない)。

    Notes:
        複数正解が本質(人間同士でも一致率 ~71%)であり、本出力は唯一の正解では
        なく「編集可能な提案」である。左右手割当("auto")は音高中央値の簡易版で
        あり、手交差や声部分離は原理的に扱えない(モジュール docstring 参照)。
    """
    if hand not in ("right", "left", "auto"):
        raise ValueError(
            f"hand は 'right'/'left'/'auto' のいずれか。受領値: {hand!r}"
        )

    if not notes:
        return []

    # 1. 実音(midi>=0 かつ有限)のみ抽出。元インデックスを保持する。
    playable: list[tuple[int, int]] = []  # (元index, midi)
    for idx, note in enumerate(notes):
        midi = _safe_midi(note)
        # float("nan") 由来など非有限は int 化で例外になり得るが、contracts 上
        # midi は int。負(休符)は運指対象外として落とす。
        if midi < 0:
            continue
        playable.append((idx, midi))

    if not playable:
        return []

    # 2. 手割当を決める。
    if hand in ("right", "left"):
        hand_map: dict[int, Hand] = {idx: hand for idx, _ in playable}  # type: ignore[misc]
    else:  # auto
        hand_map = _split_hands_by_median(playable)

    # 3. 手ごとに実音を集め、DP で運指を最適化する。
    results: list[dict] = []
    for target_hand in ("left", "right"):
        # この手に属する音を旋律順(元index昇順)で集める。
        group = [(idx, midi) for idx, midi in playable if hand_map[idx] == target_hand]
        if not group:
            continue
        midis = [midi for _, midi in group]
        fingers = _optimal_fingers_for_hand(midis)
        for (idx, _midi), finger in zip(group, fingers):
            results.append(
                {"note_index": idx, "finger": finger, "hand": target_hand}
            )

    # note_index 昇順に整列(入力順に対応させ、呼び出し側で扱いやすくする)。
    results.sort(key=lambda d: d["note_index"])
    return results
