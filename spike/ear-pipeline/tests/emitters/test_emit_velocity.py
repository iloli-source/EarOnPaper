"""velocity エミッタのテスト(F-016 結線検証)。

「強弱記号がどれか1つ在る」だけでは強弱推定の正しさを保証できない。**大音量の音**と
**小音量の音**を含む合成音を与え、大音量ノートの相対velocity/強弱記号が小音量ノートより
強いこと(単調性)を検証する。
"""

from __future__ import annotations

import numpy as np
import soundfile as sf

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.velocity import (
    DYNAMIC_MARKS,
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)


def _loud_then_soft_wav(path, sr=22050):
    """0.0秒に大音量、1.0秒に小音量のトーンを置いた音声を書き出す。"""
    y = np.zeros(int(sr * 1.8), dtype="float32")

    def burst(start, amp, f):
        t = np.arange(int(sr * 0.5)) / sr
        y[int(sr * start): int(sr * start) + len(t)] += (amp * np.sin(2 * np.pi * f * t)).astype("float32")

    burst(0.0, 0.8, 261.6)   # 大音量
    burst(1.0, 0.08, 329.6)  # 小音量
    sf.write(str(path), y, sr)
    return path


def test_module_contract():
    # Arrange / Act / Assert
    assert KEY == "velocity"
    assert EXT == "txt"
    assert NEEDS_AUDIO is True
    assert NEEDS_MUSICXML is False


def test_loud_note_gets_stronger_dynamic_than_soft(tmp_path):
    # Arrange: 大音量(onset 0.0)と小音量(onset 1.0)の2音
    wav = _loud_then_soft_wav(tmp_path / "ls.wav")
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0, onset_sec=0.0, offset_sec=0.5),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=64, confidence=1.0, onset_sec=1.0, offset_sec=1.5),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="test", audio_path=wav)
    out_path = tmp_path / "velocity.txt"

    # Act
    emit(ctx, out_path)

    # Assert: 大音量ノートの velocity と強弱記号が小音量ノートより強い(単調性)
    rows = [l for l in out_path.read_text(encoding="utf-8").splitlines()
            if "\t" in l and l.split("\t")[0].isdigit()]
    assert len(rows) == 2
    loud_vel, loud_mark = float(rows[0].split("\t")[3]), rows[0].split("\t")[4]
    soft_vel, soft_mark = float(rows[1].split("\t")[3]), rows[1].split("\t")[4]
    assert loud_vel > soft_vel, f"大音量なのに velocity が弱い: {loud_vel} <= {soft_vel}"
    assert DYNAMIC_MARKS.index(loud_mark) > DYNAMIC_MARKS.index(soft_mark), \
        f"強弱記号の大小が逆: 大音量={loud_mark} 小音量={soft_mark}"


def test_emit_falls_back_to_beats_when_onset_unset(simple_wav, tmp_path):
    # Arrange: onset_sec 未設定(NaN)でも bpm から秒換算して測れる
    wav_path, _melody, bpm = simple_wav
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.9),
    ]
    ctx = EmitContext(notes=notes, bpm=float(bpm), title="fallback", audio_path=wav_path)
    out_path = tmp_path / "velocity_fb.txt"

    # Act
    emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "note_count: 2" in text
