"""区間選択採譜の区間切り出しテスト(F-007・Issue #105)。

crop_region の核心要件を AAA 形式で検証する:
    (a) 指定区間を正しい長さで切り出す
    (b) 境界にフェードがかかり切り口の振幅が 0 側へ収束する(クリック回避)
    (c) 入力 y を破壊しない(immutable)
    (d) 範囲外・不正入力は ValueError で fail-fast する
    (e) edge_fade_sec=0 やフェードが区間長を超える退化ケースが安全
"""

import numpy as np
import pytest

from earpipe.services.stem.region_select import crop_region

SR = 22050


def _tone(sec: float, freq: float = 440.0, amp: float = 0.5) -> np.ndarray:
    """指定秒のサイン波(既定振幅0.5)を作る。"""
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t)


class TestCropLength:
    def test_crops_expected_span(self):
        # Arrange: 5秒の音から 1.0〜3.0秒を切り出す
        y = _tone(5.0)

        # Act
        region = crop_region(y, SR, 1.0, 3.0)

        # Assert: 約2秒分(丸め誤差1サンプル以内)
        expected = int(round(2.0 * SR))
        assert abs(len(region) - expected) <= 1
        assert region.ndim == 1

    def test_start_zero_is_allowed(self):
        # Arrange
        y = _tone(2.0)

        # Act: 先頭からの切り出し
        region = crop_region(y, SR, 0.0, 1.0)

        # Assert
        assert abs(len(region) - int(round(1.0 * SR))) <= 1


class TestEdgeFade:
    def test_boundaries_are_faded_to_near_zero(self):
        # Arrange: 一定振幅の音(切り口は本来クリックになる)
        y = _tone(3.0, amp=0.5)

        # Act: 明示的なフェードで切り出し
        region = crop_region(y, SR, 0.5, 2.5, edge_fade_sec=0.01)

        # Assert: 先頭・末尾サンプルは 0 付近(元振幅0.5より十分小)
        assert abs(region[0]) < 0.05
        assert abs(region[-1]) < 0.05

    def test_interior_amplitude_is_preserved(self):
        # Arrange
        y = _tone(3.0, amp=0.5)

        # Act
        region = crop_region(y, SR, 0.5, 2.5, edge_fade_sec=0.005)

        # Assert: 中央部はフルスケール(0.5)近くを保つ(実音を潰さない)
        mid = len(region) // 2
        window = region[mid - 100 : mid + 100]
        assert np.abs(window).max() > 0.45

    def test_zero_fade_leaves_edges_untouched(self):
        # Arrange
        y = _tone(2.0, amp=0.5)

        # Act: フェードなし
        region = crop_region(y, SR, 0.5, 1.5, edge_fade_sec=0.0)

        # Assert: 切り出し部と元波形の対応区間が完全一致
        start = int(round(0.5 * SR))
        end = int(round(1.5 * SR))
        np.testing.assert_array_equal(region, y[start:end])

    def test_fade_longer_than_region_is_clipped_safely(self):
        # Arrange: 20ms の極短区間に 1秒のフェード指定(区間長の半分にクリップ)
        y = _tone(1.0, amp=0.5)

        # Act
        region = crop_region(y, SR, 0.1, 0.12, edge_fade_sec=1.0)

        # Assert: 例外なく・長さ維持・端は 0 付近
        assert len(region) > 0
        assert abs(region[0]) < 0.05


class TestImmutability:
    def test_input_is_not_mutated(self):
        # Arrange
        y = _tone(2.0, amp=0.5)
        original = y.copy()

        # Act
        _ = crop_region(y, SR, 0.5, 1.5, edge_fade_sec=0.01)

        # Assert: 入力波形は不変
        np.testing.assert_array_equal(y, original)

    def test_result_is_independent_copy(self):
        # Arrange
        y = _tone(2.0, amp=0.5)

        # Act
        region = crop_region(y, SR, 0.0, 1.0, edge_fade_sec=0.0)
        region[0] = 999.0

        # Assert: 返り値を書き換えても元は不変(ビューではない)
        assert y[0] != 999.0


class TestValidation:
    def test_negative_start_raises(self):
        y = _tone(2.0)
        with pytest.raises(ValueError):
            crop_region(y, SR, -0.1, 1.0)

    def test_end_not_after_start_raises(self):
        y = _tone(2.0)
        with pytest.raises(ValueError):
            crop_region(y, SR, 1.0, 1.0)

    def test_out_of_range_raises(self):
        # 波形長(2秒)を超える区間は空になり ValueError
        y = _tone(2.0)
        with pytest.raises(ValueError):
            crop_region(y, SR, 5.0, 6.0)

    def test_non_positive_sr_raises(self):
        y = _tone(2.0)
        with pytest.raises(ValueError):
            crop_region(y, 0, 0.0, 1.0)

    def test_negative_fade_raises(self):
        y = _tone(2.0)
        with pytest.raises(ValueError):
            crop_region(y, SR, 0.0, 1.0, edge_fade_sec=-0.001)

    def test_non_1d_input_raises(self):
        y = np.zeros((100, 2))  # ステレオ形状は非対応
        with pytest.raises(ValueError):
            crop_region(y, SR, 0.0, 0.001)

    def test_end_clipped_to_length_still_valid(self):
        # end_sec が総尺をわずかに超える場合は末尾へクリップし成功する
        # Arrange
        y = _tone(2.0)

        # Act
        region = crop_region(y, SR, 1.0, 2.5)

        # Assert: 1.0秒〜末尾(2.0秒)= 約1秒
        assert abs(len(region) - int(round(1.0 * SR))) <= 1
