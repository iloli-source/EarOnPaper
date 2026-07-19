"""フィールド録音分析(C8): SNR推定と非音程成分の分類。

「雑音の海から音程のあるものだけをつまみ出す」ための前段分析。
拾わなかったエネルギーも分類して報告する(拾えないものは拾えないと正直に言う)。
分類はHPSS(調波/打撃分離)+スペクトル平坦度のヒューリスティックであり、
その限界をFieldReportのdocstringに明記している。
"""

from dataclasses import dataclass

import librosa
import numpy as np
from scipy.ndimage import median_filter

from earpipe.contracts import FieldReport

_FLATNESS_NOISE = 0.15   # これ超の平坦度は「ノイズ様」
_PERC_DOMINANCE = 2.0    # 打撃エネルギーが調波の何倍なら「打撃様」か
_SNR_CLEAN_DB = 20.0  # 実SNRスケール(dB)。#45で無音率検出器から作り直した際に再較正
_SNR_NOISY_DB = 10.0
_SNR_MAX_DB = 60.0    # 飽和上限(クリーン純音は数値床のため発散するのを防ぐ)
_MEDIAN_TO_MEAN = float(np.log(2.0))  # 指数分布(ガウス雑音のパワースペクトル)の中央値→平均補正


@dataclass(frozen=True)
class FieldAnalysis:
    """analyze_field の結果: SNRと分類レポート。"""

    snr_db: float           # 実SNR推定値(dB)。0〜60にクランプ。広帯域成分は雑音側に数える
    noise_profile: str
    report: FieldReport


_FLOOR_MEDIAN_BINS = 61  # 周波数方向メディアンフィルタの窓幅(ビン)。#51で較正:
# 音程ピーク+漏れ裾(〜9ビン)を確実に棄却しつつ、褐色混合の±6dB追跡が保つ上限が61。
# 81以上では低域傾斜の平滑化が過ぎて褐色混合の誤差が±6dBを超える(実測)。


def _estimate_snr_db(S: np.ndarray) -> float:
    """周波数方向メディアンフィルタによる雑音床分離の実SNR推定(dB)。

    各フレームのパワースペクトルに周波数方向の移動中央値(窓61ビン)をかけ、
    その結果を雑音床PSDとみなす。中央値は滑らかなスペクトル傾斜には追従し
    (単調列の中央値=中央要素)、窓幅より狭い音程ピーク+漏れ裾は棄却するため、
    スペクトル傾斜に依存しない — 全ビン一括の中央値は白色雑音専用で、
    低域偏重の有色雑音(褐色・空調・残響尾)では大半のビンが静かなため床を
    過小評価し、純雑音を est_snr=44dB/clean と誤報した(#51 R2-S1で実証)。
    ガウス雑音のビンパワーは指数分布のため中央値をln2で平均に補正し、
    雑音総パワー = Σ床、信号 = 総パワー − 雑音、として
    アクティブフレーム合算のSNRを返す。0〜_SNR_MAX_DBにクランプ。

    限界(正直な記録): ①ドラム等の広帯域「音楽」成分も雑音側に数える
    (音程抽出の観点では妥当)。②窓幅(61ビン≈650Hz)より広がる狭帯域雑音の
    集合(ハム+倍音列など)は信号側に数えられうる。③残響尾は信号のスペクトル
    形状に従うため大部分が信号側に残る(残響はSNRでなく別途の課題)。
    白色/ピンク/褐色の既知SNR混合での誤差は±6dB水準(テスト固定)。
    """
    P = S.astype(np.float64) ** 2  # (bins, frames) パワー
    frame_total = P.sum(axis=0)
    if frame_total.size == 0:
        return 0.0
    active = frame_total > max(float(frame_total.max()) * 1e-6, 1e-18)
    if not bool(active.any()):
        return 0.0
    Pa = P[:, active]
    floor = (
        median_filter(Pa, size=(_FLOOR_MEDIAN_BINS, 1), mode="nearest")
        / _MEDIAN_TO_MEAN
    )
    noise_per_frame = floor.sum(axis=0)
    total_per_frame = Pa.sum(axis=0)
    signal_per_frame = np.maximum(total_per_frame - noise_per_frame, 0.0)
    noise = float(noise_per_frame.sum()) + 1e-30
    signal = float(signal_per_frame.sum())
    snr = 10.0 * np.log10(signal / noise + 1e-30)
    return float(np.clip(snr, 0.0, _SNR_MAX_DB))


def _to_mono(y: np.ndarray) -> np.ndarray:
    """ステレオ入力をモノラルへ畳む。(frames, ch)/(ch, frames)の両配置に対応
    (soundfileとlibrosaで軸配置が逆のため。レビュー#40 M4)。"""
    if y.ndim <= 1:
        return y
    # チャンネル軸=要素数が少ない側(2ch程度)とみなす
    ch_axis = int(np.argmin(y.shape))
    return y.mean(axis=ch_axis)


def analyze_field(y: np.ndarray, sr: int) -> FieldAnalysis:
    """波形を分析し、SNR推定と成分分類(FieldReport)を返す。

    sr は現状未使用(n_fft/hopは固定)だが、契約としてサンプルレートを受け取る。
    22.05k/44.1k両系で動作確認済み(時間分解能のみ変わる)。
    """
    y = _to_mono(np.asarray(y, dtype=np.float64))
    # 境界検証: 破損WAV等由来の非有限値でlibrosaが即死しないよう無音化する(#45 S3/S4)
    if not np.all(np.isfinite(y)):
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    if len(y) == 0 or float(np.max(np.abs(y))) < 1e-9:
        report = FieldReport(0.0, "very_noisy", 0.0, 0.0, 0.0)
        return FieldAnalysis(0.0, "very_noisy", report)

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    snr_db = _estimate_snr_db(S)

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
    1フレーム未満(2048サンプル)の入力は降噪せずそのまま返す。
    """
    y = _to_mono(np.asarray(y, dtype=np.float64))
    if not np.all(np.isfinite(y)):
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    if len(y) < 2048:
        return y
    S = librosa.stft(y, n_fft=2048, hop_length=512)
    mag, phase = np.abs(S), np.angle(S)
    noise_mag = np.percentile(mag, 10, axis=1, keepdims=True)
    cleaned = np.maximum(mag - 1.5 * noise_mag, 0.05 * mag)
    y_out = librosa.istft(cleaned * np.exp(1j * phase), hop_length=512, length=len(y))
    return y_out.astype(np.float64)
