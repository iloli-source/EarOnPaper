"""LLM/人間可読エクスポート(llm_export.py・F-099/Issue #82)のテスト。

test_leadsheet.py の qn/span ヘルパに倣い、AAA(Arrange-Act-Assert)形式で
ヘッダのメタ情報・小節ブロック構造・コードの hold・音符トークン形式・
低信頼マーカー・情報欠落注記・空入力の頑健性・主音上書きを検証する。
"""

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.llm_export import to_llm_text


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    """量子化音符を1つ作るヘルパ(test_leadsheet.py に倣う)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


def span(start: float, end: float, name: str, root_pc: int, quality: str) -> ChordSpan:
    """ChordSpan を1つ作るヘルパ。"""
    return ChordSpan(
        start_beats=start, end_beats=end, name=name, root_pc=root_pc, quality=quality
    )


def _meta(out: str) -> dict[str, str]:
    """ヘッダの `key: value` 行を辞書化する(先頭 # 行と Bar 行は無視)。"""
    meta: dict[str, str] = {}
    for line in out.splitlines():
        if line.startswith("#") or line.startswith("Bar"):
            continue
        if ": " in line and not line.startswith("  "):
            k, v = line.split(": ", 1)
            meta[k] = v
    return meta


def _bar_headers(out: str) -> list[str]:
    """`Bar N | ...` の行だけ抜き出す。"""
    return [ln for ln in out.splitlines() if ln.startswith("Bar ")]


class TestToLlmText:
    def test_header_reports_bpm_meter_key_and_bars(self) -> None:
        # Arrange: C-Am-F-G の4小節進行(各4拍)＋各小節頭に単音
        chords = [
            span(0, 4, "C", 0, "major"),
            span(4, 8, "Am", 9, "minor"),
            span(8, 12, "F", 5, "major"),
            span(12, 16, "G", 7, "major"),
        ]
        notes = [qn(0, 1, 60), qn(4, 1, 69), qn(8, 1, 65), qn(12, 1, 67)]

        # Act
        out = to_llm_text(notes, chords, bpm=120)
        meta = _meta(out)

        # Assert: メタ情報が期待どおり並ぶ
        assert meta["bpm"] == "120"
        assert meta["meter"].endswith("/4")
        assert meta["bars"] == "4"
        assert "major" in meta["key"] or "minor" in meta["key"]

    def test_bar_blocks_are_labeled_and_counted(self) -> None:
        # Arrange: 2小節ぶん
        chords = [span(0, 4, "C", 0, "major"), span(4, 8, "G", 7, "major")]
        notes = [qn(0, 1, 60), qn(4, 1, 67)]

        # Act
        out = to_llm_text(notes, chords, bpm=120)
        headers = _bar_headers(out)

        # Assert: Bar 1 / Bar 2 が順に現れ bars メタと一致
        assert len(headers) == 2
        assert headers[0].startswith("Bar 1 |")
        assert headers[1].startswith("Bar 2 |")
        assert _meta(out)["bars"] == "2"

    def test_all_chord_names_present(self) -> None:
        # Arrange
        chords = [
            span(0, 4, "C", 0, "major"),
            span(4, 8, "Am", 9, "minor"),
            span(8, 12, "F", 5, "major"),
            span(12, 16, "G", 7, "major"),
        ]
        notes = [qn(0, 1, 60), qn(4, 1, 69), qn(8, 1, 65), qn(12, 1, 67)]

        # Act
        out = to_llm_text(notes, chords, bpm=120)

        # Assert: 全コード名が chord 行に出る
        chord_lines = [ln for ln in out.splitlines() if ln.strip().startswith("chord:")]
        joined = "\n".join(chord_lines)
        for name in ("C", "Am", "F", "G"):
            assert name in joined

    def test_note_token_has_pitch_start_and_duration(self) -> None:
        # Arrange: 小節内相対で C4@0(2), E4@2(2)
        notes = [qn(0, 2, 60), qn(2, 2, 64)]

        # Act
        out = to_llm_text(notes, chords=None, bpm=120)
        notes_line = next(
            ln for ln in out.splitlines() if ln.strip().startswith("notes:")
        )

        # Assert: `音名@開始(音価)` 形式で開始拍・音価拍を含む
        assert "@0(2)" in notes_line
        assert "@2(2)" in notes_line

    def test_spanning_chord_shows_hold_in_next_bar(self) -> None:
        # Arrange: 0-8拍(2小節)にまたがる C 1本
        chords = [span(0, 8, "C", 0, "major")]
        notes = [qn(0, 1, 60), qn(4, 1, 60)]

        # Act
        out = to_llm_text(notes, chords, bpm=120)
        chord_lines = [ln for ln in out.splitlines() if ln.strip().startswith("chord:")]

        # Assert: 先頭小節に C、2小節目は hold
        assert len(chord_lines) == 2
        assert "C" in chord_lines[0]
        assert "(hold)" in chord_lines[1]

    def test_empty_bar_shows_rest(self) -> None:
        # Arrange: 1小節目に音、2小節目は空(コードだけで尺を作る)
        chords = [span(0, 8, "C", 0, "major")]
        notes = [qn(0, 1, 60)]

        # Act
        out = to_llm_text(notes, chords, bpm=120)
        notes_lines = [ln for ln in out.splitlines() if ln.strip().startswith("notes:")]

        # Assert: 音のない2小節目は rest
        assert "(rest)" in notes_lines[1]

    def test_low_confidence_note_is_marked(self) -> None:
        # Arrange: 低信頼(0.2)と高信頼(0.9)を1音ずつ
        notes = [qn(0, 1, 60, conf=0.2), qn(1, 1, 64, conf=0.9)]

        # Act
        out = to_llm_text(notes, chords=None, bpm=120)
        notes_line = next(
            ln for ln in out.splitlines() if ln.strip().startswith("notes:")
        )

        # Assert: 低信頼にだけ `?` が付く(高信頼には付かない)
        tokens = notes_line.split("notes:", 1)[1].split()
        low = next(t for t in tokens if t.startswith("C4@0"))
        high = next(t for t in tokens if t.startswith("E4@1"))
        assert low.endswith("?")
        assert not high.endswith("?")

    def test_info_loss_note_is_documented(self) -> None:
        # Arrange
        notes = [qn(0, 1, 60)]

        # Act
        out = to_llm_text(notes, chords=None, bpm=120)

        # Assert: 情報欠落注記(pitfalls)が本文に含まれる
        assert "情報欠落" in out
        assert "実タイミング" in out

    def test_none_chords_treated_as_hold(self) -> None:
        # Arrange: コード None(推定なし)
        notes = [qn(0, 1, 60), qn(4, 1, 67)]

        # Act: 例外なく生成でき、全 chord 行が hold
        out = to_llm_text(notes, chords=None, bpm=120)
        chord_lines = [ln for ln in out.splitlines() if ln.strip().startswith("chord:")]

        # Assert
        assert chord_lines  # 1小節以上ある
        assert all("(hold)" in ln for ln in chord_lines)

    def test_empty_input_returns_header_and_one_bar_without_error(self) -> None:
        # Arrange: 空の音符・コード
        notes: list[QuantizedNote] = []
        chords: list[ChordSpan] = []

        # Act
        out = to_llm_text(notes, chords, bpm=120)

        # Assert: 例外なく、ヘッダ＋最小1小節(rest/hold)を返す
        assert isinstance(out, str)
        assert _meta(out)["bars"] == "1"
        assert len(_bar_headers(out)) == 1
        assert "(rest)" in out
        assert "(hold)" in out

    def test_key_tonic_pc_overrides_key_label(self) -> None:
        # Arrange: 主音を G(pc=7)に上書き
        notes = [qn(0, 1, 60), qn(1, 1, 64), qn(2, 1, 67)]

        # Act
        out = to_llm_text(notes, chords=None, bpm=120, key_tonic_pc=7)

        # Assert: key ラベルの主音が G になる
        assert _meta(out)["key"].startswith("G ")

    def test_out_of_range_tonic_pc_falls_back_to_estimate(self) -> None:
        # Arrange: 範囲外(99)の主音指定
        notes = [qn(0, 1, 60), qn(1, 1, 64), qn(2, 1, 67)]

        # Act: 例外なく生成でき、key は推定にフォールバック(空でない)
        out = to_llm_text(notes, chords=None, bpm=120, key_tonic_pc=99)

        # Assert
        key = _meta(out)["key"]
        assert key and key != "unknown"
