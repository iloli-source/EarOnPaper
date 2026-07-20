"""耳層: 入力音源に応じた mono/poly エンジンの自動選択(Issue #64)。

背景: mono(pYIN)は単旋律専用で、伴奏を含む混合音源ではほぼ何も拾えない
(実測 Bon Jovi mono=1音)。逆に poly(basic-pitch)は純単旋律だとオクターブ
倍音を誤検出して2音化する(かえるのうた問題)。どちらも既定にすると片方の
音源で静かに失敗するため、音源のポリフォニーを推定して切り替える。

判定は2信号の OR:
  (1) ポリフォニー推定 >= POLY_MIN … 同時に鳴る独立基音の中央値
  (2) mono被覆率 < MIN_MONO_COVERAGE … monoが音源をほとんど説明できない
      (混合音源でポリフォニー推定が低く出た場合の安全網)
poly が実行不能(basic-pitch未導入)な環境では正直に mono へフォールバックし、
その旨を戻り値に残す(黙って劣化させない)。

実測較正(2026-07-21): かえるのうた=1.0 / むすんでひらいて=3.0 /
Bon Jovi混合=23.0 / K-POP混合=15.0。単旋律(≤3)と混合(≥15)は大きく分離。
"""

from dataclasses import dataclass

import librosa
import numpy as np

from earpipe.contracts import PitchEvent

# 同時発音の独立基音がこの中央値以上なら多声と判定
POLY_MIN = 5.0
# エネルギーのあるフレームだけを対象にする分位点
_ENERGY_PERCENTILE = 60.0
# ピーク採用の相対しきい(最大ピークから-18dB)
_REL_DB = 18.0
# 倍音抑制の許容(f/f0 が整数±この割合なら倍音とみなし独立基音に数えない)
_HARM_TOL = 0.03
_N_FFT = 4096
_HOP = 2048
# monoが音源をこれ未満しか説明できなければ、単旋律でなく取りこぼしと見て poly へ
MIN_MONO_COVERAGE = 0.15
# 被覆率の分母(有音とみなす)エネルギー分位点
_VOICED_PERCENTILE = 70.0
# スペクトル平坦度がこれ超なら非調波(ノイズ性)と見なし、poly昇格を止めて mono に固定する。
# ノイズは広帯域でピークが乱立し多声と誤判定されやすいが、音符化してはいけない
# (絶対音感エミュレータの正直原則: ノイズ→音符ゼロ)。実測: 白色ノイズ=0.57 /
# 実曲=0.01〜0.06 / 純音・和音=0.00 と大きく分離するため 0.30 で安全に切れる。
NOISE_FLATNESS_MAX = 0.30


def estimate_polyphony(
    y: np.ndarray,
    sr: int,
    n_fft: int = _N_FFT,
    hop: int = _HOP,
    rel_db: float = _REL_DB,
    harm_tol: float = _HARM_TOL,
) -> float:
    """音源の同時発音数(独立基音)の中央値を推定する。

    各フレームのスペクトルからピークを取り、低い基音の整数倍(倍音)を除いた
    残りを「独立に鳴っている音」と数える。単旋律なら基音+倍音で ~1、
    伴奏込みの混合音源なら複数の基音が立ち >=数 になる。
    """
    y = np.asarray(y, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) < n_fft or float(np.max(np.abs(y))) < 1e-6:
        return 0.0

    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = (freqs >= 65.0) & (freqs <= 2100.0)  # C2〜およそC7の音楽帯域
    fb = freqs[band]
    Sb = S[band, :]

    frame_energy = Sb.sum(axis=0)
    thr = float(np.percentile(frame_energy, _ENERGY_PERCENTILE))

    counts: list[int] = []
    for j in range(Sb.shape[1]):
        if frame_energy[j] < thr:
            continue
        col = Sb[:, j]
        cmax = float(col.max())
        if cmax <= 0.0:
            continue
        floor = cmax * (10.0 ** (-rel_db / 20.0))
        # 局所極大かつ floor 以上をピークとする
        peaks = [
            k for k in range(1, len(col) - 1)
            if col[k] >= floor and col[k] > col[k - 1] and col[k] >= col[k + 1]
        ]
        if not peaks:
            continue
        fpk = sorted(float(fb[k]) for k in peaks)
        fundamentals: list[float] = []
        for f in fpk:
            is_harmonic = any(
                round(f / f0) >= 2 and abs((f / f0) - round(f / f0)) < harm_tol
                for f0 in fundamentals
            )
            if not is_harmonic:
                fundamentals.append(f)
        counts.append(len(fundamentals))

    if not counts:
        return 0.0
    return float(np.median(counts))


def _median_flatness(y: np.ndarray, sr: int) -> float:
    """有音フレームのスペクトル平坦度の中央値(0-1)。1に近いほどノイズ的。"""
    y = np.asarray(y, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) < _N_FFT or float(np.max(np.abs(y))) < 1e-6:
        return 0.0
    S = np.abs(librosa.stft(y, n_fft=_N_FFT, hop_length=_HOP))
    flatness = librosa.feature.spectral_flatness(S=S)[0]
    energy = S.sum(axis=0)
    thr = float(np.percentile(energy, _ENERGY_PERCENTILE))
    mask = energy >= thr
    vals = flatness[mask] if mask.any() else flatness
    return float(np.median(vals))


def _mono_coverage(y: np.ndarray, sr: int, mono_events: list[PitchEvent]) -> float:
    """monoが検出した音符が、有音区間の何割を覆っているか(0-1)。"""
    y = np.asarray(y, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) < _N_FFT:
        return 1.0
    rms = librosa.feature.rms(y=y, frame_length=_N_FFT, hop_length=_HOP)[0]
    times = librosa.times_like(rms, sr=sr, hop_length=_HOP)
    thr = float(np.percentile(rms, _VOICED_PERCENTILE))
    voiced = rms >= thr
    voiced_dur = float(np.sum(voiced)) * (_HOP / sr)
    if voiced_dur <= 0.0:
        return 1.0
    note_dur = sum(max(0.0, e.offset - e.onset) for e in mono_events)
    return min(1.0, note_dur / voiced_dur)


@dataclass(frozen=True)
class EngineChoice:
    """自動選択の結果と根拠(戻り値・診断用)。"""

    engine: str            # "mono" | "poly"
    requested: str         # 呼び出し時の指定("auto")
    polyphony: float       # 推定ポリフォニー
    mono_coverage: float   # monoの被覆率(算出した場合。未算出は-1.0)
    poly_available: bool   # basic-pitchが使える環境か
    reason: str            # 選択理由(人間可読)
    fell_back: bool        # polyを選びたかったがmonoに退避したか


def choose_engine(
    y: np.ndarray,
    sr: int,
    mono_events: list[PitchEvent] | None,
    poly_available: bool,
) -> EngineChoice:
    """音源特性から mono/poly を選ぶ。poly不能なら正直に mono へ退避する。

    mono_events: 先に mono 検出済みなら渡す(被覆率の安全網に使う)。None可。
    """
    # 非調波ゲート: ノイズは広帯域でピークが乱立し多声と誤判定されるが、音符化しては
    # いけない。平坦度が高い(ノイズ性)なら poly 昇格を止め mono に固定する
    # (mono はノイズに音符ゼロを返す。研究裏づけ: 単音特化器は非調波入力で沈黙的)。
    flatness = _median_flatness(y, sr)
    if flatness > NOISE_FLATNESS_MAX:
        return EngineChoice(
            engine="mono", requested="auto", polyphony=0.0,
            mono_coverage=-1.0, poly_available=poly_available,
            reason=f"非調波(ノイズ性)と判定(flatness={flatness:.2f})→ mono に固定",
            fell_back=False,
        )

    poly = estimate_polyphony(y, sr)
    coverage = -1.0
    want_poly = poly >= POLY_MIN
    if not want_poly and mono_events is not None:
        coverage = _mono_coverage(y, sr, mono_events)
        # 有音なのに mono がほとんど拾えていない = 取りこぼし → poly へ
        if coverage < MIN_MONO_COVERAGE:
            want_poly = True

    if not want_poly:
        return EngineChoice(
            engine="mono", requested="auto", polyphony=round(poly, 2),
            mono_coverage=round(coverage, 3), poly_available=poly_available,
            reason=f"単旋律と判定(polyphony={poly:.1f} < {POLY_MIN})", fell_back=False,
        )
    if not poly_available:
        return EngineChoice(
            engine="mono", requested="auto", polyphony=round(poly, 2),
            mono_coverage=round(coverage, 3), poly_available=False,
            reason=(
                f"多声と判定(polyphony={poly:.1f})だが basic-pitch 未導入のため"
                "mono へ退避。EARPIPE_BP_PYTHON を設定すると poly を使用"
            ),
            fell_back=True,
        )
    return EngineChoice(
        engine="poly", requested="auto", polyphony=round(poly, 2),
        mono_coverage=round(coverage, 3), poly_available=True,
        reason=f"多声と判定(polyphony={poly:.1f} >= {POLY_MIN})", fell_back=False,
    )
