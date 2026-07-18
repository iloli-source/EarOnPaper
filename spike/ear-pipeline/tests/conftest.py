"""テストフィクスチャ: 正解が構成的に既知の合成メロディ。

ground truth は (midi, start_beats, dur_beats) のリストと BPM。
秒に変換した (midi, onset_sec, offset_sec) を突合に使う。
"""

import numpy as np
import pytest

SR = 22050

# 4/4・4小節。16分音符の走句と裏拍(8分裏)開始を含む
# → テンポ推定でBPM/2の格子では説明できない配置にしてある
MELODY_SIMPLE = [
    # (midi, start_beats, dur_beats)  beats=四分音符単位
    (60, 0.0, 1.0),
    (62, 1.0, 1.0),
    (64, 2.0, 0.5),
    (65, 2.5, 0.5),
    (67, 3.0, 1.0),
    (69, 4.0, 0.25),  # 16分の走句
    (67, 4.25, 0.25),
    (65, 4.5, 0.25),
    (64, 4.75, 0.25),
    (62, 5.0, 2.0),
    (60, 7.5, 0.5),   # 8分裏開始(シンコペーション)
    (64, 8.0, 2.0),
    (67, 10.0, 1.0),
    (72, 11.0, 1.0),
    (71, 12.0, 2.0),
    (67, 14.0, 2.0),
]

MELODY_DOTTED = [
    (67, 0.0, 1.5),   # 付点四分
    (69, 1.5, 0.5),
    (71, 2.0, 1.5),
    (72, 3.5, 0.5),
    (74, 4.0, 1.0),
    (72, 5.0, 0.75),  # 付点八分
    (71, 5.75, 0.25),
    (69, 6.0, 2.0),
]


def melody_to_seconds(melody, bpm):
    """ground truth を秒に変換: [(midi, onset_sec, offset_sec)]"""
    spb = 60.0 / bpm
    return [(m, s * spb, (s + d) * spb) for m, s, d in melody]


def render_melody(melody, bpm, sr=SR, gap=0.03, amp=0.4):
    """sine で合成。各音に短いアタック/リリースをつけ、音間に gap 秒の無音を挟む
    (同音連打の分離とオンセット検出のため)。"""
    spb = 60.0 / bpm
    total = (max(s + d for _, s, d in melody)) * spb + 0.5
    y = np.zeros(int(total * sr), dtype=np.float64)
    for midi, start, dur in melody:
        f = 440.0 * 2 ** ((midi - 69) / 12)
        t0 = start * spb
        t1 = (start + dur) * spb - gap
        n0, n1 = int(t0 * sr), int(t1 * sr)
        n = n1 - n0
        if n <= 0:
            continue
        t = np.arange(n) / sr
        tone = amp * np.sin(2 * np.pi * f * t)
        env = np.ones(n)
        a = min(int(0.005 * sr), n // 4)
        r = min(int(0.02 * sr), n // 4)
        if a > 0:
            env[:a] = np.linspace(0, 1, a)
        if r > 0:
            env[-r:] = np.linspace(1, 0, r)
        y[n0:n1] += tone * env
    return y.astype(np.float32)


def note_f1(truth_sec, pred_sec, onset_tol=0.08):
    """音高一致かつオンセット±tol秒での1対1マッチングF1。"""
    truth = list(truth_sec)
    matched = 0
    used = set()
    for pm, po, _ in pred_sec:
        best = None
        for i, (tm, to, _) in enumerate(truth):
            if i in used or tm != pm:
                continue
            d = abs(po - to)
            if d <= onset_tol and (best is None or d < best[1]):
                best = (i, d)
        if best is not None:
            used.add(best[0])
            matched += 1
    p = matched / len(pred_sec) if pred_sec else 0.0
    r = matched / len(truth) if truth else 0.0
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


@pytest.fixture(scope="session")
def simple_wav(tmp_path_factory):
    import soundfile as sf
    path = tmp_path_factory.mktemp("audio") / "simple_120.wav"
    sf.write(path, render_melody(MELODY_SIMPLE, 120), SR)
    return path, MELODY_SIMPLE, 120


@pytest.fixture(scope="session")
def dotted_wav(tmp_path_factory):
    import soundfile as sf
    path = tmp_path_factory.mktemp("audio") / "dotted_100.wav"
    sf.write(path, render_melody(MELODY_DOTTED, 100), SR)
    return path, MELODY_DOTTED, 100


@pytest.fixture(scope="session")
def silence_wav(tmp_path_factory):
    import soundfile as sf
    path = tmp_path_factory.mktemp("audio") / "silence.wav"
    sf.write(path, np.zeros(SR * 3, dtype=np.float32), SR)
    return path


@pytest.fixture(scope="session")
def noise_wav(tmp_path_factory):
    import soundfile as sf
    rng = np.random.default_rng(42)
    path = tmp_path_factory.mktemp("audio") / "noise.wav"
    sf.write(path, (rng.standard_normal(SR * 3) * 0.1).astype(np.float32), SR)
    return path


# ---- v0.2 多声フィクスチャ ----

# 4/4・BPM100・三和音×8（各2拍）。ルート移動と転回を含む
CHORDS_PROG = [
    # (midis, start_beats, dur_beats)
    ((60, 64, 67), 0.0, 2.0),   # C
    ((65, 69, 72), 2.0, 2.0),   # F
    ((62, 67, 71), 4.0, 2.0),   # G(転回)
    ((60, 64, 67), 6.0, 2.0),   # C
    ((57, 60, 64), 8.0, 2.0),   # Am
    ((65, 69, 72), 10.0, 2.0),  # F
    ((62, 65, 71), 12.0, 2.0),  # G7断片
    ((60, 64, 67), 14.0, 2.0),  # C
]


def chords_to_seconds(chords, bpm):
    """[(midi, onset_sec, offset_sec)] に展開（和音は音ごとに1行）。"""
    spb = 60.0 / bpm
    out = []
    for midis, s, d in chords:
        for m in midis:
            out.append((m, s * spb, (s + d) * spb))
    return out


def render_chords(chords, bpm, sr=SR, gap=0.04, amp=0.22, harmonics=(1.0, 0.5, 0.25)):
    """三和音を倍音つきで合成（純粋sineより実楽器に近づけ、多声検出器が扱える音色にする）。"""
    spb = 60.0 / bpm
    total = max(s + d for _, s, d in chords) * spb + 0.5
    y = np.zeros(int(total * sr), dtype=np.float64)
    for midis, start, dur in chords:
        t0 = start * spb
        t1 = (start + dur) * spb - gap
        n0, n1 = int(t0 * sr), int(t1 * sr)
        n = n1 - n0
        if n <= 0:
            continue
        t = np.arange(n) / sr
        seg = np.zeros(n)
        for m in midis:
            f = 440.0 * 2 ** ((m - 69) / 12)
            for k, h in enumerate(harmonics, start=1):
                seg += amp * h * np.sin(2 * np.pi * f * k * t)
        env = np.ones(n)
        a = min(int(0.008 * sr), n // 4)
        r = min(int(0.04 * sr), n // 4)
        if a > 0:
            env[:a] = np.linspace(0, 1, a)
        if r > 0:
            env[-r:] = np.linspace(1, 0, r)
        y[n0:n1] += seg * env
    peak = float(np.max(np.abs(y)))
    if peak > 0.9:
        y *= 0.9 / peak
    return y.astype(np.float32)


@pytest.fixture(scope="session")
def chords_wav(tmp_path_factory):
    import soundfile as sf
    path = tmp_path_factory.mktemp("audio") / "chords_100.wav"
    sf.write(path, render_chords(CHORDS_PROG, 100), SR)
    return path, CHORDS_PROG, 100
