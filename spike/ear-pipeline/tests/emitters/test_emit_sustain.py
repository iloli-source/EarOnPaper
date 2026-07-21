"""sustain エミッタのテスト(F-102 結線スモーク)。"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.sustain import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _note(start_beats, dur_beats, midi, onset_sec, offset_sec):
    return QuantizedNote(
        start_beats=start_beats,
        dur_beats=dur_beats,
        midi=midi,
        confidence=1.0,
        onset_sec=onset_sec,
        offset_sec=offset_sec,
    )


def test_module_contract():
    # Arrange / Act / Assert: エミッタ契約(結線に必要な公開定数)
    assert KEY == "sustain"
    assert EXT == "txt"
    assert NEEDS_MUSICXML is False
    assert NEEDS_AUDIO is False


def test_emit_writes_nonempty_report_with_span(tmp_path):
    # Arrange: 音1の尾(0.0-1.0s)が音2の打鍵(0.5s)を0.5s越えて残る=ペダル候補
    notes = [
        _note(0.0, 1.0, 60, onset_sec=0.0, offset_sec=1.0),
        _note(1.0, 1.0, 62, onset_sec=0.5, offset_sec=1.5),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="テスト曲")
    out = tmp_path / f"pedal.{EXT}"

    # Act
    result = emit(ctx, out)

    # Assert: 非空ファイルが書かれ、区間候補が1つ以上含まれる
    assert result == out
    text = out.read_text(encoding="utf-8")
    assert text.strip() != ""
    assert "span_count: 1" in text
    assert "layer=sound_off" in text


def test_emit_writes_nonempty_report_without_span(tmp_path):
    # Arrange: 重なりのない単一ノート → 候補ゼロでも非空レポートを出す
    notes = [_note(0.0, 1.0, 60, onset_sec=0.0, offset_sec=1.0)]
    ctx = EmitContext(notes=notes, bpm=120.0, title="単音")
    out = tmp_path / f"pedal.{EXT}"

    # Act
    result = emit(ctx, out)

    # Assert
    text = result.read_text(encoding="utf-8")
    assert text.strip() != ""
    assert "span_count: 0" in text
