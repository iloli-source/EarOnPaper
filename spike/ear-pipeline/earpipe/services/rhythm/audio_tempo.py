"""音響信号ベースのテンポ推定(#136・二段推定のフォールバック側)。

IOI格子フィット(quantize.estimate_tempo)は検出イベントに依存するため、
倍音の嵐(実測: 歪みギターステムで約18音/秒)では破綻して既定値へ退避する。
本モジュールは検出結果を経由せず、onset強度エンベロープから直接テンポを
推定する。既知の失敗例(オクターブ誤り・事前分布中心への引き寄せ)への対策:
フレーム別推定の中央値集約＋探索範囲内へのオクターブ折り＋音楽的事前分布
(_log2_gauss・quantize.pyと同一)での候補選択。
"""

from __future__ import annotations

import numpy as np

from earpipe.services.rhythm.quantize import (
    PRIOR_CENTER_BPM,
    PRIOR_SIGMA_LOG2,
    _log2_gauss,
)


def estimate_audio_tempo(
    y: np.ndarray, sr: int, bpm_min: float, bpm_max: float
) -> float | None:
    """onset強度エンベロープからテンポを推定し、範囲内へオクターブ折りして返す。

    推定不能(無音・非有限・範囲内に折れない)は None を返し、呼び出し側の
    既定値退避に委ねる。フォールバック専用のため例外は投げない方針。
    """
    import librosa  # 遅延import(D4M-017方針: 軽量経路でのimport強制を避ける)

    if y is None or len(y) == 0 or not np.any(np.isfinite(y)) or not np.any(y):
        return None
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        if onset_env is None or not np.any(onset_env > 0):
            return None
        frames = librosa.feature.tempo(
            onset_envelope=onset_env, sr=sr, aggregate=None
        )
        raw = float(np.median(frames))
    except Exception:
        return None
    if not np.isfinite(raw) or raw <= 0:
        return None

    # 範囲内へオクターブ折り: {raw*2^k} の範囲内候補から事前分布最大を選ぶ
    candidates = []
    for k in range(-3, 4):
        b = raw * (2.0 ** k)
        if bpm_min <= b <= bpm_max:
            candidates.append(b)
    if not candidates:
        return None
    return max(candidates, key=lambda b: _log2_gauss(b, PRIOR_CENTER_BPM, PRIOR_SIGMA_LOG2))
