"""エミッタ: プレビュー音声のソニフィケーション(F-054/Issue #69・#109 B-2 参考実装)。

notes を実タイミングで一時MIDIへ書き出し、render_preview で MIDI→音声合成し
プレビューWAV(またはffmpeg有時MP3)を **副次成果物として** 出力する。既定の
五線譜/MIDI/PDF出力は変えない(オプトイン)。preview モジュール(render_preview)
を実採譜フローへ結線する(孤立解消)。notes→音声型エミッタの参考実装。

パラメータ: --emit preview:sr=22050(合成サンプルレート、既定 22050)。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.preview import DEFAULT_SR, render_preview
from earpipe.services.notate.score import write_midi_raw

KEY = "preview"
EXT = "wav"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    sr = ctx.param_int("sr", DEFAULT_SR)

    # notes を実タイミングMIDIへ書き出し(格子化ロスを避ける raw 側)。
    # 一時MIDIは合成後に破棄する(副次成果物は音声のみ)。
    with tempfile.TemporaryDirectory() as tmpdir:
        midi_path = Path(tmpdir) / "preview_source.mid"
        write_midi_raw(ctx.notes, midi_path, ctx.bpm)
        return render_preview(midi_path, out_path, sr=sr)
