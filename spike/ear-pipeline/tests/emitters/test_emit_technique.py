"""technique エミッタのスモーク: 音声→奏法検出レポートを非空で出す。

detect_techniques(耳層)への結線を検証する。合成純音では奏法が検出されない
ことも正常(module の正直な限界)。ここでは「例外なく非空レポートを書く」ことと
モジュール契約(KEY/EXT/NEEDS_*)を保証する。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.technique import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _notes() -> list[QuantizedNote]:
    """simple_wav(BPM120)の先頭数音に対応する最小ノート。"""
    specs = [
        (60, 0.0, 1.0),
        (62, 1.0, 1.0),
        (64, 2.0, 0.5),
    ]
    return [
        QuantizedNote(
            start_beats=s,
            dur_beats=d,
            midi=m,
            confidence=0.9,
        )
        for m, s, d in specs
    ]


def test_module_contract():
    # Arrange / Act / Assert
    assert KEY == "technique"
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
    out_path = tmp_path / "technique.txt"

    # Act
    result = emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert len(text) > 0
    assert "technique_count:" in text
    assert "# 奏法検出レポート (F-078)" in text
