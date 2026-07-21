"""drums エミッタのスモークテスト(#109 B-2 結線検証)。

detect_drums を実採譜フロー(EmitContext→emit)へ結線したことを、
音声入力から非空レポートが出ることで確認する。AAA形式。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import drums as drums_emitter
from earpipe.services.emitters.base import EmitContext


def test_drums_emitter_writes_nonempty_report(simple_wav, tmp_path):
    # Arrange
    wav_path, _melody, bpm = simple_wav
    ctx = EmitContext(
        notes=[QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9)],
        bpm=float(bpm),
        title="drums-smoke",
        audio_path=wav_path,
    )
    out_path = tmp_path / f"out.{drums_emitter.EXT}"

    # Act
    result = drums_emitter.emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    body = out_path.read_text(encoding="utf-8")
    assert body.strip()  # 非空
    assert "hit_count:" in body
    assert "kit_summary:" in body


def test_drums_emitter_declares_audio_contract():
    # Arrange / Act / Assert
    assert drums_emitter.KEY == "drums"
    assert drums_emitter.NEEDS_AUDIO is True
    assert drums_emitter.NEEDS_MUSICXML is False
