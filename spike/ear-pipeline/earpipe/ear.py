"""耳層: 音声 → 音程イベント列(楽器非依存・NF-050準拠)。

v0 は librosa pYIN による単音(モノフォニック)実装。
basic-pitch(多声)は Python 3.14 でビルド不能のため見送り(READMEに記録)。
エンジン層に楽器固有の分岐は持たない。
"""

from dataclasses import dataclass

import librosa
import numpy as np

FMIN = 65.0     # C2
FMAX = 2093.0   # C7
FRAME = 2048
HOP = 256
MIN_DUR_SEC = 0.08    # これ未満の断片はノイズ扱い
MIN_CONFIDENCE = 0.5  # 有声確率の平均がこれ未満なら破棄


@dataclass(frozen=True)
class PitchEvent:
    """音程イベント: いつからいつまで、どの高さ(MIDIノート番号)が、どれくらい確かか。"""

    onset: float       # 開始秒
    offset: float      # 終了秒
    midi: int          # MIDIノート番号(60=中央のド)
    confidence: float  # 0-1


def detect_events(
    y: np.ndarray,
    sr: int,
    fmin: float = FMIN,
    fmax: float = FMAX,
    min_dur: float = MIN_DUR_SEC,
    min_conf: float = MIN_CONFIDENCE,
) -> list[PitchEvent]:
    """音声波形から音程イベント列を抽出する。

    音程が確かに検出できた区間だけをイベント化し、
    無音・ノイズは「音符ゼロ」として正直に返す(絶対音感エミュレータの設計原則)。
    """
    y = np.asarray(y, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) < FRAME or float(np.max(np.abs(y))) < 1e-6:
        return []

    f0, voiced, vprob = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, frame_length=FRAME, hop_length=HOP,
    )
    times = librosa.times_like(f0, sr=sr, hop_length=HOP)
    safe_f0 = np.where(np.isfinite(f0), f0, 1.0)
    midi = np.round(librosa.hz_to_midi(safe_f0)).astype(int)
    midi = np.where(np.asarray(voiced, dtype=bool) & np.isfinite(f0), midi, -1)

    events: list[PitchEvent] = []
    start: int | None = None
    for i in range(len(midi) + 1):
        cur = int(midi[i]) if i < len(midi) else -1
        if start is None:
            if cur >= 0:
                start = i
            continue
        if cur != midi[start]:
            onset = float(times[start])
            end_t = float(times[i - 1] + HOP / sr)
            seg_prob = vprob[start:i]
            conf = float(np.nanmean(seg_prob)) if len(seg_prob) else 0.0
            if end_t - onset >= min_dur and conf >= min_conf:
                events.append(
                    PitchEvent(onset=onset, offset=end_t, midi=int(midi[start]), confidence=round(conf, 4))
                )
            start = i if cur >= 0 else None
    return events
