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
