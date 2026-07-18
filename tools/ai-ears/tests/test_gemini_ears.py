"""gemini_ears の純粋部テスト(レビューHIGH-2対応)。API呼び出しは行わない。"""

import pathlib

import pytest

import gemini_ears


class TestLoadKey:
    def test_missing_env_file_raises_clear_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        with pytest.raises(SystemExit, match="見つかりません"):
            gemini_ears.load_key()

    def test_reads_key_from_env_file(self, tmp_path, monkeypatch):
        (tmp_path / ".gemini").mkdir()
        (tmp_path / ".gemini" / ".env").write_text('GEMINI_API_KEY="abc123"\n')
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        assert gemini_ears.load_key() == "abc123"

    def test_env_file_without_key_raises(self, tmp_path, monkeypatch):
        (tmp_path / ".gemini").mkdir()
        (tmp_path / ".gemini" / ".env").write_text("OTHER=1\n")
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        with pytest.raises(SystemExit, match="APIキー"):
            gemini_ears.load_key()


class TestModelsOverride:
    def test_default_models_nonempty(self):
        assert gemini_ears.MODELS, "MODELSが空でないこと"

    def test_to_wav_bytes_passthrough_for_wav(self, tmp_path):
        import numpy as np
        import soundfile as sf

        p = tmp_path / "a.wav"
        sf.write(p, np.zeros(1000, dtype=np.float32), 22050)
        data = gemini_ears.to_wav_bytes(str(p))
        assert data == p.read_bytes()
