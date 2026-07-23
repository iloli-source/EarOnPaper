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
    # #115: 署名だけでなく実寸法を検証。Twitter Card準拠 1200x630 の横長PNG。
    width, height = _png_dimensions(out_path)
    assert (width, height) == (1200, 630)
    assert width > height  # 横長カード


def _png_dimensions(path) -> tuple[int, int]:
    # PNG IHDR(署名8byte + 長さ4 + "IHDR"4 の直後に width,height の big-endian uint32)
    import struct

    data = path.read_bytes()
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_emit_card_content_changes_with_input(simple_wav, tmp_path):
    # #115: タイトル/ノートが変われば描画内容(PNGバイト)も変わる(固定画像の偽成功でない)。
    wav_path, _melody, bpm = simple_wav
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9)]

    def render(title: str) -> bytes:
        out = tmp_path / f"card_{title}.png"
        card.emit(
            EmitContext(notes=notes, bpm=float(bpm), title=title, audio_path=wav_path),
            out,
        )
        return out.read_bytes()

    a = render("アルファ")
    b = render("ベータ")
    assert a != b  # タイトルが実際に描画へ反映される


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
