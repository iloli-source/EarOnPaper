"""耳層(多声): basic-pitch による多重音高検出。

basic-pitch は Python 3.14 に未対応のため、3.12 venv 上の bp_worker.py を
subprocess で呼び出す(契約は JSON)。エンジン層に楽器固有の分岐は持たない(NF-050)。
"""

import json
import os
import subprocess
from pathlib import Path

from earpipe.ear import PitchEvent

MIN_DUR_SEC = 0.05
MIN_CONFIDENCE = 0.15  # basic-pitchのamplitudeは控えめに出るため耳(単音)より低め
_WORKER = Path(__file__).with_name("bp_worker.py")
_DEFAULT_BP_PYTHON = (
    Path(__file__).resolve().parents[3] / "tools" / "ai-ears" / ".venv312" / "bin" / "python"
)


def bp_python_path() -> str | None:
    """basic-pitch が動くインタプリタを探す。環境変数 EARPIPE_BP_PYTHON が最優先。"""
    env = os.environ.get("EARPIPE_BP_PYTHON")
    if env:
        return env if Path(env).exists() else None
    if _DEFAULT_BP_PYTHON.exists():
        return str(_DEFAULT_BP_PYTHON)
    return None


def detect_events_poly(
    path,
    min_dur: float = MIN_DUR_SEC,
    min_conf: float = MIN_CONFIDENCE,
) -> list[PitchEvent]:
    """音声ファイルから多声の音程イベント列を抽出する。

    検出できなかったもの・信頼度の低いものは黙って捨てるのではなく
    閾値で明示的にフィルタする(値は本docstringと定数で公開)。
    """
    py = bp_python_path()
    if py is None:
        raise RuntimeError(
            "basic-pitch 実行環境が見つかりません。"
            "tools/ai-ears/.venv312 を用意するか EARPIPE_BP_PYTHON を設定してください。"
        )
    proc = subprocess.run(
        [py, str(_WORKER), str(path)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"bp_worker failed: {proc.stderr[-500:]}")
    raw = json.loads(proc.stdout)

    events = [
        PitchEvent(
            onset=r["onset"],
            offset=r["offset"],
            midi=r["midi"],
            confidence=r["confidence"],
        )
        for r in raw
        if (r["offset"] - r["onset"]) >= min_dur and r["confidence"] >= min_conf
    ]
    return sorted(events, key=lambda e: (e.onset, e.midi))
