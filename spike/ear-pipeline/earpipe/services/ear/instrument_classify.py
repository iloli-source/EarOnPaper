"""楽器の粗い推測(F-015): 1区間の波形から支配的な1楽器を推定する。

学習は一切使わない。spectral centroid/bandwidth/rolloff/ZCR と HPSS 打楽器比
を組み合わせた閾値ヒューリスティックであり、確信度は正直に低めに頭打ちする。

重要な限界(文献一致・正直な記録):
- これは「支配的な1楽器の粗い推測」であって多楽器の同時分類ではない。
  多楽器同時発音(piano+guitar 等)は単純特徴では原理的に分離不能(ISMIR2009)。
- spectral centroid は同一音でも時間変動するため(ResearchGate)、絶対Hz閾値には
  強く依存させず「目安」として confidence を下げる材料に使う。
- HPSS は白色雑音/拍手を調波・打撃へほぼ均等分配する(audiolabs-erlangen)ため、
  広帯域雑音は perc_ratio で捕まらず、正直に "unknown" へ倒す。
- ZCR は無声摩擦音/ノイズ/打楽器/シビランス/撥弦アタックすべてで上がるため、
  単独判定はせず必ず HPSS 打楽器比・調波優勢と AND で使う。

契約型 InstrumentGuess は現状 contracts.py に存在しないため、field.py が
FieldAnalysis をローカル定義するのと同じ流儀で本モジュール冒頭に frozen dataclass
として定義する(親が後で contracts.py へ昇格・配線する想定)。
"""

from dataclasses import dataclass

import librosa
import numpy as np

# --- 較正定数(粗判定・すべて「目安」。境界は unknown に倒す) ------------------
_MIN_LEN = 256              # これ未満のサンプル数は解析対象外(unknown)
_SILENCE_ABS = 1e-6         # 最大振幅がこれ未満なら無音扱い(unknown)
_ROUND_NDIGITS = 4          # features/confidence の丸め桁

_PERC_RATIO_HIGH = 0.60     # HPSS 打楽器比がこれ超なら打楽器性が強い
_PERC_ZCR_MIN = 0.10        # 打楽器判定に併用する ZCR 下限(単独では使わない)
_NOISE_PERC_BAND = 0.40     # perc_ratio がこの帯(≈0.4-0.6)の広帯域は雑音疑い→unknown

_BASS_CENTROID_HZ = 500.0   # これ未満の重心は低音寄り(bass guitar は低 centroid)
_BASS_ROLLOFF_HZ = 1500.0   # bass 判定の rolloff 上限目安

# 声の判定は flux 単独だと全楽器を拾う catch-all になる(実ラベル7楽器で確認)。
# 実測: vocal flux≈0.47/perc≈0.30、他の旋律楽器は perc がずっと低い(piano0.03/
# violin0.02/guitar0.11)。声は子音/息で打楽器成分が中程度に乗るため flux と perc の
# AND で分離する(2026-07-21 実データ較正)。
_VOCAL_FLUX_MIN = 0.42      # 重心の相対変動(音素遷移で揺れる)がこれ超で声候補
_VOCAL_PERC_MIN = 0.18      # 声は子音/息で打楽器成分が中程度に乗る(純持続音との分離)
_VOCAL_CENTROID_HZ = 3300.0  # 声の重心上限目安

_KEY_CENTROID_HI = 900.0    # これ未満の重心＋安定調波は鍵盤寄り(piano 実測≈565)
_KEY_ZCR_MAX = 0.10         # keyboard は撥弦アタックほど ZCR が高くない
_STRING_CENTROID_LO = 900.0  # 中域重心の調波優勢は撥弦/擦弦(guitar≈1162/violin≈1348)
_STRING_CENTROID_HI = 3300.0

_HARMONIC_DOMINANT = 0.50   # 調波エネルギー比がこれ以上で「調波優勢」

# 確信度の頭打ち(学習なし・単一区間の粗判定なので過信は害)
_CONF_CAP = 0.55            # 全ラベル共通の上限
_CONF_BASE = 0.30           # ヒットしたラベルの下限(unknown 以外)


@dataclass(frozen=True)
class InstrumentGuess:
    """classify_instrument の結果: 支配的な1楽器の粗い推測。

    label は {"vocal_like","guitar_string_like","bass_like","percussive",
    "keyboard_like","unknown"} のいずれか。学習を使わない閾値ヒューリスティックの
    ため confidence は低めに頭打ちする(最大 ~0.55)。features には丸め済みの
    生特徴(centroid/bandwidth/rolloff/zcr/perc_ratio/hp_ratio 等)を格納する。
    """

    label: str
    confidence: float          # 0-1: 粗判定の確からしさ(低めに頭打ち)
    features: dict[str, float]  # 丸め済みの生特徴(空 dict もあり得る)


def _to_mono(y: np.ndarray) -> np.ndarray:
    """ステレオ入力をモノラルへ畳む。(frames, ch)/(ch, frames)の両配置に対応
    (soundfileとlibrosaで軸配置が逆のため。field.py::_to_mono と同一方針)。"""
    if y.ndim <= 1:
        return y
    # チャンネル軸=要素数が少ない側(2ch程度)とみなす
    ch_axis = int(np.argmin(y.shape))
    return y.mean(axis=ch_axis)


def _guess(label: str, confidence: float, features: dict[str, float]) -> InstrumentGuess:
    """InstrumentGuess を生成する(confidence を 0-1 にクランプし丸める)。"""
    return InstrumentGuess(
        label=label,
        confidence=round(float(np.clip(confidence, 0.0, 1.0)), _ROUND_NDIGITS),
        features={k: round(float(v), _ROUND_NDIGITS) for k, v in features.items()},
    )


def classify_instrument(y: np.ndarray, sr: int) -> InstrumentGuess:
    """1区間の波形から支配的な1楽器を粗く推測する(F-015・学習なし)。

    判定順(疑わしきは unknown に倒す):
      1. 無音/極小/非有限 → "unknown"(confidence 0.0)
      2. 打楽器比が高く ZCR も高め、かつ広帯域雑音でない → "percussive"
      3. 重心が低く rolloff も低め・調波優勢 → "bass_like"
      4. 重心変動(flux)が大きく中低域・調波優勢 → "vocal_like"
      5. 中域重心・撥弦アタック(高め ZCR)・調波優勢 → "guitar_string_like"
      6. 中域重心・安定調波(低め ZCR)・調波優勢 → "keyboard_like"
      7. どれにも当てはまらない → "unknown"

    confidence は最大 ~0.55 に頭打ちする(学習なし・単一区間・閾値ヒューリスティック
    なので過信は害)。features には丸め済みの生特徴を格納する。

    限界(正直な記録):
    - 「支配的な1楽器の粗い推測」であり多楽器の同時分類ではない。
    - centroid/ZCR の絶対閾値は脆く、境界帯は "unknown"+低 confidence に倒す。
    - 白色雑音/拍手は HPSS で均等分配され perc_ratio で捕まらないため "unknown"。
    """
    y = _to_mono(np.asarray(y, dtype=np.float64))
    # 境界検証: 破損WAV等由来の非有限値で librosa が即死しないよう無音化する
    if not np.all(np.isfinite(y)):
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    if len(y) < _MIN_LEN or float(np.max(np.abs(y))) < _SILENCE_ABS:
        return _guess("unknown", 0.0, {})

    n_fft = 2048 if len(y) >= 2048 else 512
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=n_fft // 4))
    if S.size == 0:
        return _guess("unknown", 0.0, {})

    # --- スペクトル特徴(各フレーム平均。centroid は有限値でフィルタ) -----------
    centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
    centroid = centroid[np.isfinite(centroid)]
    mean_centroid = float(np.mean(centroid)) if centroid.size else 0.0
    # 重心の相対変動(声は音素遷移で重心が揺れる)。定常音は小さい
    centroid_flux = (
        float(np.std(centroid) / (mean_centroid + 1e-9)) if centroid.size else 0.0
    )

    bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=sr)[0]
    bandwidth = bandwidth[np.isfinite(bandwidth)]
    mean_bandwidth = float(np.mean(bandwidth)) if bandwidth.size else 0.0

    rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr, roll_percent=0.85)[0]
    rolloff = rolloff[np.isfinite(rolloff)]
    mean_rolloff = float(np.mean(rolloff)) if rolloff.size else 0.0

    zcr = librosa.feature.zero_crossing_rate(y)[0]
    mean_zcr = float(np.mean(zcr)) if zcr.size else 0.0

    # --- HPSS 打楽器性 ---------------------------------------------------------
    H, P = librosa.decompose.hpss(S)
    h_e = float(np.sum(H**2))
    p_e = float(np.sum(P**2))
    denom = h_e + p_e + 1e-18
    perc_ratio = p_e / denom
    hp_ratio = h_e / denom  # 調波エネルギー比(調波優勢の指標)

    features: dict[str, float] = {
        "centroid": mean_centroid,
        "bandwidth": mean_bandwidth,
        "rolloff": mean_rolloff,
        "zcr": mean_zcr,
        "centroid_flux": centroid_flux,
        "perc_ratio": perc_ratio,
        "hp_ratio": hp_ratio,
    }

    harmonic_dominant = hp_ratio >= _HARMONIC_DOMINANT

    # 2) 打楽器: HPSS 打楽器比が高く ZCR も高め。ただし広帯域雑音(perc_ratio が
    #    中間帯≈0.4-0.6)は HPSS が均等分配した結果でありうるので unknown に倒す。
    if perc_ratio > _PERC_RATIO_HIGH and mean_zcr >= _PERC_ZCR_MIN:
        conf = _CONF_BASE + (perc_ratio - _PERC_RATIO_HIGH)
        return _guess("percussive", min(_CONF_CAP, conf), features)

    # 3) 低音楽器: 重心が低く rolloff も低め・調波優勢(bass guitar は低 centroid)。
    if (
        harmonic_dominant
        and 0.0 < mean_centroid < _BASS_CENTROID_HZ
        and 0.0 < mean_rolloff < _BASS_ROLLOFF_HZ
    ):
        conf = _CONF_BASE + (_BASS_CENTROID_HZ - mean_centroid) / _BASS_CENTROID_HZ * 0.2
        return _guess("bass_like", min(_CONF_CAP, conf), features)

    # 4) 声: 重心変動(flux)が大きく、かつ子音/息由来の打楽器成分が中程度に乗る。
    #    flux 単独だと純持続音(piano/violin)まで拾う catch-all になるため perc と AND。
    if (
        harmonic_dominant
        and centroid_flux >= _VOCAL_FLUX_MIN
        and perc_ratio >= _VOCAL_PERC_MIN
        and 0.0 < mean_centroid <= _VOCAL_CENTROID_HZ
    ):
        conf = _CONF_BASE + min(0.2, centroid_flux - _VOCAL_FLUX_MIN)
        return _guess("vocal_like", min(_CONF_CAP, conf), features)

    # 5) 鍵盤: 重心が低め・安定調波・撥弦ほど高くない ZCR(piano 実測 centroid≈565)。
    if (
        harmonic_dominant
        and 0.0 < mean_centroid < _KEY_CENTROID_HI
        and mean_zcr < _KEY_ZCR_MAX
    ):
        conf = _CONF_BASE + min(0.2, hp_ratio - _HARMONIC_DOMINANT)
        return _guess("keyboard_like", min(_CONF_CAP, conf), features)

    # 6) 撥弦/擦弦(ギター・弦): 中域重心・調波優勢(guitar≈1162/violin≈1348)。
    #    ギターと弦(バイオリン)は単一区間の粗特徴では分離困難なので同一ラベルに束ねる。
    if (
        harmonic_dominant
        and _STRING_CENTROID_LO <= mean_centroid <= _STRING_CENTROID_HI
    ):
        conf = _CONF_BASE + min(0.2, hp_ratio - _HARMONIC_DOMINANT)
        return _guess("guitar_string_like", min(_CONF_CAP, conf), features)

    # 7) どれにも強く当てはまらない → unknown(境界帯は正直に低 confidence)
    return _guess("unknown", 0.2, features)
