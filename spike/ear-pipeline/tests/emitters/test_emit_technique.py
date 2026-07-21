"""technique エミッタのテスト(F-078 結線検証)。

「非空レポートが出る/technique_count: が在る」だけでは検出0でも通ってしまう(偽成功)。
そこで **ビブラート音**(周波数を±40centで5.5Hz揺らした合成音)を与え、実際に奏法が
1件以上検出され kind=vibrato が報告されることを検証する。奏法検出は原理的に曖昧だが、
明確なビブラート gesture は決定的に拾えることを利用する。
"""

from __future__ import annotations

import numpy as np
import soundfile as sf

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.technique import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _vibrato_wav(path, sr=22050, dur=1.5, base_hz=440.0, depth_cents=40.0, rate_hz=5.5):
    """base_hz を ±depth_cents で rate_hz 揺らしたビブラート音を書き出す。"""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    cents = depth_cents * np.sin(2 * np.pi * rate_hz * t)
    freq = base_hz * 2 ** (cents / 1200.0)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    sf.write(str(path), (0.4 * np.sin(phase)).astype("float32"), sr)
    return path


def test_module_contract():
    assert KEY == "technique"
    assert EXT == "txt"
    assert NEEDS_AUDIO is True
    assert NEEDS_MUSICXML is False


def test_emit_detects_vibrato(tmp_path):
    # Arrange: 明確なビブラート音(検出0では落ちる)
    wav = _vibrato_wav(tmp_path / "vib.wav")
    ctx = EmitContext(
        notes=[QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=69, confidence=0.9)],
        bpm=120.0,
        title="test",
        audio_path=wav,
    )
    out_path = tmp_path / "technique.txt"

    # Act
    emit(ctx, out_path)

    # Assert: 奏法が実際に1件以上検出され、vibrato が報告されている
    lines = out_path.read_text(encoding="utf-8").splitlines()
    count = int(next(l for l in lines if l.startswith("technique_count:")).split(":")[1])
    assert count >= 1, f"ビブラート音なのに奏法が検出されていない(偽成功): \n{lines}"
    kinds = {l.split("\t")[1] for l in lines if "\t" in l and l.split("\t")[0].isdigit()}
    assert "vibrato" in kinds, f"vibrato が検出されていない: {kinds}"
