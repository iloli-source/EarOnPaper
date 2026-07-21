"""エミッタ: 記譜前MIDIクリーンアップ・レポート(F-084/Issue #78・#109 B-2 結線)。

量子化済みノート列を記譜に渡す前の保守的・可逆な整理(極短・重複・倍音誤検出の
除去)を実行し、その削除集計と可逆情報を人間可読テキストとして出力する。
midi_cleanup モジュール(cleanup_notes / RemovedNote)を実採譜フローへ結線する
(孤立解消)。notes-in→テキストレポート型エミッタ(validate.py 参照)。

削除は非破壊なので report["removed"] の各 RemovedNote から元インスタンスと削除
根拠(reason/detail)を可視化する(「消した音をレビューできる」)。既定の -o 出力
(五線譜/MusicXML)は一切変えない。オプトインの副次成果物。

パラメータ:
  --emit midiclean:min_dur_beats=0.125(微小音価しきい値・拍単位・既定 0.125=32分)
  --emit midiclean:conf_floor=0.35(低信頼しきい値・[0,1]・既定 0.35)
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.rhythm.midi_cleanup import (
    RemovedNote,
    cleanup_notes,
)

KEY = "midiclean"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def _format_removed(r: RemovedNote) -> str:
    """RemovedNote の可逆情報を1行に整形(元ノート位置+削除根拠)。"""
    n = r.note
    return (
        f"  - [{r.reason}] start={n.start_beats} midi={n.midi} "
        f"dur={n.dur_beats} conf={n.confidence}: {r.detail}"
    )


def emit(ctx: EmitContext, out_path: Path) -> Path:
    min_dur_beats = ctx.param_float("min_dur_beats", 0.125)
    conf_floor = ctx.param_float("conf_floor", 0.35)

    cleaned, report = cleanup_notes(
        ctx.notes, min_dur_beats=min_dur_beats, conf_floor=conf_floor
    )

    removed: list[RemovedNote] = report["removed"]
    reasons: dict[str, int] = report["reasons"]

    lines = [
        f"# 記譜前MIDIクリーンアップ (F-084/Issue #78): {ctx.title}",
        f"params: min_dur_beats={min_dur_beats} conf_floor={conf_floor}",
        f"input_count: {report['input_count']}",
        f"output_count: {report['output_count']}",
        f"removed_count: {report['removed_count']}",
        "reasons:",
        *[f"  {reason}: {count}" for reason, count in sorted(reasons.items())],
        f"removed ({len(removed)}):",
        *[_format_removed(r) for r in removed],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
