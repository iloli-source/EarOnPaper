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
    _reduce_to_melody,
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


class TestIdiomaticVoicing:
    """#142: 慣用ヴォイシング優先(DS-04東スポ氏指摘・調査 tab-fingering-idiom-research.md)。

    音高は変えず、同じ音高集合の複数運指から慣用形(パワーコード/オクターブ/バレー)を
    優先する。単音は非影響。
    """

    def _assign_map(self, midis: list[int]) -> dict[int, tuple[int, int]]:
        tabs = assign_frets([qn(0.0, 1.0, m) for m in midis])
        assert len(tabs) == len(midis)
        return {TUNING_GUITAR[t.string_index] + t.fret: (t.string_index, t.fret)
                for t in tabs}

    def test_power_chord_triad_uses_classic_shape(self):
        # G5 {G2,D3,G3}: 貪欲最低フレットだと分散配置になるが、
        # 慣用形ボーナスで 6弦3F/5弦5F/4弦5F (3-5-5) を選ぶこと
        played = self._assign_map([43, 50, 55])
        assert played[43] == (0, 3)
        assert played[50] == (1, 5)
        assert played[55] == (2, 5)

    def test_root_fifth_pair_lands_on_adjacent_strings(self):
        # root+5th の2音は隣接弦ペアに載る(パワーコード形)
        played = self._assign_map([45, 52])  # A2+E3
        assert abs(played[45][0] - played[52][0]) == 1

    def test_barre_run_prefers_same_fret(self):
        # 1F横並び3音 {D#3,G#3,C4}: 4弦1F/3弦1F/2弦1F のバレー形
        played = self._assign_map([51, 56, 60])
        frets = {v[1] for v in played.values()}
        assert frets == {1}
        assert sorted(v[0] for v in played.values()) == [2, 3, 4]

    def test_single_notes_unaffected(self):
        # 単音メロディは列挙経路に入らず従来挙動(構造保証)
        tabs = assign_frets([qn(0.0, 1.0, 64), qn(1.0, 1.0, 67), qn(2.0, 1.0, 69)])
        assert all(0 <= t.fret <= MAX_FRET for t in tabs)
        assert len(tabs) == 3

    def test_idiom_shapes_reported(self, tmp_path: Path):
        notes = [qn(0.0, 1.0, 43), qn(0.0, 1.0, 50), qn(0.0, 1.0, 55)]
        res = write_tab_pdf(notes, 120.0, tmp_path / "t.pdf")
        assert res["n_idiom_shapes"] >= 1


class TestSpacingRods:
    """#139: 簡易spring-rod＋密度適応段組(調査 tab-spacing-research.md)。

    固定4小節/段＋純粋拍比例で16分連打の2桁フレットが癒着していた
    (実曲最大77重なり/曲)。rod=数字幅+余白の最小間隔を保証し、
    小節の必要幅に応じて段あたり小節数を1〜4で可変にする。
    """

    def test_flagship_dense_two_digit_16ths_no_overlap(self, tmp_path: Path):
        # 141414型: 2桁フレットの16分連打2小節ぶん → 重なりゼロが採用条件
        notes = [qn(i * 0.25, 0.25, 78 if i % 2 == 0 else 80) for i in range(32)]
        res = write_tab_pdf(notes, 120.0, tmp_path / "dense.pdf")
        assert res["n_overlaps"] == 0

    def test_solve_anchors_enforces_rods(self):
        from earpipe.services.notate.tab import _solve_anchors

        # 0.25拍刻み×8音・数字幅40 → 隣接間隔は必ず rod(44) 以上
        onsets = [(i * 0.25, 40.0) for i in range(8)]
        anchors = _solve_anchors(onsets, width=300.0)
        xs = [x for _, x in anchors]
        assert all(x2 - x1 >= 43.99 for x1, x2 in zip(xs, xs[1:]))
        assert xs == sorted(xs)

    def test_solve_anchors_sparse_stays_proportional(self):
        from earpipe.services.notate.tab import _solve_anchors, _nominal_inner_width

        # 4分音符×4(疎) → 拍比例位置とほぼ一致(回帰ゼロの構造保証)
        w = _nominal_inner_width()
        onsets = [(float(b), 29.0) for b in range(4)]
        anchors = _solve_anchors(onsets, width=w)
        for (b, x) in anchors:
            ideal = (b / 4.0) * w
            assert abs(x - ideal) < w * 0.05

    def test_pack_measures_density_adaptive(self):
        from earpipe.services.notate.tab import _pack_measures

        # 密な小節は段が分かれ、疎のみなら4小節/段
        rows = _pack_measures([2000.0, 300.0, 300.0, 300.0], page_w=1840.0)
        assert rows[0] == [0]
        rows2 = _pack_measures([300.0] * 8, page_w=1840.0)
        assert rows2 == [[0, 1, 2, 3], [4, 5, 6, 7]]
        # 1小節でも収まらない場合は1小節段として正直に置く
        rows3 = _pack_measures([3000.0], page_w=1840.0)
        assert rows3 == [[0]]

    def test_sparse_song_keeps_four_measures_per_system(self, tmp_path: Path):
        # 疎な4分音符メロディ16拍(4小節) → 従来どおり1段4小節・重なり0
        notes = [qn(float(i), 1.0, 60 + (i % 5)) for i in range(16)]
        res = write_tab_pdf(notes, 120.0, tmp_path / "sparse.pdf")
        assert res["n_overlaps"] == 0
        assert res["pages"] == 1


class TestRhythmNotationComplete:
    """#143: 拍子表示・単独旗・タイ・三連括弧(調査 tab-rhythm-notation-research.md)。"""

    def _render(self, notes: list[QuantizedNote], beats: int = 4, gpb: int = 4) -> str:
        from earpipe.services.notate.tab import _render_pages

        tabs = assign_frets(notes)
        return " ".join(_render_pages(tabs, 120, "T", 0, 0, [], chord_diagrams=False,
                                      beats_per_measure=beats, grid_per_beat=gpb))

    def test_time_signature_is_drawn(self):
        svg = self._render([qn(0.0, 1.0, 60)], beats=3)
        assert svg.count('class="timesig"') == 2  # 分子と分母
        assert ">3<" in svg  # 分子に3

    def test_measures_split_by_beats(self):
        from earpipe.services.notate.tab import _layout_rows

        tabs = assign_frets([qn(0.0, 1.0, 60), qn(3.0, 1.0, 62)])
        mls = [ml for row in _layout_rows(tabs, beats=3) for ml in row]
        assert max(ml["m"] for ml in mls) == 1  # 3拍基準ならstart=3.0は第2小節

    def test_write_tab_pdf_accepts_meter_override(self, tmp_path: Path):
        notes = [qn(float(b), 1.0, 60) for b in range(6)]
        res = write_tab_pdf(notes, 120.0, tmp_path / "m34.pdf", beats_per_measure=3)
        assert res["pages"] >= 1
        assert res["beats_per_measure"] == 3

    def test_isolated_eighth_gets_flag(self):
        svg = self._render([qn(0.0, 0.5, 60), qn(1.0, 1.0, 62)])
        assert svg.count('class="flag"') == 1

    def test_isolated_sixteenth_gets_two_flags(self):
        svg = self._render([qn(0.0, 0.25, 60), qn(1.0, 1.0, 62)])
        assert svg.count('class="flag"') == 2

    def test_beamed_eighths_have_no_flags(self):
        svg = self._render([qn(i * 0.5, 0.5, 60) for i in range(8)])
        assert svg.count('class="flag"') == 0
        assert svg.count('class="beam"') == 4

    def test_cross_barline_tie_drawn_and_rests_fixed(self):
        # 4/4で3拍目から2拍伸びる音 → 次小節頭に括弧数字+タイ弧・
        # 次小節の占有区間(0-1拍)に休符を出さない(現行バグの回帰固定)
        svg = self._render([qn(3.0, 2.0, 60)])
        assert svg.count('class="tie"') == 1
        assert svg.count('class="tie-digit"') == 1
        # m0: 0-3拍空き(2分+4分) / m1: 1-4拍空き(4分+2分) = 計4個(全休符1個ではない)
        assert svg.count('class="rest"') == 4

    def test_triplet_brackets_only_on_triplet_grid(self):
        third = 1.0 / 3.0
        notes = [qn(i * third, third, 60) for i in range(6)]  # 2拍ぶんの8分3連
        assert self._render(notes, gpb=3).count('class="tuplet3"') == 2
        assert self._render(notes, gpb=4).count('class="tuplet3"') == 0

    def test_tie_continuation_yields_to_same_string_new_note(self):
        # 同弦で持続が次の音の開始と重なる場合、継続(n)は描かず新音を優先
        # (同弦の持続は次の押弦で物理的に消える=記譜的にも正しい)。重なりゼロ。
        notes = [qn(3.5, 1.0, 64), qn(4.0, 1.0, 64)]
        tabs = assign_frets(notes)
        assert count_overlaps(tabs) == 0
        svg = self._render(notes)
        assert svg.count('class="tie-digit"') == 0

    def test_chord_band_fits_diagram(self):
        from earpipe.services.notate.tab import _CHORD_BAND_H, _DIAGRAM_TOTAL_H

        assert _CHORD_BAND_H >= _DIAGRAM_TOTAL_H + 6  # 図の下端がTAB上線に触れない


class TestCountOverlaps:
    def test_sparse_melody_no_overlap(self):
        # 1拍ずつ離れた単音列 → 重なりゼロ
        tabs = assign_frets([qn(i, 1, m) for i, m in enumerate([60, 62, 64, 65, 67])])
        assert count_overlaps(tabs) == 0

    def test_dense_same_string_no_longer_overlaps(self):
        # 同一弦の16分連続2桁: #139以前は重なりが出た入力。spring-rodレイアウト
        # 導入後は rod(数字幅+余白) が保証されるため0になる(設計不変量の検証)。
        tabs = [
            TabNote(start_beats=i * 0.25, dur_beats=0.25, string_index=5,
                    fret=12, octave_shift=0, confidence=0.9)
            for i in range(8)
        ]
        assert count_overlaps(tabs) == 0

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


class TestReduceToMelody:
    def test_keeps_highest_note_per_onset(self):
        # Arrange: 同じ拍に3和音(C-E-G)、次の拍に単音
        chord = [qn(0, 1, 60), qn(0, 1, 64), qn(0, 1, 67)]
        nxt = [qn(1, 1, 62)]
        # Act
        melody = _reduce_to_melody(chord + nxt)
        # Assert: 各オンセット1音、和音は最高音(67)を採用
        assert [n.midi for n in melody] == [67, 62]

    def test_tie_break_by_confidence(self):
        # Arrange: 同オンセット・同音高なら高信頼度を残す
        melody = _reduce_to_melody([qn(0, 1, 60, conf=0.3), qn(0, 1, 60, conf=0.9)])
        # Assert
        assert len(melody) == 1 and melody[0].confidence == 0.9

    def test_empty(self):
        assert _reduce_to_melody([]) == []

    def test_drops_low_confidence_overtone(self):
        # #119: 高信頼の主旋律音(60)＋低信頼の倍音らしき高音(79)が同時。
        # 無条件スカイラインだと79へ跳ねる(音が飛ぶ)。低信頼倍音は除外し60を選ぶ。
        melody = _reduce_to_melody([qn(0, 1, 60, conf=0.9), qn(0, 1, 79, conf=0.1)])
        assert [n.midi for n in melody] == [60]

    def test_keeps_highest_when_confidence_comparable(self):
        # 信頼度が同程度なら従来どおり最高音(スカイライン)を主旋律に採る
        melody = _reduce_to_melody([qn(0, 1, 60, conf=0.8), qn(0, 1, 67, conf=0.75)])
        assert [n.midi for n in melody] == [67]

    def test_monophonic_tab_has_no_overlaps(self):
        # Arrange: 押さえられない密集和音を各拍に配置
        notes = []
        for beat in range(4):
            for m in (55, 58, 60, 63, 67, 70):  # 同時6音・広域
                notes.append(qn(beat, 1, m))
        # Act: monophonic=True で単旋律TAB化
        mono_tabs = assign_frets(_reduce_to_melody(notes))
        # Assert: 各オンセット1音のみ→弦の重なり(同時発音)が無い
        assert count_overlaps(mono_tabs) == 0
        assert len(mono_tabs) == 4

    def test_write_tab_pdf_monophonic_flag(self, tmp_path: Path):
        # Arrange: 和音を含む音符列
        notes = [qn(0, 1, 60), qn(0, 1, 64), qn(0, 1, 67), qn(1, 1, 62)]
        out = tmp_path / "mono.pdf"
        # Act
        write_tab_pdf(notes, bpm=120, out_pdf=out, monophonic=True)
        # Assert: PDFが生成され、単旋律化で同時発音が消える
        assert out.exists() and out.stat().st_size > 0
        assert count_overlaps(assign_frets(_reduce_to_melody(notes))) == 0


class TestMonophonicKeepsChords:
    """回帰: --tab-mono(単旋律化)でもコード帯は原音(多声)から出す。

    monophonic=True で estimate_chords を間引き後の単音に掛けると、和音判定
    不能で全て N.C. になりコード帯が消える不具合の再発防止(EOP tab-mono)。
    """

    def _progression(self) -> list[QuantizedNote]:
        # C→F→G→C 各4拍・3音同時の明確な和音進行
        prog = {0.0: (60, 64, 67), 4.0: (65, 69, 72),
                8.0: (67, 71, 74), 12.0: (60, 64, 67)}
        return [qn(sb, 4, m) for sb, ms in prog.items() for m in ms]

    def test_monophonic_still_detects_chords(self, tmp_path: Path):
        # Arrange: 多声の和音進行
        notes = self._progression()
        out = tmp_path / "mono_chords.pdf"
        # Act: 単旋律TAB化してもコード推定は原音で行われるべき
        result = write_tab_pdf(notes, bpm=120, out_pdf=out, monophonic=True)
        # Assert: コードが消えていない(間引き後の単音なら n_chords==0 になる)
        assert result["n_chords"] > 0

    def test_render_gate_chord_names_in_svg(self):
        # 描画ゲート: monophonic経路のSVGにコード名(C/F/G)が実際に載る
        # (単字OCRは不安定なため出力SVGのテキストを直接照合する)
        from earpipe.services.notate.chord import estimate_chords
        from earpipe.services.notate.tab import _render_pages

        notes = self._progression()
        chord_spans = estimate_chords(notes, bpm=120)  # 原音から推定
        tabs = assign_frets(_reduce_to_melody(notes))  # TABは単旋律
        svg = " ".join(_render_pages(
            tabs, 120, "T", 0, 0, chord_spans, chord_diagrams=False))
        for name in ("C", "F", "G"):
            assert f">{name}<" in svg, f"コード名 {name} がSVGに描画されていない"


class TestVisualElementsGpStyle:
    """#127 GP風見た目: リズム表記・休符・小節番号・和音囲み・太字数字。

    SVG要素は class 属性(stem/beam/dot/rest/chord-ellipse/mnum)で識別する
    (既存 test_render_gate_chord_names_in_svg と同じ「出力SVGを直接照合」パターン)。
    """

    def _render(self, notes: list[QuantizedNote], monophonic: bool = False) -> str:
        from earpipe.services.notate.tab import _render_pages

        tab_notes = _reduce_to_melody(notes) if monophonic else notes
        tabs = assign_frets(tab_notes)
        return " ".join(_render_pages(tabs, 120, "T", 0, 0, [], chord_diagrams=False))

    def test_quarter_notes_have_stems(self):
        # Arrange: 4分音符×4(1小節)
        svg = self._render([qn(b, 1.0, 60) for b in range(4)])
        # Assert: 符尾4本・連桁なし
        assert svg.count('class="stem"') == 4
        assert svg.count('class="beam"') == 0

    def test_eighth_pairs_are_beamed(self):
        # Arrange: 8分音符×8(1小節)。同一拍内のペアが連桁で結ばれる
        svg = self._render([qn(i * 0.5, 0.5, 60) for i in range(8)])
        # Assert: 符尾8本・連桁4本(拍ごと)
        assert svg.count('class="stem"') == 8
        assert svg.count('class="beam"') == 4

    def test_dotted_note_has_dot(self):
        # Arrange: 付点4分(1.5拍)＋8分
        svg = self._render([qn(0.0, 1.5, 60), qn(1.5, 0.5, 62)])
        # Assert: 付点が1つ描かれる
        assert svg.count('class="dot"') == 1

    def test_whole_note_has_no_stem(self):
        # Arrange: 全音符1つ → GP慣行で符尾なし
        svg = self._render([qn(0.0, 4.0, 60)])
        assert svg.count('class="stem"') == 0

    def test_rests_drawn_for_gaps(self):
        # Arrange: 1拍目と3拍目のみ音(2・4拍目は無音) → 4分休符2つ
        svg = self._render([qn(0.0, 1.0, 60), qn(2.0, 1.0, 62)])
        assert svg.count('class="rest"') >= 2

    def test_empty_measure_gets_whole_rest(self):
        # Arrange: 1小節目と3小節目に音・2小節目は完全に無音
        svg = self._render([qn(0.0, 4.0, 60), qn(8.0, 4.0, 62)])
        # Assert: 空の2小節目に全休符が置かれる(休符要素が最低1つ)
        assert svg.count('class="rest"') >= 1

    def test_measure_numbers_on_all_measures(self):
        # Arrange: 8小節ぶんの音列(2システム)
        svg = self._render([qn(m * 4.0, 4.0, 60) for m in range(8)])
        # Assert: 全8小節に番号が振られる
        assert svg.count('class="mnum"') == 8
        for n in range(1, 9):
            assert f'>{n}<' in svg, f"小節番号 {n} がない"

    def test_chord_ellipse_for_stacked_frets(self):
        # Arrange: 3音同時の和音(非mono) → 楕円囲みあり
        chord = [qn(0.0, 4.0, m) for m in (60, 64, 67)]
        svg = self._render(chord, monophonic=False)
        assert svg.count('class="chord-ellipse"') >= 1

    def test_no_chord_ellipse_when_monophonic(self):
        # Arrange: 同じ和音でも monophonic なら単音化され楕円なし
        chord = [qn(0.0, 4.0, m) for m in (60, 64, 67)]
        svg = self._render(chord, monophonic=True)
        assert svg.count('class="chord-ellipse"') == 0

    def test_fret_digits_are_bold(self):
        # Arrange: フレット数字は太字(参考動画準拠)
        svg = self._render([qn(0.0, 1.0, 60)])
        assert 'font-weight="bold"' in svg
