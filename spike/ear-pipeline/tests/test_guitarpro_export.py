"""F-051 Guitar Pro(.gp5)エクスポートのテスト。

先行研究(F-051-{grok,codex}.md)で観測された失敗例が再現しないことを回帰で固定する:
- 書出し→読戻しでビートが潰れない(PyGuitarPro Issue #4)
- validに開ける(TuxGuitarゼロバイト破損 codex 2-1 の回避)
- 弦/フレットが tab.py の割当と整合する
- guitarpro非導入時はMIDIへフォールバック(拡張子.mid)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.guitarpro_export import (
    TUNING_STANDARD,
    _string_number,
    _to_ascii,
    write_guitarpro,
)
from earpipe.services.notate.tab import assign_frets

guitarpro = pytest.importorskip("guitarpro")


def _c_major_run() -> list[QuantizedNote]:
    """2小節にまたがる単旋律のサンプル音符列。"""
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=0.9),
        QuantizedNote(start_beats=2.0, dur_beats=0.5, midi=64, confidence=0.8),
        QuantizedNote(start_beats=2.5, dur_beats=0.5, midi=65, confidence=0.8),
        QuantizedNote(start_beats=4.0, dur_beats=2.0, midi=67, confidence=0.9),
        QuantizedNote(start_beats=6.0, dur_beats=2.0, midi=72, confidence=0.7),
    ]


def test_writes_valid_gp5_that_reopens(tmp_path: Path) -> None:
    # Arrange
    notes = _c_major_run()
    out = tmp_path / "song.gp5"

    # Act
    written = write_guitarpro(notes, out, bpm=100)

    # Assert: ファイルが存在し非ゼロで、guitarproで再パースできる(valid)
    assert written.exists()
    assert written.suffix == ".gp5"
    assert written.stat().st_size > 0
    song = guitarpro.parse(str(written))
    assert len(song.tracks) == 1
    assert song.tempo == 100


def test_all_notes_survive_roundtrip_no_beat_collapse(tmp_path: Path) -> None:
    # Arrange: PyGuitarPro Issue #4(全ビート1つに潰れる)を回帰で防ぐ
    notes = _c_major_run()
    out = tmp_path / "roundtrip.gp5"

    # Act
    written = write_guitarpro(notes, out, bpm=120)
    song = guitarpro.parse(str(written))

    # Assert: 入力6音がすべてファイル内に存在する(潰れていない)
    total_notes = sum(
        len(beat.notes)
        for measure in song.tracks[0].measures
        for voice in measure.voices
        for beat in voice.beats
    )
    assert total_notes == len(notes)
    # 2小節に展開されている(4拍/小節、最終音は6拍目開始)
    assert len(song.tracks[0].measures) == 2


def test_fret_and_string_match_tab_assignment(tmp_path: Path) -> None:
    # Arrange: 開放低E(midi=40)は tab では 6弦・fret0
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=40, confidence=0.9)]
    tabs = assign_frets(notes)
    expected_string = _string_number(tabs[0].string_index)  # 6
    expected_fret = tabs[0].fret  # 0
    out = tmp_path / "open_e.gp5"

    # Act
    written = write_guitarpro(notes, out)
    song = guitarpro.parse(str(written))
    beat = song.tracks[0].measures[0].voices[0].beats[0]

    # Assert
    assert beat.notes[0].string == expected_string == 6
    assert beat.notes[0].value == expected_fret == 0


def test_empty_notes_produce_valid_single_measure_rest(tmp_path: Path) -> None:
    # Arrange
    out = tmp_path / "empty.gp5"

    # Act
    written = write_guitarpro([], out, bpm=90)
    song = guitarpro.parse(str(written))

    # Assert: 空入力でも壊れず、1小節の休符が入る
    assert written.stat().st_size > 0
    assert len(song.tracks[0].measures) == 1
    beats = song.tracks[0].measures[0].voices[0].beats
    assert len(beats) >= 1


def test_chord_notes_share_one_beat(tmp_path: Path) -> None:
    # Arrange: 同一開始拍の3音(Cメジャー和音)は1ビートに束ねる
    chord = [
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=48, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=52, confidence=0.9),
        QuantizedNote(start_beats=0.0, dur_beats=2.0, midi=55, confidence=0.9),
    ]
    out = tmp_path / "chord.gp5"

    # Act
    written = write_guitarpro(chord, out)
    song = guitarpro.parse(str(written))
    first_beat = song.tracks[0].measures[0].voices[0].beats[0]

    # Assert: 3音が同一ビートに乗り、弦が重複しない
    assert len(first_beat.notes) == 3
    strings = [n.string for n in first_beat.notes]
    assert len(set(strings)) == len(strings)


def test_invalid_bpm_raises(tmp_path: Path) -> None:
    # Arrange / Act / Assert
    notes = _c_major_run()
    with pytest.raises(ValueError):
        write_guitarpro(notes, tmp_path / "bad.gp5", bpm=0)
    with pytest.raises(ValueError):
        write_guitarpro(notes, tmp_path / "bad2.gp5", bpm=float("inf"))


def test_invalid_tuning_length_raises(tmp_path: Path) -> None:
    # Arrange / Act / Assert: 6弦以外はエラー
    notes = _c_major_run()
    with pytest.raises(ValueError):
        write_guitarpro(notes, tmp_path / "bad.gp5", tuning=(40, 45, 50))


def test_non_gp5_suffix_is_normalized(tmp_path: Path) -> None:
    # Arrange: 拡張子違いを渡しても .gp5 に正規化される
    notes = _c_major_run()
    out = tmp_path / "song.txt"

    # Act
    written = write_guitarpro(notes, out)

    # Assert
    assert written.suffix == ".gp5"
    assert written.exists()


def test_non_ascii_title_is_normalized_not_garbled() -> None:
    # Arrange / Act: cp1252化け回避のため日本語はASCIIへ落とす(codex 3-7)
    result = _to_ascii("採譜テスト Song")

    # Assert: ASCII部分は残り、非ASCIIは置換されて出力可能
    assert result.encode("ascii")  # ASCIIエンコード可能=化けない
    assert "Song" in result


def test_custom_tuning_is_written(tmp_path: Path) -> None:
    # Arrange: Drop D(低E→D=38)チューニングを指定
    drop_d = (38, 45, 50, 55, 59, 64)
    notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=38, confidence=0.9)]
    out = tmp_path / "dropd.gp5"

    # Act
    written = write_guitarpro(notes, out, tuning=drop_d)
    song = guitarpro.parse(str(written))

    # Assert: 最低弦(number=6, 高→低の最後)が38になっている
    low_string = max(song.tracks[0].strings, key=lambda s: s.number)
    assert low_string.value == 38


def test_default_tuning_is_standard() -> None:
    # Arrange / Act / Assert: 既定は標準EADGBE(低E→高E)
    assert TUNING_STANDARD == (40, 45, 50, 55, 59, 64)


def test_non_representable_durations_do_not_crash(tmp_path) -> None:
    """#113 回帰: GP5が単一ビートで表せない音価(2.5拍=5/8等)でも ValueError で落ちない。

    Duration.fromTime は非表現音価で例外を投げる。_snap_ticks で直近の表現可能音価へ
    丸めることで、任意の量子化長を安全に書き出せることを固定する(非空・valid)。
    """
    # Arrange: 2.5拍(=2400ticks, 従来クラッシュ)・付点系・三連端数を含む
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=2.5, midi=60, confidence=1.0),
        QuantizedNote(start_beats=2.5, dur_beats=1.5, midi=64, confidence=1.0),
        QuantizedNote(start_beats=4.0, dur_beats=0.33, midi=67, confidence=1.0),
        QuantizedNote(start_beats=4.33, dur_beats=5.0, midi=62, confidence=1.0),
    ]
    out = tmp_path / "awkward.gp5"

    # Act: 例外を投げないこと自体が回帰対象
    written = write_guitarpro(notes, out, bpm=120)

    # Assert: 非空 & 再パース可能(破損していない)
    assert Path(written).stat().st_size > 0
    song = guitarpro.parse(str(written))
    assert len(song.tracks) >= 1
