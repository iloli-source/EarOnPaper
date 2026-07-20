"""譜面密度の連続簡略化(F-095)のユニットテスト。

先行研究(F-095-grok.md)の失敗例を回帰テストとして固定する:
- 失敗D(skyline 固定間引きが重要情報を落とす): 各時刻の最上声部・小節頭・
  長音は保護され、弱拍/短音から先に落ちることを検証。
- 失敗K(コントロール不能): level→間引きは決定的・単調。落下記録が理由付きで
  返り、生存音の timing/pitch は不変(削除のみ)であることを検証。
- 失敗J(拍位置が死ぬ): 生き残る音符が改変されないことを検証。
- 失敗H(下げすぎで無音): level=1.0 でも骨格(skyline かつ小節頭)は残す。
"""

from math import isnan

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.density import (
    DroppedNote,
    simplify_density,
    simplify_density_verbose,
)


def note(start: float, dur: float, midi: int, conf: float = 0.9) -> QuantizedNote:
    """テスト用の QuantizedNote ファクトリ(実側は既定NaNのまま)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


class TestBasics:
    def test_empty_input_returns_empty(self):
        # Arrange
        notes: list[QuantizedNote] = []

        # Act
        result = simplify_density(notes, level=1.0)

        # Assert
        assert result == []

    def test_level_zero_is_no_change(self):
        # Arrange
        notes = [note(0.0, 1.0, 60), note(1.0, 0.5, 62), note(1.5, 0.5, 64)]

        # Act
        result = simplify_density(notes, level=0.0)

        # Assert: 内容・順序ともに入力と同一(非破壊)
        assert result == notes
        assert [n.midi for n in result] == [60, 62, 64]

    def test_level_zero_returns_new_list_not_same_object(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act
        result = simplify_density(notes, level=0.0)

        # Assert: 不変則(新規 list を返し元 list を破壊しない)
        assert result is not notes
        assert result == notes

    def test_does_not_mutate_input_list(self):
        # Arrange
        notes = [note(0.0, 1.0, 60), note(0.5, 0.25, 62), note(1.0, 1.0, 64)]
        original = list(notes)

        # Act
        simplify_density(notes, level=1.0)

        # Assert: 元 list は不変
        assert notes == original


class TestLevelRange:
    def test_negative_level_raises(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act / Assert
        with pytest.raises(ValueError):
            simplify_density(notes, level=-0.1)

    def test_level_above_one_raises(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act / Assert
        with pytest.raises(ValueError):
            simplify_density(notes, level=1.1)

    def test_non_positive_bar_beats_raises(self):
        # Arrange
        notes = [note(0.0, 1.0, 60)]

        # Act / Assert
        with pytest.raises(ValueError):
            simplify_density(notes, level=0.5, bar_beats=0.0)


class TestMonotonicAndDeterministic:
    def _dense_notes(self) -> list[QuantizedNote]:
        # 8分音符 16 個。強弱拍・高低音混在で保護スコアに差をつける。
        out: list[QuantizedNote] = []
        for i in range(16):
            start = i * 0.5
            dur = 1.0 if i % 4 == 0 else 0.5  # 小節頭は長音
            midi = 72 if i % 2 == 0 else 60    # 交互に高低
            out.append(note(start, dur, midi))
        return out

    def test_higher_level_removes_at_least_as_many(self):
        # Arrange
        notes = self._dense_notes()

        # Act: level を上げると残存数は単調に減る(増えない)
        counts = [len(simplify_density(notes, level=lv)) for lv in (0.0, 0.25, 0.5, 0.75, 1.0)]

        # Assert
        for earlier, later in zip(counts, counts[1:]):
            assert later <= earlier
        assert counts[0] == len(notes)   # level=0 は無変更
        assert counts[-1] < len(notes)   # level=1 は減っている

    def test_deterministic_same_input_same_output(self):
        # Arrange
        notes = self._dense_notes()

        # Act
        a = simplify_density(notes, level=0.6)
        b = simplify_density(notes, level=0.6)

        # Assert: 同一入力+level は完全一致
        assert a == b


class TestProtectsImportantNotes:
    def test_skyline_top_note_survives_over_inner_voice(self):
        # Arrange: 同一 start_beats に高音(skyline)と低音(内声)。低音は短く弱い。
        top = note(0.0, 1.0, 76, conf=0.9)     # skyline かつ小節頭かつ長音
        inner = note(0.0, 0.25, 60, conf=0.3)  # 非最上・短音・低確信
        filler = note(1.0, 0.25, 62, conf=0.3)
        notes = [top, inner, filler]

        # Act: 1 個だけ落とす程度の level
        kept = simplify_density(notes, level=0.4)

        # Assert: skyline の最上音は残る
        assert top in kept

    def test_bar_head_note_survives_at_max_level(self):
        # Arrange: 小節頭(拍0)の音 + 弱拍の短音たち
        bar_head = note(0.0, 1.0, 64)
        weak = [note(0.5, 0.25, 60), note(1.5, 0.25, 62), note(2.5, 0.25, 63)]
        notes = [bar_head] + weak

        # Act: 最大間引き
        kept = simplify_density(notes, level=1.0)

        # Assert: 骨格(skyline かつ小節頭)は最大 level でも残る
        assert bar_head in kept
        assert len(kept) >= 1

    def test_long_note_more_protected_than_short_note(self):
        # Arrange: 同じ弱拍位置帯で長音 vs 短音。どちらも非小節頭・同じ高さ。
        long_note = note(1.0, 2.0, 60, conf=0.5)   # 長音
        short_note = note(3.5, 0.25, 60, conf=0.5)  # 短音・弱拍
        # skyline を別音で占有させ、上記2音を内声側にする
        sky = note(0.0, 1.0, 80)
        notes = [sky, long_note, short_note]

        # Act: 1 個落とす
        kept = simplify_density(notes, level=0.34)

        # Assert: 短音の方が先に落ち、長音は残る
        assert long_note in kept
        assert short_note not in kept


class TestTimingPreserved:
    def test_surviving_notes_unchanged(self):
        # Arrange
        notes = [
            note(0.0, 1.0, 60),
            note(0.5, 0.25, 62),
            note(1.0, 1.0, 64),
            note(1.5, 0.25, 65),
        ]

        # Act
        kept = simplify_density(notes, level=0.5)

        # Assert: 生存音は元インスタンスと完全一致(timing/pitch を改変しない)
        for k in kept:
            assert k in notes

    def test_kept_notes_preserve_original_order(self):
        # Arrange
        notes = [note(float(i), 1.0, 60 + i) for i in range(8)]

        # Act
        kept = simplify_density(notes, level=0.5)

        # Assert: 残存音の start_beats は昇順(入力順を保つ)
        starts = [k.start_beats for k in kept]
        assert starts == sorted(starts)

    def test_nan_confidence_treated_as_low_and_no_crash(self):
        # Arrange: 実側 NaN 既定 + confidence を NaN にした音符
        weird = QuantizedNote(
            start_beats=0.5, dur_beats=0.25, midi=61, confidence=float("nan")
        )
        strong = note(0.0, 1.0, 72)
        notes = [strong, weird]

        # Act
        kept = simplify_density(notes, level=0.5)

        # Assert: 例外なく処理でき、低確信の weird が先に落ちる
        assert strong in kept
        assert weird not in kept
        # 元の NaN は保持されていること(改変していない証跡)
        assert isnan(weird.confidence)


class TestVerboseReport:
    def test_kept_plus_dropped_equals_input(self):
        # Arrange
        notes = [note(float(i) * 0.5, 0.5, 60 + (i % 3)) for i in range(12)]

        # Act
        kept, dropped = simplify_density_verbose(notes, level=0.6)

        # Assert: 分割は漏れ・重複なし(input = kept + dropped)
        assert len(kept) + len(dropped) == len(notes)
        dropped_indices = {d.index for d in dropped}
        assert len(dropped_indices) == len(dropped)  # index 重複なし

    def test_dropped_records_have_reason_and_original_note(self):
        # Arrange
        notes = [note(0.0, 1.0, 72), note(0.5, 0.25, 60), note(1.5, 0.25, 61)]

        # Act
        kept, dropped = simplify_density_verbose(notes, level=1.0)

        # Assert: 落下記録は理由と元インスタンスを持つ(復元可能)
        assert all(isinstance(d, DroppedNote) for d in dropped)
        for d in dropped:
            assert d.reason  # 空でない日本語理由
            assert d.note in notes
            assert notes[d.index] == d.note

    def test_dropped_sorted_by_index(self):
        # Arrange
        notes = [note(float(i) * 0.5, 0.25, 60 + i) for i in range(10)]

        # Act
        _, dropped = simplify_density_verbose(notes, level=0.7)

        # Assert
        indices = [d.index for d in dropped]
        assert indices == sorted(indices)

    def test_public_and_verbose_agree_on_kept(self):
        # Arrange
        notes = [note(float(i) * 0.5, 0.5, 60 + (i % 4)) for i in range(14)]

        # Act
        public_kept = simplify_density(notes, level=0.55)
        verbose_kept, _ = simplify_density_verbose(notes, level=0.55)

        # Assert: 2 つの公開 API は同じ生存集合を返す
        assert public_kept == verbose_kept
