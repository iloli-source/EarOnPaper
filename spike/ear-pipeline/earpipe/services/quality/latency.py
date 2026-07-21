"""採譜処理時間の計測(NF-004)。

処理時間 p50/p95 等を再現可能に計測するためのユーティリティ。pipeline を直接
import すると循環参照になるため、**計測対象は callable として受け取る**(依存の向きを
notate/quality → pipeline に逆流させない)。bench/bench_latency.py が transcribe を
束ねて本関数へ渡す。

percentiles は numpy の線形補間(既定)に委譲する。空入力は無理に推定せず ValueError。
"""

from __future__ import annotations

import time
from typing import Callable

import numpy as np


def percentiles(samples: list[float], ps: list[float]) -> dict[float, float]:
    """samples の各パーセンタイル ps(0-100)を返す。

    Raises:
        ValueError: samples が空(計測が無いのに数値を捏造しない)。
    """
    if not samples:
        raise ValueError("percentiles: samples が空です")
    arr = np.asarray(samples, dtype=float)
    return {p: float(np.percentile(arr, p)) for p in ps}


def measure_latency(
    fn: Callable[[], object], runs: int, warmup: int = 0
) -> dict:
    """fn を warmup 回だけ捨て計測した後、runs 回実行して秒単位の統計を返す。

    Args:
        fn: 計測対象(引数なし callable)。戻り値は無視する。
        runs: 本計測の反復回数(>=1)。
        warmup: 統計に含めない事前実行回数(JIT/キャッシュ暖機)。

    Returns:
        {"runs", "samples", "mean", "p50", "p95", "p99", "min", "max"}(秒)。

    Raises:
        ValueError: runs < 1。
    """
    if runs < 1:
        raise ValueError("measure_latency: runs は 1 以上")
    for _ in range(max(0, warmup)):
        fn()
    samples: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    pct = percentiles(samples, [50, 95, 99])
    return {
        "runs": runs,
        "samples": samples,
        "mean": float(np.mean(samples)),
        "p50": pct[50],
        "p95": pct[95],
        "p99": pct[99],
        "min": float(np.min(samples)),
        "max": float(np.max(samples)),
    }
