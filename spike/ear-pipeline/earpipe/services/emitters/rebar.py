"""エミッタ: 小節・拍オフセットの系統補正／リバーリング(F-083/Issue #77・#109 B-2 結線)。

量子化済み音符列に残る「系統的な拍位相ずれ」を検出して格子頭へ再整列し
(rebarring)、補正後の譜面を **別MusicXMLとして** 出力する(既定の -o 出力は
変えない。オプトインの副次成果物)。rhythm/rebar.py モジュール
(correct_beat_offset / add_sync_points)を実採譜フローへ結線する(孤立解消)。

補正は格子側 start_beats のみ。実タイミング onset_sec/offset_sec は保持する(C3)。
系統ずれが検出できない(ルバート・既に整合・範囲外)場合は何も変えず、その旨と
信頼度をタイトルへ正直に注記する。

手動同期点を渡すと、系統補正の前に区分線形ワープを掛ける(add_sync_points)。
パラメータ:
  --emit rebar:grid=4(1拍あたり格子分割数。既定4=16分格子)
  --emit rebar:beats_per_bar=4(1小節の拍数。既定4)
  --emit rebar:sync=measured:target;measured:target;...(手動同期点。任意)
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.score import to_score, write_musicxml
from earpipe.services.rhythm.rebar import add_sync_points, correct_beat_offset

KEY = "rebar"
EXT = "musicxml"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def _parse_sync_points(raw: str) -> list[tuple[float, float]]:
    """"m1:t1;m2:t2;..." 形式を (measured, target) 対のリストへ。空なら空リスト。"""
    points: list[tuple[float, float]] = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        measured_str, _, target_str = chunk.partition(":")
        points.append((float(measured_str), float(target_str)))
    return points


def emit(ctx: EmitContext, out_path: Path) -> Path:
    grid = ctx.param_int("grid", 4)
    beats_per_bar = ctx.param_int("beats_per_bar", 4)
    sync_raw = ctx.param_str("sync", "")

    notes = ctx.notes
    sync_note = ""
    sync_points = _parse_sync_points(sync_raw)
    if sync_points:
        notes = add_sync_points(notes, sync_points)
        sync_note = f", 手動同期点 {len(sync_points)}点適用"

    corrected, confidence = correct_beat_offset(
        notes, grid_per_beat=grid, beats_per_bar=beats_per_bar
    )

    title = (
        f"{ctx.title} (リバーリング grid={grid}/beat, {beats_per_bar}/4"
        f", 信頼度 {confidence:.2f}{sync_note})"
    )
    score = to_score(corrected, ctx.bpm, title=title)
    write_musicxml(score, out_path)
    return out_path
