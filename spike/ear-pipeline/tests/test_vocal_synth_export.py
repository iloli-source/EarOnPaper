"""歌声合成向け単旋律エクスポート(vocal_synth_export.py)のテスト(F-098)。

先行研究(F-098-grok/codex)の pitfall を回帰固定する:
- ビブラート過分割(同一音高の微小分割を結合)
- しゃくり誤ノート化(極短前置音を本体へ吸収)
- ブレスのノート化(休符に音高を与えない・USTは R)
AAA(Arrange-Act-Assert)形式。
"""

from pathlib import Path

import pretty_midi
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.vocal_synth_export import (
    DEFAULT_LYRIC,
    UST_REST_LYRIC,
    UST_TICKS_PER_QUARTER,
    to_ust,
    to_vocal_midi,
)


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    """テスト用 QuantizedNote 生成ヘルパ(格子側のみ指定)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


# --- to_vocal_midi ---


def test_vocal_midi_writes_file_and_returns_path(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 60), qn(1.0, 1.0, 62), qn(2.0, 1.0, 64)]
    out = tmp_path / "vocal.mid"

    # Act
    result = to_vocal_midi(notes, out, bpm=120.0)

    # Assert
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_vocal_midi_is_monophonic_no_overlap(tmp_path: Path) -> None:
    # Arrange: 単純な順次3音
    notes = [qn(0.0, 1.0, 60), qn(1.0, 1.0, 62), qn(2.0, 1.0, 64)]
    out = tmp_path / "mono.mid"

    # Act
    to_vocal_midi(notes, out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(out))

    # Assert: 単旋律なので前音の終端が次音の開始を越えない
    inst_notes = sorted(pm.instruments[0].notes, key=lambda n: n.start)
    for a, b in zip(inst_notes, inst_notes[1:]):
        assert a.end <= b.start + 1e-6


def test_vocal_midi_bpm_scales_timing(tmp_path: Path) -> None:
    # Arrange: 120BPMなら1拍=0.5秒、1拍の音は0.5秒になる
    notes = [qn(0.0, 1.0, 60)]
    out = tmp_path / "tempo.mid"

    # Act
    to_vocal_midi(notes, out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(out))

    # Assert
    note = pm.instruments[0].notes[0]
    assert note.start == pytest.approx(0.0, abs=1e-3)
    assert (note.end - note.start) == pytest.approx(0.5, abs=1e-3)


def test_vocal_midi_merges_vibrato_split_same_pitch(tmp_path: Path) -> None:
    # Arrange: 同一音高が微小隙間で3分割 = ビブラート由来の過分割
    notes = [qn(0.0, 0.3, 60), qn(0.3, 0.3, 60), qn(0.6, 0.4, 60)]
    out = tmp_path / "vibrato.mid"

    # Act
    to_vocal_midi(notes, out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(out))

    # Assert: 1音のロングトーンに結合される(短音符列にならない)
    assert len(pm.instruments[0].notes) == 1


def test_vocal_midi_absorbs_scoop_into_target(tmp_path: Path) -> None:
    # Arrange: 極短の低音(装飾)→ 直後に本体の高音が隙間なく続く = しゃくり
    notes = [qn(0.0, 0.1, 58), qn(0.1, 0.9, 62)]
    out = tmp_path / "scoop.mid"

    # Act
    to_vocal_midi(notes, out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(out))

    # Assert: 前置音は独立ノート化されず、本体1音(midi=62)に吸収される
    inst_notes = pm.instruments[0].notes
    assert len(inst_notes) == 1
    assert inst_notes[0].pitch == 62


def test_vocal_midi_keeps_breath_gap_as_silence(tmp_path: Path) -> None:
    # Arrange: 2音の間に大きな隙間(ブレス)
    notes = [qn(0.0, 1.0, 60), qn(3.0, 1.0, 62)]
    out = tmp_path / "breath.mid"

    # Act
    to_vocal_midi(notes, out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(out))

    # Assert: 隙間はノート化されず2音のまま(無音として残る)
    assert len(pm.instruments[0].notes) == 2


def test_vocal_midi_drops_chord_keeps_top_note(tmp_path: Path) -> None:
    # Arrange: 同一開始拍に和音(3音)。歌声は単声。
    notes = [qn(0.0, 1.0, 60), qn(0.0, 1.0, 64), qn(0.0, 1.0, 67)]
    out = tmp_path / "chord.mid"

    # Act
    to_vocal_midi(notes, out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(out))

    # Assert: 最高音のみ残る
    inst_notes = pm.instruments[0].notes
    assert len(inst_notes) == 1
    assert inst_notes[0].pitch == 67


def test_vocal_midi_rejects_invalid_bpm(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 60)]
    out = tmp_path / "bad.mid"

    # Act / Assert
    with pytest.raises(ValueError):
        to_vocal_midi(notes, out, bpm=0.0)
    with pytest.raises(ValueError):
        to_vocal_midi(notes, out, bpm=-10.0)


def test_vocal_midi_empty_notes_writes_valid_file(tmp_path: Path) -> None:
    # Arrange
    out = tmp_path / "empty.mid"

    # Act
    result = to_vocal_midi([], out, bpm=120.0)
    pm = pretty_midi.PrettyMIDI(str(result))

    # Assert: 空でも壊れないMIDIが出る
    assert out.exists()
    assert sum(len(i.notes) for i in pm.instruments) == 0


# --- to_ust ---


def test_ust_writes_file_and_returns_path(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 60), qn(1.0, 1.0, 62)]
    out = tmp_path / "song.ust"

    # Act
    result = to_ust(notes, out, bpm=120.0)

    # Assert
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "[#VERSION]" in text
    assert "[#TRACKEND]" in text


def test_ust_has_tempo_and_notenum(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 67)]
    out = tmp_path / "tempo.ust"

    # Act
    to_ust(notes, out, bpm=100.0)
    text = out.read_text(encoding="utf-8")

    # Assert
    assert "Tempo=100.00" in text
    assert "NoteNum=67" in text
    assert f"Lyric={DEFAULT_LYRIC}" in text


def test_ust_tempo_argument_overrides_bpm(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 60)]
    out = tmp_path / "override.ust"

    # Act: bpm=120 だが tempo=90 を明示
    to_ust(notes, out, bpm=120.0, tempo=90.0)
    text = out.read_text(encoding="utf-8")

    # Assert: ヘッダは tempo 引数優先
    assert "Tempo=90.00" in text


def test_ust_length_matches_480_tpq(tmp_path: Path) -> None:
    # Arrange: 四分音符1拍 = 480 tick
    notes = [qn(0.0, 1.0, 60)]
    out = tmp_path / "len.ust"

    # Act
    to_ust(notes, out, bpm=120.0)
    text = out.read_text(encoding="utf-8")

    # Assert
    assert f"Length={UST_TICKS_PER_QUARTER}" in text


def test_ust_inserts_rest_for_breath_gap(tmp_path: Path) -> None:
    # Arrange: 2音の間に大きな隙間(ブレス)
    notes = [qn(0.0, 1.0, 60), qn(3.0, 1.0, 62)]
    out = tmp_path / "rest.ust"

    # Act
    to_ust(notes, out, bpm=120.0)
    text = out.read_text(encoding="utf-8")

    # Assert: 休符 R が挿入される(音高ノートにしない)
    assert f"Lyric={UST_REST_LYRIC}" in text


def test_ust_no_rest_when_notes_contiguous(tmp_path: Path) -> None:
    # Arrange: 隙間なく連続する2音
    notes = [qn(0.0, 1.0, 60), qn(1.0, 1.0, 62)]
    out = tmp_path / "contig.ust"

    # Act
    to_ust(notes, out, bpm=120.0)
    text = out.read_text(encoding="utf-8")

    # Assert: 休符は挿入されない
    assert f"Lyric={UST_REST_LYRIC}" not in text


def test_ust_omits_source_paths_for_privacy(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 60)]
    out = tmp_path / "clean.ust"

    # Act
    to_ust(notes, out, bpm=120.0)
    text = out.read_text(encoding="utf-8").lower()

    # Assert: 配布時パス漏洩回避(grok 2E)。パス系フィールドを書かない。
    assert "voicedir" not in text
    assert "outfile" not in text
    assert "cachedir" not in text
    assert "\\" not in text and ":/" not in text


def test_ust_rejects_invalid_bpm(tmp_path: Path) -> None:
    # Arrange
    notes = [qn(0.0, 1.0, 60)]
    out = tmp_path / "bad.ust"

    # Act / Assert
    with pytest.raises(ValueError):
        to_ust(notes, out, bpm=0.0)


def test_ust_merges_vibrato_split(tmp_path: Path) -> None:
    # Arrange: 同一音高の微小分割(ビブラート)
    notes = [qn(0.0, 0.3, 60), qn(0.3, 0.3, 60), qn(0.6, 0.4, 60)]
    out = tmp_path / "vib.ust"

    # Act
    to_ust(notes, out, bpm=120.0)
    text = out.read_text(encoding="utf-8")

    # Assert: NoteNum=60 の音符ブロックが1つに結合される
    assert text.count("NoteNum=60") == 1
