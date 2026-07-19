"""基準ピッチ補正: A=440基準からのチューニングずれ(cents)を推定し補正する(C1・#55)。

背景: 演奏・録音は必ずしもA=440ではない(古楽A=415、生録音のわずかな狂い、
再生機材のピッチずれ等)。半音格子への量子化は「A=440前提」なので、全体が
一律に±数十centsずれていると、音高が隣の半音へ丸め込まれ音程を取り違える。
この層で「全体が何centsずれているか」を推定し、リサンプリングで格子に戻す。

推定手法(スペクトルピーク法): librosa.estimate_tuning は音声のスペクトルピークを
半音格子に照合し、格子中心からの偏差の最頻値をチューニングずれとして返す。
本モジュールはこれを A=440基準の cents(±50cents範囲)に換算して返す。
n_fft を大きめに取り周波数分解能を上げることで、合成デチューン音源で
推定誤差±5cents以内を確認済み(test_tuning.py)。

補正はリサンプリング(rate = 2^(cents/1200))で行う。微小なずれ(閾値未満)は
補正しない — 不要なリサンプリングによる音質劣化を避けるため(絶対音感エミュレータは
入力を極力そのまま扱う原則)。
"""

import os
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

# 推定範囲: A=440基準で ±50cents(半音の半分)。これを超えるずれは
# 「別の半音」として扱うべきで、チューニングずれとは区別する。
MAX_OFFSET_CENTS = 50.0

# 補正発動閾値: |offset| がこれ未満なら無補正(リサンプリング劣化回避)。
# 8cents未満のずれは半音格子への丸めに影響しない実用上無害な範囲。
CORRECTION_THRESHOLD_CENTS = 8.0

# 推定用FFTサイズ。既定の2048より大きく取り周波数分解能を上げる
# (合成音源で worst-case 誤差 4.8→0.8cents に改善することを確認・#55)。
_ESTIMATE_N_FFT = 8192
_ESTIMATE_RESOLUTION = 0.002  # 半音の何分の1刻みでピークを探すか(≈0.24cents)


def estimate_tuning_offset_cents(audio: np.ndarray, sr: int) -> float:
    """音声から A=440基準のチューニングずれ(cents)を推定する。

    戻り値は ±MAX_OFFSET_CENTS にクランプした float。正なら全体が高め(シャープ)、
    負なら低め(フラット)。無音・極小振幅では推定不能なため 0.0 を返す。

    限界(正直な記録): ±50centsを超える系統的ずれは、隣の半音格子として
    観測されるため本手法では検出できない(クランプされる)。これは仕様上の
    設計判断であり、±50cents超は「移調」であってチューニングずれではない。
    """
    y = np.asarray(audio, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if len(y) < _ESTIMATE_N_FFT or float(np.max(np.abs(y))) < 1e-6:
        return 0.0

    # estimate_tuning は「半音の何分の1ずれているか」を返す(範囲[-0.5, 0.5))。
    # cents に換算(×100)する。
    tuning_fraction = librosa.estimate_tuning(
        y=y, sr=sr, resolution=_ESTIMATE_RESOLUTION, n_fft=_ESTIMATE_N_FFT,
    )
    cents = float(tuning_fraction) * 100.0
    return float(np.clip(cents, -MAX_OFFSET_CENTS, MAX_OFFSET_CENTS))


def apply_tuning_correction(audio: np.ndarray, sr: int, cents: float) -> np.ndarray:
    """チューニングずれ cents を打ち消すようリサンプリングで補正した音声を返す。

    |cents| が CORRECTION_THRESHOLD_CENTS 未満なら無補正で入力をそのまま返す
    (float64正規化のみ・不要な音質劣化を避ける)。

    補正は再生レートを rate=2^(cents/1200) 倍することに相当する。全体が
    +cents 高いなら、それだけ下げる(rate<1相当のリサンプリング)ことで格子に戻す。
    """
    y = np.asarray(audio, dtype=np.float64)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if abs(cents) < CORRECTION_THRESHOLD_CENTS or len(y) == 0:
        return y

    # +cents 高い音を格子(A=440)に戻すには周波数を 2^(-cents/1200) 倍する。
    # librosa.resample(orig_sr, target_sr) は元を target/orig 倍の長さに変える。
    # 周波数を factor 倍したい ⇔ サンプルを factor で読み替える ⇔
    # orig_sr=sr, target_sr=sr/factor でリサンプル後、元srで再生すると周波数がfactor倍。
    factor = 2.0 ** (-cents / 1200.0)
    corrected = librosa.resample(
        y, orig_sr=sr, target_sr=int(round(sr / factor)),
    )
    return corrected


def correct_tuning_file(path: str | Path) -> tuple[Path, float]:
    """wavパスを受け取り、チューニング補正の要否を判定して結果を返す(pipeline統合用)。

    戻り値 (out_path, offset_cents):
      - offset_cents: 推定したチューニングずれ(A=440基準・cents)
      - out_path: |offset_cents| >= CORRECTION_THRESHOLD_CENTS なら補正済み音声を
        書き出した一時wavのPath。閾値未満なら補正不要のため入力 path をそのまま返す。

    一時ファイルは tempfile で作成する(呼び出し側が不要になったら削除する責務を持つ)。
    補正が発動しなかった場合は一時ファイルを作らない(入力pathを返すのみ)。
    """
    src = Path(path)
    # librosa.load はwav以外(mp3等)も既存パイプラインと同じ経路で読める
    y, sr = librosa.load(str(src), sr=None, mono=True)
    offset = estimate_tuning_offset_cents(y, int(sr))
    if abs(offset) < CORRECTION_THRESHOLD_CENTS:
        return src, offset

    corrected = apply_tuning_correction(y, sr, offset)
    # mkstempでOS衝突のない一意名を確保。fdは即閉じ、書き込みはsoundfileに委ねる。
    fd, tmp_name = tempfile.mkstemp(suffix="_tuned.wav", prefix="earpipe_")
    os.close(fd)
    out_path = Path(tmp_name)
    sf.write(str(out_path), corrected, sr)
    return out_path, offset
