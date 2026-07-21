"""エミッタ: サステインペダル区間候補レポート(F-102・#109 B-2 結線)。

耳層 pedal モジュールの detect_sustain を実採譜フローへ結線する(孤立解消)。
量子化済みノートの実タイミング(onset_sec/offset_sec)の音響的な尾の重なりから
ペダルが踏まれていそうな区間の「候補」を推定し、人間可読テキストで出力する。

重要(F-102 の 3層分離): ここで出すのは記譜の音価でも物理 note_off でもない
「音響 sound_off 層の候補(Ped.線を引く候補位置)」であって CC64 真値ではない。
既定の五線譜/MIDI 出力は一切変えない(オプトインの副次成果物)。

パラメータ:
  --emit sustain:min_overlap=0.08(尾がこの秒数以上次打鍵に食い込めば候補・既定0.08)
  --emit sustain:merge_gap=0.15(この秒数以上の切れ目で別区間に割る・既定0.15)
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.ear.pedal import (
    DEFAULT_MERGE_GAP_SEC,
    DEFAULT_MIN_OVERLAP_SEC,
    detect_sustain,
)
from earpipe.services.emitters.base import EmitContext

KEY = "sustain"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    min_overlap = ctx.param_float("min_overlap", DEFAULT_MIN_OVERLAP_SEC)
    merge_gap = ctx.param_float("merge_gap", DEFAULT_MERGE_GAP_SEC)

    spans = detect_sustain(ctx.notes, min_overlap_sec=min_overlap, merge_gap_sec=merge_gap)

    lines = [
        f"# サステインペダル区間候補 (F-102): {ctx.title}",
        "# 注意: これは音響sound_off層の候補であってCC64真値ではない(音価は不変)。",
        f"min_overlap_sec: {min_overlap}",
        f"merge_gap_sec: {merge_gap}",
        f"span_count: {len(spans)}",
    ]
    for i, span in enumerate(spans, start=1):
        lines.append(
            f"[{i}] {span['start_sec']:.3f}s - {span['end_sec']:.3f}s "
            f"confidence={span['confidence']} note_count={span['note_count']} "
            f"layer={span['layer']}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
