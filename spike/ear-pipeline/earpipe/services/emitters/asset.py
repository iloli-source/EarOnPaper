"""エミッタ: 手直し済み拍グリッド＋音符の可搬JSON資産(F-096/Issue #98・#109 B-2 結線)。

notes/bpm を「別プロジェクト・別DAW・別記譜ソフトへ持ち出せる」可搬JSON資産として
**別ファイルに**書き出す(既定の -o 出力は変えない。オプトインの副次成果物)。
asset_io モジュール(export_asset/import_asset)を実採譜フローへ結線する(孤立解消)。

書き出し後に import_asset で読み戻し、往復(round-trip)で音符数・bpm・grid_per_beat が
不変であることを検証したうえでファイルを残す(研究の「BPM 120 落ち」を境界で弾く)。

パラメータ: --emit asset:grid_per_beat=4(既定 GRID_PER_BEAT=4)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.asset_io import export_asset, import_asset
from earpipe.services.rhythm.quantize import GRID_PER_BEAT

KEY = "asset"
EXT = "json"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    grid_per_beat = ctx.param_int("grid_per_beat", GRID_PER_BEAT)
    export_asset(ctx.notes, ctx.bpm, grid_per_beat, out_path)

    # 往復不変を検証(export→import で件数・bpm・格子解像度が一致)。
    notes, bpm, grid = import_asset(out_path)
    if len(notes) != len(ctx.notes) or bpm != float(ctx.bpm) or grid != grid_per_beat:
        raise ValueError(
            "可搬JSON資産の往復不変が破れた"
            f"(notes {len(notes)}/{len(ctx.notes)}, bpm {bpm}/{ctx.bpm}, grid {grid}/{grid_per_beat})"
        )
    return out_path
