"""score_rhythm（楽譜レベルのリズムKPI）の序列検証テスト。

設計意図（Issue #33）:
- ms単位の生タイミングではなく「拍・小節に対する正しさ」を測る
- テンポの別名（2倍/半分の等価表記）は等価として扱う（オクターブ不変）
- 序列: 完全一致 ≈ テンポ等価表記 > 音価半減 > 拍位置シャッフル
"""

from __future__ import annotations

import random

import pretty_midi
import pytest

from score_metrics import score_rhythm

BPM = 120.0
# (拍位置, 音価[拍], MIDIピッチ) — 4分・8分・付点混在の16音メロディ
MELODY = [
    (0.0, 1.0, 60), (1.0, 0.5, 62), (1.5, 0.5, 64), (2.0, 1.0, 65),
    (3.0, 1.0, 67), (4.0, 0.5, 69), (4.5, 0.5, 67), (5.0, 1.5, 65),
    (6.5, 0.5, 64), (7.0, 1.0, 62), (8.0, 2.0, 60), (10.0, 0.5, 64),
    (10.5, 0.5, 65), (11.0, 1.0, 67), (12.0, 2.0, 72), (14.0, 2.0, 60),
]


def build_pm(notes: list[tuple[float, float, int]], bpm: float) -> pretty_midi.PrettyMIDI:
    """拍単位のメロディを指定テンポの PrettyMIDI にする。"""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0)
    spb = 60.0 / bpm
    for beat, dur, pitch in notes:
        inst.notes.append(
            pretty_midi.Note(
                velocity=80,
                pitch=pitch,
                start=beat * spb,
                end=(beat + dur) * spb,
            )
        )
    pm.instruments.append(inst)
    return pm


@pytest.fixture(scope="module")
def gt() -> pretty_midi.PrettyMIDI:
    return build_pm(MELODY, BPM)


def test_identical_scores_high(gt):
    est = build_pm(MELODY, BPM)
    r = score_rhythm(gt, est)
    assert r["total"] >= 0.9
    assert r["beat_f1"] >= 0.95
    assert r["dur_agreement"] >= 0.95


def test_tempo_octave_alias_is_equivalent(gt):
    """同じ音楽を「テンポ半分・音価2倍」で書いた等価表記は高得点のまま。"""
    alias = [(b * 2, d * 2, p) for b, d, p in MELODY]
    est = build_pm(alias, BPM / 2)  # 実時間は同一・記法だけ別名
    r = score_rhythm(gt, est)
    assert r["total"] >= 0.85
    assert r["beat_f1"] >= 0.9


def test_duration_halved_is_middle(gt):
    """拍位置は正しいが音価が全部半分 → 中間の点（f1高・音価一致低）。"""
    halved = [(b, d / 2, p) for b, d, p in MELODY]
    est = build_pm(halved, BPM)
    r = score_rhythm(gt, est)
    assert r["beat_f1"] >= 0.9  # 拍位置は正しい
    assert r["dur_agreement"] <= 0.35  # 音価クラスはほぼ全滅
    assert 0.5 <= r["total"] < 0.9


def test_shuffled_beats_score_low(gt):
    """拍位置を大きく崩す → 低得点。"""
    rng = random.Random(7)
    # 格子に乗らない連続ジッター（格子倍数だと同音高の別音符に再マッチしうるため）
    shuffled = [
        (max(0.0, b + rng.choice([-1, 1]) * rng.uniform(0.35, 1.6)), d, p)
        for b, d, p in MELODY
    ]
    est = build_pm(shuffled, BPM)
    r = score_rhythm(gt, est)
    assert r["total"] <= 0.55


def test_ordering(gt):
    """序列: 完全一致 ≈ 等価表記 > 音価半減 > シャッフル。"""
    identical = score_rhythm(gt, build_pm(MELODY, BPM))["total"]
    alias = score_rhythm(
        gt, build_pm([(b * 2, d * 2, p) for b, d, p in MELODY], BPM / 2)
    )["total"]
    halved = score_rhythm(gt, build_pm([(b, d / 2, p) for b, d, p in MELODY], BPM))["total"]
    rng = random.Random(7)
    shuffled = score_rhythm(
        gt,
        build_pm(
            [(max(0.0, b + rng.choice([-1, 1]) * rng.uniform(0.35, 1.6)), d, p) for b, d, p in MELODY],
            BPM,
        ),
    )["total"]
    assert identical >= alias - 0.05
    assert alias > halved
    assert halved > shuffled


def test_empty_transcription_scores_zero(gt):
    est = pretty_midi.PrettyMIDI(initial_tempo=BPM)
    est.instruments.append(pretty_midi.Instrument(program=0))
    r = score_rhythm(gt, est)
    assert r["total"] == 0.0
    assert r["beat_f1"] == 0.0


def test_wrong_tempo_meta_with_real_seconds(gt):
    """BP素点のケース: テンポメタが120固定のまま実秒で書かれた採譜。

    実時間はGTと一致しているので、スケール探索により高いbeat_f1が出るべき。
    """
    # GTと同じ実秒だがテンポメタだけ違うMIDIを作る
    est = pretty_midi.PrettyMIDI(initial_tempo=97.0)  # 出鱈目なメタ
    inst = pretty_midi.Instrument(program=0)
    spb = 60.0 / BPM
    for beat, dur, pitch in MELODY:
        inst.notes.append(
            pretty_midi.Note(velocity=80, pitch=pitch, start=beat * spb, end=(beat + dur) * spb)
        )
    est.instruments.append(inst)
    r = score_rhythm(gt, est)
    assert r["beat_f1"] >= 0.9
