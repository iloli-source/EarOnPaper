"""preview エミッタのスモークテスト(#109 B-2 結線検証)。

notes → 一時MIDI → render_preview で非空のプレビュー音声が書けることを検証する。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import preview as preview_emitter
from earpipe.services.emitters.base import EmitContext


def test_preview_emit_writes_nonempty_audio(tmp_path: Path) -> None:
    # Arrange: 最小の2音メロディ(実秒未指定→bpm格子秒へフォールバック)。
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.8),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="preview-smoke")
    out_path = tmp_path / "preview.wav"

    # Act
    written = preview_emitter.emit(ctx, out_path)

    # Assert: 実在する非空の音声ファイルが返る。
    assert written.exists()
    assert written.stat().st_size > 0


def test_preview_emit_respects_sr_param(tmp_path: Path) -> None:
    # Arrange: sr パラメータを明示指定しても非空ファイルが出ること。
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=67, confidence=1.0)]
    ctx = EmitContext(
        notes=notes, bpm=100.0, title="preview-sr", params={"sr": "16000"}
    )
    out_path = tmp_path / "preview_sr.wav"

    # Act
    written = preview_emitter.emit(ctx, out_path)

    # Assert
    assert written.exists()
    assert written.stat().st_size > 0
