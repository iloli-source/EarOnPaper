"""stemサービス: 音源の読み込み・前処理(ロード+モノラル化+先頭無音トリム)。

将来のステム分離(F-003)・音質診断(F-002)はこのサービスに実装する。
"""

import os
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

# 先頭無音トリムの閾値(dB)と、音の頭を削らないためのマージン(秒)
_TRIM_TOP_DB = 40
_TRIM_MARGIN_SEC = 0.05


def load_audio(in_path: Path | str) -> tuple[np.ndarray, float]:
    """音声ファイルを読み込みモノラル波形とサンプルレートを返す。"""
    y, sr = librosa.load(str(in_path), sr=None, mono=True)
    return y, sr


def trim_leading_silence(y: np.ndarray, sr: int) -> tuple[np.ndarray, float]:
    """先頭の無音を除去する。(トリム後波形, カットした秒数)を返す。

    曲前の無音は楽譜の先頭を休符にして精度を落とすため、最初に音が鳴る
    位置まで詰める(ユーザー実証 2026-07-20)。音の頭を削らないよう
    _TRIM_MARGIN_SEC のマージンを残す。全無音・空入力は安全に素通しする。
    """
    if y.size == 0:
        return y, 0.0
    intervals = librosa.effects.split(y, top_db=_TRIM_TOP_DB)
    if len(intervals) == 0:
        return y, 0.0  # 全区間が無音 → 触らない
    start = int(intervals[0][0])
    margin = int(_TRIM_MARGIN_SEC * sr)
    start = max(0, start - margin)
    if start == 0:
        return y, 0.0
    return y[start:], start / sr


def trim_leading_silence_file(in_path: Path | str) -> tuple[Path, float]:
    """ファイルの先頭無音を除いた一時wavを返す(pipeline統合用)。

    戻り値 (out_path, cut_sec)。カット不要なら入力pathをそのまま返す
    (呼び出し側は out_path != in_path のときだけ一時ファイル削除の責務を持つ)。
    """
    src = Path(in_path)
    y, sr = librosa.load(str(src), sr=None, mono=True)
    trimmed, cut_sec = trim_leading_silence(y, int(sr))
    if cut_sec <= 0.0:
        return src, 0.0
    fd, tmp_name = tempfile.mkstemp(suffix="_trimmed.wav", prefix="earpipe_")
    os.close(fd)
    out_path = Path(tmp_name)
    sf.write(str(out_path), trimmed, sr)
    return out_path, cut_sec
