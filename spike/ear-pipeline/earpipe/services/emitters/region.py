"""エミッタ: 区間切り出し音声の書き出し(F-007・Issue #105・#109 B-2 参考実装)。

入力音声から [start, end) 秒を切り出し、境界に微小フェード(クリック除去)を
かけた副次成果物 WAV を出力する。region_select.crop_region を実採譜フローへ
結線する(孤立解消)。生波形を load して1ファイルを書き出す音声型エミッタ。

パラメータ: --emit region:start=0.0:end=5.0:fade=0.005
    start(既定 0.0)/end(既定 5.0)秒、fade(境界フェード秒・既定 0.005)。
"""

from __future__ import annotations

from pathlib import Path

import soundfile as sf

from earpipe.services.emitters.base import EmitContext
from earpipe.services.stem import load_audio
from earpipe.services.stem.region_select import crop_region

KEY = "region"
EXT = "wav"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    start_sec = ctx.param_float("start", 0.0)
    end_sec = ctx.param_float("end", 5.0)
    fade_sec = ctx.param_float("fade", 0.005)

    y, sr = load_audio(ctx.audio_path)
    region = crop_region(y, int(sr), start_sec, end_sec, edge_fade_sec=fade_sec)
    sf.write(str(out_path), region, int(sr))
    return out_path
