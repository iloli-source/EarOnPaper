"""F-101 鍵盤運指推定(指番号自動付与・右手/左手割当)(Issue #92)のユニットテスト。

DP による指番号付与(値域1-5・系列一貫性)、音高中央値による左右手割当(簡易版)、
物理的到達不能・逆行運指などの失敗ケース抑制、縮退入力(空/休符/単音)を
AAA 形式で検証する。複数正解が本質のため「唯一の正解」ではなく「値域・整合性・
物理妥当性・決定性」を主に検証する(モジュール docstring の限界を参照)。
"""

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.piano_fingering import (
    MAX_FINGER,
    MAX_HAND_SPAN_SEMITONES,
    MIN_FINGER,
    assign_fingering,
)


def _note(midi: int, dur_beats: float = 1.0, start_beats: float = 0.0) -> QuantizedNote:
    """テスト用 QuantizedNote 生成ヘルパ(実側 onset/offset は既定 NaN のまま)。"""
    return QuantizedNote(
        start_beats=start_beats, dur_beats=dur_beats, midi=midi, confidence=0.9
    )


class TestFingerRangeAndShape:
    """指番号の値域(1-5)と戻り値の形(note_index/finger/hand)を検証する。"""

    def test_all_fingers_within_1_to_5(self):
        # Arrange: ハ長調音階 C4..C5
        notes = [_note(m) for m in (60, 62, 64, 65, 67, 69, 71, 72)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert all(MIN_FINGER <= r["finger"] <= MAX_FINGER for r in result)

    def test_result_keys_present(self):
        # Arrange
        notes = [_note(60), _note(62)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        for r in result:
            assert set(r.keys()) == {"note_index", "finger", "hand"}

    def test_one_result_per_playable_note(self):
        # Arrange: 全て実音
        notes = [_note(m) for m in (60, 62, 64)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert len(result) == 3

    def test_note_index_matches_input_order(self):
        # Arrange
        notes = [_note(60), _note(64), _note(67)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert: note_index は 0,1,2 の昇順
        assert [r["note_index"] for r in result] == [0, 1, 2]


class TestHandAssignment:
    """hand 引数に応じた右手/左手割当を検証する。"""

    def test_right_hand_all_right(self):
        # Arrange
        notes = [_note(m) for m in (60, 62, 64)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert all(r["hand"] == "right" for r in result)

    def test_left_hand_all_left(self):
        # Arrange
        notes = [_note(m) for m in (48, 50, 52)]
        # Act
        result = assign_fingering(notes, hand="left")
        # Assert
        assert all(r["hand"] == "left" for r in result)

    def test_auto_splits_low_and_high_by_median(self):
        # Arrange: 低音群(伴奏)と高音群(旋律)が明確に分離。奇数個ずつ配置し、
        # 中央値(>=median を right とする境界)で低音側 index0-2 が left、
        # 高音側 index3-5 が right に割れることを確認する。
        low = [_note(m) for m in (36, 38, 40)]        # index 0-2(全て中央値未満)
        high = [_note(m) for m in (72, 74, 76)]       # index 3-5(全て中央値以上)
        notes = low + high
        # Act: sorted=[36,38,40,72,74,76], (n-1)//2=2 → median=40。
        #      >=40 が right(40,72,74,76)、<40 が left(36,38)になるため、
        #      index2(midi40)は right に寄る点を検証で明示する。
        result = assign_fingering(notes, hand="auto")
        hand_by_index = {r["note_index"]: r["hand"] for r in result}
        # Assert: 低い2音は left、中央値ちょうど含む高音側4音は right
        assert all(hand_by_index[i] == "left" for i in (0, 1))
        assert all(hand_by_index[i] == "right" for i in (2, 3, 4, 5))

    def test_invalid_hand_raises(self):
        # Arrange
        notes = [_note(60)]
        # Act / Assert
        with pytest.raises(ValueError):
            assign_fingering(notes, hand="third")


class TestPhysicalPlausibility:
    """物理妥当性(到達不能の抑制・逆行運指の抑制)を検証する。"""

    def test_ascending_scale_fingers_generally_increase(self):
        # Arrange: 上行音階は指番号がおおむね増える(逆行は抑制されている)
        notes = [_note(m) for m in (60, 62, 64, 65, 67)]
        # Act
        result = assign_fingering(notes, hand="right")
        fingers = [r["finger"] for r in result]
        # Assert: 隣接で指が減る回数(逆行)は半数未満に抑えられる
        contrary = sum(1 for a, b in zip(fingers, fingers[1:]) if b < a)
        assert contrary < len(fingers) / 2

    def test_wide_leap_does_not_reuse_impossible_span(self):
        # Arrange: MAX_HAND_SPAN を大きく超える跳躍を含む片手列
        wide = MAX_HAND_SPAN_SEMITONES + 12
        notes = [_note(60), _note(60 + wide), _note(60)]
        # Act: 例外を出さず有効な運指を返すこと(到達不能でも破綻しない)
        result = assign_fingering(notes, hand="right")
        # Assert: 全指が値域内で、件数が一致する
        assert len(result) == 3
        assert all(MIN_FINGER <= r["finger"] <= MAX_FINGER for r in result)

    def test_repeated_same_pitch_stays_in_range(self):
        # Arrange: 同音反復(同じ指の使い回しは許容されるべき)
        notes = [_note(64) for _ in range(5)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert all(MIN_FINGER <= r["finger"] <= MAX_FINGER for r in result)


class TestDegenerateInput:
    """縮退入力(空/休符のみ/休符混在/単音)を検証する。"""

    def test_empty_returns_empty(self):
        # Arrange
        notes: list[QuantizedNote] = []
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert result == []

    def test_only_rests_returns_empty(self):
        # Arrange: midi<0 は休符 → 運指対象外
        notes = [_note(-1), _note(-1)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert result == []

    def test_rests_are_excluded_and_indices_preserved(self):
        # Arrange: index1 が休符。実音 index0,2 のみ結果に残る
        notes = [_note(60), _note(-1), _note(64)]
        # Act
        result = assign_fingering(notes, hand="right")
        indices = [r["note_index"] for r in result]
        # Assert
        assert indices == [0, 2]

    def test_single_note_returns_one_finger(self):
        # Arrange
        notes = [_note(60)]
        # Act
        result = assign_fingering(notes, hand="right")
        # Assert
        assert len(result) == 1
        assert MIN_FINGER <= result[0]["finger"] <= MAX_FINGER


class TestDeterminism:
    """決定性(同一入力は同一出力・同点タイブレークの安定)を検証する。"""

    def test_same_input_same_output(self):
        # Arrange
        notes = [_note(m) for m in (60, 64, 67, 72, 67, 64, 60)]
        # Act
        first = assign_fingering(notes, hand="right")
        second = assign_fingering(notes, hand="right")
        # Assert
        assert first == second

    def test_auto_output_sorted_by_note_index(self):
        # Arrange: 左右に散る入力でも note_index 昇順で返る
        notes = [_note(72), _note(40), _note(74), _note(43)]
        # Act
        result = assign_fingering(notes, hand="auto")
        indices = [r["note_index"] for r in result]
        # Assert
        assert indices == sorted(indices)
