"""エミッタ: 音質診断レポート(F-002・#109 B-2 結線)。

入力音声の生波形を読み込み、diagnose_audio でクリッピング率・SNR・帯域上限・
残響を評価し、総合rating(green/yellow/red)と日本語警告を人間可読テキストで
出力する。stem.diagnose モジュールを実採譜フローへ結線する(孤立解消)。
audio-in 型エミッタの参考実装。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.stem import load_audio
from earpipe.services.stem.diagnose import diagnose_audio

KEY = "diagnose"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    y, sr = load_audio(ctx.audio_path)
    quality = diagnose_audio(y, int(sr))
    lines = [
        f"# 音質診断 (F-002): {Path(ctx.audio_path).name}",
        f"rating: {quality.rating}",
        f"clipping_rate: {quality.clipping_rate}",
        f"snr_db: {quality.snr_db}",
        f"reverb_ratio: {quality.reverb_ratio}",
        f"band_limit_hz: {quality.band_limit_hz}",
        f"warnings ({len(quality.warnings)}):",
        *[f"  - {w}" for w in quality.warnings],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
