"""ステム分離(F-003)のテスト。

Demucs は重い別venv依存のため、実分離テストは demucs_available() で skip する。
分離不能時の正直なエラー・ステム名検証・出力パス構造は環境非依存で検証する。
"""

import numpy as np
import pytest
import soundfile as sf

from earpipe.services.stem.separate import (
    MELODIC_STEMS,
    STEMS,
    SeparationResult,
    StemSeparationUnavailable,
    demucs_available,
    demucs_python_path,
    separate_stems,
)


class TestAvailability:
    def test_python_path_returns_str_or_none(self):
        p = demucs_python_path()
        assert p is None or isinstance(p, str)

    def test_available_is_bool(self):
        assert isinstance(demucs_available(), bool)


class TestGracefulUnavailable:
    def test_raises_when_unavailable(self, tmp_path, monkeypatch):
        # Arrange — demucs を「使えない環境」に固定
        monkeypatch.setattr(
            "earpipe.services.stem.separate.demucs_python_path", lambda: None
        )
        wav = tmp_path / "x.wav"
        sf.write(wav, np.zeros(2048, dtype=np.float32), 22050)
        # Act / Assert — 黙って劣化させず明示エラー
        with pytest.raises(StemSeparationUnavailable):
            separate_stems(wav, tmp_path / "out")

    def test_missing_input_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "earpipe.services.stem.separate.demucs_python_path",
            lambda: "/usr/bin/python3",
        )
        with pytest.raises(FileNotFoundError):
            separate_stems(tmp_path / "nope.wav", tmp_path / "out")


class TestStemConstants:
    def test_stems_are_four(self):
        assert STEMS == ("vocals", "drums", "bass", "other")

    def test_melodic_excludes_drums(self):
        assert "drums" not in MELODIC_STEMS
        assert set(MELODIC_STEMS) <= set(STEMS)


class TestSeparationResult:
    def test_melodic_filters_drums(self, tmp_path):
        # Arrange
        res = SeparationResult(
            stems={s: tmp_path / f"{s}.wav" for s in STEMS}, model="htdemucs"
        )
        # Act
        mel = res.melodic()
        # Assert
        assert "drums" not in mel
        assert set(mel) == set(MELODIC_STEMS)


@pytest.mark.skipif(not demucs_available(), reason="Demucs 未導入(別venv)")
class TestRealSeparation:
    def test_separates_into_four_stems(self, tmp_path):
        # 合成の短い正弦波を分離(内容の質は問わず、4ステムwavが出ることを確認)
        wav = tmp_path / "tone.wav"
        t = np.linspace(0, 3.0, int(22050 * 3.0), endpoint=False)
        sf.write(wav, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), 22050)
        res = separate_stems(wav, tmp_path / "out")
        assert set(res.stems) <= set(STEMS)
        assert len(res.stems) >= 1
        for p in res.stems.values():
            assert p.exists() and p.stat().st_size > 0
