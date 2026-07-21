"""convert エミッタのテスト(F-037/Issue #85 結線スモーク)。

staff->jianpu / staff->tab / tab->staff の3変換を1レポートに束ねる convert
エミッタが、実ノートから非空ファイルを生成することを検証する。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.convert import EXT, KEY, emit


def test_key_and_ext_are_wired():
    # Arrange / Act / Assert: レジストリ発見に必要な定数が担当KEYで定義済み。
    assert KEY == "convert"
    assert EXT == "txt"


def test_conversions_are_correct(tmp_path: Path):
    """節見出しだけでなく変換の中身が正しいことを検証する。

    C長調の C(60)/E(64)/G(67) を入力し、簡譜が度数 1 3 5、TAB→staff 往復で
    元の midi 3音が厳密復元されることを固定する(往復忠実性)。
    """
    # Arrange: C長調の主要三和音を分散
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=1.0),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=67, confidence=1.0),
    ]
    ctx = EmitContext(notes=notes, bpm=120.0, title="CEG")
    out_path = tmp_path / f"convert.{EXT}"

    # Act
    emit(ctx, out_path)

    # Assert
    lines = out_path.read_text(encoding="utf-8").splitlines()
    # 簡譜: C長調で C/E/G = 度数 1/3/5
    jianpu_idx = lines.index("## 簡譜 (staff->jianpu, 不可逆)")
    assert lines[jianpu_idx + 1].strip() == "1 3 5", f"簡譜の度数が誤り: {lines[jianpu_idx + 1]!r}"
    # 往復復元: 元の3音 midi が厳密に復元される(TAB→staff の忠実性)
    restored = sorted(
        int(l.split("midi=")[1].split()[0]) for l in lines if l.strip().startswith("midi=")
    )
    assert restored == [60, 64, 67], f"往復復元が元音高と不一致: {restored}"


def test_emit_empty_notes_still_writes(tmp_path: Path):
    # Arrange: 空入力でも例外を出さず非空レポートを書く(縮退の堅牢性)。
    ctx = EmitContext(notes=[], bpm=100.0, title="空")
    out_path = tmp_path / f"convert.{EXT}"

    # Act
    emit(ctx, out_path)

    # Assert
    assert out_path.read_text(encoding="utf-8").strip() != ""
