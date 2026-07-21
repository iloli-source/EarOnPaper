"""エミッタ: SNS共有用ビジュアルカードPNG(F-109/Issue #93・#109 B-2 結線)。

入力音声の波形(背景)と抽出音符(前景)を重畳した固定比率(1200x630=OGP/
Twitter Card準拠)の共有用PNGを端末内で生成する。visual_card モジュールを
実採譜フローへ結線する(孤立解消)。audio+notes→単一PNG型エミッタ。

限界(正直な記録・モジュール本体に準拠):
- これは共有用の「見せるための簡約」であり採譜そのものの正しさを保証しない。
- offsetは曖昧なため音価は厳密表示せず、バーは相対的な長さの目安に留める。

パラメータ: --emit card:title=... (省略時は ctx.title を使う)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.visual_card import render_visual_card
from earpipe.services.stem.preprocess import load_audio

KEY = "card"
EXT = "png"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    title = ctx.param_str("title", ctx.title)
    y, sr = load_audio(ctx.audio_path)
    sr_int = int(round(sr))
    return render_visual_card(
        y,
        sr_int,
        ctx.notes,
        out_path,
        title=title,
        bpm=ctx.bpm,
    )
