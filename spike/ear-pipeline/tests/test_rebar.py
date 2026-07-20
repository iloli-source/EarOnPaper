"""rebar(小節・拍オフセット系統補正／リバーリング・F-083)のユニットテスト。

先行研究(F-083-grok/codex)の落とし穴を回帰で固定する:
- 系統8分ずれの検出と先頭拍への再整列(rebarring)
- 過補正の回避(既に合っている列・ルバート列は触らない)
- 実タイミング(onset_sec/offset_sec)の保持(C3)
- 手動同期点の区分線形補間と誤入力の早期拒否
"""

import math

import numpy as np
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.rhythm.rebar import (
    MAX_PHASE_SHIFT_BEATS,
    add_sync_points,
    correct_beat_offset,
)


def _note(start_beats: float, midi: int = 60, dur: float = 0.5) -> QuantizedNote:
    """実タイミングは start_beats=1拍/秒 相当で機械的に埋めたテスト用音符。"""
    return QuantizedNote(
        start_beats=start_beats,
        dur_beats=dur,
        midi=midi,
        confidence=0.9,
        onset_sec=start_beats,
        offset_sec=start_beats + dur,
    )


def _aligned_notes() -> list[QuantizedNote]:
    """8分格子にぴたり乗った16音(0.0, 0.5, ... 7.5拍)。"""
    return [_note(i * 0.5, midi=60 + (i % 5)) for i in range(16)]


# --- correct_beat_offset: 系統8分ずれの検出と再整列 ---


def test_detects_systematic_sub_grid_latency_and_realigns_to_grid():
    # Arrange: 全ノートが一様に 0.06拍(格子未満のオンセット遅延)後ろへずれた列。
    # これが検出可能な「系統的な拍位相ずれ」= 格子に対する共通の端数。
    grid_per_beat = 4
    offset = 0.06
    notes = [
        QuantizedNote(i * 0.5 + offset, 0.5, 60, 0.9, i * 0.5, i * 0.5 + 0.5)
        for i in range(16)
    ]

    # Act
    corrected, confidence = correct_beat_offset(notes, grid_per_beat)

    # Assert: 共通端数が打ち消され、先頭が格子頭(0.0)へ再整列する
    assert corrected[0].start_beats == pytest.approx(0.0, abs=1e-9)
    assert confidence > 0.8


def test_correction_preserves_real_timing_c3():
    # Arrange: 系統ずれのある列(実側は元イベント時刻)
    notes = [
        QuantizedNote(i * 0.5 + 0.2, 0.5, 60, 0.9, onset_sec=i * 0.37, offset_sec=i * 0.37 + 0.3)
        for i in range(16)
    ]

    # Act
    corrected, _ = correct_beat_offset(notes, grid_per_beat=4)

    # Assert: 格子側は動いても実タイミングは1つも変わらない(C3二重表現)
    for before, after in zip(notes, corrected):
        assert after.onset_sec == before.onset_sec
        assert after.offset_sec == before.offset_sec


def test_correction_shift_is_uniform_across_all_notes():
    # Arrange
    notes = [
        QuantizedNote(i * 0.5 + 0.2, 0.5, 60, 0.9, i * 0.5, i * 0.5 + 0.5)
        for i in range(16)
    ]

    # Act
    corrected, _ = correct_beat_offset(notes, grid_per_beat=4)

    # Assert: 相対間隔は不変(全体平行移動であり内部リズムを壊さない)
    orig_diffs = np.diff([n.start_beats for n in notes])
    new_diffs = np.diff([n.start_beats for n in corrected])
    assert np.allclose(orig_diffs, new_diffs)


# --- correct_beat_offset: 過補正の回避 ---


def test_does_not_touch_already_aligned_notes():
    # Arrange: 既に拍頭へ乗っている列
    notes = _aligned_notes()

    # Act
    corrected, _ = correct_beat_offset(notes, grid_per_beat=4)

    # Assert: 開始拍は一切変わらない(意味のないマイクロシフトを掛けない)
    assert [n.start_beats for n in corrected] == [n.start_beats for n in notes]


def test_rubato_scatter_is_not_corrected():
    # Arrange: 残差がランダムに散る(ルバート/揺れ)列
    rng = np.random.default_rng(0)
    notes = [
        QuantizedNote(i * 0.5 + float(rng.uniform(-0.2, 0.2)), 0.5, 60, 0.9, i * 0.5, i * 0.5 + 0.5)
        for i in range(24)
    ]

    # Act
    corrected, confidence = correct_beat_offset(notes, grid_per_beat=4)

    # Assert: 散らばりが大きいので補正せず、低信頼を返す(過補正回避)
    assert confidence == pytest.approx(0.0)
    assert [n.start_beats for n in corrected] == [n.start_beats for n in notes]


def test_too_few_notes_returns_zero_confidence_unchanged():
    # Arrange: 統計判定に足りない少数
    notes = [_note(0.2), _note(0.7)]

    # Act
    corrected, confidence = correct_beat_offset(notes, grid_per_beat=4)

    # Assert
    assert confidence == pytest.approx(0.0)
    assert [n.start_beats for n in corrected] == [n.start_beats for n in notes]


def test_input_list_is_not_mutated():
    # Arrange
    notes = [
        QuantizedNote(i * 0.5 + 0.2, 0.5, 60, 0.9, i * 0.5, i * 0.5 + 0.5)
        for i in range(16)
    ]
    snapshot = [n.start_beats for n in notes]

    # Act
    correct_beat_offset(notes, grid_per_beat=4)

    # Assert: 入力は破壊されない(immutability)
    assert [n.start_beats for n in notes] == snapshot


# --- correct_beat_offset: 境界検証 ---


def test_invalid_grid_per_beat_raises():
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        correct_beat_offset(_aligned_notes(), grid_per_beat=0)


def test_invalid_beats_per_bar_raises():
    with pytest.raises(ValueError):
        correct_beat_offset(_aligned_notes(), grid_per_beat=4, beats_per_bar=0)


def test_offset_stays_within_half_beat_bound_and_coarse_grid_is_safe():
    # Arrange: 粗い1拍格子で拍頭に乗った列(残差0=既に整列)。
    # 残差は構造上 [-subdiv/2, subdiv/2] に収まるため offset は常に |0.5| 拍以内。
    on_grid = [
        QuantizedNote(float(i), 0.5, 60, 0.9, float(i), float(i) + 0.5)
        for i in range(16)
    ]

    # Act
    corrected, _ = correct_beat_offset(on_grid, grid_per_beat=1)

    # Assert: 既に整列(offset≈0)なので不動。粗格子でも境界ロジックが破綻しない。
    assert [n.start_beats for n in corrected] == [n.start_beats for n in on_grid]
    assert MAX_PHASE_SHIFT_BEATS == 0.5


# --- add_sync_points: 区分線形補間 ---


def test_sync_points_linear_interpolation_between_anchors():
    # Arrange: measured 2拍→target 3拍、measured 6拍→target 8拍。
    # 区間内の 4拍(measured)は線形補間で 5.5拍(target)へ写る。
    notes = [_note(2.0), _note(4.0), _note(6.0)]
    points = [(2.0, 3.0), (6.0, 8.0)]

    # Act
    warped = add_sync_points(notes, points)

    # Assert
    assert warped[0].start_beats == pytest.approx(3.0)
    assert warped[1].start_beats == pytest.approx(5.5)
    assert warped[2].start_beats == pytest.approx(8.0)


def test_sync_points_single_point_is_constant_offset():
    # Arrange: 1点は一定オフセットの平行移動
    notes = [_note(1.0), _note(2.0), _note(3.0)]
    points = [(1.0, 2.5)]  # +1.5拍

    # Act
    warped = add_sync_points(notes, points)

    # Assert
    assert [n.start_beats for n in warped] == pytest.approx([2.5, 3.5, 4.5])


def test_sync_points_empty_returns_equivalent_notes():
    # Arrange
    notes = [_note(1.0), _note(2.0)]

    # Act
    warped = add_sync_points(notes, [])

    # Assert
    assert [n.start_beats for n in warped] == [1.0, 2.0]


def test_sync_points_extrapolates_outside_anchor_range():
    # Arrange: 同期点の外側(前方)の音符も潰れず端の傾きで外挿される
    notes = [_note(0.0), _note(2.0), _note(10.0)]
    points = [(2.0, 3.0), (6.0, 8.0)]  # 傾き 5/4 = 1.25

    # Act
    warped = add_sync_points(notes, points)

    # Assert: measured 0拍 → 3 + 1.25*(0-2) = 0.5拍(端値クランプなら3.0に潰れる)
    assert warped[0].start_beats == pytest.approx(0.5)
    # measured 10拍 → 8 + 1.25*(10-6) = 13.0拍
    assert warped[2].start_beats == pytest.approx(13.0)


def test_sync_points_preserve_real_timing():
    # Arrange
    notes = [_note(2.0), _note(6.0)]
    points = [(2.0, 3.0), (6.0, 8.0)]

    # Act
    warped = add_sync_points(notes, points)

    # Assert: 実タイミングは保持(C3)
    for before, after in zip(notes, warped):
        assert after.onset_sec == before.onset_sec
        assert after.offset_sec == before.offset_sec


def test_sync_points_reject_duplicate_measured_beat():
    # Arrange: 同一 measured_beat は傾き未定義
    notes = [_note(1.0)]
    points = [(2.0, 3.0), (2.0, 5.0)]

    # Act / Assert
    with pytest.raises(ValueError):
        add_sync_points(notes, points)


def test_sync_points_reject_order_reversing_targets():
    # Arrange: target が measured の順序を逆転(時間反転)する誤入力
    notes = [_note(1.0)]
    points = [(2.0, 8.0), (6.0, 3.0)]

    # Act / Assert
    with pytest.raises(ValueError):
        add_sync_points(notes, points)


def test_sync_points_does_not_mutate_input():
    # Arrange
    notes = [_note(2.0), _note(6.0)]
    snapshot = [n.start_beats for n in notes]

    # Act
    add_sync_points(notes, [(2.0, 3.0), (6.0, 8.0)])

    # Assert
    assert [n.start_beats for n in notes] == snapshot


def test_no_nan_or_inf_in_outputs():
    # Arrange
    notes = [
        QuantizedNote(i * 0.5 + 0.2, 0.5, 60, 0.9, i * 0.5, i * 0.5 + 0.5)
        for i in range(16)
    ]

    # Act
    corrected, conf = correct_beat_offset(notes, grid_per_beat=4)
    warped = add_sync_points(notes, [(0.0, 0.0), (7.5, 7.5)])

    # Assert
    assert math.isfinite(conf)
    assert all(math.isfinite(n.start_beats) for n in corrected)
    assert all(math.isfinite(n.start_beats) for n in warped)
