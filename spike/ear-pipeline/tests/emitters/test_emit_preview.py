"""preview エミッタのスモークテスト(#109 B-2 結線検証)。

notes → 一時MIDI → render_preview で非空のプレビュー音声が書けることを検証する。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import preview as preview_emitter
from earpipe.services.emitters.base import EmitContext


def test_preview_emit_writes_nonempty_audio(tmp_path: Path) -> None:
    # Arrange: 最小の2音メロディ(実秒未指定→bpm格子秒へフォールバック)。
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.8),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="preview-smoke")
    out_path = tmp_path / "preview.wav"

    # Act
    written = preview_emitter.emit(ctx, out_path)

    # Assert: 実在する非空の音声ファイルが返る。
    assert written.exists()
    assert written.stat().st_size > 0


def _read_wav(path: Path):
    import numpy as np
    import soundfile as sf

    y, sr = sf.read(str(path))
    if y.ndim > 1:
        y = y.mean(axis=1)
    return np.asarray(y), sr


def test_preview_audio_is_not_silent(tmp_path: Path) -> None:
    # #115: 「非空ファイル」ではなく、実際に音が鳴っている(無音でない)ことを検証。
    import numpy as np

    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=1.0),
    ]
    written = preview_emitter.emit(
        EmitContext(notes=notes, bpm=120.0, title="notsilent"), tmp_path / "a.wav")
    y, _sr = _read_wav(written)
    assert float(np.max(np.abs(y))) > 0.1  # ピークが立つ(ゼロ埋めの無音でない)
    assert float(np.sqrt(np.mean(y ** 2))) > 1e-3  # RMSも有意


def test_preview_duration_scales_with_note_count(tmp_path: Path) -> None:
    # #115: 出力長が入力(音数)に相関する。長い旋律ほど長い音声になる。
    def dur(n: int) -> float:
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60 + i, confidence=1.0)
            for i in range(n)
        ]
        w = preview_emitter.emit(
            EmitContext(notes=notes, bpm=120.0, title=f"n{n}"), tmp_path / f"n{n}.wav")
        y, sr = _read_wav(w)
        return len(y) / sr

    assert dur(6) > dur(2)


def test_preview_respects_sr_in_output(tmp_path: Path) -> None:
    # #115: sr パラメータが「非空」だけでなく実際の出力サンプルレートへ反映される。
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=67, confidence=1.0)]
    written = preview_emitter.emit(
        EmitContext(notes=notes, bpm=100.0, title="sr", params={"sr": "16000"}),
        tmp_path / "sr.wav")
    _y, sr = _read_wav(written)
    assert sr == 16000


def test_preview_emit_respects_sr_param(tmp_path: Path) -> None:
    # Arrange: sr パラメータを明示指定しても非空ファイルが出ること。
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=67, confidence=1.0)]
    ctx = EmitContext(
        notes=notes, bpm=100.0, title="preview-sr", params={"sr": "16000"}
    )
    out_path = tmp_path / "preview_sr.wav"

    # Act
    written = preview_emitter.emit(ctx, out_path)

    # Assert
    assert written.exists()
    assert written.stat().st_size > 0
