"""CLI(compare/inspect)の実挙動テストと、gemini_ears の純粋関数のテスト。"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import gemini_ears

HARNESS_DIR = Path(__file__).resolve().parent.parent
PYTHON = str(HARNESS_DIR / ".venv/bin/python")


@pytest.mark.integration
class TestCli:
    def test_compare_outputs_json_and_report(self, reference_audio, reference_midi, tmp_path):
        report = tmp_path / "report.md"
        proc = subprocess.run(
            [PYTHON, str(HARNESS_DIR / "ears.py"), "compare",
             "--original", str(reference_audio),
             "--transcription", str(reference_midi),
             "--report", str(report)],
            capture_output=True, text=True, timeout=300,
        )
        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout)
        assert result["overall"]["score"] >= 0.8
        assert report.exists()
        assert "総合スコア" in report.read_text()

    def test_inspect_health_only(self, reference_midi):
        proc = subprocess.run(
            [PYTHON, str(HARNESS_DIR / "ears.py"), "inspect",
             "--transcription", str(reference_midi)],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout)
        assert set(result.keys()) == {"health"}
        assert 0.0 <= result["health"]["score"] <= 1.0

    def test_missing_subcommand_fails(self):
        proc = subprocess.run(
            [PYTHON, str(HARNESS_DIR / "ears.py")],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode != 0


@pytest.mark.unit
class TestGeminiEarsPureParts:
    """gemini_ears のAPI非依存部分のみテスト(API呼び出し部はカバレッジ除外・理由はconfig参照)。"""

    def test_load_key_reads_env_file(self, monkeypatch, tmp_path):
        gem_dir = tmp_path / ".gemini"
        gem_dir.mkdir()
        (gem_dir / ".env").write_text('GEMINI_API_KEY="test-key-123"\n')
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        assert gemini_ears.load_key() == "test-key-123"

    def test_load_key_missing_exits(self, monkeypatch, tmp_path):
        gem_dir = tmp_path / ".gemini"
        gem_dir.mkdir()
        (gem_dir / ".env").write_text("OTHER=1\n")
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        with pytest.raises(SystemExit):
            gemini_ears.load_key()

    def test_to_wav_bytes_passthrough(self, reference_audio):
        data = gemini_ears.to_wav_bytes(str(reference_audio))
        assert data[:4] == b"RIFF"

    def test_prompt_requests_structured_json(self):
        assert "ear_or_notation" in gemini_ears.PROMPT
        assert "estimated_fix_effort" in gemini_ears.PROMPT


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
