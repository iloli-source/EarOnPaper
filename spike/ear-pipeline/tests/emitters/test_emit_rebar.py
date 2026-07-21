"""rebar エミッタのスモーク/結線テスト(F-083/Issue #77・#109 B-2)。"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import rebar as rebar_emitter
from earpipe.services.emitters.base import EmitContext


def _shifted_notes(offset: float = 0.06) -> list[QuantizedNote]:
    """全ノートが16分格子に対し共通の端数 offset だけ後ろへずれた系統ずれ列。"""
    grid = [0.0, 1.0, 2.0, 2.5, 3.0, 4.0]
    return [
        QuantizedNote(start_beats=g + offset, dur_beats=0.5, midi=60 + i, confidence=1.0)
        for i, g in enumerate(grid)
    ]


def test_emit_writes_non_empty_musicxml(tmp_path: Path) -> None:
    # Arrange
    ctx = EmitContext(notes=_shifted_notes(), bpm=120.0, title="テスト曲",
                      params={"grid": "4"})
    out = tmp_path / f"out.{rebar_emitter.EXT}"

    # Act
    result = rebar_emitter.emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0
    assert "<note" in out.read_text(encoding="utf-8")


def test_emit_default_params(tmp_path: Path) -> None:
    # Arrange: paramなしでも既定 grid=4 / beats_per_bar=4 で非空出力
    ctx = EmitContext(notes=_shifted_notes(), bpm=100.0, title="既定")
    out = tmp_path / "out.musicxml"

    # Act
    result = rebar_emitter.emit(ctx, out)

    # Assert
    assert result.stat().st_size > 0


def test_emit_applies_sync_points(tmp_path: Path) -> None:
    # Arrange: 手動同期点(add_sync_points 経由)でも非空出力に到達する
    ctx = EmitContext(notes=_shifted_notes(), bpm=120.0, title="同期",
                      params={"sync": "0.0:0.0;4.0:4.0"})
    out = tmp_path / "out.musicxml"

    # Act
    result = rebar_emitter.emit(ctx, out)

    # Assert
    assert result.stat().st_size > 0
    assert "<note" in out.read_text(encoding="utf-8")
