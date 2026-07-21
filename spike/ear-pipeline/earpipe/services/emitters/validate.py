"""エミッタ: MusicXML 妥当性検証レポート(F-052/NF-011・#109 B-2 参考実装)。

出力済み MusicXML を検証し、is_valid / errors / warnings / note_count /
roundtrip_ok を人間可読テキストで出力する。musicxml_validate モジュールを
実採譜フローへ結線する(孤立解消)。musicxml-in 型エミッタの参考実装。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.musicxml_validate import validate_musicxml

KEY = "validate"
EXT = "txt"
NEEDS_MUSICXML = True
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    report = validate_musicxml(ctx.musicxml_path)
    lines = [
        f"# MusicXML検証 (F-052/NF-011): {Path(ctx.musicxml_path).name}",
        f"is_valid: {report.is_valid}",
        f"note_count: {report.note_count}",
        f"roundtrip_ok: {report.roundtrip_ok}",
        f"errors ({len(report.errors)}):",
        *[f"  - {e}" for e in report.errors],
        f"warnings ({len(report.warnings)}):",
        *[f"  - {w}" for w in report.warnings],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
