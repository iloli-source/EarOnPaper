"""CLI(compare/inspect)の実挙動テスト。"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


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




if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
