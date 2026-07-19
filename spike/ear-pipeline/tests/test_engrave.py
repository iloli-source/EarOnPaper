"""五線譜PDF出力(engrave段・Issue #41)のテスト。ADR-004: Verovio+cairosvg+pypdf。"""

from pathlib import Path

import pytest
from pypdf import PdfReader

from earpipe.pipeline import transcribe_file
from earpipe.services.notate import (
    render_svg_pages,
    svg_note_count,
    to_score,
    write_musicxml,
    write_pdf,
)
from earpipe.services.rhythm import quantize_events
from earpipe.contracts import PitchEvent


def _simple_musicxml(tmp_path: Path) -> Path:
    """既知の8音メロディからMusicXMLを作る(正解が構成的に既知)。"""
    events = [
        PitchEvent(onset=i * 0.5, offset=i * 0.5 + 0.45, midi=60 + d, confidence=0.9)
        for i, d in enumerate([0, 2, 4, 5, 7, 5, 4, 0])
    ]
    notes = quantize_events(events, bpm=120.0)
    score = to_score(notes, bpm=120.0)
    out = tmp_path / "melody.musicxml"
    write_musicxml(score, out)
    return out


class TestEngraveUnit:
    def test_svg_pages_and_note_count(self, tmp_path):
        xml = _simple_musicxml(tmp_path)
        svgs = render_svg_pages(xml)
        assert len(svgs) >= 1
        assert svg_note_count(svgs[0]) >= 8  # 8音符が描画されている

    def test_write_pdf_valid(self, tmp_path):
        xml = _simple_musicxml(tmp_path)
        out = tmp_path / "melody.pdf"
        meta = write_pdf(xml, out)
        assert out.exists()
        assert out.read_bytes()[:5] == b"%PDF-"
        reader = PdfReader(str(out))
        assert len(reader.pages) == meta["pages"] >= 1
        assert meta["notes_engraved"] >= 8

    def test_empty_score_raises(self, tmp_path):
        score = to_score([], bpm=120.0)
        xml = tmp_path / "empty.musicxml"
        write_musicxml(score, xml)
        # 空スコアは「ページ0」でも「例外」でもよいが、黙って壊れたPDFを出さないこと
        try:
            meta = write_pdf(xml, tmp_path / "empty.pdf")
            assert meta["pages"] >= 1  # verovioが空ページを出す場合は妥当なPDFであること
        except RuntimeError:
            pass  # 明示的な失敗はOK(黙殺しない)


class TestEngraveE2E:
    def test_pipeline_pdf_option(self, tmp_path, simple_wav):
        wav, _melody, _bpm = simple_wav
        out_xml = tmp_path / "out.musicxml"
        out_pdf = tmp_path / "out.pdf"
        result = transcribe_file(wav, out_musicxml=out_xml, out_pdf=out_pdf)
        assert out_pdf.exists() and out_pdf.read_bytes()[:5] == b"%PDF-"
        assert result["engrave"]["pages"] >= 1
        assert result["engrave"]["notes_engraved"] >= 1

    def test_pdf_without_musicxml_raises(self, tmp_path, simple_wav):
        wav, _melody, _bpm = simple_wav
        with pytest.raises(ValueError):
            transcribe_file(wav, out_musicxml=None, out_pdf=tmp_path / "x.pdf")


class TestIssue49Engrave:
    """Issue #49: 豆腐化対策とsvg_note_count計数修正。"""

    def _render_two_note_svg(self, tmp_path):
        import math

        from earpipe.contracts import QuantizedNote
        from earpipe.services.notate.engrave import render_svg_pages
        from earpipe.services.notate.score import to_score, write_musicxml

        nan = math.nan
        notes = [
            QuantizedNote(midi=72, start_beats=0.0, dur_beats=1.0, confidence=0.9,
                          onset_sec=nan, offset_sec=nan),
            QuantizedNote(midi=76, start_beats=1.0, dur_beats=1.0, confidence=0.9,
                          onset_sec=nan, offset_sec=nan),
        ]
        xml = tmp_path / "two.musicxml"
        write_musicxml(to_score(notes, bpm=119.5, title="Two"), xml)
        return render_svg_pages(xml)[0]

    def test_svg_note_count_excludes_noteheads(self, tmp_path):
        # notehead は note の前方一致に含まれ2倍計数されていた(P2)
        from earpipe.services.notate.engrave import svg_note_count

        svg = self._render_two_note_svg(tmp_path)
        assert svg_note_count(svg) == 2

    def test_plain_tempo_svg_removes_music_font(self, tmp_path):
        # cairosvgが解決できないSMuFLグリフ(Leipzig)をテンポ表記から除去し
        # ASCIIの "BPM <n>" にフォールバックする(P1: 豆腐ゼロ)
        from earpipe.services.notate.engrave import plain_tempo_svg

        svg = self._render_two_note_svg(tmp_path)
        assert 'font-family="Leipzig"' in svg  # 前提: 素のVerovio出力にはグリフがある
        out = plain_tempo_svg(svg)
        assert 'font-family="Leipzig"' not in out
        assert "BPM" in out

    def test_write_pdf_and_png_apply_plain_tempo(self, tmp_path, monkeypatch):
        # write_pdf / write_png_preview の経路でも豆腐フォントが残らない
        import earpipe.services.notate.engrave as eng

        captured: list[str] = []
        real_svg2pdf = None
        import cairosvg

        real_svg2pdf = cairosvg.svg2pdf

        def spy(bytestring=None, **kw):
            captured.append(bytestring.decode("utf-8"))
            return real_svg2pdf(bytestring=bytestring, **kw)

        monkeypatch.setattr(cairosvg, "svg2pdf", spy)
        import math

        from earpipe.contracts import QuantizedNote
        from earpipe.services.notate.score import to_score, write_musicxml

        nan = math.nan
        notes = [QuantizedNote(midi=72, start_beats=0.0, dur_beats=1.0, confidence=0.9,
                               onset_sec=nan, offset_sec=nan)]
        xml = tmp_path / "one.musicxml"
        write_musicxml(to_score(notes, bpm=100.0, title="One"), xml)
        eng.write_pdf(xml, tmp_path / "one.pdf")
        assert captured and all('font-family="Leipzig"' not in s for s in captured)
