"""cleanse エミッタのテスト(F-086 結線スモーク)。

調外音を含むメロディで、候補レポートが非空ファイルとして出力されることを確認する。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters import cleanse


def _c_major_with_outlier() -> list[QuantizedNote]:
    """ハ長調の走句に強拍の調外音 C#(midi=61) を1つ混ぜる。"""
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=61, confidence=0.8),  # 調外 C#
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=64, confidence=0.9),
        QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=67, confidence=0.9),
    ]


def test_emit_writes_non_empty_report(tmp_path):
    # Arrange
    notes = _c_major_with_outlier()
    ctx = EmitContext(notes=notes, bpm=120.0, title="cleanse-test")
    out_path = tmp_path / "cleanse.txt"

    # Act
    result = cleanse.emit(ctx, out_path)

    # Assert: 調外音がちょうど1件検出され、その C#(61) が調内音へスナップされる(中身まで検証)
    assert result == out_path
    text = out_path.read_text(encoding="utf-8")
    assert "out_of_scale: 1" in text, "調外音の検出数が想定と違う"
    # C#(61) の補正候補行があり、最近傍の調内音(60 or 62)へスナップされている
    cand = next(l for l in text.splitlines() if l.startswith("[") and "midi 61" in l)
    assert "-> 60" in cand or "-> 62" in cand, f"C# のスナップ先が調内音でない: {cand}"


def test_emit_apply_true_records_applied(tmp_path):
    # Arrange
    notes = _c_major_with_outlier()
    ctx = EmitContext(
        notes=notes, bpm=120.0, title="cleanse-apply", params={"apply": "true"}
    )
    out_path = tmp_path / "cleanse_apply.txt"

    # Act
    cleanse.emit(ctx, out_path)

    # Assert
    text = out_path.read_text(encoding="utf-8")
    assert "applied:" in text
