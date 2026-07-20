"""ASCIIリードシート生成(leadsheet.py・F-034/Issue #71)のテスト。

test_chord.py の qn/chord_at ヘルパを模倣し、AAA(Arrange-Act-Assert)形式で
コード名の出現・小節区切り・またぎコードの hold・コード行/メロディ行の縦整合を検証する。
"""

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.leadsheet import to_leadsheet


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    """量子化音符を1つ作るヘルパ(test_chord.py に倣う)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


def span(start: float, end: float, name: str, root_pc: int, quality: str) -> ChordSpan:
    """ChordSpan を1つ作るヘルパ。"""
    return ChordSpan(
        start_beats=start, end_beats=end, name=name, root_pc=root_pc, quality=quality
    )


def _measure_count(line: str) -> int:
    """1行に含まれる小節数(区切り `|` は末尾込みで n_measures+1 本)。"""
    return line.count("|")


class TestToLeadsheet:
    def test_chord_progression_names_and_bar_separators(self) -> None:
        # Arrange: C-Am-F-G の4小節進行(各4拍)＋各小節頭に単音メロディ
        chords = [
            span(0, 4, "C", 0, "major"),
            span(4, 8, "Am", 9, "minor"),
            span(8, 12, "F", 5, "major"),
            span(12, 16, "G", 7, "major"),
        ]
        notes = [qn(0, 1, 60), qn(4, 1, 69), qn(8, 1, 65), qn(12, 1, 67)]

        # Act
        out = to_leadsheet(notes, chords, bpm=120)

        # Assert: 全コード名が含まれ、小節区切り `|` が3本以上ある
        for name in ("C", "Am", "F", "G"):
            assert name in out
        chord_line = out.split("\n")[1]
        assert chord_line.count("|") >= 3

    def test_empty_input_returns_short_string_without_error(self) -> None:
        # Arrange: 空の音符・コード
        notes: list[QuantizedNote] = []
        chords: list[ChordSpan] = []

        # Act
        out = to_leadsheet(notes, chords, bpm=120)

        # Assert: 例外なく短い(最小1小節枠の)文字列を返す
        assert isinstance(out, str)
        assert out  # 空でない
        assert len(out.splitlines()) == 3  # header + chord行 + melody行

    def test_spanning_chord_appears_only_in_first_measure(self) -> None:
        # Arrange: 0-4拍(=1小節ぶん)だが 2小節にまたがるよう end を 8 にした C 1本
        chords = [span(0, 8, "C", 0, "major")]
        notes = [qn(0, 1, 60), qn(4, 1, 60)]  # 総尺8拍=2小節

        # Act
        out = to_leadsheet(notes, chords, bpm=120)
        chord_line = out.split("\n")[1]
        cells = [c for c in chord_line.split("|") if c != ""]

        # Assert: 先頭小節に C、2小節目は空欄(hold)
        assert len(cells) == 2
        assert "C" in cells[0]
        assert cells[1].strip() == ""

    def test_chord_and_melody_lines_have_equal_measures(self) -> None:
        # Arrange: 2小節ぶんのコードとメロディ
        chords = [span(0, 4, "C", 0, "major"), span(4, 8, "G", 7, "major")]
        notes = [qn(0, 1, 60), qn(4, 1, 67)]

        # Act
        out = to_leadsheet(notes, chords, bpm=120)
        lines = out.split("\n")
        chord_line, melody_line = lines[1], lines[2]

        # Assert: コード行とメロディ行の小節区切り数が一致(縦整合)
        assert _measure_count(chord_line) == _measure_count(melody_line)
        assert _measure_count(chord_line) >= 2

    def test_columns_are_vertically_aligned(self) -> None:
        # Arrange: コード名長が異なる(maj7 と C)入力で縦揃いを確認
        chords = [span(0, 4, "Cmaj7", 0, "maj7"), span(4, 8, "G", 7, "major")]
        notes = [qn(0, 1, 60), qn(4, 1, 67)]

        # Act
        out = to_leadsheet(notes, chords, bpm=120)
        lines = out.split("\n")
        chord_line, melody_line = lines[1], lines[2]

        # Assert: `|` の出現位置(桁)がコード行とメロディ行で完全一致
        chord_bars = [i for i, ch in enumerate(chord_line) if ch == "|"]
        melody_bars = [i for i, ch in enumerate(melody_line) if ch == "|"]
        assert chord_bars == melody_bars
