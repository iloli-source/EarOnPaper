"""エミッタ: 楽器プロファイル適合レポート(F-079/Issue #90・#109 B-2 結線)。

notes を指定の楽器プロファイル(既定 guitar6)に照らし、そのまま演奏可能な音
(in_range)と音域外の音(out_of_range・必要オクターブ移動数つき)に分類して
人間可読テキストで出力する。instrument_profile モジュール(fit_to_profile /
get_profile)を実採譜フローへ結線する(孤立解消)。notes→テキストレポート型。

音域外は黙って丸めず、収めるのに必要なオクターブ移動数を添える(研究の推奨)。

パラメータ: --emit profile:name=guitar6(既定 guitar6。PROFILES のキー)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.instrument_profile import fit_to_profile, get_profile

KEY = "profile"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    name = ctx.param_str("name", "guitar6")
    profile = get_profile(name)
    result = fit_to_profile(ctx.notes, profile)
    lines = [
        f"# 楽器プロファイル適合 (F-079): {profile.name_ja}",
        f"profile: {profile.name}",
        f"strings(low->high): {', '.join(str(s) for s in profile.strings)}",
        f"fret_max: {profile.fret_max}",
        f"range_midi: {profile.lowest_open_midi}..{profile.highest_midi}",
        f"notes_total: {result.n_in_range + result.n_out_of_range}",
        f"in_range: {result.n_in_range}",
        f"out_of_range: {result.n_out_of_range}",
    ]
    for note, shift in result.out_of_range:
        direction = "up" if shift > 0 else "down"
        lines.append(
            f"  - midi={note.midi} start={note.start_beats} "
            f"octave_shift_suggested={shift:+d} ({direction})"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
