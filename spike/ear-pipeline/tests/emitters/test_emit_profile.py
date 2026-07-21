"""profile エミッタのテスト(F-079 結線スモーク)。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import profile as profile_emitter
from earpipe.services.emitters.base import EmitContext


def _note(midi: int, start: float = 0.0) -> QuantizedNote:
    return QuantizedNote(
        start_beats=start, dur_beats=1.0, midi=midi, confidence=1.0
    )


def test_emit_writes_nonempty_report_with_in_range_notes(tmp_path):
    # Arrange: guitar6 音域内の音(E4=64 など)。
    ctx = EmitContext(
        notes=[_note(40), _note(52), _note(64)],
        bpm=120.0,
        title="テスト",
    )
    out_path = tmp_path / "profile.txt"

    # Act
    result = profile_emitter.emit(ctx, out_path)

    # Assert
    assert result == out_path
    text = out_path.read_text(encoding="utf-8")
    assert text.strip()
    assert "in_range: 3" in text
    assert "out_of_range: 0" in text


def test_emit_classifies_out_of_range_with_octave_shift(tmp_path):
    # Arrange: guitar6 音域下限(40)未満の低音(midi=20)は音域外。
    ctx = EmitContext(
        notes=[_note(20), _note(60)],
        bpm=100.0,
        title="テスト",
        params={"name": "guitar6"},
    )
    out_path = tmp_path / "profile.txt"

    # Act
    profile_emitter.emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "in_range: 1" in text
    assert "out_of_range: 1" in text
    assert "octave_shift_suggested" in text
    assert profile_emitter.KEY == "profile"
