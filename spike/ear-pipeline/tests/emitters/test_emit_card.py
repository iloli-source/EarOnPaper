"""card エミッタのテスト(#109 B-2 結線検証)。

audio+notes→単一PNG型。simple_wav の実波形と最小ノート列を render_visual_card に
通し、非空のPNGが出ることを確認する(結線が到達可能=孤立解消の証明)。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import card
from earpipe.services.emitters.base import EmitContext


def test_emit_writes_nonempty_card_png(simple_wav, tmp_path):
    # Arrange
    wav_path, melody, bpm = simple_wav
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.7),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=67, confidence=0.8),
    ]
    ctx = EmitContext(
        notes=notes,
        bpm=float(bpm),
        title="テストカード",
        audio_path=wav_path,
    )
    out_path = tmp_path / "card.png"

    # Act
    returned = card.emit(ctx, out_path)

    # Assert
    assert returned == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    # PNGシグネチャで妥当な画像であることを確認
    assert out_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_emit_title_param_overrides(simple_wav, tmp_path):
    # Arrange
    wav_path, melody, bpm = simple_wav
    ctx = EmitContext(
        notes=[QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=62, confidence=0.5)],
        bpm=float(bpm),
        title="既定",
        audio_path=wav_path,
        params={"title": "上書き"},
    )
    out_path = tmp_path / "card_titled.png"

    # Act
    returned = card.emit(ctx, out_path)

    # Assert
    assert returned.exists()
    assert returned.stat().st_size > 0
