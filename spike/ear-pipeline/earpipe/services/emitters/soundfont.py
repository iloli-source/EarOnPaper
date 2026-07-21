"""エミッタ: 任意SF2音色での試聴音声レンダリング(F-097/Issue #104・#109 B-2 結線)。

notes を実タイミングで一時MIDIへ書き出し、render_soundfont_preview で
ユーザー指定SF2音色を用いた試聴WAVを **副次成果物として** 出力する。既定の
五線譜/MIDI/PDF出力は変えない(オプトイン)。soundfont_preview モジュール
(render_soundfont_preview / fluidsynth_available)を実採譜フローへ結線する
(孤立解消)。preview エミッタ(GMデフォルト音源)に対し、本エミッタは
「任意SF2を明示指定した試聴(audition)」を担う。

SF2未指定・または pyfluidsynth 未導入(本CI含む)の場合は、render_soundfont_preview
が pretty_midi 内蔵サイン波合成へフォールバックし、その事実を
<out>.wav.note.txt サイドカーへ明記する(無言のなりすまし禁止)。

パラメータ:
  --emit soundfont:sr=44100          合成サンプルレート(既定 DEFAULT_SR=44100)。
  --emit soundfont:soundfont=/path/to/font.sf2
                                      使用するSF2ファイル(既定 空=未指定→フォールバック)。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.score import write_midi_raw
from earpipe.services.notate.soundfont_preview import (
    DEFAULT_SR,
    render_soundfont_preview,
)

KEY = "soundfont"
EXT = "wav"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    sr = ctx.param_int("sr", DEFAULT_SR)
    # 既定は空=未指定。空文字はSF2なし(=フォールバック)として扱う。
    sf_raw = ctx.param_str("soundfont", "")
    soundfont_path = sf_raw if sf_raw.strip() else None

    # notes を実タイミングMIDIへ書き出し(格子化ロスを避ける raw 側)。
    # 一時MIDIは合成後に破棄する(副次成果物は音声のみ)。
    with tempfile.TemporaryDirectory() as tmpdir:
        midi_path = Path(tmpdir) / "soundfont_source.mid"
        write_midi_raw(ctx.notes, midi_path, ctx.bpm)
        return render_soundfont_preview(
            midi_path, out_path, soundfont_path=soundfont_path, sr=sr
        )
