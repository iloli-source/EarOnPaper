"""soundfont エミッタのスモークテスト(#109 B-2 結線検証)。

notes → 一時MIDI → render_soundfont_preview で非空の試聴音声が書けることを検証する。
SF2未指定・pyfluidsynth 未導入のCI環境ではサイン波フォールバックへ落ちるが、
いずれの経路でも非空WAVが返ることを確認する(結線の到達性が目的)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import soundfont as soundfont_emitter
from earpipe.services.emitters.base import EmitContext


def test_soundfont_emit_writes_nonempty_audio(tmp_path: Path) -> None:
    # Arrange: 最小の2音メロディ(実秒未指定→bpm格子秒へフォールバック)。
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.8),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="soundfont-smoke")
    out_path = tmp_path / "soundfont.wav"

    # Act
    written = soundfont_emitter.emit(ctx, out_path)

    # Assert: 実在する非空の音声ファイルが返る。
    assert written.exists()
    assert written.stat().st_size > 0


def test_soundfont_emit_respects_sr_param(tmp_path: Path) -> None:
    # Arrange: sr パラメータを明示指定しても非空ファイルが出ること。
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=67, confidence=1.0)]
    ctx = EmitContext(
        notes=notes, bpm=100.0, title="soundfont-sr", params={"sr": "16000"}
    )
    out_path = tmp_path / "soundfont_sr.wav"

    # Act
    written = soundfont_emitter.emit(ctx, out_path)

    # Assert
    assert written.exists()
    assert written.stat().st_size > 0


def test_soundfont_emit_missing_sf2_raises(tmp_path: Path) -> None:
    # Arrange: 存在しないSF2を指定→サイレント無音を避けるため例外(F-097)。
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0)]
    missing_sf2 = tmp_path / "does_not_exist.sf2"
    ctx = EmitContext(
        notes=notes,
        bpm=120.0,
        title="soundfont-missing",
        params={"soundfont": str(missing_sf2)},
    )
    out_path = tmp_path / "soundfont_missing.wav"

    # Act / Assert
    raised = False
    try:
        soundfont_emitter.emit(ctx, out_path)
    except FileNotFoundError:
        raised = True
    assert raised
