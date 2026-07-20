"""打楽器の粗い推測(F-018 / Issue #84): 波形から打点とキット種別を推定する。

学習は一切使わない。オンセット検出(librosa)で打点を拾い、各打点直後の
短い解析窓のスペクトル帯域エネルギー分布から kit を粗く分類する
軽量ヒューリスティックである。確信度は正直に低めに頭打ちする。

分類の直観(粗判定・すべて「目安」):
  - kick    : 低域(≲150Hz)にエネルギーが集中する持続的な低音。
  - snare   : 低〜中域の胴鳴りに加え広帯域ノイズ(スナッピー)が乗る。
              スペクトルが平坦(白色寄り)で ZCR も高い。
  - hihat   : 高域(≳6kHz)偏重の短いノイズ。重心が非常に高く ZCR も高い。
  - tom     : 中低域(≈100-400Hz)に明確なピッチ感を持つ胴鳴り。
  - cymbal  : 高域偏重だが hihat より裾が広く長く尾を引く広帯域金属音。
  - unknown : どれにも強く当てはまらない(境界は正直に unknown へ倒す)。

重要な限界(文献一致・正直な記録。notes にも反映):
- ドメインギャップ: 帯域エネルギー閾値は音源(ドラムキット/収録/ミックス)ごとに
  大きく動く。ここでの閾値は合成・一般的な生ドラムを想定した「目安」であり、
  電子ドラム/加工音では簡単に外れる。過信しないため confidence を低く頭打ちする。
- 同時打音(kick+snare, hihat重ね等)は単一打点として1ラベルに束ねられ、
  帯域が混ざるため分離不能(単純特徴の原理的限界)。混合時は最も支配的な帯域へ
  倒れ、確信度は下がる。多層のドラム分解は本ヒューリスティックの範囲外。
- snare と cymbal/hihat はいずれも広帯域ノイズ性が高く、重心と低域エネルギーの
  相対量でしか切り分けられない。境界帯は unknown へ倒す。
- オンセット検出は速いロール/ゴーストノートを取りこぼす/過検出しうる。
"""

from dataclasses import dataclass

import librosa
import numpy as np

# --- 解析パラメータ ----------------------------------------------------------
_MIN_LEN = 512             # これ未満のサンプル数は解析対象外(打点なし)
_SILENCE_ABS = 1e-6        # 最大振幅がこれ未満なら無音扱い(打点なし)
_ROUND_NDIGITS = 4         # onset_sec / confidence の丸め桁
_WIN_SEC = 0.06            # 各打点から切り出す解析窓の長さ(秒)。打撃の立ち上がりを見る
_N_FFT = 1024              # 解析窓のFFT長(窓が短いので小さめ)

# --- 帯域境界(Hz。すべて「目安」・境界帯は unknown に倒す) ------------------
_KICK_HI_HZ = 150.0        # これ未満を低域(kick 帯)とみなす
_TOM_LO_HZ = 100.0         # tom 胴鳴りの下限
_TOM_HI_HZ = 400.0         # tom 胴鳴りの上限
_HIHAT_LO_HZ = 6000.0      # これ超を高域(hihat/cymbal 帯)とみなす

# --- 判定閾値(比率。実測でなく合成・一般ドラム想定の目安) --------------------
_LOW_DOMINANT = 0.55       # 低域比率がこれ以上なら低音打撃(kick)寄り
_HIGH_DOMINANT = 0.45      # 高域比率がこれ以上なら金属高域(hihat/cymbal)寄り
_TOM_BAND_MIN = 0.40       # tom 帯比率がこれ以上で胴鳴り優勢
_FLATNESS_NOISY = 0.30     # スペクトル平坦度がこれ以上で広帯域ノイズ性(snare/cymbal)
_ZCR_HIGH = 0.15           # ZCR がこれ以上で高域ノイズ性(hihat/snare)
_HIHAT_CENTROID_HZ = 7000.0  # 重心がこれ以上なら hihat 寄り(cymbal はやや低く裾広)

# --- 確信度(学習なし・粗判定なので過信は害。低めに頭打ち) --------------------
_CONF_CAP = 0.50           # 全キット共通の上限
_CONF_BASE = 0.25          # ヒットしたキットの下限(unknown 以外)
_CONF_UNKNOWN = 0.20       # 打点はあるが分類できない場合の確信度


@dataclass(frozen=True)
class _Bands:
    """1打点の解析窓から抽出した帯域・スペクトル特徴(内部専用・丸め前)。"""

    low_ratio: float       # <_KICK_HI_HZ のエネルギー比
    tom_ratio: float       # _TOM_LO_HZ.._TOM_HI_HZ のエネルギー比
    high_ratio: float      # >_HIHAT_LO_HZ のエネルギー比
    centroid: float        # スペクトル重心(Hz)
    flatness: float        # スペクトル平坦度(0-1。1に近いほど白色/ノイズ様)
    zcr: float             # ゼロ交差率(高いほど高域ノイズ性)


def _to_mono(y: np.ndarray) -> np.ndarray:
    """ステレオ入力をモノラルへ畳む((frames, ch)/(ch, frames)両配置に対応)。

    soundfile と librosa で軸配置が逆のため、要素数が少ない側をチャンネル軸とみなす
    (instrument_classify._to_mono と同一方針)。
    """
    if y.ndim <= 1:
        return y
    ch_axis = int(np.argmin(y.shape))
    return y.mean(axis=ch_axis)


def _sanitize(y: np.ndarray) -> np.ndarray:
    """非有限値(NaN/Inf)を 0 に潰し、float64 モノラル配列へ整える。

    破損WAV等の非有限値で librosa が即死しないための境界ガード。
    """
    y = _to_mono(np.asarray(y, dtype=np.float64))
    if not np.all(np.isfinite(y)):
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    return y


def _band_features(seg: np.ndarray, sr: int) -> _Bands:
    """1打点の解析窓 seg から帯域エネルギー比・重心・平坦度・ZCR を求める。"""
    n_fft = _N_FFT if len(seg) >= _N_FFT else max(64, 1 << (len(seg).bit_length() - 1))
    # 窓長より hop を小さくして最低1フレームは確保する
    S = np.abs(librosa.stft(seg, n_fft=n_fft, hop_length=max(1, n_fft // 4)))
    power = np.sum(S**2, axis=1)  # 周波数ビンごとの総パワー(時間方向に合算)
    total = float(np.sum(power)) + 1e-18
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    low = float(np.sum(power[freqs < _KICK_HI_HZ])) / total
    tom = float(np.sum(power[(freqs >= _TOM_LO_HZ) & (freqs < _TOM_HI_HZ)])) / total
    high = float(np.sum(power[freqs > _HIHAT_LO_HZ])) / total

    centroid_frames = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
    centroid_frames = centroid_frames[np.isfinite(centroid_frames)]
    centroid = float(np.mean(centroid_frames)) if centroid_frames.size else 0.0

    flatness_frames = librosa.feature.spectral_flatness(S=S)[0]
    flatness_frames = flatness_frames[np.isfinite(flatness_frames)]
    flatness = float(np.mean(flatness_frames)) if flatness_frames.size else 0.0

    zcr_frames = librosa.feature.zero_crossing_rate(seg)[0]
    zcr = float(np.mean(zcr_frames)) if zcr_frames.size else 0.0

    return _Bands(
        low_ratio=low,
        tom_ratio=tom,
        high_ratio=high,
        centroid=centroid,
        flatness=flatness,
        zcr=zcr,
    )


def _classify_kit(b: _Bands) -> tuple[str, float]:
    """帯域特徴から kit ラベルと確信度(0-1)を返す(疑わしきは unknown)。

    判定順(排他ではなく優先順。境界帯は下位の広帯域/unknown へ流れる):
      1. 高域偏重ノイズ + 高 ZCR → hihat(重心が極めて高い) / cymbal(裾が広い)
      2. 低域集中 → kick
      3. 広帯域ノイズ性 + 中低域の胴鳴り → snare
      4. 中低域(tom 帯)優勢のピッチ感 → tom
      5. どれにも当てはまらない → unknown
    """
    # 1) 高域偏重: hihat / cymbal。重心の高さで hihat と cymbal を粗く分ける。
    if b.high_ratio >= _HIGH_DOMINANT and b.zcr >= _ZCR_HIGH:
        if b.centroid >= _HIHAT_CENTROID_HZ:
            conf = _CONF_BASE + min(0.2, b.high_ratio - _HIGH_DOMINANT)
            return "hihat", min(_CONF_CAP, conf)
        conf = _CONF_BASE + min(0.15, b.high_ratio - _HIGH_DOMINANT)
        return "cymbal", min(_CONF_CAP, conf)

    # 2) 低域集中: kick(低域比率が支配的)。
    if b.low_ratio >= _LOW_DOMINANT:
        conf = _CONF_BASE + min(0.2, b.low_ratio - _LOW_DOMINANT)
        return "kick", min(_CONF_CAP, conf)

    # 3) snare: 広帯域ノイズ性(平坦度高)かつ高域一辺倒ではない(胴鳴りが残る)。
    if b.flatness >= _FLATNESS_NOISY and b.zcr >= _ZCR_HIGH:
        conf = _CONF_BASE + min(0.15, b.flatness - _FLATNESS_NOISY)
        return "snare", min(_CONF_CAP, conf)

    # 4) tom: 中低域帯にエネルギーが集まりピッチ感がある(平坦度は低め)。
    if b.tom_ratio >= _TOM_BAND_MIN and b.flatness < _FLATNESS_NOISY:
        conf = _CONF_BASE + min(0.15, b.tom_ratio - _TOM_BAND_MIN)
        return "tom", min(_CONF_CAP, conf)

    # 5) どれにも強く当てはまらない → unknown(境界帯は正直に低 confidence)
    return "unknown", _CONF_UNKNOWN


def detect_drums(y: np.ndarray, sr: int) -> list[dict]:
    """波形から打楽器の打点と kit 種別を粗く推定する(F-018・学習なし)。

    処理:
      1. モノラル化・非有限値ガード。無音/極小/極短は空リストを返す。
      2. librosa.onset.onset_detect で打点(秒)を検出する。
      3. 各打点から _WIN_SEC 秒の窓を切り出し、帯域エネルギー分布・重心・平坦度・
         ZCR から kit を粗く分類する。

    Args:
        y: 波形(モノラル or ステレオ)。float 配列。
        sr: サンプリング周波数(Hz)。

    Returns:
        打点ごとの dict のリスト(onset_sec 昇順)。各 dict は:
          - "onset_sec": float  打点の時刻(秒)
          - "kit": str          {"kick","snare","hihat","tom","cymbal","unknown"}
          - "confidence": float 0-1(学習なし粗判定のため ~0.50 に頭打ち)
        打点が無い/入力不正の場合は空リスト。

    限界(正直な記録):
    - 学習なしの帯域ヒューリスティックであり、キット/収録/ミックス差(ドメインギャップ)で
      閾値は容易に外れる。confidence を低く頭打ちして過信を避ける。
    - 同時打音(kick+snare 等)は1打点1ラベルに束ねられ分離不能。支配帯域へ倒れる。
    - snare/hihat/cymbal はいずれも広帯域ノイズ性が高く、重心と低域量でしか切れない。
      境界帯は unknown に倒す(「拾えないものは拾えないと正直に言う」)。
    """
    y = _sanitize(y)
    if len(y) < _MIN_LEN or float(np.max(np.abs(y))) < _SILENCE_ABS:
        return []

    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, backtrack=True, units="frames"
    )
    if len(onset_frames) == 0:
        return []
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    win = max(_MIN_LEN, int(_WIN_SEC * sr))
    results: list[dict] = []
    for onset_sec in onset_times:
        start = int(round(float(onset_sec) * sr))
        start = max(0, min(start, len(y) - 1))
        seg = y[start : start + win]
        if len(seg) < 64 or float(np.max(np.abs(seg))) < _SILENCE_ABS:
            # 末尾の極短窓や無音窓は分類できない → unknown で打点だけ残す
            kit, conf = "unknown", _CONF_UNKNOWN
        else:
            kit, conf = _classify_kit(_band_features(seg, sr))
        results.append(
            {
                "onset_sec": round(float(onset_sec), _ROUND_NDIGITS),
                "kit": kit,
                "confidence": round(float(np.clip(conf, 0.0, 1.0)), _ROUND_NDIGITS),
            }
        )

    return results
