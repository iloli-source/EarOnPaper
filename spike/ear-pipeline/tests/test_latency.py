"""処理時間計測ユーティリティ(NF-004)のテスト。

計測対象は callable なので、決定的な fake で percentiles/measure_latency の
契約(反復回数・統計キー・空入力の明示失敗)を固定する。実採譜の実測はベンチ
(bench/bench_latency.py)側で行い、ここでは計測ロジックの正しさを検証する。
"""

import pytest

from earpipe.services.quality.latency import measure_latency, percentiles


def test_percentiles_basic():
    # Arrange: 1..100
    samples = [float(i) for i in range(1, 101)]
    # Act
    pct = percentiles(samples, [50, 95])
    # Assert: 線形補間の代表値(numpy 既定)
    assert 49.0 <= pct[50] <= 52.0
    assert 94.0 <= pct[95] <= 96.0


def test_percentiles_empty_raises():
    # Arrange / Act / Assert: 空は数値を捏造せず ValueError
    with pytest.raises(ValueError):
        percentiles([], [50])


def test_measure_latency_runs_and_keys():
    # Arrange: 呼び出し回数を数える fake
    calls = {"n": 0}

    def _fn():
        calls["n"] += 1

    # Act: warmup 2 + runs 5 → 合計7回、統計は runs 分
    stats = measure_latency(_fn, runs=5, warmup=2)

    # Assert
    assert calls["n"] == 7
    assert stats["runs"] == 5
    assert len(stats["samples"]) == 5
    for key in ("mean", "p50", "p95", "p99", "min", "max"):
        assert key in stats and stats[key] >= 0.0


def test_measure_latency_rejects_zero_runs():
    with pytest.raises(ValueError):
        measure_latency(lambda: None, runs=0)
