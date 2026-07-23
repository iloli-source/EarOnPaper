"""長尺チャンク分割のテスト(F-004・Issue #68)。

無音優先分割の核心要件を AAA 形式で検証する:
    (a) 単一短尺は1チャンク
    (b) max_sec 超過時は無音位置(中点)で分割し、音の途中で切らない
    (c) 無音が無ければ固定窓で強制分割し max_sec 制約を守る
    (d) 空入力は空list
    (e) 各チャンク端が低振幅(=無音)で、音の頭・減衰を削らない
"""

import numpy as np

from earpipe.services.stem.chunk import Chunk, split_into_chunks

SR = 22050


def _tone(sec: float, freq: float = 440.0) -> np.ndarray:
    """指定秒のサイン波(振幅0.5)を作る。"""
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * freq * t)


def _silence(sec: float) -> np.ndarray:
    """指定秒の無音を作る。"""
    return np.zeros(int(SR * sec))


class TestSingleShortChunk:
    def test_short_input_is_one_chunk(self):
        # Arrange: max_sec より十分短い単一の音
        y = _tone(2.0)

        # Act
        chunks = split_into_chunks(y, SR, max_sec=10.0)

        # Assert: 1チャンク・全域・index0
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].start_sec == 0.0
        assert abs(chunks[0].end_sec - len(y) / SR) < 1e-9
        assert len(chunks[0].samples) == len(y)


class TestSilenceAwareSplit:
    def test_splits_at_silence_gap(self):
        # Arrange: [3秒音][1秒無音][3秒音]、max_sec=4 → 1つ目の後で切れるはず
        y = np.concatenate([_tone(3.0), _silence(1.0), _tone(3.0)])

        # Act
        chunks = split_into_chunks(y, SR, max_sec=4.0, min_silence_sec=0.3)

        # Assert: 複数チャンク・区間は連続・全チャンクmax_sec以下
        assert len(chunks) >= 2
        assert chunks[0].start_sec == 0.0
        for c in chunks:
            assert c.end_sec - c.start_sec <= 4.0 + 1e-6
        # 境界は無音帯(3.0〜4.0秒)の中点=3.5秒付近(固定窓4.0より手前)
        assert 3.3 < chunks[0].end_sec < 3.7

    def test_chunks_are_contiguous(self):
        # Arrange
        y = np.concatenate([_tone(3.0), _silence(1.0), _tone(3.0)])

        # Act
        chunks = split_into_chunks(y, SR, max_sec=4.0, min_silence_sec=0.3)

        # Assert: 隙間なく連続し末尾が全長に一致
        for a, b in zip(chunks[:-1], chunks[1:]):
            assert abs(a.end_sec - b.start_sec) < 1e-9
        assert abs(chunks[-1].end_sec - len(y) / SR) < 1e-6


class TestFixedWindowFallback:
    def test_no_silence_uses_fixed_window(self):
        # Arrange: 無音のない連続音・6秒、max_sec=2 → 固定窓で3分割
        y = _tone(6.0)

        # Act
        chunks = split_into_chunks(y, SR, max_sec=2.0, min_silence_sec=0.3)

        # Assert: 全チャンクmax_sec以下・被覆完全
        assert len(chunks) >= 3
        for c in chunks:
            assert c.end_sec - c.start_sec <= 2.0 + 1e-6
        assert chunks[0].start_sec == 0.0
        assert abs(chunks[-1].end_sec - len(y) / SR) < 1e-6

    def test_pure_silence_is_safe(self):
        # Arrange: 全無音・長尺(splitは全域1区間を返す→候補ゼロ→固定窓)
        y = _silence(6.0)

        # Act
        chunks = split_into_chunks(y, SR, max_sec=2.0)

        # Assert: 例外なく分割・start<end不変条件
        assert len(chunks) >= 3
        for c in chunks:
            assert c.start_sec < c.end_sec


class TestEmptyInput:
    def test_empty_returns_empty_list(self):
        # Arrange / Act
        chunks = split_into_chunks(np.array([]), SR, max_sec=10.0)

        # Assert
        assert chunks == []


class TestBoundaryNotInSound:
    def test_boundary_lands_in_silence(self):
        # Arrange: 音-無音-音、max_sec超で無音位置分割を強制
        y = np.concatenate([_tone(3.0), _silence(1.0), _tone(3.0)])

        # Act
        chunks = split_into_chunks(y, SR, max_sec=4.0, min_silence_sec=0.3)

        # Assert: 各チャンクの端(±10ms)が低振幅=音の途中で切っていない
        edge = SR // 100  # 10ms
        for c in chunks:
            head = np.abs(c.samples[:edge]).max()
            tail = np.abs(c.samples[-edge:]).max()
            # 少なくとも一方の端は無音側(中点分割なので端は無音帯に接する)
            assert head < 0.05 or tail < 0.05


class TestChunkDataclass:
    def test_chunk_fields_are_frozen(self):
        # Arrange
        c = Chunk(index=0, start_sec=0.0, end_sec=1.0, samples=np.zeros(4))

        # Act / Assert: frozen なので属性代入は不可
        import dataclasses

        try:
            c.index = 1  # type: ignore[misc]
            assert False, "frozen のはず"
        except dataclasses.FrozenInstanceError:
            pass

class TestInputValidation:
    def test_rejects_non_positive_or_extreme_sample_rate(self):
        import pytest
        y = np.zeros(1, dtype=np.float32)
        for sr in (0, -1, 384001, 1.5):
            with pytest.raises(ValueError):
                split_into_chunks(y, sr)  # type: ignore[arg-type]

    def test_rejects_non_finite_or_extreme_durations(self):
        import pytest
        y = np.zeros(1, dtype=np.float32)
        for value in (0.0, -1.0, float('nan'), float('inf'), 86401.0):
            with pytest.raises(ValueError):
                split_into_chunks(y, SR, max_sec=value)
        for value in (-1.0, float('nan'), float('inf'), 86401.0):
            with pytest.raises(ValueError):
                split_into_chunks(y, SR, min_silence_sec=value)

    def test_rejects_stereo_nonnumeric_and_nonfinite_waveforms(self):
        import pytest
        bad = [
            np.zeros((2, 2), dtype=np.float32),
            np.array(['audio'], dtype=object),
            np.array([np.nan], dtype=np.float32),
            np.array([np.inf], dtype=np.float32),
        ]
        for y in bad:
            with pytest.raises(ValueError):
                split_into_chunks(y, SR)
