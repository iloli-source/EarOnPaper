"""装飾音・演奏ノイズの記譜解釈(ornament.py・F-082/Issue #91)のテスト。

test_leadsheet.py の qn ヘルパに倣い、AAA(Arrange-Act-Assert)形式で
微小音符の装飾候補分類・非破壊性・保守的な判定保留・境界条件を検証する。
先行研究 F-082-grok の失敗例(偽音符化・32分羅列・付け先無し grace)への
保守挙動を回帰として固定する。
"""

from math import isnan

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.ornament import (
    JUDGE_GRACE,
    JUDGE_INDETERMINATE,
    JUDGE_KEEP_AS_NOTE,
    KIND_ACCIACCATURA,
    KIND_GRACE,
    interpret_ornaments,
)


def qn(
    start: float,
    dur: float,
    midi: int,
    conf: float = 0.9,
) -> QuantizedNote:
    """量子化音符を1つ作るヘルパ(test_leadsheet.py に倣う)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


class TestBasicClassification:
    def test_tiny_note_before_main_is_grace_candidate(self) -> None:
        # Arrange: 極短の微小音符(C#4)→ 主音(C4, 1拍)
        notes = [qn(0.0, 0.1, 61), qn(0.1, 1.0, 60)]

        # Act
        out, orn = interpret_ornaments(notes, min_main_beats=0.25)

        # Assert: 装飾候補が1件、後続主音(index 1)へ before で付く
        assert len(orn) == 1
        cand = orn[0]
        assert cand["index"] == 0
        assert cand["judgement"] == JUDGE_GRACE
        assert cand["main_index"] == 1
        assert cand["direction"] == "before"
        assert cand["interval_semitones"] == 1
        # 非破壊: 出力は入力と同一内容の新規 list
        assert out == notes
        assert out is not notes

    def test_all_full_length_notes_yield_no_ornaments(self) -> None:
        # Arrange: すべて閾値以上の本音符
        notes = [qn(0.0, 1.0, 60), qn(1.0, 1.0, 62), qn(2.0, 2.0, 64)]

        # Act
        out, orn = interpret_ornaments(notes, min_main_beats=0.25)

        # Assert
        assert orn == []
        assert out == notes

    def test_acciaccatura_kind_for_extremely_short(self) -> None:
        # Arrange: 32分以下の極短装飾(半音下)→ 主音
        notes = [qn(0.0, 0.0625, 59), qn(0.0625, 1.0, 60)]

        # Act
        _, orn = interpret_ornaments(notes)

        # Assert: 短前打音(acciaccatura)に分類
        assert orn[0]["judgement"] == JUDGE_GRACE
        assert orn[0]["kind"] == KIND_ACCIACCATURA

    def test_grace_kind_for_short_but_not_tiny(self) -> None:
        # Arrange: 極短ではないが閾値未満(0.2拍)の装飾
        notes = [qn(0.0, 0.2, 62), qn(0.2, 1.0, 60)]

        # Act
        _, orn = interpret_ornaments(notes, min_main_beats=0.25)

        # Assert: 一般の装飾(grace)に分類
        assert orn[0]["judgement"] == JUDGE_GRACE
        assert orn[0]["kind"] == KIND_GRACE


class TestConservativePitfalls:
    def test_low_confidence_tiny_is_indeterminate(self) -> None:
        # Arrange: 微小だが低確信(偽音符=弦こすれ/息音の可能性。grok F10/F16)
        notes = [qn(0.0, 0.1, 61, conf=0.2), qn(0.1, 1.0, 60)]

        # Act
        _, orn = interpret_ornaments(notes)

        # Assert: 装飾と断定せず判定保留(kind は非設定)
        assert orn[0]["judgement"] == JUDGE_INDETERMINATE
        assert orn[0]["kind"] == ""

    def test_wide_leap_tiny_is_indeterminate(self) -> None:
        # Arrange: 主音から遠く跳躍(オクターブ)する微小音符は装飾より跳躍音符寄り
        notes = [qn(0.0, 0.1, 72), qn(0.1, 1.0, 60)]

        # Act
        _, orn = interpret_ornaments(notes)

        # Assert: 判定保留
        assert orn[0]["judgement"] == JUDGE_INDETERMINATE

    def test_isolated_tiny_without_main_kept_as_note(self) -> None:
        # Arrange: 隣接主音が無い(全部微小)→ 付け先無し。宙に浮く grace を作らない
        notes = [qn(0.0, 0.1, 60), qn(0.1, 0.1, 62)]

        # Act
        _, orn = interpret_ornaments(notes)

        # Assert: どちらも本音符として保持
        assert len(orn) == 2
        assert all(c["judgement"] == JUDGE_KEEP_AS_NOTE for c in orn)
        assert all(c["main_index"] is None for c in orn)
        assert all(c["direction"] is None for c in orn)
        assert all(c["interval_semitones"] is None for c in orn)

    def test_trailing_tiny_attaches_after_preceding_main(self) -> None:
        # Arrange: 末尾の微小音符は先行主音へ after(後打)で付く
        notes = [qn(0.0, 1.0, 60), qn(1.0, 0.1, 62)]

        # Act
        _, orn = interpret_ornaments(notes)

        # Assert
        assert orn[0]["index"] == 1
        assert orn[0]["main_index"] == 0
        assert orn[0]["direction"] == "after"
        assert orn[0]["judgement"] == JUDGE_GRACE


class TestNonDestructiveAndInputIntegrity:
    def test_output_is_new_list_not_mutating_input(self) -> None:
        # Arrange
        notes = [qn(0.0, 0.1, 61), qn(0.1, 1.0, 60)]
        snapshot = list(notes)

        # Act
        out, _ = interpret_ornaments(notes)

        # Assert: 入力 list は変更されず、出力は別オブジェクト
        assert notes == snapshot
        assert out is not notes
        assert out == notes

    def test_nan_confidence_normalized_to_zero_and_indeterminate(self) -> None:
        # Arrange: onset/offset 未設定(旧4引数構築)で confidence NaN 相当
        note = QuantizedNote(
            start_beats=0.0, dur_beats=0.1, midi=61, confidence=float("nan")
        )
        notes = [note, qn(0.1, 1.0, 60)]

        # Act
        _, orn = interpret_ornaments(notes)

        # Assert: NaN は 0.0 に正規化され、低確信として判定保留
        assert not isnan(orn[0]["confidence"])
        assert orn[0]["confidence"] == 0.0
        assert orn[0]["judgement"] == JUDGE_INDETERMINATE

    def test_empty_input_returns_empty(self) -> None:
        # Arrange / Act
        out, orn = interpret_ornaments([])

        # Assert
        assert out == []
        assert orn == []


class TestBoundaryAndValidation:
    def test_note_exactly_at_threshold_is_main(self) -> None:
        # Arrange: 拍長がちょうど閾値の音符は微小ではない(< で判定)
        notes = [qn(0.0, 0.25, 61), qn(0.25, 1.0, 60)]

        # Act
        _, orn = interpret_ornaments(notes, min_main_beats=0.25)

        # Assert: 装飾候補ゼロ
        assert orn == []

    def test_non_positive_threshold_raises(self) -> None:
        # Arrange
        notes = [qn(0.0, 0.1, 60)]

        # Act / Assert
        for bad in (0.0, -0.5):
            try:
                interpret_ornaments(notes, min_main_beats=bad)
                raised = False
            except ValueError:
                raised = True
            assert raised, f"min_main_beats={bad} で ValueError を期待"
