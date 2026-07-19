"""基準ピッチ補正(C1・#55)のユニットテスト。

変則ピッチ(A≠440)の合成音源を作り、(a)ずれ推定が±5cents以内、
(b)補正後に検出音高が正しい半音格子へ戻ること、を検証する。
検証は単音エンジン earpipe/services/ear/mono.detect_events を用いる
(basic-pitch不要の経路)。
"""

import numpy as np
import pytest

from earpipe.services.ear.mono import detect_events
from earpipe.services.ear.tuning import (
    CORRECTION_THRESHOLD_CENTS,
    MAX_OFFSET_CENTS,
    apply_tuning_correction,
    estimate_tuning_offset_cents,
)

SR = 22050

# 3曲: 異なる音高列。A=440基準の正しいMIDI番号を ground truth に持つ。
MELODY_A = [(60, 0, 1), (64, 1, 1), (67, 2, 1), (72, 3, 1), (67, 4, 1), (64, 5, 1)]
MELODY_B = [
    (62, 0, 0.5), (65, 0.5, 0.5), (69, 1, 1), (67, 2, 0.5),
    (64, 2.5, 0.5), (60, 3, 1), (62, 4, 1), (67, 5, 1),
]
MELODY_C = [(55, 0, 1), (59, 1, 0.5), (62, 1.5, 0.5), (67, 2, 1), (64, 3, 1), (59, 4, 1), (55, 5, 1)]


def _render(melody, bpm, detune_cents=0.0, sr=SR, gap=0.03, amp=0.4):
    """conftestのrender_melodyを踏襲しつつ、全音を detune_cents 一律にずらして合成。"""
    spb = 60.0 / bpm
    total = max(s + d for _, s, d in melody) * spb + 0.5
    y = np.zeros(int(total * sr), dtype=np.float64)
    factor = 2.0 ** (detune_cents / 1200.0)
    for midi, start, dur in melody:
        f = 440.0 * 2 ** ((midi - 69) / 12) * factor
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


# 変則ピッチ3曲ケース: (曲, デチューン量cents)。設計指針の +30/-25/+15 を含む。
DETUNE_CASES = [
    ("MELODY_A", MELODY_A, 30.0),
    ("MELODY_B", MELODY_B, -25.0),
    ("MELODY_C", MELODY_C, 15.0),
]


@pytest.mark.parametrize("name,melody,detune", DETUNE_CASES)
def test_estimate_within_5cents(name, melody, detune):
    """推定誤差が±5cents以内(変則ピッチ3曲)。"""
    y = _render(melody, 120, detune)
    est = estimate_tuning_offset_cents(y, SR)
    err = abs(est - detune)
    assert err <= 5.0, f"{name} detune={detune:+} 推定={est:+.2f} 誤差={err:.2f}cents > 5"


@pytest.mark.parametrize("name,melody,detune", DETUNE_CASES)
def test_correction_restores_grid(name, melody, detune):
    """補正後の検出音高が、無デチューン音源の検出音高と一致(正しい格子へ復帰)。"""
    truth_notes = _detected_midis(_render(melody, 120, 0.0))
    y_detuned = _render(melody, 120, detune)
    est = estimate_tuning_offset_cents(y_detuned, SR)
    corrected = apply_tuning_correction(y_detuned, SR, est)
    got_notes = _detected_midis(corrected)
    assert got_notes == truth_notes, (
        f"{name} detune={detune:+}: 補正後音高{got_notes} != 正解{truth_notes}"
    )


def _detected_midis(y):
    """検出イベントのMIDI番号列(オンセット順)。"""
    return [e.midi for e in detect_events(y, SR)]


def test_correction_is_non_trivial_at_rounding_edge():
    """補正の実効性を保証: -48centsでは無補正だと全音が1半音下へ丸め込まれ、
    補正で初めて正しい格子へ戻る(この境界で補正が必須であることを明示)。

    背景: detect_eventsのround()は±50cents内なら最寄り半音へ丸めるが、
    pYINの系統バイアス(≈+4cents)が加わると-48cents付近で下の半音側へ倒れる。
    ここが「補正しないと音高を取り違える」実害域。
    """
    truth = _detected_midis(_render(MELODY_A, 120, 0.0))
    y = _render(MELODY_A, 120, -48.0)
    raw = _detected_midis(y)
    assert raw != truth, "前提が崩れた: -48centsで無補正でも正解している(境界がずれた)"
    est = estimate_tuning_offset_cents(y, SR)
    corrected_notes = _detected_midis(apply_tuning_correction(y, SR, est))
    assert corrected_notes == truth, f"補正後も不一致: {corrected_notes} != {truth}"


def test_zero_detune_no_correction():
    """0centsの正常音源では補正が発動せず、入力が無劣化で返る。"""
    y = _render(MELODY_A, 120, 0.0)
    est = estimate_tuning_offset_cents(y, SR)
    assert abs(est) < CORRECTION_THRESHOLD_CENTS, f"正常音源で推定{est:+.2f}が閾値超"
    out = apply_tuning_correction(y, SR, est)
    # 無補正なら入力(モノ化・float64)とサンプル一致(長さも変わらない)
    y_mono = np.asarray(y, dtype=np.float64)
    assert len(out) == len(y_mono)
    np.testing.assert_allclose(out, y_mono, atol=1e-12)


@pytest.mark.parametrize("detune", [45.0, -45.0])
def test_boundary_large_detune_no_breakdown(detune):
    """±30cents超(±45)でも推定が破綻せず、範囲内にクランプ・符号が正しい。"""
    y = _render(MELODY_A, 120, detune)
    est = estimate_tuning_offset_cents(y, SR)
    assert -MAX_OFFSET_CENTS <= est <= MAX_OFFSET_CENTS, f"推定{est}が範囲外"
    # 破綻しない=誤差が半音(±100cents未満)、符号が一致する程度は最低保証
    assert np.sign(est) == np.sign(detune), f"符号不一致 detune={detune} est={est}"
    assert abs(est - detune) <= 5.0, f"±45cents境界で誤差{abs(est-detune):.2f} > 5"


def test_silence_estimates_zero():
    """無音は推定不能なため0.0を返す(破綻せず正直に無補正)。"""
    y = np.zeros(SR * 2, dtype=np.float32)
    assert estimate_tuning_offset_cents(y, SR) == 0.0


def test_correct_tuning_file_roundtrip(tmp_path):
    """correct_tuning_file: 補正発動時は一時wavパス、無補正時は入力パスを返す。"""
    import soundfile as sf

    from earpipe.services.ear.tuning import correct_tuning_file

    # 補正あり(+30cents)
    detuned_path = tmp_path / "detuned.wav"
    sf.write(str(detuned_path), _render(MELODY_A, 120, 30.0), SR)
    out_path, offset = correct_tuning_file(detuned_path)
    assert abs(offset - 30.0) <= 5.0
    assert out_path != detuned_path, "補正発動時は別の一時ファイルを返すべき"
    assert out_path.exists()
    out_path.unlink()

    # 補正なし(0cents) → 入力パスをそのまま返す
    clean_path = tmp_path / "clean.wav"
    sf.write(str(clean_path), _render(MELODY_A, 120, 0.0), SR)
    same_path, offset0 = correct_tuning_file(clean_path)
    assert same_path == clean_path, "閾値未満なら入力pathを返すべき"
    assert abs(offset0) < CORRECTION_THRESHOLD_CENTS


def test_transcribe_preserves_input_file(tmp_path):
    """回帰(#55修正バグ): transcribe_file は入力ファイルを絶対に削除しない。

    str/Path混在の比較誤りで「無補正パススルー時に入力本体を一時ファイルと
    誤認して削除する」バグが全スイートで実測された(FileNotFound連鎖)。
    strパス・Pathパスの両方で入力が残ることを固定する。
    """
    import soundfile as sf

    from earpipe.pipeline import transcribe_file

    wav = tmp_path / "keep_me.wav"
    sf.write(str(wav), _render(MELODY_A, 120, 0.0), SR)

    transcribe_file(str(wav))  # strで渡す(バグの再現条件)
    assert wav.exists(), "strパス入力が削除された"
    transcribe_file(wav)  # Pathで渡す
    assert wav.exists(), "Pathパス入力が削除された"
