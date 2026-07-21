"""エミッタ: ドラム譜(打点→percussion clef MusicXML)(F-036/Issue #89・#109 B-2)。

notes(QuantizedNote列)を打点列とみなし、drums_to_musicxml でドラム譜 MusicXML を
**別ファイルとして**出力する(既定の -o 出力は変えない。オプトインの副次成果物)。
drum_notation モジュール(drums_to_musicxml / gm_note_to_musicxml_unpitched)を
実採譜フローへ結線する(孤立解消)。

制約(正直な記録):
- QuantizedNote は kit(打楽器種)情報を持たない。よって各ノートを単一の kit
  レーン(既定 snare)へ倒す。kit は --emit drumscore:kit=hihat 等で切替可能。
- 実タイミング onset_sec が NaN のノートは start_beats を秒へ換算して代替する
  (grid 側の拍位置を信頼する。QuantizedNote docstring の二重表現に従う)。

パラメータ: --emit drumscore:kit=snare(既定 snare。kick/snare/hihat/tom/cymbal/unknown)。
"""

from __future__ import annotations

import math
from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.drum_notation import drums_to_musicxml

KEY = "drumscore"
EXT = "musicxml"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False

_DEFAULT_KIT = "snare"


def _onset_sec_of(note, sec_per_beat: float) -> float:
    """ノートの打点(秒)を得る。実側 onset_sec が NaN なら格子側から換算する。"""
    onset = note.onset_sec
    if onset is None or math.isnan(onset):
        return max(0.0, float(note.start_beats) * sec_per_beat)
    return max(0.0, float(onset))


def emit(ctx: EmitContext, out_path: Path) -> Path:
    kit = ctx.param_str("kit", _DEFAULT_KIT)
    sec_per_beat = 60.0 / ctx.bpm
    drum_hits = [
        {
            "onset_sec": _onset_sec_of(note, sec_per_beat),
            "kit": kit,
            "confidence": note.confidence,
        }
        for note in ctx.notes
    ]
    drums_to_musicxml(drum_hits, ctx.bpm, out_path=out_path)
    return out_path
