"""エミッタ: 音符密度の簡略化(F-025・#109 B-2 参考実装)。

notes を level(0.0〜1.0)で連続的に間引き、簡略化後の譜面を **別MusicXMLとして**
出力する(既定の -o 出力は変えない。オプトインの副次成果物)。density モジュールを
実採譜フローへ結線する(孤立解消)。notes変換→MusicXML出力型エミッタの参考実装。

パラメータ: --emit simplify:level=0.5(既定 0.5)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.density import simplify_density
from earpipe.services.notate.score import to_score, write_musicxml

KEY = "simplify"
EXT = "musicxml"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    level = ctx.param_float("level", 0.5)
    reduced = simplify_density(ctx.notes, level)
    score = to_score(reduced, ctx.bpm, title=f"{ctx.title} (簡略化 level={level})")
    write_musicxml(score, out_path)
    return out_path
