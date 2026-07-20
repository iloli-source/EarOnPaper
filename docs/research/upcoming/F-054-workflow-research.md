# F-054 音声プレビュー出力 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #69 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
実装対象: render_preview(midi_path, out_path, sr=22050)->Path。新規モジュール1つ(例 earpipe/services/notate/preview.py)+新規テスト1つのみ。既存ファイルは一切編集しない。

【合成】pretty_midi.PrettyMIDI(str(midi_path)) で読み込み。fluidsynth優先→失敗時サイン合成、の二段構え。
- 内蔵synthesize(サイン合成)は本環境の実経路: `pm.synthesize(fs=sr)` を使う(installed 0.2.11で確認済みシグネチャ synthesize(self, fs=44100, wave=<ufunc sin>, normalize=True))。normalize=True既定で max|amp|=1.0 に正規化される(1音で実測1.0)。
- fluidsynthは try で試す。本環境ではpyfluidsynth未導入のため `pm.fluidsynth(fs=sr)` は ImportError("fluidsynth() was called but pyfluidsynth is not installed.") を送出(実測)。fluidsynthバイナリも無い(/opt にfluidsynth無し)。よって except (ImportError, Exception) で握って synthesize にフォールバックする。仕様通り「fluidsynth無ければ内蔵サイン合成」を素直に実装。テスト経路は必ずサイン合成側になる。
- 合成関数名は仕様指定の synthesize を内部ヘルパ名にせず、pretty_midiのメソッド呼び出しで足りる(自前サイン合成を書くなら _synthesize_sine(pm, sr) を別途用意し、pretty_midi合成が空/失敗した時のみ使う程度)。要件の「内蔵サイン合成synthesize」= pretty_midi.PrettyMIDI.synthesize を指すと解釈するのが最も堅牢(依存追加不要)。

【WAV書き出し】soundfile.write(str(wav_path), audio, sr)。audioはfloat32へ明示キャスト(audio.astype(np.float32))。soundfile既定はWAVならPCM_16へ内部変換され、範囲外は正規化でなくクリップされるため、書き出し前に max|amp|>1.0 なら振幅正規化してから渡す(pretty_midi normalize=Trueで通常≤1だが二重防御)。

【MP3化】out_pathの拡張子で分岐。.mp3 かつ shutil.which("ffmpeg") が真 → 一旦一時WAVをsoundfileで書き、subprocess.run(["ffmpeg","-y","-i",wav,"-loglevel","error", out_mp3], check=...) でMP3化(実測 rc=0 で1.6KB生成、/opt/homebrew/bin/ffmpeg 在)。成功したらMP3パスを返し一時WAVは削除。ffmpeg無し/失敗時は out_path を .wav 拡張子に置換したパスへWAVを書きそのPathを返す(フォールバック)。.wav指定時は直接WAV書き出し。

【戻り値/型】常に Path を返す(実際に書けたファイルのパス)。引数は str|Path 受け入れ、内部で Path(...) 正規化。lazy import(pretty_midi, soundfile, subprocess, shutil を関数内 or モジュール冒頭)。既存 engrave.py は関数内lazy importパターン(verovio/cairosvg等)なので踏襲可。frozen dataclassは戻り値に不要(Pathを返すだけ)だが、もし設定を持たせるなら@dataclass(frozen=True)。日本語docstring・PEP8・型注釈必須。

【テスト(AAA)】pretty_midiで1〜数音のPrettyMIDIを組み1音inst追加→tmp_pathへ.mid書き出し→render_preview呼び出し。(1).wav出力: 返り値Pathが存在・拡張子.wav・soundfile.read でsamplerate==sr・len>0を検証。(2).mp3出力: ffmpeg在れば .mp3 が生成されmagic/サイズ>0、返り値拡張子.mp3。ffmpeg無し環境も想定するなら shutil.which でskip分岐 or WAVフォールバックを検証。(3)空MIDI(音符0)経路: synthesizeが shape(0,) を返す(実測)ため、空配列でsoundfile.writeが落ちないよう最低1サンプル無音でパディングする防御を入れ、それをテスト。pytestは .venv/bin/python -m pytest <newtest> -q -p no:cacheprovider で自分のテストのみ実行し緑を確認。

## 落とし穴・失敗例(pitfalls)
1. pm.fluidsynth() は soft-fail しない: pyfluidsynth未導入で ImportError を送出(実測)。RuntimeErrorだけ握るとクラッシュ。except Exception 広めに握ってサイン合成へ落とすこと。本環境はpyfluidsynth無し+fluidsynthバイナリ無しなので実行経路は必ずサイン合成。fluidsynth側はテストで到達不能、テストはサイン経路のみ緑にする。

2. 空MIDI/無音: pm.synthesize は音符ゼロで np.array([]) shape(0,) float64 を返す(実測)。この空配列を soundfile.write に渡すと0バイトwav/エラーの恐れ。len(audio)==0 なら np.zeros(1, np.float32) 等で最低1サンプル確保する防御が必須。

3. クリッピング: soundfile.write は範囲[-1,1]外をクリップ(正規化しない)。pretty_midi normalize=True で通常≤1だが、fluidsynth経路やwave差し替え時に>1になり得る。書き出し前に max|amp| で正規化する二重防御。int16化はsoundfileが暗黙にやる(WAV既定PCM_16)。

4. dtype: synthesizeはfloat64を返す。soundfileはfloat64も受けるが、明示 .astype(np.float32) が安全・省メモリ。

5. サンプルレート整合: pm.synthesize(fs=sr) と soundfile.write(..., sr) の fs を必ず一致させる。片方44100既定のままだと再生速度/ピッチがずれる典型バグ。

6. ffmpeg分岐: shutil.which("ffmpeg") で存在確認してから subprocess。ハードコードパス禁止。失敗時(rc!=0 or 例外)はWAVフォールバックし .wav パスを返す — 「fluidsynth無ければWAVにフォールバックしパスを返す」の要件通り、MP3化も同様に握る。subprocessは check=False + returncode検査 or try/except で握り、捏造の「成功」を返さない。-loglevel error でノイズ抑制。

7. 一時WAV後始末: MP3化のための中間WAVは finally/削除で消す。out_pathと同ディレクトリに作ると権限/衝突。tempfile か out_path.with_suffix('.wav') を使い、MP3成功時のみ中間を消す(WAVフォールバック時は残して返す)。

8. パス型: str|Path 混在。全て Path() 正規化し、subprocessには str(path) を渡す(古いffmpeg/OSでPathObjが通らない事故防止)。out_path の親ディレクトリ非存在なら mkdir(parents=True, exist_ok=True)。

9. soundfile 0.14 は実はMP3直書き対応(sf.available_formats に 'MP3' 有=実測)。ただし仕様は「ffmpegでMP3化」なので指示に従う。soundfile MP3直書きは代替案としてのみ言及(新依存不要だがビットレート制御が弱い)。

10. 既存ファイル改変禁止: __init__.py/pipeline.py に配線を足したくなるが厳禁。モジュールは import earpipe.services.notate.preview で直接テストから叩けるようにする(親が後で配線)。

## 参考(prior_art)
pretty_midi公式(craffel/pretty-midi, 0.2.11 本環境導入済)がソニフィケーションの一次情報。二つのAPI: synthesize(fs=44100, wave=np.sin, normalize=True) は各音をサイン波合成する簡易法でFluidsynth不要=フォールバックに最適。fluidsynth(fs=None, sfid=0, sf2_path=None, normalize=True) はFluidsynthプログラム+SoundFont(pretty_midi同梱の簡易sf2)でGM合成するが、pyfluidsynth未導入だとImportErrorを送出(公式実装 https://github.com/craffel/pretty-midi/blob/main/pretty_midi/pretty_midi.py, 実測エラー文言 "fluidsynth() was called but pyfluidsynth is not installed.")。synthesizeは楽器ゼロで np.array([]) を返し、複数楽器は最長波形長にゼロパディングして総和・正規化する(公式ソース確認)。

soundfile(bastibe/python-soundfile 0.14 導入済): sf.write はWAV既定PCM_16。float入力で[-1,1]外はクリップ(正規化しない)ため事前正規化が定石(Issue #275/#20, KVR/Star Vibe記事)。int16スケールは±32767。

ffmpeg(/opt/homebrew/bin/ffmpeg 在、実測 `ffmpeg -y -i in.wav out.mp3` rc=0でMP3生成)がWAV→MP3の実務標準。Python内蔵でMP3エンコード手段は乏しく(wave/audioopは非圧縮のみ)、外部ffmpeg委譲かlameバインディングが通例。pydubも内部でffmpegを呼ぶだけなので新依存不要のsubprocess直呼びで十分。

中文圈の慣例(CSDN/知乎の pretty_midi 教程): 「fluidsynth 需要单独安装二进制否则报错，测试/CI环境用 synthesize() 正弦波合成兜底」が定番。MP3導出は「先 soundfile 写 WAV，再 ffmpeg 转 MP3」が最も安定と紹介される。要点は fs 一致・空音频兜底・写前归一化の3点で、本タスクのpitfallsと一致。

本リポ内先例: earpipe/services/notate/engrave.py が重依存(verovio/cairosvg/pypdf)を関数内lazy importするパターンを採用。preview.py も pretty_midi/soundfile を同様にlazy importすると起動コスト/循環回避で整合。write_musicxml(score, path)/write_pdf(...,out) 等の「out_path受け取り→書き出し→Path/None返し」シグネチャ流儀に render_preview(...)->Path を合わせる。

## 実装上の限界・正直な注記(notes)
重要: 指定された【新規モジュール1つ】earpipe/services/notate/preview.py と【新規テスト1つ】tests/test_preview.py は、着手時点で既にリポジトリに存在し(git commit 5167a73)、仕様(先行リサーチのapproach/pitfalls)と完全に一致する完成済み実装だった。厳守事項「作成してよいのは指定の新規モジュール1つと新規テスト1つだけ/既存ファイルは絶対に編集しない」に従い、既存の完成コードを上書き・改変せず、実際にpytestを実行して緑であることのみ検証した(捏造・推測での合格宣言はしていない)。

実装が満たしているpitfalls対策: (1)pm.fluidsynth()のImportErrorをexcept Exceptionで広く握りサイン合成へフォールバック、(2)空MIDIの shape(0,) を _MIN_SAMPLES=1 の無音パディングで防御、(3)書き出し前 peak>1.0 時の振幅正規化(soundfileクリップ二重防御)、(4)audio.astype(np.float32)明示キャスト、(5)synthesize(fs=sr)とsf.write(...,sr)のfs一致、(6)shutil.which("ffmpeg")存在確認後にsubprocess(ハードコードパス無し・-loglevel error)、(7)MP3成功時のみ中間WAV削除・失敗時は残してそのパスを返す、(8)str|Path正規化とsubprocessへstr(path)。

限界: fluidsynth合成経路は本環境(pyfluidsynth未導入+バイナリ無し)ではテストから到達不能で、サイン波合成経路のみ緑。これはリサーチ通りの想定挙動。MP3経路はffmpeg依存のためテストは shutil.which でskip分岐を持つが、本環境ではffmpeg在のため実際に実行され合格した。
