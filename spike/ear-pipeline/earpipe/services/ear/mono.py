"""耳層: 音声 → 音程イベント列(楽器非依存・NF-050準拠)。

v0 は librosa pYIN による単音(モノフォニック)実装。
basic-pitch(多声)は Python 3.14 でビルド不能のため見送り(READMEに記録)。
エンジン層に楽器固有の分岐は持たない。
"""

import librosa
import numpy as np

from earpipe.contracts import PitchEvent

FMIN = 65.0     # C2
FMAX = 2093.0   # C7
FRAME = 2048
HOP = 256
MIN_DUR_SEC = 0.08    # これ未満の断片はノイズ扱い
MIN_CONFIDENCE = 0.5  # 有声確率の平均がこれ未満なら破棄
PITCH_TOL_SEMITONES = 0.5  # セグメント中心からの許容偏差(ビブラート統合幅・#46)
STEP_TOL_SEMITONES = 0.7   # フレーム間連続性の許容(深いビブラートの最急部≈0.66/フレームまで継続。
                           # pYINは音替わりも滑走するため、持続的シフトは事後分割で切る。#46)
SPLIT_GAP_SEMITONES = 0.8  # 事後分割: 局所窓の中央値がこれ以上離れたら別音とみなす
# 反復同音分割: RMSフラックス最大値に対するピーク閾値の比。#138のかえるのうた
# スイープ実測: 0.06はn=29だが持続音の偽分割2件(GG/FF)、0.15は偽分割ゼロで
# 編集距離同点 → 「ノイズを音符化しない」原則で0.15を採用(0.2から緩和)。
# 残るレガート連打(CC/DD/EE級・エネルギー谷が浅い)はre-onset学習系の領域(#114)。
# アタック相対の適応閾値も実験したが編集距離7〜16で明確に悪化し不採用(調査ノート)。
ONSET_SPLIT_DELTA = 0.15
# #138根治: 窓・最小断片長は秒で定義し実行時にsrから換算する。旧実装はフレーム数
# 定数(22050Hz前提)で、ネイティブsr=48kHzでは実時間窓が半減(意図81ms→実37ms)し、
# pYINの音替わり滑走(50〜100ms)が窓を覆って段差検出が失敗していた。
SPLIT_MIN_SEC = 0.035      # 事後分割の最小断片長(≈35ms)
SPLIT_WINDOW_SEC = 0.081   # 局所中央値の窓(≈81ms。6Hzビブラートの半周期相当で振動を平均化)
POST_AVG_SEC = 0.058       # peak_pick後方平均窓(≈58ms)


def _frames(sec: float, sr: int) -> int:
    """秒→フレーム数(HOP格子)。22050Hzで従来のフレーム定数と一致する。"""
    return max(3, round(sec * sr / HOP))



def detect_events(
    y: np.ndarray,
    sr: int,
    fmin: float = FMIN,
    fmax: float = FMAX,
    min_dur: float = MIN_DUR_SEC,
    min_conf: float = MIN_CONFIDENCE,
    pitch_tol: float = PITCH_TOL_SEMITONES,
) -> list[PitchEvent]:
    """音声波形から音程イベント列を抽出する。

    音程が確かに検出できた区間だけをイベント化し、
    無音・ノイズは「音符ゼロ」として正直に返す(絶対音感エミュレータの設計原則)。

    セグメント化は連続音高(丸め前のMIDI実数値)がセグメント中心(実行平均)から
    ±pitch_tol半音以内に収まる限り継続する(#46: 旧実装の整数丸め切断は、
    半音境界近傍のビブラートを多数の断片に砕いて音符を消失・断片化させた)。
    音符の音高はセグメント内実数値の中央値を丸めて決める。
    限界(正直な記録): 深いビブラート(±1半音超)やグリッサンドは中心が
    追従しきれず分割されうる。ビブラート±0.5半音まではテストで保存を保証。
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
    # librosa仕様変更(hop/frame変更時のフレーム数不一致)を早期検出する(レビューMEDIUM-4)
    if len(times) != len(f0):
        raise RuntimeError(
            f"times({len(times)})とf0({len(f0)})の長さが不一致 — librosaのフレーム計算仕様を確認"
        )
    voiced_mask = np.asarray(voiced, dtype=bool) & np.isfinite(f0)
    safe_f0 = np.where(np.isfinite(f0), f0, 1.0)
    midi_float = np.where(voiced_mask, librosa.hz_to_midi(safe_f0), np.nan)

    # 反復同音(ピッチ変化なし)の切れ目を拾うためのエネルギーonset(根治 2026-07-23)。
    # pYINのピッチ区間分割だけでは、同じ音高の連続(例: 唱歌の反復8分「けろけろ…」)が
    # 1音にマージされ速い音を取りこぼす→リズムが曖昧になり三連符に誤爆する原因。
    # 同一frameグリッド(hop=HOP)でonset frameを求め、セグメント分割の境界に足す。
    # スペクトルフラックスonsetはビブラート(ピッチ変動)を再アタックと誤認するため、
    # RMSエネルギーの正の増分(再アタック=エネルギー谷→山)で分割点を拾う。反復同音は
    # 音間でエネルギーが落ちて立ち上がる→ピーク、ビブラートは定常エネルギー→ピークなし。
    min_frames = _frames(SPLIT_MIN_SEC, sr)
    win_frames = _frames(SPLIT_WINDOW_SEC, sr)
    try:
        rms = librosa.feature.rms(y=y, hop_length=HOP, frame_length=FRAME)[0]
        flux = np.maximum(0.0, np.diff(rms, prepend=rms[:1]))
        thr = ONSET_SPLIT_DELTA * float(np.max(flux)) if flux.size else 0.0
        onset_frames = {
            int(fr)
            for fr in librosa.util.peak_pick(
                flux, pre_max=min_frames, post_max=min_frames, pre_avg=min_frames,
                post_avg=_frames(POST_AVG_SEC, sr),
                delta=thr, wait=min_frames,
            )
        }
    except Exception:
        onset_frames = set()

    events: list[PitchEvent] = []
    start: int | None = None
    acc: list[float] = []
    acc_sum = 0.0

    def emit(s: int, e: int) -> None:
        """区間[s,e)を音符として出力(min_dur/min_confを満たす場合)。"""
        onset = float(times[s])
        end_t = float(times[e - 1] + HOP / sr)
        seg_prob = vprob[s:e]
        conf = float(np.nanmean(seg_prob)) if len(seg_prob) else 0.0
        if end_t - onset >= min_dur and conf >= min_conf:
            note = int(round(float(np.median(midi_float[s:e]))))
            events.append(
                PitchEvent(onset=onset, offset=end_t, midi=note, confidence=round(conf, 4))
            )

    def split_and_emit(s: int, e: int) -> None:
        """持続的な音高シフトを再帰的に探して分割する(#46 事後分割)。

        各候補点kの前後±窓(約80ms)の局所中央値を比較する。音替わり(pYINは
        滑走する)は局所的に≥SPLIT_GAPのシフトとして現れ、ビブラート(±0.5まで)は
        窓内で平均化されて閾値未満に収まる。A-B-A型の複数音統合も局所検出で
        各境界が見つかる(全体の前半/後半比較では対称パターンを見逃すため)。
        """
        vals = midi_float[s:e]
        if e - s < 2 * min_frames or float(np.max(vals) - np.min(vals)) < SPLIT_GAP_SEMITONES:
            emit(s, e)
            return
        w = win_frames
        best_k, best_gap = -1, 0.0
        for k in range(s + min_frames, e - min_frames + 1):
            left = midi_float[max(s, k - w):k]
            right = midi_float[k:min(e, k + w)]
            gap = abs(float(np.median(left)) - float(np.median(right)))
            if gap > best_gap:
                best_gap, best_k = gap, k
        if best_gap >= SPLIT_GAP_SEMITONES:
            split_and_emit(s, best_k)
            split_and_emit(best_k, e)
        else:
            emit(s, e)

    def close_segment(end_i: int) -> None:
        nonlocal start
        assert start is not None
        # エネルギーonsetで反復同音を先に区切り、各断片内でピッチ変化分割する。
        # 境界から最小断片長未満のonsetは無視(断片が短すぎる誤分割を避ける)。
        cuts = [
            fr for fr in sorted(onset_frames)
            if start + min_frames <= fr <= end_i - min_frames
        ]
        bounds = [start, *cuts, end_i]
        for a, b in zip(bounds, bounds[1:]):
            if b > a:
                split_and_emit(a, b)
        start = None

    for i in range(len(midi_float) + 1):
        cur = float(midi_float[i]) if i < len(midi_float) else float("nan")
        cur_ok = not np.isnan(cur)
        if start is None:
            if cur_ok:
                start = i
                acc = [cur]
                acc_sum = cur
            continue
        center = acc_sum / len(acc)
        prev = acc[-1]
        # 中心±tol(ビブラート幅) または フレーム間連続(pYINの滑走に追従)で継続し、
        # 音替わり(持続的シフト)は close 時の事後分割で切る
        if cur_ok and (abs(cur - center) <= pitch_tol or abs(cur - prev) <= STEP_TOL_SEMITONES):
            acc.append(cur)
            acc_sum += cur
            continue
        close_segment(i)
        if cur_ok:
            start = i
            acc = [cur]
            acc_sum = cur
    return events
