"""F-052 / Issue #66: validate_musicxml のAAA形式テスト。

検査対象は earpipe/services/notate/musicxml_validate.validate_musicxml。
to_score → write_musicxml で作った実出力を検証に流し、親のpipeline配線を
待たずテスト単体で閉じる(既存 test_score_checks.py と同じ流儀)。

固定する不変条件:
- 有効な最小Score: is_valid=True / roundtrip_ok=True / note_count一致。
- 壊れたXML・空ファイル: 例外を投げず is_valid=False かつ errors非空。
- 和音を含む譜面: note_count が要素数(pitch総数でない)。
- XSDロード失敗の擬似(monkeypatch): warnings に未実行注記が入り、
  is_valid は構造検査結果で決まる。
"""

from pathlib import Path

import music21

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.score import to_score, write_musicxml
from earpipe.services.notate import musicxml_validate
from earpipe.services.notate.musicxml_validate import (
    ValidationReport,
    validate_musicxml,
)


def _write_score(notes: list[QuantizedNote], tmp_path: Path, bpm: float = 120.0) -> Path:
    """量子化音符列からMusicXMLファイルを作って返すヘルパー。"""
    score = to_score(notes, bpm=bpm)
    out = tmp_path / "score.musicxml"
    write_musicxml(score, out)
    return out


class TestValidMinimalScore:
    """有効な最小Scoreが妥当と判定されること。"""

    def test_valid_score_is_valid_with_roundtrip(self, tmp_path):
        # Arrange
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60 + i, confidence=0.9)
            for i in range(4)
        ]
        path = _write_score(notes, tmp_path)

        # Act
        report = validate_musicxml(path)

        # Assert
        assert isinstance(report, ValidationReport)
        assert report.is_valid is True
        assert report.errors == []
        assert report.roundtrip_ok is True
        assert report.note_count == 4

    def test_note_count_matches_parsed_elements(self, tmp_path):
        # Arrange
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=62 + i, confidence=0.8)
            for i in range(3)
        ]
        path = _write_score(notes, tmp_path)
        expected = len(list(music21.converter.parse(str(path)).recurse().notes))

        # Act
        report = validate_musicxml(path)

        # Assert
        assert report.note_count == expected


class TestBrokenInput:
    """壊れた入力でも例外を投げず is_valid=False にすること。"""

    def test_malformed_xml_is_invalid_without_raising(self, tmp_path):
        # Arrange
        broken = tmp_path / "broken.musicxml"
        broken.write_text("<score-partwise><this-is-not closed>", encoding="utf-8")

        # Act
        report = validate_musicxml(broken)

        # Assert
        assert report.is_valid is False
        assert report.errors  # 非空
        assert report.roundtrip_ok is False

    def test_empty_file_is_invalid_without_raising(self, tmp_path):
        # Arrange
        empty = tmp_path / "empty.musicxml"
        empty.write_text("", encoding="utf-8")

        # Act
        report = validate_musicxml(empty)

        # Assert
        assert report.is_valid is False
        assert report.errors


class TestChordNoteCount:
    """和音を含む譜面で note_count が要素数(pitch総数でない)であること。"""

    def test_chord_counts_as_single_element(self, tmp_path):
        # Arrange: C-E-G の和音(3 pitch = 1 要素) + 単音1つ → 要素2 / pitch4
        notes = [
            QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
            QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=64, confidence=0.9),
            QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=67, confidence=0.9),
            QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=72, confidence=0.9),
        ]
        path = _write_score(notes, tmp_path)
        parsed = music21.converter.parse(str(path))
        pitch_total = sum(len(n.pitches) for n in parsed.recurse().notes)

        # Act
        report = validate_musicxml(path)

        # Assert
        assert report.note_count == 2  # 要素数
        assert pitch_total == 4  # pitch総数(採用しない値)
        assert report.note_count != pitch_total


class TestXsdFallback:
    """XSDロード失敗時に warning 注記が入り、構造検査で判定されること。"""

    def test_xsd_unavailable_falls_back_with_warning(self, tmp_path, monkeypatch):
        # Arrange: スキーマロードを常に失敗(None)へ差し替える。
        notes = [
            QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
            QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.9),
        ]
        path = _write_score(notes, tmp_path)
        monkeypatch.setattr(musicxml_validate, "_load_schema", lambda: None)

        # Act
        report = validate_musicxml(path)

        # Assert
        assert any("XSD未実行" in w for w in report.warnings)
        # 構造検査は通るので is_valid は True のまま。
        assert report.is_valid is True
