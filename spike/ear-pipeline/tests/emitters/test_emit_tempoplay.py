"""tempoplay エミッタの結線スモークテスト(F-059/#109 B-2)。

audio-in→slow-WAV-out が非空ファイルを出すことを確認する。tempo_playback の
time_stretch / loop_region / is_artifact_prone への到達(孤立解消)を担保する。
"""

from __future__ import annotations

import soundfile as sf

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import tempoplay
from earpipe.services.emitters.base import EmitContext


def _ctx(audio_path, **params):
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0)]
    return EmitContext(
        notes=notes,
        bpm=120.0,
        title="test",
        audio_path=audio_path,
        params={k: str(v) for k, v in params.items()},
    )


def test_emits_nonempty_slow_wav(simple_wav, tmp_path):
    # Arrange
    audio_path, _melody, _bpm = simple_wav
    out_path = tmp_path / "slow.wav"
    ctx = _ctx(audio_path, rate=0.5)

    # Act
    result = tempoplay.emit(ctx, out_path)

    # Assert
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_slow_output_is_longer_than_source(simple_wav, tmp_path):
    # Arrange
    audio_path, _melody, _bpm = simple_wav
    src, sr = sf.read(str(audio_path))
    out_path = tmp_path / "slow.wav"
    ctx = _ctx(audio_path, rate=0.5)

    # Act
    tempoplay.emit(ctx, out_path)

    # Assert: 半速なら概ね元より長い(ピッチ維持タイムストレッチの効果)
    out, out_sr = sf.read(str(out_path))
    assert out_sr == sr
    assert out.shape[0] > src.shape[0]


def test_loop_region_path_emits_nonempty(simple_wav, tmp_path):
    # Arrange: A-B ループ経路(loop_region への到達)を通す
    audio_path, _melody, _bpm = simple_wav
    out_path = tmp_path / "loop.wav"
    ctx = _ctx(audio_path, rate=1.0, start=0.0, end=0.5, times=3)

    # Act
    tempoplay.emit(ctx, out_path)

    # Assert
    assert out_path.stat().st_size > 0


def test_module_contract_constants():
    # Arrange / Act / Assert: レジストリ自動発見に必要な公開契約
    assert tempoplay.KEY == "tempoplay"
    assert tempoplay.EXT == "wav"
    assert tempoplay.NEEDS_AUDIO is True
    assert tempoplay.NEEDS_MUSICXML is False
