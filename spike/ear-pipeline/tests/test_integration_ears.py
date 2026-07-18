"""統合: パイプライン出力を AIの耳(tools/ai-ears/ears.py) にかけ総合スコア≥0.8。"""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]  # プロジェクトルート(採譜/)
EARS = ROOT / "tools" / "ai-ears" / "ears.py"
EARS_PY = ROOT / "tools" / "ai-ears" / ".venv" / "bin" / "python"


@pytest.mark.skipif(not EARS.exists() or not EARS_PY.exists(), reason="ai-ears harness not present")
class TestAiEarsIntegration:
    def test_overall_score(self, simple_wav, tmp_path):
        from earpipe.pipeline import transcribe_file

        wav, _, _ = simple_wav
        midi = tmp_path / "simple.mid"
        transcribe_file(wav, out_midi=midi)
        proc = subprocess.run(
            [str(EARS_PY), str(EARS), "compare", "--original", str(wav), "--transcription", str(midi)],
            capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        result = json.loads(proc.stdout)
        score = result["overall"]["score"]
        assert score >= 0.8, f"AIの耳 総合スコア {score} < 0.8: {json.dumps(result['overall'], ensure_ascii=False)}"
