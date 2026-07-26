"""エミッタ: confidence込みノート列のJSONエクスポート(#147 剪定前提(a))。

既定のCLI stdout要約は notes を意図的に落とす(出力肥大防止)ため、
イベント層の confidence・実タイミング(onset_sec/offset_sec)が外部から
参照できない。剪定ゲート検証やベンチのラベル付けにはこれらの実値が
必要なので、機械可読な副次成果物としてオプトイン出力する。

パラメータ: なし。--emit notesjson=path.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from earpipe.services.emitters.base import EmitContext

KEY = "notesjson"
EXT = "json"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def _finite_or_none(value: float) -> float | None:
    return None if math.isnan(value) else value


def emit(ctx: EmitContext, out_path: Path) -> Path:
    notes = [
        {
            "start_beats": n.start_beats,
            "dur_beats": n.dur_beats,
            "midi": n.midi,
            "confidence": n.confidence,
            "onset_sec": _finite_or_none(n.onset_sec),
            "offset_sec": _finite_or_none(n.offset_sec),
        }
        for n in ctx.notes
    ]
    payload = {
        "title": ctx.title,
        "bpm": ctx.bpm,
        "n_notes": len(notes),
        "notes": notes,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    return out_path
