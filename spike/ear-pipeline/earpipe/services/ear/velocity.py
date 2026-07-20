"""耳層(F-016): 各ノートの相対強弱(velocity)推定と強弱記号への離散化。

研究(docs/research/upcoming/F-016-*.md)の核心 pitfall を設計に反映する。

なぜ「相対値」しか返さないか(codex報告 §3 / grok報告 BP-3):
  MIDI velocity や録音の音量は「楽譜上の絶対的な強弱(pp..ff)」ではない。
  同じ演奏でも録音ゲイン・音源・楽器・マイク距離・部屋鳴り・正規化・
  コンプレッサで振幅は容易に変わる(codex §2)。Onsets and Frames 論文
  (arXiv:1710.11153)自身、評価時に推定 velocity をスケール・オフセット
  補正してから比較しており、研究側も「生の絶対 velocity」を信頼していない。
  よって本モジュールは絶対 dB/velocity を返さず、曲内の相対強弱(0-1)に
  正規化した値だけを返す。

絶対閾値マップを使わない(codex §3 / grok F4):
  `velocity>=96 => f` のような固定表は、弱い演奏だと全部 p、強い演奏だと
  全部 f になり破綻する。to_dynamic_marks は曲内の分位点(percentile)で
  相対的に段階記号へ写像する。したがって「この曲の中での相対的な強弱段階」
  であって、他曲・他録音と比較可能な絶対強弱ではない。

原理的限界(過大主張しない・notes に正直に記す):
  - 録音レベル依存で絶対値は不正確。返すのは曲内相対値のみ。
  - 低音は倍音/残響が強く、和音は同時発音数でエネルギーが増えるため、
    音域・和声で系統的なバイアスが残る(codex §2 音域依存/和音依存)。
  - オンセット位置がズレるとアタックのエネルギーを取り逃がす。
  - hairpin(crescendo/decrescendo)は本モジュールでは扱わない
    (勾配検出はノイズに弱く過検出しやすい。codex §4 / grok F5)。
"""

from __future__ import annotations

import numpy as np

from earpipe.contracts import PitchEvent

# オンセット近傍でエネルギーを測る窓(秒)。打鍵直後のアタックを捉えるため
# オンセットから前後に少しだけ広げる。研究に固定値の根拠はないため、
# 短めのアタック窓(打鍵の立ち上がり)を保守的に置く。
DEFAULT_ONSET_PRE_SEC = 0.01   # オンセット直前(立ち上がりの取りこぼし防止)
DEFAULT_ONSET_POST_SEC = 0.06  # オンセット直後(アタックのピーク帯)

# RMS が実質無音とみなせる下限(相対正規化のゼロ割・log 発散を防ぐ)。
_RMS_FLOOR = 1e-8

# 曲内の dB レンジがこの幅(dB)未満なら「意味のある相対差なし」とみなし、
# 順位を捏造せず一律 0.5 を返す。窓 RMS は位相・窓境界・測定誤差で 1dB 未満の
# 微差が常に出るため、これを相対強弱段階に増幅すると偽の順位が生まれる
# (研究: 生の絶対 velocity は測定ノイズを含む相対制御値。codex §2)。
_MIN_DYNAMIC_RANGE_DB = 1.0

# 強弱記号(弱→強)。to_dynamic_marks はこの順の等分位点で写像する。
DYNAMIC_MARKS: tuple[str, ...] = ("pp", "p", "mp", "mf", "f", "ff")


def _to_mono(y: np.ndarray) -> np.ndarray:
    """多チャンネル音声をモノラル(float64)に畳み込む。"""
    y = np.asarray(y, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    return y


def _onset_rms(
    y: np.ndarray,
    sr: int,
    onset: float,
    pre_sec: float,
    post_sec: float,
) -> float:
    """オンセット近傍窓の RMS(二乗平均平方根エネルギー)を返す。

    窓は [onset-pre_sec, onset+post_sec] を音声長にクリップした範囲。
    窓が音声外・空になる場合は無音として _RMS_FLOOR を返す。
    """
    n = len(y)
    start = int(round((onset - pre_sec) * sr))
    end = int(round((onset + post_sec) * sr))
    start = max(0, min(start, n))
    end = max(0, min(end, n))
    if end <= start:
        return _RMS_FLOOR
    segment = y[start:end]
    rms = float(np.sqrt(np.mean(np.square(segment))))
    return max(rms, _RMS_FLOOR)


def estimate_velocities(
    y: np.ndarray,
    sr: int,
    events: list[PitchEvent],
    pre_sec: float = DEFAULT_ONSET_PRE_SEC,
    post_sec: float = DEFAULT_ONSET_POST_SEC,
) -> list[float]:
    """各ノートのオンセット近傍エネルギーから曲内相対強弱(0-1)を推定する。

    アルゴリズム(相対正規化・絶対値を主張しない):
      1. 各イベントの onset 近傍窓の RMS を測る(アタックのエネルギー)。
      2. RMS を dB(log スケール)に変換する — 音量の知覚は概ね対数的で、
         線形振幅のまま正規化すると強音に極端に引っ張られるため。
      3. 曲内の dB 分布を [最小, 最大] で min-max 正規化し 0-1 にする
         (曲内相対値。録音ゲインが変わっても分布形は概ね保たれる)。
      4. 曲内 dB レンジが _MIN_DYNAMIC_RANGE_DB 未満(実質同一エネルギー)なら
         一律 0.5 を返す(測定ノイズ級の微差から偽の順位を作らない)。

    返り値: events と同じ長さ・同じ順序の 0-1 相対強弱リスト。

    入力検証(システム境界):
      - sr が非正なら ValueError。
      - pre_sec/post_sec が負・非有限なら ValueError。
      - events が空なら空リストを返す。
      - y が空で events が非空なら ValueError(測定不能を黙認しない)。

    限界(module docstring 参照): これは曲内の相対順位であって絶対強弱では
    ない。録音レベル・音源・音域・和声に依存するバイアスは除去できない。
    """
    if sr <= 0:
        raise ValueError(f"sr must be positive, got {sr}")
    if not (np.isfinite(pre_sec) and pre_sec >= 0.0):
        raise ValueError(f"pre_sec must be finite and >= 0, got {pre_sec}")
    if not (np.isfinite(post_sec) and post_sec >= 0.0):
        raise ValueError(f"post_sec must be finite and >= 0, got {post_sec}")

    if not events:
        return []

    y = _to_mono(y)
    if len(y) == 0:
        raise ValueError("audio signal y must be non-empty when events are given")

    rms_values = np.array(
        [_onset_rms(y, sr, ev.onset, pre_sec, post_sec) for ev in events],
        dtype=np.float64,
    )

    # 対数(dB)スケールへ。知覚に近づけ、強音への過剰な偏りを抑える。
    db_values = 20.0 * np.log10(rms_values)

    db_min = float(np.min(db_values))
    db_max = float(np.max(db_values))
    span = db_max - db_min

    # 相対差が測定ノイズ級(< _MIN_DYNAMIC_RANGE_DB)なら順位を捏造せず中庸を返す。
    if span < _MIN_DYNAMIC_RANGE_DB:
        return [0.5] * len(events)

    normalized = (db_values - db_min) / span
    return [float(v) for v in normalized]


def to_dynamic_marks(
    vels: list[float],
    marks: tuple[str, ...] = DYNAMIC_MARKS,
) -> list[str]:
    """曲内相対強弱(0-1)を強弱記号(pp..ff)へ分位点で離散化する。

    絶対閾値マップ(0.0-0.16=pp 等の固定分割)は使わない。研究(codex §3・
    grok F4)が示す通り固定表は録音・演奏強度で破綻するため、曲内の
    分位点(percentile)で相対的に段階へ写像する。すなわち返る記号は
    「この曲の中での相対段階」であって絶対強弱ではない。

    写像方式(等分位点):
      各記号 marks[i] に曲内の分位点区間を割り当てる。値 v は
      floor(v * len(marks)) 番目の段階へ落とす(v==1.0 は最上段へクリップ)。
      これにより「弱い演奏でも最弱〜最強の相対段階が付く」相対性を保つ。

    入力検証(システム境界):
      - vels が空なら空リストを返す。
      - marks が空なら ValueError。
      - vels の各要素が非有限、または [0,1] 範囲外なら ValueError
        (estimate_velocities の契約=0-1 を破る入力を黙認しない)。

    返り値: vels と同じ長さ・同じ順序の記号リスト。

    限界: 段階数(既定6)は読みやすさのための粗い量子化。微細な強弱変化は
    段階に丸められて失われる(過密記譜の回避。codex §5 notation過密)。
    """
    if not marks:
        raise ValueError("marks must be non-empty")
    if not vels:
        return []

    n_marks = len(marks)
    result: list[str] = []
    for v in vels:
        if not np.isfinite(v):
            raise ValueError(f"velocity must be finite, got {v}")
        if v < 0.0 or v > 1.0:
            raise ValueError(f"velocity must be in [0,1], got {v}")
        idx = int(v * n_marks)
        if idx >= n_marks:  # v == 1.0 のクリップ
            idx = n_marks - 1
        result.append(marks[idx])
    return result
