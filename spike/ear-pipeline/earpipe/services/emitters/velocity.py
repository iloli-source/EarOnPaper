"""エミッタ: 各ノートの曲内相対強弱(velocity)と強弱記号レポート(F-016)。

入力音声のオンセット近傍エネルギーから、曲内相対強弱(0-1)を推定し、
強弱記号(pp..ff)へ離散化して人間可読テキストで出力する。velocity モジュール
(estimate_velocities / to_dynamic_marks / DYNAMIC_MARKS)を実採譜フローへ結線
する(孤立解消)。既定の五線譜/MIDI 出力は変えない(オプトインの副次成果物)。

なぜ音声が要るか: velocity は打鍵直後のアタックエネルギー(RMS)を測るため
生波形が必須。よって NEEDS_AUDIO=True。オンセット秒は notes の実側 onset_sec を
使い、未設定(NaN)なら bpm から拍→秒へ換算する。

限界(velocity module docstring に正直に記載): 返るのは曲内相対順位であって
絶対強弱ではない。録音レベル・音源・音域・和声に依存するバイアスは除去できない。

パラメータ: --emit velocity:pre_sec=0.01:post_sec=0.06(既定は velocity の既定値)。
"""

from __future__ import annotations

import math
from pathlib import Path

from earpipe.contracts import PitchEvent
from earpipe.services.ear.velocity import (
    DEFAULT_ONSET_POST_SEC,
    DEFAULT_ONSET_PRE_SEC,
    DYNAMIC_MARKS,
    estimate_velocities,
    to_dynamic_marks,
)
from earpipe.services.emitters.base import EmitContext
from earpipe.services.stem import load_audio

KEY = "velocity"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def _notes_to_events(ctx: EmitContext) -> list[PitchEvent]:
    """notes を velocity 推定用の PitchEvent 列へ写す。

    実側 onset_sec/offset_sec があればそれを使い(格子スナップで壊れていない
    実タイミング。C3 の二重表現)、未設定(NaN)なら bpm から拍→秒へ換算する。
    """
    spb = 60.0 / ctx.bpm if ctx.bpm > 0 else 0.5
    events: list[PitchEvent] = []
    for note in ctx.notes:
        onset = note.onset_sec
        offset = note.offset_sec
        if not math.isfinite(onset):
            onset = note.start_beats * spb
        if not math.isfinite(offset):
            offset = (note.start_beats + note.dur_beats) * spb
        events.append(
            PitchEvent(
                onset=onset,
                offset=offset,
                midi=note.midi,
                confidence=note.confidence,
            )
        )
    return events


def emit(ctx: EmitContext, out_path: Path) -> Path:
    pre_sec = ctx.param_float("pre_sec", DEFAULT_ONSET_PRE_SEC)
    post_sec = ctx.param_float("post_sec", DEFAULT_ONSET_POST_SEC)

    events = _notes_to_events(ctx)
    y, sr = load_audio(ctx.audio_path)
    vels = estimate_velocities(y, int(sr), events, pre_sec=pre_sec, post_sec=post_sec)
    marks = to_dynamic_marks(vels, marks=DYNAMIC_MARKS)

    lines = [
        f"# 相対強弱レポート (F-016): {ctx.title}",
        "# 曲内相対値(0-1)であって絶対強弱ではない(録音レベル依存)。",
        f"note_count: {len(events)}",
        f"dynamic_marks: {' '.join(DYNAMIC_MARKS)} (弱→強)",
        "idx\tonset_sec\tmidi\tvelocity\tmark",
    ]
    for i, (ev, vel, mark) in enumerate(zip(events, vels, marks)):
        lines.append(f"{i}\t{ev.onset:.3f}\t{ev.midi}\t{vel:.3f}\t{mark}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
