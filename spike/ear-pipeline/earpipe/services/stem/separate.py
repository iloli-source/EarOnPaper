"""ステム分離(F-003): Demucs による vocals/drums/bass/other の4ステム分離。

設計方針(先行リサーチ docs/research/engine-select-*.md の反映):
- **常時ONにしない**。分離は採譜を改善することも悪化させることもある(分離アーティファクト
  =空洞アタック・広帯域ノイズ・境界アーティファクトがオンセット/ピッチを破壊、
  オラクルステム比で約10ptのWER悪化の実測)。よってオプトイン＋品質ゲート＋
  「分離あり/なしのA/B」で運用する(quality_gate参照)。
- **4-stem を使う**(6-stemはpianoに大量のbleed。Demucs README明記)。**再分離は禁止**。
- Demucs は torch 依存で重いため、専用venv上で subprocess 呼び出し(basic-pitchの
  bp_worker と同方式)。環境変数 EARPIPE_DEMUCS_PYTHON が最優先。無い環境では
  StemSeparationUnavailable を送出し、黙って劣化させない(NF-050: 耳層は分離結果を
  受け取るだけで、分離自体は前処理サービスに隔離)。
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Demucs 4-stem の標準ステム名(vocals/drums/bass/other)
STEMS: tuple[str, ...] = ("vocals", "drums", "bass", "other")
# 音程を持つ主な旋律ステム(採譜対象。drumsは非音程なので既定で除外)
MELODIC_STEMS: tuple[str, ...] = ("vocals", "bass", "other")
_DEFAULT_MODEL = "htdemucs"

# Demucs が動く Python の探索候補(上から優先)。EARPIPE_DEMUCS_PYTHON が最優先。
_DEMUCS_PYTHON_CANDIDATES = (
    Path(__file__).resolve().parents[3] / ".venv-demucs" / "bin" / "python",
    Path(__file__).resolve().parents[4] / ".venv-demucs" / "bin" / "python",
)


class StemSeparationUnavailable(RuntimeError):
    """Demucs が使えない環境での明示エラー(黙って劣化させないための送出)。"""


def demucs_python_path() -> str | None:
    """Demucs が動くインタプリタを探す。環境変数 EARPIPE_DEMUCS_PYTHON が最優先。"""
    env = os.environ.get("EARPIPE_DEMUCS_PYTHON")
    if env:
        return env if Path(env).exists() else None
    for cand in _DEMUCS_PYTHON_CANDIDATES:
        if cand.exists():
            return str(cand)
    return None


def demucs_available() -> bool:
    """Demucs 分離が実行可能な環境かどうか。"""
    return demucs_python_path() is not None


@dataclass(frozen=True)
class SeparationResult:
    """分離結果: ステム名→wavパスと、使用モデル。"""

    stems: dict[str, Path]
    model: str

    def melodic(self) -> dict[str, Path]:
        """採譜対象の旋律ステムだけ(drums除外)。"""
        return {k: v for k, v in self.stems.items() if k in MELODIC_STEMS}


def separate_stems(
    in_path: str | Path,
    out_dir: str | Path,
    model: str = _DEFAULT_MODEL,
    device: str = "cpu",
    timeout_sec: float = 1800.0,
) -> SeparationResult:
    """音源を4ステムに分離し、{ステム名: wavパス} を返す。

    Demucs CLI(`python -m demucs`)を専用venvで呼び出す。CPU既定(可搬性のため。
    量子化/GPUで必ず速くなる前提を置かない=NF-004方針)。分離不能なら
    StemSeparationUnavailable。
    """
    py = demucs_python_path()
    if py is None:
        raise StemSeparationUnavailable(
            "Demucs が見つかりません。EARPIPE_DEMUCS_PYTHON に demucs 導入済みの "
            "Python を設定するか、spike/ear-pipeline/.venv-demucs を作成してください。"
        )
    in_path = Path(in_path)
    if not in_path.exists():
        raise FileNotFoundError(f"入力音源が存在しません: {in_path}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        py, "-m", "demucs",
        "-n", model,
        "-d", device,
        "-o", str(out_dir),
        str(in_path),
    ]
    try:
        subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=timeout_sec
        )
    except subprocess.CalledProcessError as e:  # 分離失敗は原因を残して送出
        raise StemSeparationUnavailable(
            f"Demucs 実行に失敗しました(returncode={e.returncode}): {e.stderr[-500:]}"
        ) from e

    # Demucs の出力は out_dir/<model>/<trackname>/<stem>.wav
    track_dir = out_dir / model / in_path.stem
    stems: dict[str, Path] = {}
    for name in STEMS:
        p = track_dir / f"{name}.wav"
        if p.exists():
            stems[name] = p
    if not stems:
        raise StemSeparationUnavailable(
            f"Demucs 出力が見つかりません(探索先: {track_dir})"
        )
    return SeparationResult(stems=stems, model=model)
