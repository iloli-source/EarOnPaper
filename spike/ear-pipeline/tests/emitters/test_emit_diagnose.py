"""diagnose エミッタのテスト(#109 B-2 結線検証)。

simple_wav フィクスチャの実波形を diagnose_audio 経由で診断し、
非空のテキストレポートが出ることを確認する(孤立解消の到達性検証)。
"""

from __future__ import annotations


from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import diagnose
from earpipe.services.emitters.base import EmitContext


def test_emit_writes_nonempty_diagnosis_report(simple_wav, tmp_path):
    # Arrange
    audio_path, _melody, bpm = simple_wav
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0)]
    ctx = EmitContext(
        notes=notes,
        bpm=float(bpm),
        title="test",
        audio_path=audio_path,
    )
    out_path = tmp_path / f"report.{diagnose.EXT}"

    # Act
    result = diagnose.emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert text.strip() != ""
    assert "rating:" in text
    assert diagnose.KEY == "diagnose"
    assert diagnose.NEEDS_AUDIO is True
