"""musescore エミッタのテスト(F-055 結線・#109 B-2)。

notes→MusicXML を書いてから、musescore エミッタが out_path に非空の .mxl
ハンドオフを生成すること・README/非圧縮コピーが併置されることを検証する。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters import musescore
from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.score import to_score, write_musicxml


def _make_notes() -> list[QuantizedNote]:
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=64, confidence=0.9),
    ]


def _write_source_musicxml(path: Path) -> None:
    score = to_score(_make_notes(), 120.0, title="test")
    write_musicxml(score, path)


def test_emit_writes_nonempty_mxl(tmp_path: Path) -> None:
    # Arrange: 先に正本 MusicXML を用意し、EmitContext に musicxml_path を渡す。
    src = tmp_path / "song.musicxml"
    _write_source_musicxml(src)
    ctx = EmitContext(notes=_make_notes(), bpm=120.0, title="test", musicxml_path=src)
    out_path = tmp_path / "song.musescore.mxl"

    # Act
    result = musescore.emit(ctx, out_path)

    # Assert: 契約どおり out_path に非空ファイルを書き、その Path を返す。
    assert result == out_path
    assert out_path.is_file()
    assert out_path.stat().st_size > 0


def test_emit_produces_valid_mxl_zip(tmp_path: Path) -> None:
    # Arrange
    src = tmp_path / "song.xml"
    _write_source_musicxml(src)
    ctx = EmitContext(notes=_make_notes(), bpm=120.0, title="test", musicxml_path=src)
    out_path = tmp_path / "song.musescore.mxl"

    # Act
    musescore.emit(ctx, out_path)

    # Assert: .mxl は W3C container 準拠の ZIP(mimetype 先頭・container.xml あり)。
    with zipfile.ZipFile(out_path) as zf:
        names = zf.namelist()
        assert names[0] == "mimetype"
        assert "META-INF/container.xml" in names


def test_emit_places_readme_and_uncompressed_copy(tmp_path: Path) -> None:
    # Arrange
    src = tmp_path / "song.musicxml"
    _write_source_musicxml(src)
    ctx = EmitContext(notes=_make_notes(), bpm=120.0, title="test", musicxml_path=src)
    out_path = tmp_path / "song.musescore.mxl"

    # Act
    musescore.emit(ctx, out_path)

    # Assert: 同ディレクトリに README と非圧縮コピーが併置される(prepare_handoff 仕様)。
    assert (out_path.parent / "README_musescore.txt").is_file()
    assert (out_path.parent / "song.musicxml").is_file()
