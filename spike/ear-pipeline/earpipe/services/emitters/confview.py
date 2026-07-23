"""エミッタ: 信頼度ハイライト＋波形の解析ビューPDF(#121 の一部)。

入力音声の波形(背景)に採譜音符を重ね、各音符を信頼度で色分け(緑=高/橙=中/
赤=低)した「校正用」PDFを端末内で生成する。analysis_view モジュールを実採譜
フローへ結線する。audio+notes→単一PDF型エミッタ。完全ローカル処理。

パラメータ: --emit confview:title=... (省略時は ctx.title を使う)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.analysis_view import render_confidence_view_pdf
from earpipe.services.stem.preprocess import load_audio

KEY = "confview"
EXT = "pdf"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    title = ctx.param_str("title", ctx.title)
    y, sr = load_audio(ctx.audio_path)
    return render_confidence_view_pdf(
        y, int(round(sr)), ctx.notes, ctx.bpm, out_path, title=title
    )
