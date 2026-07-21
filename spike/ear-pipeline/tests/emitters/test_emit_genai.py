"""genai エミッタのテスト(F-092/Issue #99・#109 B-2 結線)。

genai_preprocess / GENAI_PRESET の孤立解消。simple_wav フィクスチャ(音声必須)を
使い、emit が非空の診断テキストを出しプリセット値と前処理指標を含むことを検証する。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import genai
from earpipe.services.emitters.base import EmitContext


def _ctx(audio_path):
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.9),
    ]
    return EmitContext(
        notes=notes,
        bpm=120.0,
        title="genai-test",
        audio_path=audio_path,
    )


def test_emit_writes_nonempty_report(simple_wav, tmp_path):
    # Arrange
    audio_path, _melody, _bpm = simple_wav
    out_path = tmp_path / "genai.txt"

    # Act
    result = genai.emit(_ctx(audio_path), out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_emit_report_contains_preset_and_metrics(simple_wav, tmp_path):
    # Arrange
    audio_path, _melody, _bpm = simple_wav
    out_path = tmp_path / "genai.txt"

    # Act
    genai.emit(_ctx(audio_path), out_path)
    text = out_path.read_text(encoding="utf-8")

    # Assert: プリセット値と前処理指標が結線されて出力される
    assert "detect_min_conf: 0.6" in text
    assert "grid_per_beat: 4" in text
    assert "high_freq_ratio(after/before)" in text
    assert "peak_after" in text


def test_emitter_contract(simple_wav):
    # Arrange / Act / Assert: モジュールレベル契約
    assert genai.KEY == "genai"
    assert genai.EXT == "txt"
    assert genai.NEEDS_AUDIO is True
    assert genai.NEEDS_MUSICXML is False
