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

from earpipe.contracts import NOTABLE_CLASSES, FieldReport, SoundClass, SoundEvent

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


# --- F-108 音事件分類(6タグ) -------------------------------------------
#
# 「雑音の海から音程のあるものだけをつまみ出す」ため、音符化の前に各音事件を
# 6タグ(SoundClass)へ振り分ける。分類はHPSS+スペクトル平坦度+調波ピーク数の
# ヒューリスティックであり、ASRやピッチ多重推定の置き換えではない。
# 目的は「音程を持つ成分だけを音符化し、非音程/声/和音は正直に別扱いする」こと。

_HARM_FLATNESS_STRONG = 0.03  # これ以下は調波性が非常に強い = 即pitched確定(声判定より優先)
_HARM_FLATNESS_MAX = 0.08   # これ以下の平坦度なら「調波性がある」候補(単音の実測は≈0)
_NOISE_FLATNESS_MIN = 0.30  # これ以上は明確な広帯域雑音(白色)
_NOISE_FLATNESS_MID = 0.10  # これ以上かつ強いピーク構造がなければ有色雑音(ピンク/褐色)扱い
_INHARMONIC_PERC_RATIO = 2.5  # 打撃エネルギーが調波の何倍超で inharmonic とみなすか
_TRANSIENT_DUR_SEC = 0.12   # これ未満の調波音は pitched_transient(撥弦アタック等)
_POLY_PEAK_COUNT = 4        # 独立した強スペクトルピークがこの数以上なら poly(和音)候補
_SPEECH_FLUX_MIN = 0.14     # スペクトル重心の相対変動がこれ超で speech 候補(粗い代理)
_SPEECH_MIN_DUR_SEC = 0.20  # speech判定の最小長。短い断片は重心が不安定なので声扱いしない
_SPEECH_CENTROID_HZ = 3000.0  # 声の重心上限目安。これ超の高域偏重は speech から除外
_PEAK_PROMINENCE = 0.25     # ピーク検出: 局所最大/フレーム最大 のしきい値


def _spectral_peak_count(mag_frame: np.ndarray) -> int:
    """1フレームの振幅スペクトルから、際立つ局所ピークの数を数える。

    和音(poly)は独立した基本波+倍音列が複数立つためピーク数が増える。
    フレーム最大に対する相対しきい値で微小リップルを無視する。
    """
    if mag_frame.size < 3:
        return 0
    peak = float(mag_frame.max())
    if peak <= 0:
        return 0
    thr = peak * _PEAK_PROMINENCE
    left = mag_frame[1:-1] > mag_frame[:-2]
    right = mag_frame[1:-1] > mag_frame[2:]
    strong = mag_frame[1:-1] > thr
    return int(np.count_nonzero(left & right & strong))


def classify_segment(y: np.ndarray, sr: int) -> SoundEvent:
    """音事件セグメント(モノラル波形)を6タグ(SoundClass)に分類する(F-108)。

    判定順(倒し方は「疑わしきは音符化しない」側):
      1. 無音/極小 → noisy(音響オブジェクト扱い。音符化しない)
      2. 打撃エネルギーが調波を大きく上回る → inharmonic(金属打・ノック)
      3. 平坦度が高い(白色) → noisy(HPSSは雑音を調波/打撃に均等分配する)
      4. 強スペクトルピークが多く調波が支配的 → poly(和音。オンデマンド分解)
      5. 調波が非常に強い(平坦度極小・単音) → pitched(声誤判定を防ぐ短絡)
      6. 中程度平坦で強いピーク構造なし → noisy(有色雑音: ピンク/褐色)
      7. 一定長あり重心が不安定で中低域寄り → speech(声。採譜対象外)
      8. 調波性がある → 持続長で pitched_stable / pitched_transient
      9. 中間帯 → noisy(音符化しない側=正直)

    confidence は最有力クラスの代理スコア(0-1)。

    限界(正直な記録):
    - speech は「有声だが調波が不安定で中低域寄り」の粗い代理であり、ASR相当の
      音声区間検出ではない。歌声(安定した調波)は pitched に落ちるのが正常。
    - poly は同時発音のピーク数ベースで、密な倍音を持つ単音(金管)を誤検出しうる。
    - inharmonic/noisy の境界は連続的で、混合音では支配成分に丸められる。
    分類の目的は完全なラベリングではなく「音程を持つ成分だけを音符化する」ゲート。
    """
    y = _to_mono(np.asarray(y, dtype=np.float64))
    if not np.all(np.isfinite(y)):
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    dur = len(y) / sr if sr > 0 else 0.0
    if len(y) < 256 or float(np.max(np.abs(y))) < 1e-6:
        return SoundEvent("noisy", 0.0, "noisy" in NOTABLE_CLASSES)

    n_fft = 2048 if len(y) >= 2048 else 512
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=n_fft // 4))
    if S.size == 0:
        return SoundEvent("noisy", 0.0, False)

    H, P = librosa.decompose.hpss(S)
    h_e = float(np.sum(H**2))
    p_e = float(np.sum(P**2)) + 1e-18
    flatness = float(np.mean(librosa.feature.spectral_flatness(S=S)[0]))
    centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
    centroid = centroid[np.isfinite(centroid)]
    mean_centroid = float(np.mean(centroid)) if centroid.size else 0.0
    # 重心の相対変動(声は音素遷移で重心が揺れる)。定常音は小さい
    centroid_flux = (
        float(np.std(centroid) / (mean_centroid + 1e-9)) if centroid.size else 0.0
    )
    peak_counts = [_spectral_peak_count(S[:, j]) for j in range(S.shape[1])]
    med_peaks = float(np.median(peak_counts)) if peak_counts else 0.0

    hp_ratio = h_e / (h_e + p_e + 1e-18)

    def pitched(conf: float) -> SoundEvent:
        label: SoundClass = "pitched_transient" if dur < _TRANSIENT_DUR_SEC else "pitched_stable"
        return _sound_event(label, max(0.3, min(1.0, conf)))

    # 2) 非調波(打撃主体): 打撃エネルギーが調波を大きく上回る(ノック・金属打)
    if p_e > _INHARMONIC_PERC_RATIO * h_e:
        return _sound_event("inharmonic", min(1.0, p_e / (_INHARMONIC_PERC_RATIO * h_e + 1e-18)))

    # 3) 明確な広帯域雑音(白色): 平坦度が高い。HPSSは白色雑音を調波/打撃へほぼ均等
    #    分配するため h_e<p_e を条件にできず、平坦度単独で判定する
    if flatness >= _NOISE_FLATNESS_MIN:
        return _sound_event("noisy", min(1.0, flatness / _NOISE_FLATNESS_MIN))

    # 4) 多声(和音): 強ピークが多数立ち、調波が支配的。単音(med_peaks≈2)と分離する
    #    ため poly を pitched短絡より先に判定する
    if med_peaks >= _POLY_PEAK_COUNT and hp_ratio >= 0.5 and flatness <= _HARM_FLATNESS_MAX:
        return _sound_event("poly", min(1.0, med_peaks / (_POLY_PEAK_COUNT * 2.0)))

    # 5) 調波が非常に強い単音: 声判定より優先して pitched 確定。
    #    純音+倍音は平坦度が極小・重心が安定・明確なピークを持つ。この3条件で
    #    (a)重心が揺れる声(cf大)と (b)ピークを持たない褐色雑音(med_peaks=0)を除外する
    #    — どちらも平坦度だけ見ると≈0で単音に化けるため。
    if (
        flatness <= _HARM_FLATNESS_STRONG
        and h_e >= p_e
        and centroid_flux < _SPEECH_FLUX_MIN
        and med_peaks >= 1
    ):
        return pitched(1.0)

    # 6) 有色雑音(ピンク/褐色): 単音/和音は上の rule 4/5 で平坦度≈0のうちに確定済み。
    #    ここに残る「中程度の平坦度」は安定した調波構造がない証拠=雑音側に倒す
    #    (ピンクは平坦度が中程度でランダムピークを持つ)。褐色は平坦度≈0でも
    #    med_peaks=0(明確なピークなし)で拾う。
    if med_peaks < 1 or flatness > _HARM_FLATNESS_MAX:
        return _sound_event("noisy", min(1.0, max(flatness / _NOISE_FLATNESS_MID, 0.5)))

    # 7) 声: 一定長あり調波はあるが重心が不安定で中低域寄り(粗い代理)。
    #    声は基本波+複数フォルマントで med_peaks>=2。低域偏重の褐色雑音(ピーク乏しい)は
    #    ここで拾わず、直前の rule 6 で noisy 側に落とす。
    if (
        dur >= _SPEECH_MIN_DUR_SEC
        and centroid_flux >= _SPEECH_FLUX_MIN
        and mean_centroid <= _SPEECH_CENTROID_HZ
        and h_e >= p_e
        and med_peaks >= 2
    ):
        return _sound_event("speech", min(1.0, centroid_flux / _SPEECH_FLUX_MIN))

    # 8) 調波性がある → 持続長で安定/過渡を分ける
    if flatness <= _HARM_FLATNESS_MAX or h_e >= p_e:
        return pitched(hp_ratio + (_HARM_FLATNESS_MAX - min(flatness, _HARM_FLATNESS_MAX)))

    # 9) どれにも強く当てはまらない中間帯は noisy に倒す(音符化しない側=正直)
    return _sound_event("noisy", 0.5)


def _sound_event(label: SoundClass, confidence: float) -> SoundEvent:
    return SoundEvent(
        label=label,
        confidence=round(float(np.clip(confidence, 0.0, 1.0)), 3),
        is_notable=label in NOTABLE_CLASSES,
    )


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
