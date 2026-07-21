"""エミッタ: 奏法検出レポート(F-078/Issue #73・#109 B-2 結線)。

耳層 technique モジュールの detect_techniques を実採譜フローへ結線する
(孤立解消)。入力音声から f0 軌跡(librosa pYIN)を抽出し、bend/slide・
vibrato・hammer_on/pull_off をルールベースで分類して人間可読テキストで出力する。

なぜ音声が要るか: 奏法は f0 の連続軌跡(cent領域の傾き・周期変調・急峻な跳躍)
から判定するため、量子化済みノートでは表現できない生の f0 が必須。よって
NEEDS_AUDIO=True。f0 抽出は耳層 mono と同じ pYIN 設定に揃える。

正直な限界(technique module docstring 準拠): bend/slide は原理的に混同しやすく、
hammer/pull は f0 推定ノイズに敏感。confidence は控えめに出る。実録音では
誤分類が増えるため過信しないこと。既定の五線譜/MIDI 出力は一切変えない
(オプトインの副次成果物)。

パラメータ:
  --emit technique:fmin=65.0(pYIN 探索下限 Hz・既定 C2=65.0)
  --emit technique:fmax=2093.0(pYIN 探索上限 Hz・既定 C7=2093.0)
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.technique import detect_techniques
from earpipe.services.stem import load_audio

KEY = "technique"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True

# f0 抽出は耳層 mono(librosa pYIN)と同じ設定に揃える(C2〜C7・hop=256)。
_FMIN = 65.0
_FMAX = 2093.0
_FRAME = 2048
_HOP = 256


def emit(ctx: EmitContext, out_path: Path) -> Path:
    fmin = ctx.param_float("fmin", _FMIN)
    fmax = ctx.param_float("fmax", _FMAX)

    y, sr = load_audio(ctx.audio_path)
    y = np.asarray(y, dtype=np.float64)

    techniques = _detect(y, int(sr), fmin, fmax)

    lines = [
        f"# 奏法検出レポート (F-078): {ctx.title}",
        "# bend/slide は原理的に曖昧・hammer/pull は f0 ノイズに敏感。過信しないこと。",
        f"technique_count: {len(techniques)}",
        "idx\tkind\tonset_sec\toffset_sec\tconfidence",
    ]
    if not techniques:
        lines.append("(奏法は検出されませんでした: 無声/短尺/合成純音など)")
    for i, tech in enumerate(techniques):
        lines.append(
            f"{i}\t{tech.kind}\t{tech.onset_sec:.3f}\t"
            f"{tech.offset_sec:.3f}\t{tech.confidence:.2f}"
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _detect(y: np.ndarray, sr: int, fmin: float, fmax: float):
    """波形から f0 軌跡を抽出し detect_techniques へ渡す。

    空/無音は detect_techniques 側が空 list を返すため、ここでは素直に
    times/f0 の同長配列を組んで委譲する(判定ロジックは module 側が唯一の真実)。
    """
    if y.size < _FRAME or float(np.max(np.abs(y))) < 1e-6:
        return detect_techniques(np.zeros(0), np.zeros(0))
    f0, _voiced, _vprob = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, frame_length=_FRAME, hop_length=_HOP
    )
    times = librosa.times_like(f0, sr=sr, hop_length=_HOP)
    return detect_techniques(times, np.asarray(f0, dtype=np.float64))
