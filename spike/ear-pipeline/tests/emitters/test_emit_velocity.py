"""velocity エミッタのスモーク: notes+音声→相対強弱レポートを非空で出す。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.velocity import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _notes() -> list[QuantizedNote]:
    """MELODY_SIMPLE の先頭数音に対応する最小ノート(実側 onset_sec つき)。"""
    spb = 60.0 / 120.0  # simple_wav は BPM120
    specs = [
        (60, 0.0, 1.0),
        (62, 1.0, 1.0),
        (64, 2.0, 0.5),
        (65, 2.5, 0.5),
        (67, 3.0, 1.0),
    ]
    return [
        QuantizedNote(
            start_beats=s,
            dur_beats=d,
            midi=m,
            confidence=0.9,
            onset_sec=s * spb,
            offset_sec=(s + d) * spb,
        )
        for m, s, d in specs
    ]


def test_module_contract():
    # Arrange / Act / Assert
    assert KEY == "velocity"
    assert EXT == "txt"
    assert NEEDS_AUDIO is True
    assert NEEDS_MUSICXML is False


def test_emit_writes_non_empty_report(simple_wav, tmp_path):
    # Arrange
    wav_path, _melody, bpm = simple_wav
    ctx = EmitContext(
        notes=_notes(),
        bpm=float(bpm),
        title="test",
        audio_path=wav_path,
    )
    out_path = tmp_path / "velocity.txt"

    # Act
    result = emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "note_count: 5" in text
    # 各ノートに強弱記号が付く(DYNAMIC_MARKS のいずれか)
    assert any(mark in text for mark in ("pp", "p", "mp", "mf", "f", "ff"))


def test_emit_falls_back_to_beats_when_onset_unset(simple_wav, tmp_path):
    # Arrange: onset_sec 未設定(NaN)でも bpm から秒換算して測れる
    wav_path, _melody, bpm = simple_wav
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.9),
    ]
    ctx = EmitContext(notes=notes, bpm=float(bpm), title="fallback", audio_path=wav_path)
    out_path = tmp_path / "velocity_fb.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "note_count: 2" in text
