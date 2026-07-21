"""連桁・符尾の自動整理(F-024)の回帰テスト。

score.py は music21 の makeNotation を通すため、連桁(beam)と符尾(stem)は
拍単位で自動整理される(Verovio 以前の MusicXML 段階で確定)。独自の連桁エンジンは
持たない(makeNotation が正しく処理するため・KISS/YAGNI)。ここではその挙動を回帰固定し、
将来 makeNotation を外す等で連桁が消えたら検知できるようにする。
"""

import re

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.score import to_score, write_musicxml


def _xml(notes, tmp_path, bpm=120.0):
    score = to_score(notes, bpm, title="beam")
    out = tmp_path / "beam.musicxml"
    write_musicxml(score, out)
    return out.read_text(encoding="utf-8")


def test_eighth_run_is_beamed_by_beat(tmp_path):
    """4/4 で連続8分は拍ごと(2音)に連桁される(begin/end 対が並ぶ)。"""
    # Arrange: 1小節=8つの8分音符
    notes = [QuantizedNote(start_beats=i * 0.5, dur_beats=0.5, midi=60 + (i % 5), confidence=1.0)
             for i in range(8)]
    # Act
    xml = _xml(notes, tmp_path)
    # Assert: beam 要素が存在し、begin と end が対で現れる(=連桁されている)
    assert "<beam" in xml
    assert xml.count(">begin</beam>") >= 1
    assert xml.count(">end</beam>") >= 1
    # 拍ごとの連桁: begin と end はほぼ同数(対で閉じる)
    assert abs(xml.count(">begin</beam>") - xml.count(">end</beam>")) <= 1


def test_quarter_notes_are_not_beamed(tmp_path):
    """4分音符(単独で旗を持たない音価)には連桁が付かない。"""
    # Arrange: 4分音符4つ
    notes = [QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60, confidence=1.0)
             for i in range(4)]
    # Act
    xml = _xml(notes, tmp_path)
    # Assert: 連桁なし(4分は beam 対象外)
    assert "<beam" not in xml


def test_notes_have_stems(tmp_path):
    """符尾(stem)が自動付与される。"""
    # Arrange
    notes = [QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=62, confidence=1.0)
             for i in range(4)]
    # Act
    xml = _xml(notes, tmp_path)
    # Assert: stem 要素(up/down)が付く
    assert re.search(r"<stem[^>]*>(up|down)</stem>", xml)
