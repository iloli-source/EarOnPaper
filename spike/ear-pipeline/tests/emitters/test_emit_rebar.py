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


def test_emit_preserves_notes_and_reports_correction(tmp_path: Path) -> None:
    # Arrange: 6音の系統ずれ列
    notes = _shifted_notes()
    ctx = EmitContext(notes=notes, bpm=120.0, title="テスト曲", params={"grid": "4"})
    out = tmp_path / f"out.{rebar_emitter.EXT}"

    # Act
    rebar_emitter.emit(ctx, out)

    # Assert: 入力音を1つも落としていない(小節線での連桁分割で数は増えうるが減らない)
    xml = out.read_text(encoding="utf-8")
    assert xml.count("<note") >= len(notes), f"音符が欠落: {xml.count('<note')} < {len(notes)}"
    # リバーリングが実行され、信頼度が譜面タイトルに正直に注記されている(補正ロジックが走った証跡)
    assert "リバーリング" in xml and "信頼度" in xml


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
