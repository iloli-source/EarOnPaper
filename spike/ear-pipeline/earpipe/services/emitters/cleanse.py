"""エミッタ: 調内制約クレンジング候補レポート(F-086・#109 B-2 参考実装)。

推定調に対し調外音を最近傍の調内音へスナップする「候補」を提示し、
各候補(元音・移動量・リスク・理由)を人間可読テキストで出力する。
scale_cleanse モジュールを実採譜フローへ結線する(孤立解消)。
既定は非破壊(候補提示のみ)。apply=true のとき高信頼候補のみ適用結果も注記する。

パラメータ:
    --emit cleanse:apply=true(既定 false。true で高信頼候補を実適用扱いに)
    --emit cleanse:mode=minor(既定は推定調から。指定時は major/minor を強制)
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.scale_cleanse import cleanse_to_scale
from earpipe.services.notate.spelling import estimate_key

KEY = "cleanse"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    key = estimate_key(ctx.notes)
    tonic_pc = key.tonic.pitchClass
    mode = ctx.param_str("mode", key.mode if key.mode in ("major", "minor") else "major")
    apply = ctx.param_bool("apply", False)

    out_notes, candidates = cleanse_to_scale(
        ctx.notes, tonic_pc, mode=mode, apply=apply
    )

    applied_count = sum(1 for c in candidates if c["applied"])
    lines = [
        f"# 調内クレンジング候補 (F-086): {ctx.title}",
        f"key: {key.tonic.name} {mode} (tonic_pc={tonic_pc})",
        f"notes: {len(ctx.notes)}  out_of_scale: {len(candidates)}  applied: {applied_count}",
        "",
    ]
    for c in candidates:
        lines.append(
            f"[{c['index']}] midi {c['original_midi']} -> {c['snapped_midi']} "
            f"({c['move_semitones']:+d}半音) alt={c['alt_midis']} "
            f"conf={c['confidence']:.2f} risk={c['risk']} applied={c['applied']}"
        )
        lines.append(f"    理由: {c['reason']}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
