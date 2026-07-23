"""confview エミッタ(信頼度ハイライト＋波形の解析ビュー・#121)のテスト。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import confview, emitter_keys
from earpipe.services.emitters.base import EmitContext


def _wav(tmp_path: Path) -> Path:
    sr = 22050
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    y = (0.3 * np.sin(2 * np.pi * 440 * t)).astype("float32")
    p = tmp_path / "a.wav"
    sf.write(str(p), y, sr)
    return p


def test_confview_registered():
    assert "confview" in emitter_keys()
    assert confview.KEY == "confview"
    assert confview.EXT == "pdf"
    assert confview.NEEDS_AUDIO is True


def test_confview_emits_valid_pdf(tmp_path: Path):
    wav = _wav(tmp_path)
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.95),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.30),
    ]
    out = tmp_path / "conf.pdf"
    result = confview.emit(
        EmitContext(notes=notes, bpm=120.0, title="解析", audio_path=wav), out
    )
    assert result == out
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 0
