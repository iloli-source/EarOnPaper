"""TAB譜出力プロファイル(tab.py)のテスト。

ギター6弦標準チューニング EADGBE。音域外はオクターブ移動で収める（正直注記つき）。
"""

from pathlib import Path

import pypdf

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.tab import (
    MAX_FRET,
    TUNING_GUITAR,
    TabNote,
    assign_frets,
    count_overlaps,
    fold_to_range,
    write_tab_pdf,
)


def qn(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


class TestFoldToRange:
    def test_in_range_unchanged(self):
        # Arrange: 中央ド(60)はギター音域内
        # Act
        midi, shift = fold_to_range(60)
        # Assert
        assert midi == 60
        assert shift == 0

    def test_low_note_folded_up(self):
        # Arrange: E1(28)は低すぎる → 1オクターブ上げてE2(40)
        midi, shift = fold_to_range(28)
        assert midi == 40
        assert shift == 1

    def test_very_low_note_folded_twice(self):
        # 20 → +2オクターブで44
        midi, shift = fold_to_range(20)
        assert midi == 44
        assert shift == 2

    def test_high_note_folded_down(self):
        # 95は高すぎる → -1オクターブで83（=1弦19フレット上限ちょうど）
        midi, shift = fold_to_range(95)
        assert midi == 83
        assert shift == -1

    def test_range_bounds(self):
        lo, _ = fold_to_range(TUNING_GUITAR[0])
        hi, _ = fold_to_range(TUNING_GUITAR[-1] + MAX_FRET)
        assert lo == TUNING_GUITAR[0]
        assert hi == TUNING_GUITAR[-1] + MAX_FRET


class TestAssignFrets:
    def test_open_high_e_prefers_open_string(self):
        # E4(64)は1弦開放が最小コスト
        tabs = assign_frets([qn(0, 1, 64)])
        assert len(tabs) == 1
        assert tabs[0].fret == 0
        assert TUNING_GUITAR[tabs[0].string_index] == 64

    def test_chord_no_duplicate_strings(self):
        # 開放3和音 E2/A2/D3 → 弦は3本とも別
        tabs = assign_frets([qn(0, 1, 40), qn(0, 1, 45), qn(0, 1, 50)])
        strings = [t.string_index for t in tabs]
        assert len(strings) == len(set(strings))
        assert all(t.fret == 0 for t in tabs)

    def test_out_of_range_gets_octave_shift(self):
        tabs = assign_frets([qn(0, 1, 28)])
        assert len(tabs) == 1
        assert tabs[0].octave_shift == 1
        playable = TUNING_GUITAR[tabs[0].string_index] + tabs[0].fret
        assert TUNING_GUITAR[0] <= playable <= TUNING_GUITAR[-1] + MAX_FRET

    def test_seven_note_chord_drops_honestly(self):
        # 同時7音は6弦に載らない → 6音割当+1音ドロップ
        notes = [qn(0, 1, 40 + i * 5) for i in range(7)]
        tabs = assign_frets(notes)
        assert len(tabs) == 6

    def test_empty_input(self):
        assert assign_frets([]) == []

    def test_fret_within_limit(self):
        # どの割当もフレット上限を超えない
        notes = [qn(i * 0.5, 0.5, 40 + (i * 7) % 44) for i in range(24)]
        tabs = assign_frets(notes)
        assert all(0 <= t.fret <= MAX_FRET for t in tabs)

    def test_result_is_tabnote(self):
        tabs = assign_frets([qn(0, 1, 60)])
        assert isinstance(tabs[0], TabNote)

    def test_hand_position_stays_stable(self):
        # ユーザー要望の核心: 手の移動最小化。
        # Aメジャー系アルペジオの反復 — 低フレット優先だと開放弦とハイポジを
        # 行き来してしまうが、ポジション最適化なら押弦フレットが1つの
        # ハンドポジション(4フレット幅)に収まる
        seq = [69, 73, 76, 69, 73, 76, 69, 73, 76]
        tabs = assign_frets([qn(i * 0.5, 0.5, m) for i, m in enumerate(seq)])
        fretted = [t.fret for t in tabs if t.fret > 0]
        assert fretted, "全部開放弦では検証にならない"
        assert max(fretted) - min(fretted) <= 4, f"押弦フレットが散らばりすぎ: {fretted}"

    def test_low_movement_between_adjacent_groups(self):
        # 隣接グループ間のポジション移動量合計が、単純低フレット割当より悪化しない
        # (G→A→Bm→C進行のルート+3度: ポジション跳躍が起きやすい素材)
        prog = [
            (0.0, [55, 59]),   # G3+B3
            (1.0, [57, 61]),   # A3+C#4
            (2.0, [59, 62]),   # B3+D4
            (3.0, [60, 64]),   # C4+E4
        ]
        notes = [qn(t, 1, m) for t, ms in prog for m in ms]
        tabs = assign_frets(notes)
        # 全音符が割当られている（ドロップなし）
        assert len(tabs) == 8
        # グループごとの押弦中心の移動量合計が小さいこと（4グループで合計6フレット以内）
        by_start: dict[float, list[int]] = {}
        for t in tabs:
            if t.fret > 0:
                by_start.setdefault(t.start_beats, []).append(t.fret)
        centers = [sum(fs) / len(fs) for _, fs in sorted(by_start.items())]
        total_move = sum(abs(b - a) for a, b in zip(centers, centers[1:]))
        assert total_move <= 6, f"ポジション移動が大きすぎ: centers={centers}"


class TestCountOverlaps:
    def test_sparse_melody_no_overlap(self):
        # 1拍ずつ離れた単音列 → 重なりゼロ
        tabs = assign_frets([qn(i, 1, m) for i, m in enumerate([60, 62, 64, 65, 67])])
        assert count_overlaps(tabs) == 0

    def test_dense_same_string_overlaps(self):
        # 同一弦(1弦開放E4=64)に16分間隔で連続 → 数字が重なる
        tabs = [
            TabNote(start_beats=i * 0.25, dur_beats=0.25, string_index=5,
                    fret=12, octave_shift=0, confidence=0.9)
            for i in range(8)
        ]
        assert count_overlaps(tabs) > 0

    def test_empty_no_overlap(self):
        assert count_overlaps([]) == 0


class TestWriteTabPdf:
    def test_pdf_created_and_readable(self, tmp_path: Path):
        # Arrange: かえるのうた風の単音列
        melody = [qn(i, 1, m) for i, m in enumerate([60, 62, 64, 65, 64, 62, 60])]
        out = tmp_path / "tab.pdf"
        # Act
        result = write_tab_pdf(melody, bpm=120, out_pdf=out, title="Test Song")
        # Assert
        assert out.exists() and out.stat().st_size > 0
        reader = pypdf.PdfReader(str(out))
        assert len(reader.pages) >= 1
        assert result["pages"] == len(reader.pages)

    def test_octave_shift_reported(self, tmp_path: Path):
        notes = [qn(0, 1, 28), qn(1, 1, 60)]
        result = write_tab_pdf(notes, bpm=100, out_pdf=tmp_path / "t.pdf")
        assert result["n_octave_shifted"] == 1

    def test_empty_notes_still_makes_page(self, tmp_path: Path):
        out = tmp_path / "empty.pdf"
        result = write_tab_pdf([], bpm=120, out_pdf=out)
        assert out.exists()
        assert result["pages"] >= 1
        assert result["n_octave_shifted"] == 0

    def test_result_reports_overlaps(self, tmp_path: Path):
        # 疎な単音列は重なりゼロが報告される
        melody = [qn(i, 1, m) for i, m in enumerate([60, 62, 64, 65])]
        result = write_tab_pdf(melody, bpm=120, out_pdf=tmp_path / "t.pdf")
        assert result["n_overlaps"] == 0

    def test_ocr_fret_digits_match_notes(self, tmp_path: Path):
        # 生成したTAB音符のフレット数と、PDFから抽出できる数字がほぼ一致する
        # （数字が消えていないことのデータ整合性検証）
        melody = [qn(i, 1, m) for i, m in enumerate([60, 62, 64, 65, 67, 69, 71, 72])]
        out = tmp_path / "ocr.pdf"
        write_tab_pdf(melody, bpm=120, out_pdf=out)
        tabs = assign_frets(melody)
        import re
        import pypdf
        text = " ".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out)).pages)
        digit_tokens = re.findall(r"\d{1,2}", text)
        # 各音符のフレット数字ぶんは最低限テキストに存在する（小節番号等で増える方向）
        assert len(digit_tokens) >= len(tabs)

    def test_title_in_pdf_text(self, tmp_path: Path):
        out = tmp_path / "titled.pdf"
        write_tab_pdf([qn(0, 1, 60)], bpm=120, out_pdf=out, title="Song 9")
        text = " ".join(p.extract_text() or "" for p in pypdf.PdfReader(str(out)).pages)
        assert "Song 9" in text
