"""外部デバッグ EOP-DEBUG-20260721-001 のエンジン側修正の回帰テスト。

参照: docs/debug/EOP-DEBUG-20260721-001.md
- 3.11 tab.fold_to_range: 巨大MIDI値のwhileループDoS → 定数時間補正
- 3.12 jianpu._duration_suffix: +Infinity が OverflowError を起こす非対称ガード
- 3.13 jianpu._duration_suffix: 巨大有限音価で出力文字列が無制限増幅
"""

import math

import pytest

from earpipe.services.notate.jianpu import _MAX_DURATION_DASHES, _duration_suffix
from earpipe.services.notate.tab import MAX_FRET, TUNING_GUITAR, fold_to_range


class TestFoldToRangeExtreme:
    """3.11: 巨大/敵対的MIDIでも定数時間で音域内に収まる。"""

    @pytest.mark.parametrize("midi", [10**12, -(10**12), 10**9, -(10**9)])
    def test_extreme_midi_folds_into_range(self, midi: int) -> None:
        # Arrange
        lo, hi = TUNING_GUITAR[0], TUNING_GUITAR[-1] + MAX_FRET
        # Act — 旧whileループなら約833億回で停止していた。定数時間で即返る
        m, shift = fold_to_range(midi)
        # Assert — 音域内・オクターブ整合(shift*12で元へ戻る)
        assert lo <= m <= hi
        assert m == midi + 12 * shift

    def test_in_range_is_unchanged(self) -> None:
        m, shift = fold_to_range(60)
        assert (m, shift) == (60, 0)


class TestJianpuDurationNonFinite:
    """3.12: NaN/±Infinity で OverflowError を起こさず空サフィックスへ。"""

    @pytest.mark.parametrize("dur", [float("inf"), float("-inf"), float("nan")])
    def test_non_finite_returns_empty(self, dur: float) -> None:
        # Act / Assert — 例外を投げず空文字
        assert _duration_suffix(dur) == ""

    def test_non_positive_returns_empty(self) -> None:
        assert _duration_suffix(0.0) == ""
        assert _duration_suffix(-1.0) == ""


class TestJianpuDurationBounded:
    """3.13: 巨大有限音価でも出力文字列が有界(最大 _MAX_DURATION_DASHES 本)。"""

    @pytest.mark.parametrize("dur", [10**6, 10**12, 1e9])
    def test_huge_duration_is_bounded(self, dur: float) -> None:
        # Act
        s = _duration_suffix(float(dur))
        # Assert — " -" が最大 _MAX_DURATION_DASHES 本 = 2*16=32文字以内
        assert math.isfinite(dur)
        assert len(s) <= 2 * _MAX_DURATION_DASHES
        assert s == " -" * _MAX_DURATION_DASHES
