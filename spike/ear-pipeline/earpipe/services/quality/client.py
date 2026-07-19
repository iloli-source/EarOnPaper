"""qualityサービス: AIの耳(tools/ai-ears)への薄いクライアント層。

品質判定の実体は tools/ai-ears/ears.py。本層はコマンド組み立てと実行のみを担い、
エンジン本体(stem/ear/rhythm/notate)へは依存しない。
"""

import subprocess
from pathlib import Path

_AI_EARS = Path(__file__).resolve().parents[4].parent / "tools" / "ai-ears"


def build_compare_command(
    original: Path | str, transcription: Path | str, report: Path | str | None = None
) -> list[str]:
    """ears.py compare のコマンド列を組み立てる(実行はしない)。"""
    py = _AI_EARS / ".venv" / "bin" / "python"
    cmd = [
        str(py), str(_AI_EARS / "ears.py"), "compare",
        "--original", str(original),
        "--transcription", str(transcription),
    ]
    if report is not None:
        cmd += ["--report", str(report)]
    return cmd


def run_compare(
    original: Path | str, transcription: Path | str, report: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """AIの耳で比較評価を実行する。"""
    return subprocess.run(
        build_compare_command(original, transcription, report),
        capture_output=True, text=True, check=False,
    )
