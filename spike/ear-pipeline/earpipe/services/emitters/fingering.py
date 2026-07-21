"""エミッタ: 鍵盤運指推定レポート(F-101・#109 B-2 参考実装)。

notes に指番号(1-5)と手(right/left)を付与し、人間可読テキストで出力する。
piano_fingering.assign_fingering を実採譜フローへ結線する(孤立解消)。
notes-in→テキストレポート型エミッタ。

パラメータ: --emit fingering:hand=auto(既定 right。right/left/auto)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.piano_fingering import assign_fingering

KEY = "fingering"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    hand = ctx.param_str("hand", "right")
    assignments = assign_fingering(ctx.notes, hand=hand)

    lines = [
        f"# 鍵盤運指推定 (F-101): {ctx.title}",
        f"hand: {hand}",
        f"note_count: {len(assignments)}",
        "assignments (note_index / midi / hand / finger):",
    ]
    for a in assignments:
        idx = a["note_index"]
        midi = int(ctx.notes[idx].midi)
        lines.append(f"  - {idx}\tmidi={midi}\t{a['hand']}\tfinger={a['finger']}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
