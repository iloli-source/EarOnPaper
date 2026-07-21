"""instrument エミッタのテスト(#109 B-2 結線検証)。

audio-in→テキストレポート型。simple_wav フィクスチャの実波形を classify_instrument
に通し、非空のレポートが出ることを確認する(結線が到達可能=孤立解消の証明)。
"""

from __future__ import annotations


from earpipe.services.emitters import instrument
from earpipe.services.emitters.base import EmitContext


def test_emit_writes_nonempty_instrument_report(simple_wav, tmp_path):
    # Arrange
    wav_path, melody, bpm = simple_wav
    ctx = EmitContext(
        notes=[],
        bpm=float(bpm),
        title="test",
        audio_path=wav_path,
    )
    out_path = tmp_path / "instrument.txt"

    # Act
    returned = instrument.emit(ctx, out_path)

    # Assert: label は既知6値のいずれか、confidence は 0-1、特徴が実際に計算されている
    assert returned == out_path
    text = out_path.read_text(encoding="utf-8")
    label = next(l for l in text.splitlines() if l.startswith("label:")).split(":", 1)[1].strip()
    assert label in {
        "vocal_like", "guitar_string_like", "bass_like",
        "percussive", "keyboard_like", "unknown",
    }, f"未知の label: {label}"
    conf = float(next(l for l in text.splitlines() if l.startswith("confidence:")).split(":", 1)[1])
    assert 0.0 <= conf <= 1.0
    feat_header = next(l for l in text.splitlines() if l.startswith("features ("))
    assert not feat_header.startswith("features (0)"), "特徴が空=分類が実質走っていない"


def test_emit_seconds_param_truncates(simple_wav, tmp_path):
    # Arrange
    wav_path, melody, bpm = simple_wav
    ctx = EmitContext(
        notes=[],
        bpm=float(bpm),
        title="test",
        audio_path=wav_path,
        params={"seconds": "0.5"},
    )
    out_path = tmp_path / "instrument_short.txt"

    # Act
    returned = instrument.emit(ctx, out_path)

    # Assert
    assert returned.exists()
    assert returned.read_text(encoding="utf-8").strip() != ""
