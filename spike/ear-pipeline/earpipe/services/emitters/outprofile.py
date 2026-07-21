"""エミッタ: 出力先ソフト別エクスポートプロファイル(F-103・Issue #100・#109 B-2)。

notes→MusicXML を生成し、取り込み先ソフト(MuseScore / Dorico / Sibelius /
Guitar Pro / generic)のインポート方言に合わせて軽微に調整した MusicXML を
**別ファイルとして**出力する(既定の -o 出力は変えない。オプトインの副次成果物)。
output_profiles モジュール(adjust_musicxml_for)を実採譜フローへ結線する(孤立解消)。

パラメータ: --emit outprofile:target=dorico(既定 generic)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.output_profiles import adjust_musicxml_for
from earpipe.services.notate.score import to_score, write_musicxml

KEY = "outprofile"
EXT = "musicxml"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    target = ctx.param_str("target", "generic")
    score = to_score(ctx.notes, ctx.bpm, title=f"{ctx.title} (→{target})")
    # 一度素の MusicXML をファイルへ書き、文字列として読み戻してプロファイル調整する。
    write_musicxml(score, out_path)
    raw = out_path.read_text(encoding="utf-8")
    adjusted = adjust_musicxml_for(raw, target)
    out_path.write_text(adjusted, encoding="utf-8")
    return out_path
