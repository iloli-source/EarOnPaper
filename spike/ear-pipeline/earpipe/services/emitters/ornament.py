"""エミッタ: 装飾音・演奏ノイズの記譜解釈レポート(F-082/Issue #91・#109 B-2)。

notes の微小音符を隣接主音への装飾候補(grace/acciaccatura)として分類し、
判定・付く主音・音程・理由を人間可読テキストで出力する。ornament モジュール
(interpret_ornaments)を実採譜フローへ結線する(孤立解消)。既定は非破壊で、
本体記譜(-o 出力)は一切変えないオプトインの副次成果物。notes-in→テキスト型。

パラメータ: --emit ornament:min_main_beats=0.25(既定 0.25=16分音符)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.ornament import interpret_ornaments

KEY = "ornament"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    min_main_beats = ctx.param_float("min_main_beats", 0.25)
    _out_notes, ornaments = interpret_ornaments(ctx.notes, min_main_beats)

    lines = [
        f"# 装飾音・演奏ノイズ判定 (F-082): {ctx.title}",
        f"min_main_beats: {min_main_beats:g}",
        f"note_count: {len(ctx.notes)}",
        f"ornament_candidates: {len(ornaments)}",
        "",
    ]
    if not ornaments:
        lines.append("(微小音符なし: 装飾候補は検出されませんでした)")
    for orn in ornaments:
        lines.append(
            f"- index={orn['index']} midi={orn['midi']} "
            f"dur_beats={orn['dur_beats']:g} conf={orn['confidence']:.2f} "
            f"judgement={orn['judgement']} kind={orn['kind'] or '-'} "
            f"main_index={orn['main_index']} direction={orn['direction']} "
            f"interval={orn['interval_semitones']}"
        )
        lines.append(f"    理由: {orn['reason']}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
