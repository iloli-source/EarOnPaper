"""エミッタ: 移調・キー変更(F-060/Issue #87・#109 B-2 結線)。

notes を semitones 半音移調し、移調後の譜面を **別MusicXMLとして** 出力する
(既定の -o 出力は変えない。オプトインの副次成果物)。transpose モジュール
(notate/transpose.py)を実採譜フローへ結線する(孤立解消)。

移調は「譜面/データ側の移調」のみ(音源のピッチシフトはスコープ外。
transpose.py の二層モデル参照)。タイトルには移調後の調(臨時記号最少の
異名同音を選んだもの)と、移調でTAB音域外に出る音符数を注記する。

パラメータ: --emit transpose:semitones=2(既定 2)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.score import to_score, write_musicxml
from earpipe.services.notate.spelling import estimate_key
from earpipe.services.notate.transpose import (
    spell_transposed_key,
    transpose_key,
    transpose_notes,
    transpose_tab_out_of_range,
)

KEY = "transpose"
EXT = "musicxml"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    semitones = ctx.param_int("semitones", 2)

    transposed = transpose_notes(ctx.notes, semitones)

    # 移調後の調(臨時記号最少の異名同音)をタイトルに注記する。
    # 空入力では estimate_key はハ長調を返すので常に妥当な Key が得られる。
    src_key = estimate_key(ctx.notes)
    dst_key = spell_transposed_key(src_key, semitones)
    dst_tonic_pc = transpose_key(src_key.tonic.pitchClass, semitones)

    # 移調でTAB(ギター6弦標準)音域を外れる音符数を正直に注記する。
    out_of_range = transpose_tab_out_of_range(ctx.notes, semitones)

    title = (
        f"{ctx.title} (移調 {semitones:+d}半音 → {dst_key.tonic.name}"
        f"{dst_key.mode} / pc={dst_tonic_pc}"
        f", TAB音域外 {len(out_of_range)}音)"
    )
    score = to_score(transposed, ctx.bpm, title=title)
    write_musicxml(score, out_path)
    return out_path
