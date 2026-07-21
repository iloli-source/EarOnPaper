"""diagnose エミッタのテスト(#109 B-2 結線検証)。

「rating: が書いてある」だけでは診断が実際に走ったか分からない。合成波形の既知の性質
(クリップしていない=clipping_rate が小さい)を使い、rating が正当な値域で、各指標が
妥当な範囲の数値であることを検証する(F-002)。AAA形式。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import diagnose
from earpipe.services.emitters.base import EmitContext


def _kv(text: str, key: str) -> str:
    return next(l for l in text.splitlines() if l.startswith(f"{key}:")).split(":", 1)[1].strip()


def test_diagnose_reports_valid_rating_and_metrics(simple_wav, tmp_path):
    # Arrange: simple_wav はクリップしていない合成波形
    audio_path, _melody, bpm = simple_wav
    ctx = EmitContext(
        notes=[QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0)],
        bpm=float(bpm),
        title="test",
        audio_path=audio_path,
    )
    out_path = tmp_path / f"report.{diagnose.EXT}"

    # Act
    diagnose.emit(ctx, out_path)

    # Assert: rating は正当な3値のいずれか、指標は妥当な数値
    text = out_path.read_text(encoding="utf-8")
    assert _kv(text, "rating") in {"green", "yellow", "red"}, f"不正な rating: {_kv(text, 'rating')}"
    clip = float(_kv(text, "clipping_rate"))
    assert 0.0 <= clip <= 1.0
    assert clip < 0.5, f"クリップしていない合成波形なのに clipping_rate が高い: {clip}"
    float(_kv(text, "snr_db"))  # 数値としてパースできる(NaN/文字列でない)
    assert float(_kv(text, "band_limit_hz")) > 0


def test_diagnose_declares_audio_contract():
    assert diagnose.KEY == "diagnose"
    assert diagnose.NEEDS_AUDIO is True
