"""region エミッタのスモークテスト(#109 B-2)。

crop_region が実採譜フローへ結線され、区間切り出し WAV が非空で出ることを確認。
"""

from __future__ import annotations

import soundfile as sf

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import region
from earpipe.services.emitters.base import EmitContext


def test_emit_writes_nonempty_region_wav(simple_wav, tmp_path):
    # Arrange
    audio_path, _melody, bpm = simple_wav
    ctx = EmitContext(
        notes=[QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0)],
        bpm=float(bpm),
        title="test",
        audio_path=audio_path,
        params={"start": "0.5", "end": "2.0"},
    )
    out_path = tmp_path / f"region.{region.EXT}"

    # Act
    result = region.emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    data, sr = sf.read(str(out_path))
    assert len(data) > 0
    assert sr > 0
