"""hints エミッタの結線スモークテスト(#109 B-2)。

apply_hints / AnalysisHints が emit 経由で実採譜フローに到達し、非空の
ヒント適用レポートを出力することを検証する(AAA形式)。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.hints import KEY, NEEDS_AUDIO, NEEDS_MUSICXML, emit


def _notes() -> list[QuantizedNote]:
    """C-dur 風の最小ノート列(estimate_key が動くだけの材料)。"""
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=1.0),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=67, confidence=1.0),
        QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=60, confidence=1.0),
    ]


def test_module_contract():
    # Arrange / Act は宣言のみ
    # Assert: エミッタ契約(key/入力要件)
    assert KEY == "hints"
    assert NEEDS_MUSICXML is False
    assert NEEDS_AUDIO is False


def test_emit_writes_nonempty_report(tmp_path):
    # Arrange
    ctx = EmitContext(notes=_notes(), bpm=120.0, title="テスト曲")
    out = tmp_path / "hints.txt"

    # Act
    result = emit(ctx, out)

    # Assert
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.strip()  # 非空
    # 既定行(自動推定)がすべて含まれる
    for name in ("tempo_bpm", "key_tonic_pc", "time_sig", "tuning_offset_cents", "capo"):
        assert name in text
    # ヒント未指定なので上書き行(末尾 " *")は1つも無い(既定維持)
    assert not any(line.endswith(" *") for line in text.splitlines())


def test_emit_applies_hints_and_marks_overrides(tmp_path):
    # Arrange: テンポと拍子とカポをヒント指定
    ctx = EmitContext(
        notes=_notes(),
        bpm=120.0,
        title="ヒント曲",
        params={"tempo_bpm": "140", "time_sig": "7/8", "capo": "2"},
    )
    out = tmp_path / "hints.txt"

    # Act
    emit(ctx, out)

    # Assert: 指定した項目が適用後の値になり * 印が付く
    text = out.read_text(encoding="utf-8")
    assert "-> 140.0 *" in text
    assert "(7, 8) *" in text
    assert "-> 2 *" in text
