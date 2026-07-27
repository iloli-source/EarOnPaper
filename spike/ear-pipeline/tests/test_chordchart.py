"""コード譜専用ビュー(chordchart.py)のテスト(#123, 可読化改修 #150)。

冒頭legend(ユニークコードの押さえ図)＋小節グリッド(コードネーム大書き)の
レイアウトが、入力の和音進行を正しく描画すること、密集入力でも1小節あたり
最大2スロットに整理されること、および妥当なPDFを書き出すことを検証する。
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


def test_no_melody_note_row():
    # 可読化改修(#150): メロディ音名行は廃止(旋律は五線譜/MusicXML側が担う)。
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    svg = " ".join(_render_chordchart_pages(notes, chords, 120.0, title="CC"))
    for name in ("G4", "C5", "D5"):
        assert f">{name}<" not in svg, f"廃止済みのメロディ音名 {name} が描画されている"


def test_legend_shows_each_unique_chord_once():
    # legendにはユニークコードが1回ずつ(進行 C→F→G→C なら C は1個)。
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    svg = " ".join(_render_chordchart_pages(notes, chords, 120.0, title="CC"))
    unique = {c.name for c in chords if c.name != "N.C."}
    for name in unique:
        assert svg.count(f'class="legend-name">{name}<') == 1, (
            f"legendのコード {name} が1回ちょうどでない"
        )


def test_dense_chords_capped_at_two_slots_per_measure():
    # 1拍ごとにコードが揺れる密集入力でも、グリッドは1小節最大2スロットに整理される。
    from earpipe.services.notate.chord import ChordSpan

    names = ("C", "F", "G", "Am")
    dense = [
        ChordSpan(start_beats=float(b), end_beats=float(b + 1),
                  name=names[b % 4], root_pc=(0, 5, 7, 9)[b % 4],
                  quality="major" if b % 4 < 3 else "minor")
        for b in range(8)
    ]
    svg = " ".join(_render_chordchart_pages([], dense, 120.0, title="dense"))
    n_grid_labels = svg.count('class="grid-chord"')
    assert n_grid_labels <= 2 * 2, f"2小節で最大4スロットのはずが {n_grid_labels} 個描画"


def test_diagrams_false_omits_legend():
    # ヴォーカル＆コード用途(#150): diagrams=False では押さえ図legendを描かず、
    # グリッドのコードネームだけを出す(押さえ図はギター奏者向けのオプトイン)。
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    svg = " ".join(_render_chordchart_pages(notes, chords, 120.0, title="CC", diagrams=False))
    assert 'class="legend-name"' not in svg, "diagrams=False なのに legend が描画されている"
    assert svg.count('class="grid-chord"') >= 3, "グリッドのコードネームが消えている"


def test_render_chordchart_pdf_valid(tmp_path: Path):
    notes = _progression()
    chords = estimate_chords(notes, bpm=120)
    out = tmp_path / "chordchart.pdf"
    result = render_chordchart_pdf(notes, chords, 120.0, out, title="コード譜テスト")
    assert result == out
    assert out.exists() and out.stat().st_size > 0
    assert out.read_bytes().startswith(b"%PDF")
    assert len(pypdf.PdfReader(str(out)).pages) >= 1


def test_same_chord_across_measures_elided_as_continuation():
    # 継続省略(#150の中核): 全小節が同一コードなら、コードネームは最初の1回だけ。
    from earpipe.services.notate.chord import ChordSpan

    held = [ChordSpan(start_beats=0.0, end_beats=16.0, name="C", root_pc=0, quality="major")]
    svg = " ".join(_render_chordchart_pages([], held, 120.0, title="hold"))
    assert svg.count('class="grid-chord"') == 1, "継続小節でコード名が省略されていない"


def test_all_nc_input_renders_empty_grid():
    # 全区間 N.C.(和声的に曖昧な曲): 落ちずに空グリッドのPDFになる。
    from earpipe.services.notate.chord import ChordSpan

    nc = [ChordSpan(start_beats=0.0, end_beats=32.0, name="N.C.", root_pc=-1, quality="")]
    svg = " ".join(_render_chordchart_pages([], nc, 120.0, title="nc"))
    assert 'class="grid-chord"' not in svg
    assert 'class="legend-name"' not in svg
    assert "<svg" in svg


def test_empty_notes_still_makes_pdf(tmp_path: Path):
    out = tmp_path / "empty.pdf"
    render_chordchart_pdf([], [], 120.0, out, title="empty")
    assert out.exists() and out.stat().st_size > 0
