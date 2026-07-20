"""プレビュー音声の生成: MIDI → WAV/MP3 のソニフィケーション(F-054・Issue #69)。

パイプライン: pretty_midi でMIDIを読み込み音声合成 → soundfile でWAV書き出し
             → (out_pathが.mp3かつffmpeg有) ffmpeg でMP3化。
合成は Fluidsynth を優先し、未導入/失敗時は pretty_midi 内蔵のサイン波合成
(PrettyMIDI.synthesize)へフォールバックする(依存追加不要・CI/テスト経路)。
MP3化に失敗する環境では .wav へフォールバックして書けたファイルのパスを返す。
完全ローカル処理(外部送信なし)。engrave.py に倣い重依存は関数内 lazy import。
"""

import shutil
import subprocess
from pathlib import Path

import numpy as np

# 既定サンプルレート(要件のプレビュー品質。合成と書き出しで必ず一致させる)。
DEFAULT_SR = 22050
# 空/無音MIDIでも0バイトWAVを書かないための最低サンプル数(無音パディング)。
_MIN_SAMPLES = 1


def _synthesize(midi_path: Path, sr: int) -> "np.ndarray":
    """MIDIを音声波形(float32 モノラル)へ合成する。

    Fluidsynth を優先し、pyfluidsynth 未導入やバイナリ欠如で失敗した場合は
    pretty_midi 内蔵のサイン波合成へフォールバックする。いずれの経路でも
    最低1サンプルを確保し、振幅を[-1, 1]へ正規化して返す(soundfileのクリップ防御)。

    Args:
        midi_path: 読み込むMIDIファイルのパス。
        sr: 合成サンプルレート(Hz)。

    Returns:
        float32 の1次元波形配列(最低長 _MIN_SAMPLES、振幅 |x| <= 1)。
    """
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(str(midi_path))

    audio: "np.ndarray"
    try:
        # pyfluidsynth 未導入時は ImportError を送出するため広めに握る。
        audio = pm.fluidsynth(fs=sr)
        if audio is None or len(audio) == 0:
            raise RuntimeError("fluidsynthが空の波形を返した")
    except Exception:
        # フォールバック: 内蔵サイン波合成(Fluidsynth不要)。
        audio = pm.synthesize(fs=sr)

    audio = np.asarray(audio, dtype=np.float32)

    # 空/無音MIDIは shape(0,) を返しうる。0バイトWAVを避けるため無音でパディング。
    if audio.size < _MIN_SAMPLES:
        audio = np.zeros(_MIN_SAMPLES, dtype=np.float32)

    # 範囲外はsoundfileがクリップするため、書き出し前に正規化する(二重防御)。
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        audio = audio / peak

    return audio


def _write_wav(audio: "np.ndarray", wav_path: Path, sr: int) -> Path:
    """波形をWAV(PCM_16既定)として書き出し、そのパスを返す。"""
    import soundfile as sf

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(wav_path), audio, sr)
    return wav_path


def _to_mp3(wav_path: Path, mp3_path: Path) -> bool:
    """ffmpeg で WAV→MP3 変換を試みる。成功可否を返す(捏造の成功を返さない)。"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return False
    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav_path), str(mp3_path)],
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0 and mp3_path.exists() and mp3_path.stat().st_size > 0


def render_preview(
    midi_path: str | Path,
    out_path: str | Path,
    sr: int = DEFAULT_SR,
) -> Path:
    """MIDIからプレビュー音声(WAV/MP3)を生成し、書けたファイルのパスを返す。

    合成は Fluidsynth を優先し、未導入/失敗時は内蔵サイン波合成へフォールバックする。
    out_path の拡張子が .mp3 かつ ffmpeg が利用可能なら MP3 化して返す。ffmpeg が
    無い/変換に失敗した場合は .wav 拡張子へ差し替えたパスへ WAV を書き、そのパスを返す。
    .wav 指定時は直接 WAV を書き出す。

    Args:
        midi_path: 入力MIDIファイル(str/Path)。
        out_path: 出力先(str/Path)。拡張子で .wav / .mp3 を分岐する。
        sr: サンプルレート(Hz)。合成と書き出しで一致させる。既定 DEFAULT_SR。

    Returns:
        実際に書き出せた音声ファイルの Path(常にファイルが存在する)。
    """
    midi_path = Path(midi_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    audio = _synthesize(midi_path, sr)

    # .mp3 経路: 一旦一時WAVへ書き、ffmpegでMP3化。失敗時はWAVへフォールバック。
    if out_path.suffix.lower() == ".mp3":
        tmp_wav = out_path.with_suffix(".wav")
        _write_wav(audio, tmp_wav, sr)
        try:
            if _to_mp3(tmp_wav, out_path):
                # MP3成功時のみ中間WAVを削除。
                try:
                    tmp_wav.unlink()
                except OSError:
                    pass
                return out_path
        finally:
            pass
        # ffmpeg無し/変換失敗: WAVフォールバック(中間WAVを残してそのパスを返す)。
        return tmp_wav

    # .wav もしくはその他拡張子: WAVとして直接書き出す。
    wav_path = out_path if out_path.suffix.lower() == ".wav" else out_path.with_suffix(".wav")
    return _write_wav(audio, wav_path, sr)
