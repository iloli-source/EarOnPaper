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

    # Assert: 切り出し長が [start, end) = 1.5秒 に一致する。非空だけでは crop の正しさを
    # 保証できないため、名前通り「指定区間を切り出した」ことを実測で固定する。
    assert result == out_path
    data, sr = sf.read(str(out_path))
    duration = len(data) / sr
    assert abs(duration - 1.5) < 0.05, f"切り出し長が想定と違う: {duration:.3f}s (期待 1.5s)"
