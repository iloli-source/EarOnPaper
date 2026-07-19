"""C8 フィールド録音モード(Issue #37): 雑音からの選択的抽出。

正解既知の合成メロディに雑音(ホワイト/ピンク/残響/打撃)を段階SNRで混入し、
(1) F1劣化カーブが破綻しないこと
(2) 雑音のみ入力で音符ゼロ(「拾えないものは拾えないと正直に言う」)
(3) FieldReport が非音程成分を分類報告すること
を検証する。

F1下限はベースライン封緘値(2026-07-19実測から保守的に固定した回帰ガード)であり、
目標値ではない。実測カーブは bench/results-field.md に記録する。
"""

import numpy as np
import pytest

from earpipe.contracts import FieldReport
from earpipe.pipeline import transcribe_file
from earpipe.services.ear import detect_events
from earpipe.services.ear.field_select import select_events
from earpipe.services.stem import analyze_field
from tests.conftest import MELODY_SIMPLE, SR, melody_to_seconds, note_f1, render_melody

BPM = 100
RNG = np.random.default_rng(37)


# --- 雑音生成ヘルパ -------------------------------------------------------


def white_noise(n: int) -> np.ndarray:
    return RNG.standard_normal(n)


def pink_noise(n: int) -> np.ndarray:
    """1/fノイズ(周波数領域で1/sqrt(f)整形)。"""
    spec = np.fft.rfft(RNG.standard_normal(n))
    freqs = np.fft.rfftfreq(n, d=1.0)
    freqs[0] = freqs[1] if len(freqs) > 1 else 1.0
    spec = spec / np.sqrt(freqs)
    y = np.fft.irfft(spec, n=n)
    return y / (np.max(np.abs(y)) + 1e-12)


def percussion_track(n: int, sr: int = SR, interval_sec: float = 0.5) -> np.ndarray:
    """非音程の打撃列: 短い減衰ノイズバーストを等間隔に配置。"""
    y = np.zeros(n)
    burst_len = int(0.05 * sr)
    envelope = np.exp(-np.linspace(0, 8, burst_len))
    pos = 0
    step = int(interval_sec * sr)
    while pos + burst_len < n:
        y[pos : pos + burst_len] += RNG.standard_normal(burst_len) * envelope
        pos += step
    return y


def add_reverb(y: np.ndarray, sr: int = SR, t60: float = 0.6) -> np.ndarray:
    """簡易残響: 指数減衰ノイズIRとの畳み込み。"""
    ir_len = int(t60 * sr)
    ir = RNG.standard_normal(ir_len) * np.exp(-np.linspace(0, 7, ir_len))
    ir[0] = 1.0
    wet = np.convolve(y, ir)[: len(y)]
    return 0.7 * y + 0.3 * wet / (np.max(np.abs(wet)) + 1e-12) * np.max(np.abs(y))


def mix_at_snr(signal: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """信号に対して指定SNR(dB)になるよう雑音をスケールして混合。"""
    noise = noise[: len(signal)]
    if len(noise) < len(signal):
        noise = np.pad(noise, (0, len(signal) - len(noise)))
    p_sig = float(np.mean(signal**2))
    p_noise = float(np.mean(noise**2)) + 1e-18
    scale = np.sqrt(p_sig / (p_noise * 10 ** (snr_db / 10)))
    mixed = signal + noise * scale
    return mixed / (np.max(np.abs(mixed)) + 1e-12) * 0.9


def field_f1(y: np.ndarray, sr: int = SR) -> float:
    """フィールドモード相当(解析→選択)でイベント抽出しF1を返す。"""
    from earpipe.services.stem import denoise

    analysis = analyze_field(y, sr)
    events = detect_events(denoise(y, sr), sr)
    events = select_events(events, analysis.snr_db)
    truth = melody_to_seconds(MELODY_SIMPLE, BPM)
    pred = [(e.midi, e.onset, e.offset) for e in events]
    return note_f1(truth, pred)


@pytest.fixture(scope="module")
def clean_melody() -> np.ndarray:
    return render_melody(MELODY_SIMPLE, BPM)


# --- SNR劣化カーブ(回帰ガード) -------------------------------------------


class TestDegradationCurve:
    def test_clean_baseline(self, clean_melody):
        assert field_f1(clean_melody) >= 0.8

    @pytest.mark.parametrize("snr_db,floor", [(20, 0.9), (10, 0.85)])
    def test_white_noise_floor(self, clean_melody, snr_db, floor):
        mixed = mix_at_snr(clean_melody, white_noise(len(clean_melody)), snr_db)
        f1 = field_f1(mixed)
        assert f1 >= floor, f"white SNR{snr_db}dB F1={f1:.3f} < {floor}"

    @pytest.mark.parametrize("snr_db,floor", [(20, 0.9), (10, 0.85), (5, 0.6)])
    def test_pink_noise_floor(self, clean_melody, snr_db, floor):
        mixed = mix_at_snr(clean_melody, pink_noise(len(clean_melody)), snr_db)
        f1 = field_f1(mixed)
        assert f1 >= floor, f"pink SNR{snr_db}dB F1={f1:.3f} < {floor}"

    def test_white_snr5_honest_no_garbage(self, clean_melody):
        """白色雑音SNR5dBはpYINの実測限界(検出消失)。ここでの要求は
        「間違った音符の洪水を出さない」こと — 検出数は正解数以下で、
        分類報告がvery_noisyを正直に示す。"""
        mixed = mix_at_snr(clean_melody, white_noise(len(clean_melody)), 5)
        analysis = analyze_field(mixed, SR)
        from earpipe.services.stem import denoise
        events = select_events(detect_events(denoise(mixed, SR), SR), analysis.snr_db)
        assert len(events) <= len(MELODY_SIMPLE)
        assert analysis.noise_profile == "very_noisy"

    def test_reverb_floor(self, clean_melody):
        f1 = field_f1(add_reverb(clean_melody))
        assert f1 >= 0.6, f"reverb F1={f1:.3f} < 0.6"

    def test_percussion_mix_floor(self, clean_melody):
        mixed = mix_at_snr(clean_melody, percussion_track(len(clean_melody)), 10)
        f1 = field_f1(mixed)
        assert f1 >= 0.5, f"percussion SNR10dB F1={f1:.3f} < 0.5"


# --- 正直さ: 雑音のみ → 音符ゼロ -----------------------------------------


class TestHonestZero:
    @pytest.mark.parametrize(
        "make_noise", [white_noise, pink_noise, lambda n: percussion_track(n)]
    )
    def test_noise_only_yields_zero(self, make_noise):
        n = SR * 4
        y = make_noise(n)
        y = y / (np.max(np.abs(y)) + 1e-12) * 0.5
        analysis = analyze_field(y, SR)
        events = select_events(detect_events(y, SR), analysis.snr_db)
        assert events == [], f"noise-only produced {len(events)} events"


# --- FieldReport(非音程成分の分類報告) ------------------------------------


class TestFieldReport:
    def test_report_ratios_sane(self, clean_melody):
        report = analyze_field(clean_melody, SR).report
        assert isinstance(report, FieldReport)
        for v in (
            report.harmonic_ratio,
            report.percussive_ratio,
            report.noise_like_ratio,
        ):
            assert 0.0 <= v <= 1.0
        assert report.harmonic_ratio + report.percussive_ratio + report.noise_like_ratio <= 1.5

    def test_clean_melody_is_harmonic_dominant(self, clean_melody):
        report = analyze_field(clean_melody, SR).report
        assert report.harmonic_ratio > report.percussive_ratio
        assert report.harmonic_ratio > report.noise_like_ratio

    def test_noise_heavy_is_reported(self, clean_melody):
        mixed = mix_at_snr(clean_melody, white_noise(len(clean_melody)), 0)
        clean_report = analyze_field(clean_melody, SR).report
        noisy_report = analyze_field(mixed, SR).report
        assert noisy_report.noise_like_ratio > clean_report.noise_like_ratio

    def test_percussion_is_reported(self, clean_melody):
        mixed = mix_at_snr(clean_melody, percussion_track(len(clean_melody)), 5)
        clean_report = analyze_field(clean_melody, SR).report
        perc_report = analyze_field(mixed, SR).report
        assert perc_report.percussive_ratio > clean_report.percussive_ratio

    def test_snr_estimate_orders_correctly(self, clean_melody):
        noisy = mix_at_snr(clean_melody, white_noise(len(clean_melody)), 5)
        a_clean = analyze_field(clean_melody, SR)
        a_noisy = analyze_field(noisy, SR)
        assert a_clean.snr_db > a_noisy.snr_db


# --- pipeline統合 ----------------------------------------------------------


class TestPipelineIntegration:
    def test_field_mode_returns_report(self, clean_melody, tmp_path):
        import soundfile as sf

        wav = tmp_path / "field.wav"
        sf.write(wav, clean_melody, SR)
        result = transcribe_file(wav, out_musicxml=tmp_path / "out.musicxml", field_mode=True)
        assert "field_report" in result
        fr = result["field_report"]
        assert set(fr) >= {"snr_db", "noise_profile", "harmonic_ratio", "percussive_ratio", "noise_like_ratio"}
        assert result["n_notes"] > 0

    def test_default_has_no_report(self, clean_melody, tmp_path):
        import soundfile as sf

        wav = tmp_path / "plain.wav"
        sf.write(wav, clean_melody, SR)
        result = transcribe_file(wav)
        assert "field_report" not in result
