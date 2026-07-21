"""エミッタ: 支配的な1楽器の粗い推測レポート(F-015・#109 B-2 結線)。

入力音声の全波形(または先頭 seconds 秒)から支配的な1楽器を粗く推測し、
label / confidence / 生特徴を人間可読テキストで出力する。instrument_classify
モジュールを実採譜フローへ結線する(孤立解消)。audio-in→テキストレポート型。

限界(正直な記録・モジュール本体に準拠):
- これは「支配的な1楽器の粗い推測」であって多楽器の同時分類ではない。
- 学習を使わない閾値ヒューリスティックのため confidence は低めに頭打ちする。

パラメータ: --emit instrument:seconds=0(既定 0=全波形。>0 なら先頭その秒数のみ)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.ear.instrument_classify import classify_instrument
from earpipe.services.emitters.base import EmitContext
from earpipe.services.stem.preprocess import load_audio

KEY = "instrument"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    seconds = ctx.param_float("seconds", 0.0)
    y, sr = load_audio(ctx.audio_path)
    sr_int = int(round(sr))
    if seconds > 0.0:
        n = int(seconds * sr_int)
        if n > 0:
            y = y[:n]

    guess = classify_instrument(y, sr_int)

    lines = [
        f"# 楽器推測 (F-015): {Path(ctx.audio_path).name}",
        f"label: {guess.label}",
        f"confidence: {guess.confidence}",
        f"features ({len(guess.features)}):",
        *[f"  {k}: {v}" for k, v in guess.features.items()],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
