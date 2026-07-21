"""test: voices エミッタ(F-019 声部分離・#109 B-2 結線)。"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import voices
from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.multivoice import separate_voices


def test_separation_puts_skyline_top_and_preserves_all_notes():
    """声部分離の正しさ: 上声(voices[0])が各時刻の最高音、かつ全音符が保存される。

    パート数(>=2)だけでは分離の正しさを保証できない。三和音{60,64,67}を分離し、
    上声に最高音67、下声に残り、合計音数が保存されることを検証する。
    """
    # Arrange: 同時発音の三和音
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=60, confidence=0.9),
    ]
    # Act
    result = separate_voices(notes, max_voices=3)
    # Assert: 2声部以上、上声は最高音67(skyline)、全3音が保存
    assert len(result) >= 2
    assert max(n.midi for n in result[0]) == 67, "上声(voices[0])が最高音になっていない"
    all_midis = sorted(n.midi for voice in result for n in voice)
    assert all_midis == [60, 64, 67], f"音符が欠落/重複: {all_midis}"


def _ctx(notes, **params):
    return EmitContext(
        notes=notes,
        bpm=120.0,
        title="test voices",
        params={k: str(v) for k, v in params.items()},
    )


def test_module_contract():
    # Arrange / Act / Assert
    assert voices.KEY == "voices"
    assert voices.EXT == "musicxml"
    assert voices.NEEDS_MUSICXML is False
    assert voices.NEEDS_AUDIO is False


def test_emit_writes_nonempty_musicxml(tmp_path: Path):
    # Arrange: 三和音を含む多声部入力(声部分離が働く)
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=72, confidence=0.8),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=69, confidence=0.8),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=65, confidence=0.8),
    ]
    ctx = _ctx(notes)
    out = tmp_path / "voices.musicxml"

    # Act
    result = voices.emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "score-partwise" in text


def test_emit_produces_multiple_parts(tmp_path: Path):
    # Arrange: 明確に分離可能な三和音の連続
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=60, confidence=0.9),
    ]
    ctx = _ctx(notes, max_voices=3)
    out = tmp_path / "multi.musicxml"

    # Act
    voices.emit(ctx, out)

    # Assert: 複数パート(声部)が MusicXML に現れる
    text = out.read_text(encoding="utf-8")
    assert text.count("<score-part ") >= 2


def test_emit_handles_empty_notes(tmp_path: Path):
    # Arrange
    ctx = _ctx([])
    out = tmp_path / "empty.musicxml"

    # Act
    voices.emit(ctx, out)

    # Assert: 空入力でも非空ファイル(全休符1パート)を出す
    assert out.read_text(encoding="utf-8").strip() != ""
