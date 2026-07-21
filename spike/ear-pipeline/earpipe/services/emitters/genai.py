"""エミッタ: 生成AI楽曲向け採譜プリセット + 前処理診断(F-092/Issue #99・#109 B-2)。

Suno/Udio/MusicGen 等の生成AI音源は「分離が良く低ノイズ」に見えて採譜には
逆に危険な特性を持つ。本エミッタは入力音声に軽い**非破壊**前処理
`genai_preprocess` を施し、その効果(DC除去量・ピーク・高域エネルギー変化)と
推奨採譜パラメータ `GENAI_PRESET` を人間可読テキストとして出力する。
音声波形を要する診断型エミッタ(genai_preset モジュールの結線=孤立解消)。

パラメータ: --emit genai:sr_override=0(既定0=ファイルのsrを使う)。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from earpipe.services.emitters.base import EmitContext
from earpipe.services.stem import load_audio
from earpipe.services.stem.genai_preset import (
    GENAI_PRESET,
    genai_preprocess,
    genai_preset,
)

KEY = "genai"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True

_EPS = 1e-12


def _high_freq_energy(y: np.ndarray) -> float:
    """隣接差分(1次高域強調)のエネルギーで高域成分量を近似する。"""
    if y.size < 2:
        return 0.0
    diff = np.diff(y)
    return float(np.sqrt(np.mean(diff * diff)))


def emit(ctx: EmitContext, out_path: Path) -> Path:
    sr_override = ctx.param_int("sr_override", 0)

    y, file_sr = load_audio(ctx.audio_path)
    sr = sr_override if sr_override > 0 else int(file_sr)

    preset = genai_preset()
    processed = genai_preprocess(y, sr)

    dc_before = float(np.mean(y)) if y.size else 0.0
    peak_before = float(np.max(np.abs(y))) if y.size else 0.0
    peak_after = float(np.max(np.abs(processed))) if processed.size else 0.0
    hf_before = _high_freq_energy(y)
    hf_after = _high_freq_energy(processed)
    hf_ratio = hf_after / (hf_before + _EPS)

    lines = [
        f"# 生成AI採譜プリセット診断 (F-092/Issue #99): {Path(ctx.audio_path).name}",
        f"sample_rate: {sr}",
        f"num_samples: {int(y.size)}",
        "",
        "## 前処理効果 (非破壊: DC除去 + 軽い高域デエンファシス + 利得正規化)",
        f"dc_offset_before: {dc_before:.6e}",
        f"peak_before: {peak_before:.6f}",
        f"peak_after: {peak_after:.6f}  (target={GENAI_PRESET['preprocess']['peak_target']})",
        f"high_freq_energy_before: {hf_before:.6f}",
        f"high_freq_energy_after: {hf_after:.6f}",
        f"high_freq_ratio(after/before): {hf_ratio:.4f}",
        "",
        "## 推奨採譜パラメータ (助言値: 既存パイプラインは書き換えない)",
        f"detect_min_conf: {preset.detect_min_conf}",
        f"detect_pitch_tol: {preset.detect_pitch_tol}",
        f"grid_per_beat: {preset.grid_per_beat}",
        f"quantize_strength: {preset.quantize_strength}",
        f"scale_lock: {preset.scale_lock}",
        f"pitch_bend: {preset.pitch_bend}",
        f"drums: {preset.drums}",
        "",
        "## 注記",
        preset.notes,
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
