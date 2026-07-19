"""耳層(多声): basic-pitch による多重音高検出。

basic-pitch は Python 3.14 に未対応のため、3.12 venv 上の bp_worker.py を
subprocess で呼び出す(契約は JSON)。エンジン層に楽器固有の分岐は持たない(NF-050)。
"""

import json
import os
import subprocess
from pathlib import Path

from earpipe.contracts import PitchEvent

MIN_DUR_SEC = 0.05
MIN_CONFIDENCE = 0.15  # basic-pitchのamplitudeは控えめに出るため耳(単音)より低め

# 感度プロファイル(#32 取りこぼし救済): (onset_threshold, frame_threshold, min_conf)
# normal = basic-pitch 既定。high = 弱音・ソフトアタックを拾う低閾値
# (幽霊が増える分は postfilter(#31) が除去する両輪設計)
SENSITIVITY = {
    "normal": (0.5, 0.3, MIN_CONFIDENCE),
    "high": (0.3, 0.18, 0.08),
}
_WORKER = Path(__file__).with_name("bp_worker.py")
# basic-pitch用インタプリタの探索候補（上から優先。リポジトリレイアウト差を吸収）
_BP_PYTHON_CANDIDATES = (
    Path(__file__).resolve().parents[5] / "tools" / "ai-ears" / ".venv312" / "bin" / "python",
    Path(__file__).resolve().parents[4] / ".venv-bp" / "bin" / "python",  # OSSレイアウト: engine/.venv-bp
    Path(__file__).resolve().parents[5] / ".venv-bp" / "bin" / "python",  # OSSレイアウト: リポジトリ直下
)


def bp_python_path() -> str | None:
    """basic-pitch が動くインタプリタを探す。環境変数 EARPIPE_BP_PYTHON が最優先。"""
    env = os.environ.get("EARPIPE_BP_PYTHON")
    if env:
        return env if Path(env).exists() else None
    for cand in _BP_PYTHON_CANDIDATES:
        if cand.exists():
            return str(cand)
    return None


_REQUIRED_KEYS = frozenset({"onset", "offset", "midi", "confidence"})


def _validate_worker_json(raw: object) -> list[dict]:
    """bp_worker のJSON出力をプロセス間契約として検証する(レビューMEDIUM-2)。"""
    if not isinstance(raw, list):
        raise RuntimeError(
            f"bp_worker returned unexpected JSON type: {type(raw).__name__} (list expected)"
        )
    for r in raw:
        if not isinstance(r, dict) or not _REQUIRED_KEYS <= r.keys():
            raise RuntimeError(f"bp_worker JSON要素が契約({sorted(_REQUIRED_KEYS)})に違反: {r!r}")
    return raw


def detect_events_poly(
    path: str | Path,
    min_dur: float = MIN_DUR_SEC,
    min_conf: float | None = None,
    sensitivity: str = "normal",
) -> list[PitchEvent]:
    """音声ファイルから多声の音程イベント列を抽出する。

    検出できなかったもの・信頼度の低いものは黙って捨てるのではなく
    閾値で明示的にフィルタする(値は本docstringと定数で公開)。
    sensitivity: "normal"(既定) / "high"(低閾値・#32取りこぼし救済。postfilterと組で使う)。
    min_conf を明示指定した場合は感度プロファイルの min_conf より優先する。
    """
    if sensitivity not in SENSITIVITY:
        raise ValueError(
            f"sensitivity は {sorted(SENSITIVITY)} のいずれか(指定値: {sensitivity!r})"
        )
    onset_th, frame_th, profile_conf = SENSITIVITY[sensitivity]
    effective_conf = profile_conf if min_conf is None else min_conf
    py = bp_python_path()
    if py is None:
        raise RuntimeError(
            "basic-pitch 実行環境が見つかりません。"
            "tools/ai-ears/.venv312 を用意するか EARPIPE_BP_PYTHON を設定してください。"
        )
    proc = subprocess.run(
        [py, str(_WORKER), str(path), str(onset_th), str(frame_th)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"bp_worker failed: {proc.stderr[-500:]}")
    raw = _validate_worker_json(json.loads(proc.stdout))

    events = [
        PitchEvent(
            onset=r["onset"],
            offset=r["offset"],
            midi=r["midi"],
            confidence=r["confidence"],
        )
        for r in raw
        if (r["offset"] - r["onset"]) >= min_dur and r["confidence"] >= effective_conf
    ]
    return sorted(events, key=lambda e: (e.onset, e.midi))
