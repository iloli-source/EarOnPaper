"""handoff エミッタのテスト(F-093 結線スモーク)。"""

from __future__ import annotations

import zipfile

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.base import EmitContext
from earpipe.services.emitters.handoff import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)
from earpipe.services.notate.score import to_score, write_musicxml


def _note(start_beats, dur_beats, midi, confidence):
    return QuantizedNote(
        start_beats=start_beats,
        dur_beats=dur_beats,
        midi=midi,
        confidence=confidence,
    )


def _write_draft_xml(path, notes, bpm):
    score = to_score(notes, bpm, title="下書き")
    write_musicxml(score, path)
    return path


def test_module_contract():
    # Arrange / Act / Assert: エミッタ契約(結線に必要な公開定数)
    assert KEY == "handoff"
    assert EXT == "zip"
    assert NEEDS_MUSICXML is True
    assert NEEDS_AUDIO is False


def test_emit_writes_nonempty_zip_package(tmp_path):
    # Arrange: 高信頼2音+低信頼1音の下書きMusicXMLを用意
    notes = [
        _note(0.0, 1.0, 60, confidence=0.9),
        _note(1.0, 1.0, 62, confidence=0.9),
        _note(2.0, 1.0, 64, confidence=0.2),  # 低信頼(要人手確認)
    ]
    xml_path = _write_draft_xml(tmp_path / "draft.musicxml", notes, 120.0)
    ctx = EmitContext(
        notes=notes,
        bpm=120.0,
        title="テスト曲",
        musicxml_path=xml_path,
    )
    out = tmp_path / f"handoff.{EXT}"

    # Act
    result = emit(ctx, out)

    # Assert: 非空の zip が書かれ、引き継ぎ物一式が同梱される
    assert result == out
    assert out.is_file()
    assert out.stat().st_size > 0
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert "draft.musicxml" in names
    assert "manifest.json" in names
    assert "README_for_transcriber.txt" in names
