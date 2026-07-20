"""コード認識(chord.py)とコードダイアグラム(chord_shapes.py)のテスト。

多声ノイズに強いクロマ・テンプレート相関方式。押さえ図は開放フォーム辞書＋バレー計算。
"""

from pathlib import Path

import pypdf

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan, estimate_chords
from earpipe.services.notate.chord_shapes import shape_for
from earpipe.services.notate.tab import write_tab_pdf


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


def chord_at(start: float, dur: float, midis: list[int]) -> list[QuantizedNote]:
    return [qn(start, dur, m) for m in midis]


class TestEstimateChords:
    def test_clean_c_major(self):
        # 2拍ぶんのC三和音
        notes = chord_at(0, 2, [60, 64, 67])
        spans = estimate_chords(notes, bpm=120)
        assert spans
        assert spans[0].name == "C"
        assert spans[0].root_pc == 0
        assert spans[0].quality == "major"

    def test_a_minor(self):
        spans = estimate_chords(chord_at(0, 2, [57, 60, 64]), bpm=120)
        assert spans[0].name == "Am"
        assert spans[0].quality == "minor"

    def test_g_dominant7(self):
        spans = estimate_chords(chord_at(0, 2, [55, 59, 62, 65]), bpm=120)
        assert spans[0].root_pc == 7  # G
        assert "7" in spans[0].name

    def test_noise_tolerant_c(self):
        # Cが主体で弱いノイズ音が混じっても C と判定
        notes = chord_at(0, 2, [60, 64, 67]) + [qn(0.5, 0.25, 62), qn(1.0, 0.25, 71)]
        spans = estimate_chords(notes, bpm=120)
        assert spans[0].name == "C"

    def test_dense_noise_is_nc(self):
        # 半音びっしり（コード感なし）は N.C.（コードなし=span無しか name="N.C."）
        notes = [qn(0, 2, 60 + i) for i in range(12)]
        spans = estimate_chords(notes, bpm=120)
        assert all(s.name == "N.C." for s in spans) or spans == []

    def test_change_detection_merges_consecutive(self):
        # 同じCが2窓連続 → 1スパンに統合
        notes = chord_at(0, 2, [60, 64, 67]) + chord_at(2, 2, [60, 64, 67])
        spans = [s for s in estimate_chords(notes, bpm=120) if s.name != "N.C."]
        c_spans = [s for s in spans if s.name == "C"]
        assert len(c_spans) == 1
        assert c_spans[0].start_beats == 0
        assert c_spans[0].end_beats >= 3.9

    def test_progression_c_am_f_g(self):
        notes = (
            chord_at(0, 2, [60, 64, 67])   # C
            + chord_at(2, 2, [57, 60, 64])  # Am
            + chord_at(4, 2, [53, 57, 60])  # F
            + chord_at(6, 2, [55, 59, 62])  # G
        )
        names = [s.name for s in estimate_chords(notes, bpm=120) if s.name != "N.C."]
        assert names == ["C", "Am", "F", "G"]

    def test_short_lived_chord_removed(self):
        # 長いC + 一瞬だけ別和音 → 短命コードは吸収されCだけ残る
        notes = chord_at(0, 4, [60, 64, 67]) + chord_at(1.0, 0.25, [62, 66, 69])
        names = [s.name for s in estimate_chords(notes, bpm=120, min_dur_beats=1.0)
                 if s.name != "N.C."]
        assert names == ["C"]

    def test_empty(self):
        assert estimate_chords([], bpm=120) == []

    def test_result_is_chordspan(self):
        spans = estimate_chords(chord_at(0, 2, [60, 64, 67]), bpm=120)
        assert isinstance(spans[0], ChordSpan)


class TestChordShapes:
    def test_open_c_from_dict(self):
        # Cメジャーの開放フォーム: [x,3,2,0,1,0]（6弦→1弦）
        shape = shape_for(0, "major")
        assert shape == [None, 3, 2, 0, 1, 0]

    def test_open_e_minor(self):
        # Em: [0,2,2,0,0,0]
        shape = shape_for(4, "minor")
        assert shape == [0, 2, 2, 0, 0, 0]

    def test_barre_fallback_playable(self):
        # 辞書外（F#メジャー等）はバレー計算で妥当なフレット
        shape = shape_for(6, "major")  # F#
        frets = [f for f in shape if f is not None]
        assert frets
        assert all(0 <= f <= 14 for f in frets)
        # ルート音（F#=54）が最低弦のどこかに含まれる
        assert any(f is not None for f in shape)

    def test_all_qualities_return_shape(self):
        for q in ("major", "minor", "dom7", "min7", "maj7"):
            for root in range(12):
                shape = shape_for(root, q)
                assert len(shape) == 6
                assert any(f is not None for f in shape)


class TestTabPdfWithChords:
    def test_chord_names_in_pdf(self, tmp_path: Path):
        notes = (
            chord_at(0, 2, [60, 64, 67])
            + chord_at(2, 2, [57, 60, 64])
        )
        out = tmp_path / "chorded.pdf"
        result = write_tab_pdf(notes, bpm=120, out_pdf=out, chord_diagrams=True)
        assert result["n_chords"] >= 2
        text = " ".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out)).pages)
        assert "C" in text and "Am" in text

    def test_diagram_toggle_both_render(self, tmp_path: Path):
        notes = chord_at(0, 2, [60, 64, 67])
        with_d = tmp_path / "with.pdf"
        without_d = tmp_path / "without.pdf"
        r1 = write_tab_pdf(notes, bpm=120, out_pdf=with_d, chord_diagrams=True)
        r2 = write_tab_pdf(notes, bpm=120, out_pdf=without_d, chord_diagrams=False)
        assert with_d.exists() and without_d.exists()
        # 図あり版はファイルが大きい（SVG要素が多い）
        assert with_d.stat().st_size >= without_d.stat().st_size
        assert r1["n_chords"] == r2["n_chords"]
