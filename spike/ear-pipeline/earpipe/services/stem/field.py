"""フィールド録音分析(C8): SNR推定と非音程成分の分類。

「雑音の海から音程のあるものだけをつまみ出す」ための前段分析。
拾わなかったエネルギーも分類して報告する(拾えないものは拾えないと正直に言う)。
分類はHPSS(調波/打撃分離)+スペクトル平坦度のヒューリスティックであり、
その限界をFieldReportのdocstringに明記している。
"""

from dataclasses import dataclass

import librosa
import numpy as np

from earpipe.contracts import FieldReport

_FLATNESS_NOISE = 0.15   # これ超の平坦度は「ノイズ様」
_PERC_DOMINANCE = 2.0    # 打撃エネルギーが調波の何倍なら「打撃様」か
_SNR_CLEAN_DB = 8.0   # 推定器の実測スケール(クリーン系≈9で飽和)に較正済み
_SNR_NOISY_DB = 6.0


@dataclass(frozen=True)
class FieldAnalysis:
    """analyze_field の結果: SNRと分類レポート。"""

    snr_db: float           # 内部プロキシ値(絶対SNRではない。クリーン疎音源で≈9に飽和する実測特性)
    noise_profile: str
    report: FieldReport


def _estimate_snr_db(rms: np.ndarray) -> float:
    """フレームRMSの上位/下位百分位比からSNRを概算する。

    静かなフレーム(下位10%)を雑音床、鳴っているフレーム(上位90%)を信号とみなす。
    クリーンな演奏は音間の無音が床になるためSNRが大きく出る。
    """
    lo = float(np.percentile(rms, 10)) + 1e-10
    hi = float(np.percentile(rms, 90)) + 1e-10
    return float(20.0 * np.log10(hi / lo))


def analyze_field(y: np.ndarray, sr: int) -> FieldAnalysis:
    """波形を分析し、SNR推定と成分分類(FieldReport)を返す。"""
    y = np.asarray(y, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) == 0 or float(np.max(np.abs(y))) < 1e-9:
        report = FieldReport(0.0, "very_noisy", 0.0, 0.0, 0.0)
        return FieldAnalysis(0.0, "very_noisy", report)

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    rms = librosa.feature.rms(S=S)[0]
    snr_db = _estimate_snr_db(rms)

    H, P = librosa.decompose.hpss(S)
    flatness = librosa.feature.spectral_flatness(S=S)[0]
    h_e = np.sum(H**2, axis=0)
    p_e = np.sum(P**2, axis=0)
    e = h_e + p_e + 1e-18
    total = float(np.sum(e))

    perc_frame = p_e > _PERC_DOMINANCE * h_e
    noise_frame = (~perc_frame) & (flatness > _FLATNESS_NOISE)
    harm_frame = ~(perc_frame | noise_frame)

    report = FieldReport(
        snr_db=round(snr_db, 1),
        noise_profile=_profile(snr_db),
        harmonic_ratio=round(float(np.sum(e[harm_frame])) / total, 3),
        percussive_ratio=round(float(np.sum(e[perc_frame])) / total, 3),
        noise_like_ratio=round(float(np.sum(e[noise_frame])) / total, 3),
    )
    return FieldAnalysis(snr_db=snr_db, noise_profile=report.noise_profile, report=report)


def _profile(snr_db: float) -> str:
    if snr_db >= _SNR_CLEAN_DB:
        return "clean"
    if snr_db >= _SNR_NOISY_DB:
        return "noisy"
    return "very_noisy"


def denoise(y: np.ndarray, sr: int) -> np.ndarray:
    """スペクトラルゲート降噪: 静かなフレームから雑音スペクトルを推定して差し引く。

    フィールド録音モードの前処理。雑音下でのpYIN崩壊(検出消失)を救済する。
    クリーン音源には実質無害(雑音床が小さいため差し引きも小さい)。
    """
    y = np.asarray(y, dtype=np.float64)
    if len(y) < 2048:
        return y
    S = librosa.stft(y, n_fft=2048, hop_length=512)
    mag, phase = np.abs(S), np.angle(S)
    noise_mag = np.percentile(mag, 10, axis=1, keepdims=True)
    cleaned = np.maximum(mag - 1.5 * noise_mag, 0.05 * mag)
    y_out = librosa.istft(cleaned * np.exp(1j * phase), hop_length=512, length=len(y))
    return y_out.astype(np.float64)
