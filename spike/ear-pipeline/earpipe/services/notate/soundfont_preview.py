"""任意サウンドフォント(SF2)での試聴音声レンダリング(F-097・Issue #104)。

採譜/記譜結果のMIDIを、ユーザーが選んだSF2音色でWAVへレンダリングする。
既存の render_preview(preview.py) が「GMデフォルト音源での即席プレビュー」なのに対し、
本モジュールは「任意SF2を明示指定した試聴(audition)」を担う。

設計方針(F-097-grok.md / F-097-codex.md の失敗例を反映):

- SF2は信頼できるGM音源ではなく **ユーザーデータ** として扱う(codex 4-1)。
  存在しない/読めないSF2は **サイレントに無音へ落とさず例外で拒否** する
  (codex 2-1 SF2ロード失敗 / grok 5.4「ロード失敗時の無音禁止」)。
- fluidsynth 経路では各インストゥルメントの (bank, program) を **明示 program_select** し、
  bank/program がサイレントに入れ替わる事故(codex 2-2/2-3/2-5)を避ける。
- サンプルレートを合成・書き出しで一致させ、レート不一致由来のピッチずれ
  (codex 2-8 out of tune)を避ける。
- ドラム(ch10 相当)は program change が無視される前提で、program_select を
  スキップしSF2側のドラムバンクに委ねる(codex 2-6)。
- pyfluidsynth もバイナリも無い環境(本CI含む・C依存のため導入禁止)では、
  **純Pythonフォールバック**として pretty_midi 内蔵のサイン波合成でWAVを生成する。
  この場合SF2音色は反映されない(サイン波)ため、フォールバックした事実を
  companion note(<out_wav>.note.txt)へ明記し、無言のなりすましを避ける
  (grok 失敗A「誤SFで壊れて聞こえる」/ 失敗M「音源で音が変わる」の混同防止)。

完全ローカル処理(外部送信なし)。重依存は関数内 lazy import。
"""

from pathlib import Path

import numpy as np

# 合成と書き出しで必ず一致させる既定サンプルレート(Hz)。
# レート不一致はピッチずれ(codex 2-8)を招くため単一の値に固定する。
DEFAULT_SR: int = 44100

# 空/無音MIDIでも0バイトWAVを書かないための最低サンプル数(無音パディング)。
_MIN_SAMPLES: int = 1

# フォールバック(サイン波合成)に落ちた事実を残すサイドカーの拡張子サフィックス。
_NOTE_SUFFIX: str = ".note.txt"


def fluidsynth_available() -> bool:
    """pyfluidsynth が import 可能か(=SF2音色レンダリングが可能か)を返す。

    実際の合成では fluidsynth ネイティブライブラリの有無にも依存するため、
    True でも合成が失敗しうる。合成失敗時はフォールバックへ落ちる設計にしてある
    ため、本関数は「試みる価値があるか」の粗い事前判定に留める。

    Returns:
        pyfluidsynth を import できれば True、できなければ False。
    """
    try:
        import fluidsynth  # noqa: F401
    except Exception:
        return False
    return True


def _validate_soundfont(soundfont_path: Path) -> None:
    """SF2パスを検証する。存在しない/ファイルでない場合は即例外(サイレント無音禁止)。

    Args:
        soundfont_path: 検証するSF2ファイルのパス。

    Raises:
        FileNotFoundError: パスが存在しない、または通常ファイルでない場合。
    """
    if not soundfont_path.exists():
        raise FileNotFoundError(f"サウンドフォントが見つかりません: {soundfont_path}")
    if not soundfont_path.is_file():
        raise FileNotFoundError(f"サウンドフォントがファイルではありません: {soundfont_path}")


def _synthesize_with_soundfont(
    midi_path: Path, soundfont_path: Path, sr: int
) -> "np.ndarray":
    """pretty_midi + fluidsynth + 指定SF2 でMIDIを合成する。

    各インストゥルメントの (bank, program) を明示して合成させることで、
    bank/program のサイレント入れ替え(codex 2-2/2-3)を避ける。pretty_midi の
    fluidsynth() は sf2_path 引数でSF2を明示できるため、これを用いる。

    Args:
        midi_path: 入力MIDIファイルのパス。
        soundfont_path: 使用するSF2ファイルのパス(検証済みを想定)。
        sr: 合成サンプルレート(Hz)。

    Returns:
        float32 の1次元波形配列。

    Raises:
        Exception: pyfluidsynth 未導入、ネイティブライブラリ欠如、SF2読込失敗など。
                   呼び出し側でフォールバック判定に使う。
    """
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(str(midi_path))
    # sf2_path を明示。空/無音MIDIは shape(0,) を返しうる。
    audio = pm.fluidsynth(fs=sr, sf2_path=str(soundfont_path))
    if audio is None or len(audio) == 0:
        # 無音MIDIの正当な空配列はここでは判別しづらいため、上位でパディングする。
        return np.zeros(_MIN_SAMPLES, dtype=np.float32)
    return np.asarray(audio, dtype=np.float32)


def _synthesize_fallback(midi_path: Path, sr: int) -> "np.ndarray":
    """純Pythonフォールバック: pretty_midi 内蔵のサイン波合成(SF2音色は非反映)。

    Args:
        midi_path: 入力MIDIファイルのパス。
        sr: 合成サンプルレート(Hz)。

    Returns:
        float32 の1次元波形配列(最低長 _MIN_SAMPLES)。
    """
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(str(midi_path))
    audio = pm.synthesize(fs=sr)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size < _MIN_SAMPLES:
        audio = np.zeros(_MIN_SAMPLES, dtype=np.float32)
    return audio


def _normalize(audio: "np.ndarray") -> "np.ndarray":
    """振幅を [-1, 1] へ正規化し、最低長を確保して float32 で返す(書き出し前の二重防御)。"""
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size < _MIN_SAMPLES:
        audio = np.zeros(_MIN_SAMPLES, dtype=np.float32)
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


def _write_fallback_note(out_wav: Path, soundfont_path: Path | None, reason: str) -> Path:
    """フォールバックした事実をサイドカー(.note.txt)へ記録し、そのパスを返す。

    無言でサイン波にすり替えると、採譜誤差と音色誤差が混同される(grok 失敗A/M)。
    ためにフォールバック事由を必ず外部に残す。

    Args:
        out_wav: 生成したWAVのパス。
        soundfont_path: 指定されていたSF2パス(未指定なら None)。
        reason: フォールバック事由(人間可読)。

    Returns:
        書き出したサイドカーの Path。
    """
    note_path = out_wav.with_name(out_wav.name + _NOTE_SUFFIX)
    sf_desc = str(soundfont_path) if soundfont_path is not None else "(未指定)"
    lines = [
        "SoundFont試聴フォールバック通知(F-097)",
        f"要求SF2: {sf_desc}",
        f"事由: {reason}",
        "結果: pretty_midi 内蔵サイン波合成でレンダリングしました。",
        "注意: この音声にSF2音色は反映されていません。採譜品質の判定にはSF2非依存の",
        "      情報として扱ってください(音色誤差と採譜誤差の混同を避けるため)。",
    ]
    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return note_path


def render_soundfont_preview(
    midi_path: str | Path,
    out_wav: str | Path,
    soundfont_path: str | Path | None = None,
    sr: int = DEFAULT_SR,
) -> Path:
    """MIDIを指定SF2音色で試聴用WAVへレンダリングし、書けたWAVのパスを返す。

    SF2があれば pyfluidsynth(fluidsynth)で当該音色を用いて合成する。SF2未指定、
    または pyfluidsynth 未導入/合成失敗時は、pretty_midi 内蔵のサイン波合成へ
    フォールバックし、その事実をサイドカー <out_wav>.note.txt へ明記する
    (無言のなりすまし禁止)。

    指定されたSF2が存在しない/ファイルでない場合は、サイレント無音を避けるため
    FileNotFoundError を送出する(SF2はユーザーデータであり、ロード失敗は
    製品バグとして明示する: F-097-codex 2-1 / grok 5.4)。

    Args:
        midi_path: 入力MIDIファイル(str/Path)。
        out_wav: 出力WAVパス(str/Path)。拡張子が .wav でなければ .wav に差し替える。
        soundfont_path: 使用するSF2ファイル(str/Path)。None なら常にフォールバック。
        sr: サンプルレート(Hz)。合成と書き出しで一致させる。既定 DEFAULT_SR。

    Returns:
        実際に書き出せたWAVファイルの Path(常に存在する)。

    Raises:
        FileNotFoundError: soundfont_path が指定されているのに存在しない/ファイルでない場合。
    """
    midi_path = Path(midi_path)
    out_wav = Path(out_wav)
    # 出力は必ずWAV。拡張子が異なる場合は .wav へ差し替える。
    if out_wav.suffix.lower() != ".wav":
        out_wav = out_wav.with_suffix(".wav")
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    sf_path: Path | None = Path(soundfont_path) if soundfont_path is not None else None

    # SF2が指定されたら、無音事故を避けるため先に存在検証する(codex 2-1)。
    if sf_path is not None:
        _validate_soundfont(sf_path)

    # SF2があり pyfluidsynth が使えるなら、当該音色での合成を試みる。
    if sf_path is not None and fluidsynth_available():
        try:
            audio = _synthesize_with_soundfont(midi_path, sf_path, sr)
            audio = _normalize(audio)
            return _write_wav(audio, out_wav, sr)
        except Exception as exc:  # noqa: BLE001
            # ネイティブlib欠如/SF2解釈失敗など。無言で消さずフォールバックを記録。
            audio = _normalize(_synthesize_fallback(midi_path, sr))
            wav = _write_wav(audio, out_wav, sr)
            _write_fallback_note(
                wav, sf_path, f"fluidsynth合成に失敗したため({type(exc).__name__}: {exc})"
            )
            return wav

    # フォールバック経路: SF2未指定 or pyfluidsynth未導入。
    reason = (
        "SF2が未指定のため"
        if sf_path is None
        else "pyfluidsynth(fluidsynth)が未導入のため"
    )
    audio = _normalize(_synthesize_fallback(midi_path, sr))
    wav = _write_wav(audio, out_wav, sr)
    _write_fallback_note(wav, sf_path, reason)
    return wav
