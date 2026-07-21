#!/usr/bin/env python3
"""採譜処理時間ベンチ(NF-004): 指定音源を N 回採譜し p50/p95 等を報告する。

使い方:
    .venv/bin/python bench/bench_latency.py 音源.wav --runs 20 --engine mono

計測対象は callable として latency.measure_latency に渡す(依存の逆流を避ける)。
出力先(MusicXML)は一時ファイルに捨て、I/O も含めた end-to-end 時間を測る。
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# bench/ から earpipe を解決
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from earpipe.pipeline import transcribe_file  # noqa: E402
from earpipe.services.quality.latency import measure_latency  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="採譜処理時間ベンチ(NF-004)")
    p.add_argument("input", help="入力音源")
    p.add_argument("--runs", type=int, default=20, help="計測反復回数(既定20)")
    p.add_argument("--warmup", type=int, default=1, help="暖機回数(既定1)")
    p.add_argument("--engine", choices=("auto", "mono", "poly"), default="mono")
    args = p.parse_args(argv)

    tmp = Path(tempfile.mkdtemp()) / "bench.musicxml"

    def _once() -> None:
        transcribe_file(args.input, out_musicxml=str(tmp), engine=args.engine)

    stats = measure_latency(_once, runs=args.runs, warmup=args.warmup)
    stats.pop("samples", None)  # 生サンプルは要約から除く
    stats["input"] = args.input
    stats["engine"] = args.engine
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
