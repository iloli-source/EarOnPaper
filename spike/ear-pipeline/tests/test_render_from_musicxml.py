"""採譜済みMusicXMLからの追加形式生成(render サブコマンド・#116)のテスト。

音声からのフル再採譜をやり直さず、MusicXML を notes/bpm に復元して
各形式(簡譜/度数/移動ド 等)を生成できることを検証する。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote
from earpipe.pipeline import main
from earpipe.services.notate import to_score, write_musicxml
from earpipe.services.notate.musicxml_read import notes_from_musicxml


def _write_sample_musicxml(path: Path) -> None:
    # C→F→G→C 和音進行(Cメジャー = 度数 I IV V I)
    prog = {0.0: (60, 64, 67), 4.0: (65, 69, 72), 8.0: (67, 71, 74), 12.0: (60, 64, 67)}
    notes = [
        QuantizedNote(start_beats=sb, dur_beats=4.0, midi=m, confidence=0.9)
        for sb, ms in prog.items()
        for m in ms
    ]
    write_musicxml(to_score(notes, 120.0), path)


def test_notes_from_musicxml_roundtrip(tmp_path: Path):
    xml = tmp_path / "s.musicxml"
    _write_sample_musicxml(xml)
    notes, bpm = notes_from_musicxml(xml)
    assert bpm == 120.0
    assert len(notes) == 12  # 4オンセット×3音
    assert sorted({n.start_beats for n in notes}) == [0.0, 4.0, 8.0, 12.0]
    assert sorted(n.midi for n in notes) == [60, 60, 64, 64, 65, 67, 67, 67, 69, 71, 72, 74]


def test_notes_from_musicxml_missing_file(tmp_path: Path):
    import pytest

    with pytest.raises(FileNotFoundError):
        notes_from_musicxml(tmp_path / "nope.musicxml")


def test_render_generates_format_and_analysis_without_retranscribe(tmp_path: Path):
    # #116: MusicXML から簡譜(format)とローマ数字度数(analysis)を再採譜なしで生成
    xml = tmp_path / "base.musicxml"
    _write_sample_musicxml(xml)
    jianpu = tmp_path / "out.jianpu.txt"
    roman = tmp_path / "out.roman.txt"

    rc = main([
        "render", "--from-musicxml", str(xml),
        "--format", f"jianpu={jianpu}",
        "--analysis", f"roman={roman}",
    ])
    assert rc == 0
    assert jianpu.exists() and jianpu.stat().st_size > 0
    roman_text = roman.read_text(encoding="utf-8")
    # C→F→G→C = I IV V I が度数として出る(入力音高が正しく反映されている)
    assert "I IV V I" in roman_text.replace("\n", " ")


def test_render_movable_do(tmp_path: Path):
    xml = tmp_path / "base.musicxml"
    _write_sample_musicxml(xml)
    solf = tmp_path / "out.movable_do.txt"
    rc = main(["render", "--from-musicxml", str(xml), "--analysis", f"movable_do={solf}"])
    assert rc == 0
    text = solf.read_text(encoding="utf-8")
    for syll in ("Do", "Mi", "Sol"):
        assert syll in text
