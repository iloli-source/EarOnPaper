"""F-055 MuseScore ローカル受け渡し(musescore_handoff.py)のユニットテスト(Issue #102)。

prepare_handoff を AAA 形式で検証する。先行研究(F-055-grok/codex)の失敗例を
受入基準に落として堅牢性を確認する:
  - 出力 .mxl が W3C準拠(mimetype 先頭・無圧縮/META-INF/container.xml/本体同梱)で
    MuseScore の import 失敗要因(ZIP構造・mimetype不備)を作らない(codex 1.2)。
  - README を必ず併置し「開けた≠再現できた」等の注意を人間に渡す(grok 5.3)。
  - .mscz は外部生成しない(codex 5-2: 版互換が不安定)。
  - online経路を持たない=一時ファイルを作らず out_dir 配下のみで完結。
  - 圧縮済み(.mxl)や空・非XMLの入力を黙って通さず ValueError で表面化する。
  - end-to-end: to_score→write_musicxml の実出力を渡しても壊れないこと。
"""

import zipfile
from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.musescore_handoff import prepare_handoff
from earpipe.services.notate.score import to_score, write_musicxml

_MINIMAL_MUSICXML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
    '"http://www.musicxml.org/dtds/partwise.dtd">\n'
    '<score-partwise version="4.0">\n'
    "  <part-list><score-part id=\"P1\"><part-name>Music</part-name></score-part></part-list>\n"
    '  <part id="P1"><measure number="1">\n'
    "    <note><pitch><step>C</step><octave>4</octave></pitch>"
    "<duration>4</duration><type>whole</type></note>\n"
    "  </measure></part>\n"
    "</score-partwise>\n"
)


def _write_src(tmp_path: Path, name: str = "song.musicxml") -> Path:
    """テスト用の非圧縮MusicXMLを一時ディレクトリに書いてパスを返す。"""
    src = tmp_path / name
    src.write_text(_MINIMAL_MUSICXML, encoding="utf-8")
    return src


class TestMxlContainer:
    """出力 .mxl が W3C container 仕様に沿うことを検証する。"""

    def test_returns_mxl_path_by_default(self, tmp_path):
        # Arrange
        src = _write_src(tmp_path)
        out = tmp_path / "handoff"
        # Act
        result = prepare_handoff(src, out)
        # Assert
        assert result == out / "song.mxl"
        assert result.is_file()
        assert zipfile.is_zipfile(result)

    def test_mimetype_is_first_and_stored_uncompressed(self, tmp_path):
        # Arrange
        src = _write_src(tmp_path)
        # Act
        result = prepare_handoff(src, tmp_path / "out")
        # Assert: mimetype が先頭エントリで STORED(無圧縮)であること
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert names[0] == "mimetype"
            info = zf.getinfo("mimetype")
            assert info.compress_type == zipfile.ZIP_STORED
            assert zf.read("mimetype") == b"application/vnd.recordare.musicxml"

    def test_container_and_body_present(self, tmp_path):
        # Arrange
        src = _write_src(tmp_path)
        # Act
        result = prepare_handoff(src, tmp_path / "out")
        # Assert: container.xml が本体を rootfile として参照し、本体が同梱される
        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
            assert "META-INF/container.xml" in names
            assert "song.musicxml" in names
            container = zf.read("META-INF/container.xml").decode("utf-8")
            assert 'full-path="song.musicxml"' in container
            body = zf.read("song.musicxml").decode("utf-8")
            assert "score-partwise" in body


class TestSidecarFiles:
    """README と非圧縮コピーが併置されることを検証する。"""

    def test_readme_written_with_handoff_caveats(self, tmp_path):
        # Arrange
        src = _write_src(tmp_path)
        out = tmp_path / "out"
        # Act
        prepare_handoff(src, out)
        # Assert
        readme = out / "README_musescore.txt"
        assert readme.is_file()
        text = readme.read_text(encoding="utf-8")
        assert "File > Open" in text
        assert "再計算" in text  # レイアウトは再計算される旨の注意

    def test_uncompressed_copy_written(self, tmp_path):
        # Arrange
        src = _write_src(tmp_path)
        out = tmp_path / "out"
        # Act
        prepare_handoff(src, out)
        # Assert: デバッグ用に非圧縮 .musicxml も置かれる
        copy = out / "song.musicxml"
        assert copy.is_file()
        assert "score-partwise" in copy.read_text(encoding="utf-8")

    def test_no_mscz_generated(self, tmp_path):
        # Arrange
        src = _write_src(tmp_path)
        out = tmp_path / "out"
        # Act
        prepare_handoff(src, out)
        # Assert: 外部生成の .mscz は作らない(版互換リスクのため・研究反映)
        assert not list(out.glob("*.mscz"))

    def test_only_out_dir_touched_no_temp_leak(self, tmp_path):
        # Arrange: 入力用と出力用を分離
        src_dir = tmp_path / "in"
        src_dir.mkdir()
        src = _write_src(src_dir)
        out = tmp_path / "out"
        before = set(src_dir.iterdir())
        # Act
        prepare_handoff(src, out)
        # Assert: online経路なし=入力側に一時ファイルを残さない
        assert set(src_dir.iterdir()) == before
        assert {p.name for p in out.iterdir()} == {
            "song.mxl",
            "song.musicxml",
            "README_musescore.txt",
        }


class TestValidation:
    """不正入力を黙って通さず例外で表面化することを検証する。"""

    def test_missing_file_raises(self, tmp_path):
        # Arrange
        missing = tmp_path / "nope.musicxml"
        # Act / Assert
        with pytest.raises(FileNotFoundError):
            prepare_handoff(missing, tmp_path / "out")

    def test_wrong_suffix_raises(self, tmp_path):
        # Arrange
        bad = tmp_path / "song.txt"
        bad.write_text(_MINIMAL_MUSICXML, encoding="utf-8")
        # Act / Assert
        with pytest.raises(ValueError):
            prepare_handoff(bad, tmp_path / "out")

    def test_empty_file_raises(self, tmp_path):
        # Arrange
        empty = tmp_path / "empty.musicxml"
        empty.write_text("   \n", encoding="utf-8")
        # Act / Assert
        with pytest.raises(ValueError):
            prepare_handoff(empty, tmp_path / "out")

    def test_compressed_mxl_input_rejected(self, tmp_path):
        # Arrange: 圧縮済み(.mxl)を .musicxml 拡張子で渡す誤用(先頭 PK)
        pseudo = tmp_path / "song.musicxml"
        pseudo.write_bytes(b"PK\x03\x04rest-of-zip")
        # Act / Assert
        with pytest.raises(ValueError):
            prepare_handoff(pseudo, tmp_path / "out")

    def test_non_xml_content_rejected(self, tmp_path):
        # Arrange
        notxml = tmp_path / "song.musicxml"
        notxml.write_text("this is not xml at all", encoding="utf-8")
        # Act / Assert
        with pytest.raises(ValueError):
            prepare_handoff(notxml, tmp_path / "out")


class TestEndToEnd:
    """実パイプライン出力(score→musicxml)を受け渡せることを検証する。"""

    def test_real_musicxml_from_score_roundtrips(self, tmp_path):
        # Arrange: to_score の実出力を write_musicxml で書く
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60 + i, confidence=0.9)
            for i in range(4)
        ]
        score = to_score(notes, bpm=120.0, title="E2E")
        src = tmp_path / "e2e.musicxml"
        write_musicxml(score, src)
        # Act
        result = prepare_handoff(src, tmp_path / "out")
        # Assert: 有効なZIPとして開け、本体が同梱される
        assert zipfile.is_zipfile(result)
        with zipfile.ZipFile(result) as zf:
            assert "e2e.musicxml" in zf.namelist()
            assert "score-partwise" in zf.read("e2e.musicxml").decode("utf-8")
