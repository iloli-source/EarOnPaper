"""F-002 音質診断: 生波形から録音品質を三本柱(クリッピング・SNR・帯域)+残響で評価する。

入力音源がそのまま採譜に耐えるかを事前に見立て、赤/黄/緑の信号と日本語警告を返す。
実装は librosa/numpy のみに依存し、重い盲推定ライブラリ(blind-rt60等)は使わない。

限界(正直な注記):
- SNR は「曲中に低エネルギー区間がある」前提の雑音床パーセンタイル法であり、
  密なミックスやサステイン主体の音源では過小評価しうる内部プロキシ値である。
- reverb_ratio は 0-1 の残響の"にじみ"プロキシであり、秒単位RT60ではない。
  リリースの長い楽器か実際の残響かを原理的には分離できない(誤陽性の主因)。
- クリッピング率は「フルスケール正規化(ピーク基準)」に対する相対割合であり、
  int16 やピークの低い素材でも動くようピーク正規化してから閾値判定する。
"""

from dataclasses import dataclass, field
from typing import Literal

import librosa
import numpy as np
from scipy.ndimage import median_filter

# ---- 名前付き定数(magic number禁止・全閾値をここに集約) --------------------

# クリッピング判定: ピーク基準に対しこの比率を超えた振幅を「張り付き」とみなす
_CLIP_THRESHOLD_RATIO = 0.98
# クリッピング率(割合)の段階閾値
_CLIP_YELLOW_RATE = 0.005  # 0.5%超で注意
_CLIP_RED_RATE = 0.01      # 1%超で不良

# SNR推定のSTFT設定と飽和クランプ範囲
_STFT_N_FFT = 2048
_STFT_HOP_LENGTH = 512
_RMS_FRAME_LENGTH = 2048  # 残響包絡・極短ガード判定用
_RMS_HOP_LENGTH = 512
# 周波数方向メディアンフィルタで雑音床を分離する(field.pyの実SNR推定と同方式)。
# 単純なフレームRMSパーセンタイル法は「無音率検出器」になり連続純音を雑音と誤判定するため不可。
_FLOOR_MEDIAN_BINS = 61  # 雑音床メディアン窓(ビン)
_MEDIAN_TO_MEAN = float(np.log(2.0))  # 指数分布の中央値→平均補正
_SNR_MIN_DB = 0.0
_SNR_MAX_DB = 60.0
# SNRの段階閾値(dB)
_SNR_YELLOW_DB = 20.0  # これ未満で注意
_SNR_RED_DB = 10.0     # これ未満で不良

# 帯域上限プロキシ(spectral_rolloff)の設定
_ROLLOFF_PERCENT = 0.985
# ハイファイ期待時の帯域上限段階閾値(Hz)。srに応じてナイキストで相対化する
_BAND_YELLOW_HZ = 16000.0  # これ未満で高域欠落の疑い(128kbps MP3相当)
_BAND_RED_HZ = 8000.0      # これ未満で明確な帯域不足(電話帯域・8kHz収録相当)
# srのナイキストに対しこの割合まではロールオフが頭打ちになる=帯域不足と見なさない
_NYQUIST_MARGIN = 0.9

# 残響プロキシ(オンセット包絡の自己相関=にじみ)の注意閾値(0-1)。
# 秒RT60級の信頼度は得られず、持続音と残響を原理的に分離できないため、
# 残響は単独でredにせず最大yellow(注意)止まりとする(誤陽性の主因への保守的対処)。
_REVERB_YELLOW = 0.6
# 自己相関を評価する短ラグ範囲(フレーム)。直接音はオンセットで谷が深く相関が低い。
_REVERB_LAG_LO = 1
_REVERB_LAG_HI = 6

# 数値安定化の微小値
_EPS = 1e-12

_Rating = Literal["green", "yellow", "red"]
# 悪さの順位(統合時に最悪値を採用)
_RATING_RANK: dict[str, int] = {"green": 0, "yellow": 1, "red": 2}


@dataclass(frozen=True)
class AudioQuality:
    """音質診断の結果(F-002)。frozen だが warnings は構築後に変更しない前提で扱う。

    レビュー#40注記と同様、list をfrozen dataclassに持たせても要素は可変であるため
    "不変"を厳密には保証しない。診断側は毎回新規listを生成し外部参照を共有しない
    (default_factory 使用)。呼び出し側も破壊的変更をしないこと。

    フィールド:
        clipping_rate: 振幅がピーク基準閾値を超えたサンプルの割合(0-1)
        snr_db: 推定SNR(内部プロキシ値・0〜60でクランプ)。大きいほどクリーン
        reverb_ratio: 残響の"にじみ"プロキシ(0-1)。大きいほど残響過多の疑い
        band_limit_hz: 帯域上限プロキシ(spectral_rolloffの中央値・Hz)
        rating: 総合判定 green/yellow/red(各指標の最悪値を採用)
        warnings: 不良/注意要因の日本語メッセージ列
    """

    clipping_rate: float
    snr_db: float
    reverb_ratio: float
    band_limit_hz: float
    rating: _Rating
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """不変条件の検証: rating は3値のみ、比率系は非負。"""
        if self.rating not in _RATING_RANK:
            raise ValueError(f"rating は green/yellow/red のいずれか: {self.rating!r}")
        if self.clipping_rate < 0.0 or self.reverb_ratio < 0.0:
            raise ValueError("clipping_rate/reverb_ratio は非負でなければならない")


def _to_mono_float(y: np.ndarray) -> np.ndarray:
    """入力波形をモノラルの float32 1D に正規化する。

    ステレオ(2D)は librosa.to_mono でチャンネル平均、int系はfloatへスケールする。
    """
    arr = np.asarray(y)
    # int16 等の整数型はフルスケールで割ってfloatへ
    if np.issubdtype(arr.dtype, np.integer):
        info = np.iinfo(arr.dtype)
        arr = arr.astype(np.float64) / max(abs(info.min), info.max)
    else:
        arr = arr.astype(np.float64, copy=False)
    if arr.ndim > 1:
        arr = librosa.to_mono(arr)
    return np.ascontiguousarray(arr.reshape(-1))


def _safe_default_red(warnings: list[str]) -> AudioQuality:
    """安全なデフォルト(赤)を返す。空・全ゼロ・NaN/Inf など診断不能時に使う。"""
    return AudioQuality(
        clipping_rate=0.0,
        snr_db=0.0,
        reverb_ratio=0.0,
        band_limit_hz=0.0,
        rating="red",
        warnings=list(warnings),
    )


def _estimate_clipping_rate(y: np.ndarray) -> float:
    """ピーク基準に対する張り付きサンプルの割合を返す(0-1)。"""
    peak = float(np.max(np.abs(y)))
    if peak <= _EPS:
        return 0.0
    threshold = _CLIP_THRESHOLD_RATIO * peak
    clipped = np.count_nonzero(np.abs(y) >= threshold)
    return float(clipped) / float(y.size)


def _estimate_snr_db(y: np.ndarray, sr: int) -> float:
    """スペクトル雑音床分離による実SNR(dB)を推定する。0〜60にクランプ。

    各フレームのパワースペクトルに周波数方向の移動中央値をかけ雑音床PSDとみなす
    (滑らかな傾斜には追従し、窓幅より狭い音程ピークは棄却)。中央値は指数分布の
    平均へ ln2 で補正する。雑音総パワー=Σ床、信号=総パワー−雑音として合算しSNR化。

    注記: この方式(field.pyの実SNR推定と同方式)を採るのは、単純なフレームRMSの
    上位/下位パーセンタイル比が「無音率検出器」に堕し、連続純音を雑音と誤判定する
    ため。密なミックス等では雑音床を過大に見積もりSNRを過小評価しうる内部プロキシ値。
    """
    stft = np.abs(librosa.stft(y, n_fft=_STFT_N_FFT, hop_length=_STFT_HOP_LENGTH))
    power = stft.astype(np.float64) ** 2  # (bins, frames)
    frame_total = power.sum(axis=0)
    if frame_total.size == 0:
        return _SNR_MIN_DB
    active = frame_total > max(float(frame_total.max()) * 1e-6, 1e-18)
    if not bool(active.any()):
        return _SNR_MIN_DB
    active_power = power[:, active]
    floor = median_filter(
        active_power, size=(_FLOOR_MEDIAN_BINS, 1), mode="nearest"
    ) / _MEDIAN_TO_MEAN
    noise = float(floor.sum()) + _EPS
    signal = float(np.maximum(active_power.sum(axis=0) - floor.sum(axis=0), 0.0).sum())
    snr = 10.0 * np.log10(signal / noise + _EPS)
    return float(np.clip(snr, _SNR_MIN_DB, _SNR_MAX_DB))


def _estimate_band_limit_hz(y: np.ndarray, sr: int) -> float:
    """spectral_rolloff の中央値を帯域上限プロキシ(Hz)として返す。

    無音フレームは rolloff=0 を返し中央値を汚すため、有音(rolloff>0)フレームのみ集計。
    """
    rolloff = librosa.feature.spectral_rolloff(
        y=y, sr=sr, roll_percent=_ROLLOFF_PERCENT
    ).ravel()
    voiced = rolloff[rolloff > 0.0]
    if voiced.size == 0:
        return 0.0
    return float(np.median(voiced))


def _estimate_reverb_ratio(y: np.ndarray) -> float:
    """RMS包絡の短ラグ自己相関による残響の"にじみ"プロキシを返す(0-1)。

    直接音(ドライ)はオンセットで包絡が鋭く立ち上がり谷が深いため短ラグ自己相関が
    低い。残響は谷を埋めて包絡を平滑化するため相関が上がる。1〜数フレームの自己相関の
    平均を 0-1 にクランプして返す。

    限界(正直な記録): これは秒単位RT60ではなく、リリースの長い楽器の持続音も
    「にじみ」として高く出る(誤陽性の主因)。持続音と残響を原理的には分離できないため、
    この値は単独でred判定に用いず注意(yellow)止まりとする。
    """
    rms = librosa.feature.rms(
        y=y, frame_length=_RMS_FRAME_LENGTH, hop_length=_RMS_HOP_LENGTH
    ).ravel()
    rms = rms[np.isfinite(rms)]
    if rms.size < _REVERB_LAG_HI:
        return 0.0
    env = rms - float(np.mean(rms))
    if not np.any(env):
        return 0.0
    autocorr = np.correlate(env, env, mode="full")
    autocorr = autocorr[autocorr.size // 2 :]
    zero_lag = float(autocorr[0])
    if abs(zero_lag) <= _EPS:
        return 0.0
    autocorr = autocorr / zero_lag
    short_lag = autocorr[_REVERB_LAG_LO:_REVERB_LAG_HI]
    return float(np.clip(np.mean(short_lag), 0.0, 1.0))


def _rate_clipping(rate: float, warnings: list[str]) -> _Rating:
    """クリッピング率をrating化し、必要なら日本語警告を積む。"""
    if rate > _CLIP_RED_RATE:
        warnings.append(f"クリッピング率{rate * 100:.1f}%(過大・振幅の張り付き)")
        return "red"
    if rate > _CLIP_YELLOW_RATE:
        warnings.append(f"クリッピング率{rate * 100:.1f}%(やや過大)")
        return "yellow"
    return "green"


def _rate_snr(snr_db: float, warnings: list[str]) -> _Rating:
    """SNRをrating化し、必要なら日本語警告を積む。"""
    if snr_db < _SNR_RED_DB:
        warnings.append(f"SNR{snr_db:.0f}dB(雑音過多)")
        return "red"
    if snr_db < _SNR_YELLOW_DB:
        warnings.append(f"SNR{snr_db:.0f}dB(やや雑音あり)")
        return "yellow"
    return "green"


def _rate_band_limit(band_hz: float, sr: int, warnings: list[str]) -> _Rating:
    """帯域上限をrating化する。srのナイキストで相対化し低srの誤判定を避ける。"""
    nyquist = sr / 2.0
    # srが物理的に頭打ちになる領域は帯域不足と見なさない
    red_ref = min(_BAND_RED_HZ, _NYQUIST_MARGIN * nyquist)
    yellow_ref = min(_BAND_YELLOW_HZ, _NYQUIST_MARGIN * nyquist)
    if band_hz < red_ref:
        warnings.append(f"帯域上限{band_hz / 1000:.1f}kHz(高域欠落・低ビットレートの可能性)")
        return "red"
    if band_hz < yellow_ref:
        warnings.append(f"帯域上限{band_hz / 1000:.1f}kHz(高域やや不足)")
        return "yellow"
    return "green"


def _rate_reverb(reverb_ratio: float, warnings: list[str]) -> _Rating:
    """残響プロキシをrating化する。持続音と分離できないため最大yellow止まり。"""
    if reverb_ratio > _REVERB_YELLOW:
        warnings.append(f"残響の疑い(にじみ比{reverb_ratio:.2f}・持続音の可能性あり)")
        return "yellow"
    return "green"


def _worst(ratings: list[str]) -> _Rating:
    """複数ratingの最悪値(red>yellow>green)を返す。"""
    worst = max(ratings, key=lambda r: _RATING_RANK[r])
    return worst  # type: ignore[return-value]


def diagnose_audio(y: np.ndarray, sr: int) -> AudioQuality:
    """生波形の録音品質を診断し AudioQuality を返す(F-002)。

    クリッピング率・SNR・帯域上限・残響を各々推定して green/yellow/red にビン分けし、
    最悪値を総合ratingとする。空配列・全ゼロ・NaN/Inf・極短信号は例外にせず、
    安全なデフォルト(rating="red" + 警告)を返す。

    Args:
        y: 音声波形。モノ/ステレオ(2D)・int/float いずれも受け付ける。
        sr: サンプルレート(Hz)。

    Returns:
        AudioQuality: 各指標値と総合rating・日本語警告列。
    """
    if sr <= 0:
        return _safe_default_red(["サンプルレート不正(診断不能)"])

    mono = _to_mono_float(y)

    # ---- 冒頭ガード: 診断不能な入力は安全なデフォルトで返す --------------------
    if mono.size == 0:
        return _safe_default_red(["入力が空(診断不能)"])
    if not np.all(np.isfinite(mono)):
        return _safe_default_red(["NaN/Infを含む波形(診断不能)"])
    if float(np.max(np.abs(mono))) <= _EPS:
        return _safe_default_red(["全ゼロ/無音(診断不能)"])
    # フレーム化に満たない極短信号は診断不能扱い
    if mono.size < _RMS_FRAME_LENGTH:
        return _safe_default_red(["信号が短すぎる(診断不能)"])

    # ---- 各指標の推定 ------------------------------------------------------
    clipping_rate = _estimate_clipping_rate(mono)
    snr_db = _estimate_snr_db(mono, sr)
    band_limit_hz = _estimate_band_limit_hz(mono, sr)
    reverb_ratio = _estimate_reverb_ratio(mono)

    # ---- rating統合(最悪値採用)と警告収集 --------------------------------
    warnings: list[str] = []
    ratings = [
        _rate_clipping(clipping_rate, warnings),
        _rate_snr(snr_db, warnings),
        _rate_band_limit(band_limit_hz, sr, warnings),
        _rate_reverb(reverb_ratio, warnings),
    ]
    rating = _worst(ratings)

    return AudioQuality(
        clipping_rate=round(clipping_rate, 6),
        snr_db=round(snr_db, 2),
        reverb_ratio=round(reverb_ratio, 3),
        band_limit_hz=round(band_limit_hz, 1),
        rating=rating,
        warnings=warnings,
    )
