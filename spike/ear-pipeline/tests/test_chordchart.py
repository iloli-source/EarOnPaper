"""コード譜専用ビュー(chordchart.py)のテスト(#123)。

コードネーム＋押さえ図＋メロディ音名行のレイアウトが、入力の和音進行と
旋律を正しく描画すること、および妥当なPDFを書き出すことを検証する。
"""

from __future__ import annotations

from pathlib import Path

import pypdf

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import estimate_chords
from earpipe.services.notate.chordchart import (
    _render_chordchart_pages,
    render_chordchart_pdf,
)


def _progression() -> list[QuantizedNote]:
    # C→F→G→C 各4拍・3音同時(明確な和音進行 + 最高音が旋律)
    prog = {0.0: (60, 64, 67), 4.0: (65, 69, 72), 8.0: (67, 71, 74), 12.0: (60, 64, 67)}
    return [
        QuantizedNote(start_beats=sb, dur_beats=4.0, midi=m, confidence=0.9)
        for sb, ms in prog.items()
        for m in ms
    ]


def test_svg_has_chord_names_and_diagrams():
    # 描画ゲート: 出力SVGにコード名(C/F/G)と押さえ図(rect/circle)が載る
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    svg = " ".join(_render_chordchart_pages(notes, chords, 120.0, title="CC"))
    for name in ("C", "F", "G"):
        assert f">{name}<" in svg, f"コード名 {name} が描画されていない"
    # 押さえ図が実在(SVGにフレット矩形/押弦円が含まれる)
    assert svg.count("<circle") >= 3  # 押弦点
    assert "<rect" in svg


def test_svg_has_melody_note_names():
    # メロディ行に旋律(各拍の最高音)の音名が載る。C E G C の最高音 = G5,C6,D6,G5相当
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    svg = " ".join(_render_chordchart_pages(notes, chords, 120.0, title="CC"))
    # 各オンセット最高音: 67(G4),72(C5),74(D5),67(G4) → 音名 G/C/D が現れる
    for name in ("G4", "C5", "D5"):
        assert name in svg, f"メロディ音名 {name} が描画されていない"


def test_render_chordchart_pdf_valid(tmp_path: Path):
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    out = tmp_path / "chordchart.pdf"
    result = render_chordchart_pdf(notes, chords, 120.0, out, title="コード譜テスト")
    assert result == out
    assert out.exists() and out.stat().st_size > 0
    assert out.read_bytes().startswith(b"%PDF")
    assert len(pypdf.PdfReader(str(out)).pages) >= 1


def test_empty_notes_still_makes_pdf(tmp_path: Path):
    out = tmp_path / "empty.pdf"
    render_chordchart_pdf([], [], 120.0, out, title="empty")
    assert out.exists() and out.stat().st_size > 0
