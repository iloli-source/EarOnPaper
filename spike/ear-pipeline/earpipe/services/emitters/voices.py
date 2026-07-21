"""エミッタ: 多声部の声部分離譜(F-019・#109 B-2 結線)。

notes を音高・時間連続性で 2〜3 声部へ分離し(skyline+下声のヒューリスティック)、
各声部を1パートとして **1つの MusicXML** にまとめて出力する(既定の -o 出力は
変えない。オプトインの副次成果物)。multivoice モジュール(separate_voices)を
実採譜フローへ結線する(孤立解消)。notes変換→MusicXML出力型エミッタ。

これは「編集可能な声部分けの下書き」であって、混合バンド音源からの正しいフル
スコア声部割当ではない(multivoice の docstring 参照)。単一副次ファイルに収まる
ため emitter 化する(第2譜面や外部ツールは不要)。

パラメータ: --emit voices:max_voices=3(既定 3。2 または 3 のみ)。
"""

from __future__ import annotations

from pathlib import Path

import music21

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.multivoice import separate_voices
from earpipe.services.notate.score import to_score

KEY = "voices"
EXT = "musicxml"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False

_DEFAULT_MAX_VOICES = 3


def emit(ctx: EmitContext, out_path: Path) -> Path:
    max_voices = ctx.param_int("max_voices", _DEFAULT_MAX_VOICES)
    voices = separate_voices(ctx.notes, max_voices=max_voices)

    # 各声部を1パートの譜面にし、1つの Score へ束ねる(声部数ぶんのパート)。
    # 空入力/全声部が空なら to_score([]) が全休符1小節のパートを返すため、
    # 出力は常に非空になる(正直に「音が無い」を1パートで示す)。
    merged = music21.stream.Score()
    md = music21.metadata.Metadata()
    md.movementName = f"{ctx.title} (声部分離 max_voices={max_voices})"
    merged.metadata = md

    voice_scores = voices if voices else [[]]
    for idx, voice_notes in enumerate(voice_scores, start=1):
        single = to_score(voice_notes, ctx.bpm, title=ctx.title)
        for part in single.parts:
            part.partName = f"Voice {idx}"
            merged.insert(0, part)

    merged.write("musicxml", fp=str(out_path))
    return out_path
