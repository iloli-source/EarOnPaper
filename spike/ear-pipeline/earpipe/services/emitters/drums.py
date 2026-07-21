"""エミッタ: 打楽器の粗い推測レポート(F-018 / Issue #84・#109 B-2 結線)。

入力音声波形から打点(onset)と kit 種別(kick/snare/hihat/tom/cymbal/unknown)を
粗く推定し、打点ごとの時刻・種別・確信度と kit 別集計を人間可読テキストで出力する。
drums モジュール(detect_drums)を実採譜フローへ結線する(孤立解消)。
audio-in → テキストレポート型エミッタ。

学習なしの帯域ヒューリスティックのため confidence は ~0.50 に頭打ちする(過信回避)。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from earpipe.services.ear.drums import detect_drums
from earpipe.services.emitters.base import EmitContext
from earpipe.services.stem import load_audio


KEY = "drums"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    y, sr = load_audio(ctx.audio_path)
    hits = detect_drums(y, int(sr))

    kit_counts = Counter(h["kit"] for h in hits)
    lines = [
        f"# 打楽器推測 (F-018/Issue #84): {Path(ctx.audio_path).name}",
        "注記: 学習なし帯域ヒューリスティック。confidenceは~0.50に頭打ち(目安)。",
        f"hit_count: {len(hits)}",
        "kit_summary:",
        *[f"  - {kit}: {count}" for kit, count in sorted(kit_counts.items())],
        "hits (onset_sec / kit / confidence):",
        *[
            f"  {h['onset_sec']:.4f}  {h['kit']}  {h['confidence']:.4f}"
            for h in hits
        ],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
