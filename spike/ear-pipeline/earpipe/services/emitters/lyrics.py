"""エミッタ: 歌声採譜・歌詞同期(F-020/Issue #96・#109 B-2 結線)。

notes に歌詞の音節列を順次割り当て、音符ごとの割当(音節・メリスマ継続)を
人間可読テキストで出力する。音節が余った(音符不足)場合は unassigned として
明示する(取りこぼし可視化)。vocal_lyrics モジュールを実採譜フローへ結線する
(孤立解消)。notes-in→テキストレポート型エミッタ。

パラメータ:
  --emit lyrics:syllables=ら,ら,ら(既定 空 → 歌詞なし)
    区切り文字は sep で変更可(既定 ","):--emit lyrics:sep=/:syllables=la/la/la
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.vocal_lyrics import (
    MELISMA_CONTINUATION,
    align_lyrics,
    count_unassigned,
)

KEY = "lyrics"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    sep = ctx.param_str("sep", ",")
    raw = ctx.param_str("syllables", "")
    syllables = raw.split(sep) if raw else []

    records = align_lyrics(ctx.notes, syllables)
    unassigned = count_unassigned(ctx.notes, syllables)

    lines = [
        f"# 歌詞同期 (F-020/Issue #96): {ctx.title}",
        f"note_count: {len(ctx.notes)}",
        f"syllable_input: {len([s for s in syllables if s.strip()])}",
        f"unassigned_syllables: {unassigned}",
        f"melisma_token: {MELISMA_CONTINUATION!r}",
        "assignments (note_index / syllable / melisma):",
    ]
    for rec in records:
        lines.append(
            f"  [{rec['note_index']}] {rec['syllable']!r}"
            f" melisma={rec['melisma']}"
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
