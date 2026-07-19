"""stemサービス: 音源の読み込み・前処理(現状はロード+モノラル化のみの枠)。

将来のステム分離(F-003)・音質診断(F-002)はこのサービスに実装する。
"""

from pathlib import Path

import librosa
import numpy as np


def load_audio(in_path: Path | str) -> tuple[np.ndarray, float]:
    """音声ファイルを読み込みモノラル波形とサンプルレートを返す。"""
    y, sr = librosa.load(str(in_path), sr=None, mono=True)
    return y, sr
