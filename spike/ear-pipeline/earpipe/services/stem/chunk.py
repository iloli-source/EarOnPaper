"""stemサービス: 長尺音源を無音優先で分割する(F-004・Issue #68)。

長い録音を後段(採譜エンジン)がメモリに収まる粒度で処理できるよう、
max_sec を超えない範囲でチャンクに切り分ける。切断は「音の途中で切らない」
ことを最優先し、無音(librosa.effects.split の非無音区間の隙間)の中点で切る。
無音が見つからない/次の無音まで遠すぎる場合のみ固定窓で強制分割する
(fallback)。

責務の境界(重要):
    本関数はあくまで「無音位置での分割」に責務を限定する。ASR実務では
    境界単語の欠落を防ぐため 2-3 秒の overlap を付け重複領域の確率を平均するが、
    離散ノートイベント(AMT)では重複領域のノートが両チャンクで二重計上され
    単純平均もできない。よって overlap は既定で付けない。境界を跨ぐノートの
    扱い(overlap やマージ)が必要なら、その判断は上位(pipeline配線側)に委ねる。

既知の限界:
    - top_db は相対閾値のため、ノイズ床が高い実録では無音が一切検出されず
      固定窓 fallback に落ちる(音の途中で切れる可能性がある)。
    - 固定窓 fallback は窓端の最小エネルギー点へのスナップを行わない(YAGNI)。
    - samples は y のビュー(コピー無し)。frozen でも ndarray 中身は可変なので、
      呼び出し側で破壊的変更をしないこと。
"""

from dataclasses import dataclass
import math

import librosa
import numpy as np

# 無音検出のdB閾値(preprocess.py の先頭トリムと同じ流儀に合わせる)
_SPLIT_TOP_DB = 40


@dataclass(frozen=True, eq=False)
class Chunk:
    """分割された音源チャンク(F-004)。

    eq=False の理由(レビュー#40 L1 に倣う): samples に ndarray を含むため
    eq=True だと == 比較で「真理値が曖昧」の ValueError になる。同一性は
    index もしくは秒キーで判定すること。

    - index: 0 始まりの連番
    - start_sec / end_sec: 元波形先頭からの秒(= サンプルindex / sr で導出)
    - samples: y[start:end] のビュー(コピーしない)
    """

    index: int
    start_sec: float
    end_sec: float
    samples: np.ndarray


def _silence_boundaries(y: np.ndarray, sr: int, min_silence_sec: float) -> list[int]:
    """分割候補となる無音の中点(サンプルindex)を昇順で返す。

    librosa.effects.split は「非無音区間」の [start, end] を返す。無音はその
    隙間(gap)に存在する。隣接する非無音区間 (a, b) の gap = (a[1], b[0]) が
    min_silence_sec*sr 以上のときだけ分割候補とし、境界は gap の中点を採る
    (音の途中・アタック/減衰を削らないため)。

    純無音入力でも split は空でなく全域1区間 [[0, N]] を返す(検証済)ため、
    その場合 gap は生じず候補は空になる(安全に固定窓 fallback へ落ちる)。
    """
    intervals = librosa.effects.split(y, top_db=_SPLIT_TOP_DB)
    if len(intervals) < 2:
        return []
    min_gap = int(min_silence_sec * sr)
    boundaries: list[int] = []
    for prev, cur in zip(intervals[:-1], intervals[1:]):
        gap_start = int(prev[1])
        gap_end = int(cur[0])
        if gap_end - gap_start >= min_gap:
            boundaries.append((gap_start + gap_end) // 2)
    return boundaries


def split_into_chunks(
    y: np.ndarray,
    sr: int,
    max_sec: float = 600.0,
    min_silence_sec: float = 0.3,
) -> list[Chunk]:
    """波形を max_sec を超えないチャンクへ無音優先で分割する。

    アルゴリズム:
        (1) 空入力は空listを返す。総尺 <= max_sec なら1チャンクで返す
            (単一短尺 = 1チャンク)。
        (2) 無音境界(非無音区間の隙間の中点)を候補として抽出する。
        (3) 現在の開始位置から max_sec を超えない範囲で「開始からの距離が
            max_sec 以下の最後の候補境界」を選び分割する。候補が無い/次境界まで
            max_sec を超える場合は固定窓 int(max_sec*sr) で強制分割する(fallback)。
        (4) 末尾まで反復し index を 0 から連番付与する。

    境界は常にサンプルindexを唯一の真実とし、秒は idx/sr で導出する
    (往復変換による1サンプルずれを防ぐ)。各チャンクは start < end を満たす。

    Args:
        y: モノラル波形(1次元float配列を想定)。
        sr: サンプルレート(Hz)。
        max_sec: 1チャンクの最大秒数。これを超えて長いチャンクは作らない。
        min_silence_sec: この長さ未満の無音は分割候補としない(短無音無視)。

    Returns:
        Chunk のリスト(index昇順・区間は隙間なく連続)。空入力では空list。
    """
    if not isinstance(sr, (int, np.integer)) or not 1 <= int(sr) <= 384000:
        raise ValueError("sr は1〜384000Hzの整数で指定してください")
    if not math.isfinite(float(max_sec)) or not 0.001 <= float(max_sec) <= 86400:
        raise ValueError("max_sec は0.001〜86400秒の有限値で指定してください")
    if not math.isfinite(float(min_silence_sec)) or not 0 <= float(min_silence_sec) <= 86400:
        raise ValueError("min_silence_sec は0〜86400秒の有限値で指定してください")
    y = np.asarray(y)
    if y.ndim != 1:
        raise ValueError("y は1次元のモノラル波形で指定してください")
    if not np.issubdtype(y.dtype, np.number):
        raise ValueError("y は数値配列で指定してください")
    if not np.isfinite(y).all():
        raise ValueError("y にNaNまたは無限値を含めないでください")
    n = int(y.shape[0])
    if n == 0:
        return []

    max_len = max(1, int(max_sec * sr))
    if n <= max_len:
        return [Chunk(index=0, start_sec=0.0, end_sec=n / sr, samples=y[0:n])]

    boundaries = _silence_boundaries(y, sr, min_silence_sec)

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < n:
        limit = start + max_len
        if limit >= n:
            end = n
        else:
            # start より後・limit 以下にある最後の無音境界を選ぶ
            candidate = None
            for b in boundaries:
                if b <= start:
                    continue
                if b > limit:
                    break
                candidate = b
            end = candidate if candidate is not None else limit

        # 退化ケース防御: start < end を必ず保証する
        if end <= start:
            end = min(start + max_len, n)
        chunks.append(
            Chunk(
                index=idx,
                start_sec=start / sr,
                end_sec=end / sr,
                samples=y[start:end],
            )
        )
        start = end
        idx += 1

    return chunks
