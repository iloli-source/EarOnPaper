> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

# AI採譜（AMT）GitHub網羅調査レポート

`gh` CLIで音楽採譜（audio→MIDI／audio→score）関連リポジトリを横断検索し、主要プロジェクトのメタデータとissueを収集。スター数・pushはすべて調査時点（2026-07-18）の値。`pushed`（最終コミット）が実態を表すため`updated`と区別している。

全体像：**ピアノ採譜は成熟・高精度だが「MIDIが汚い/使えない」という不満が支配的**、**マルチ楽器採譜（MT3系）はインストール地獄が最大の障壁**、**多くの学術リポジトリはpush停止で停滞**、という構図。

## リポジトリカタログ

### ピアノ採譜（最も成熟した領域）
| リポジトリ | ★ | 最終push | 機能概要 | 対応楽器 | 出力 |
|---|---|---|---|---|---|
| **spotify/basic-pitch** | 5,297 | 2025-11 | 軽量・多楽器audio→MIDI、pitch bend検出。CoreML/TF/ONNX | 多楽器 | MIDI |
| **DamRsn/NeuralNote** | 2,820 | 2025-01 | basic-pitchをJUCEでVST/AU化。DAW内でaudio→MIDI | 多楽器 | MIDI |
| **bytedance/piano_transcription** | 2,017 | 2023-08(**archived**) | 高精度ピアノ採譜(ペダル/velocity)。研究コード | ピアノ | MIDI |
| **azuwis/pianotrans** | 1,496 | — | ByteDanceモデルのGUI(ペダル対応)。非技術者向け | ピアノ | MIDI |
| **qiuqiangkong/piano_transcription_inference** | 471 | — | ByteDance著者の推論専用軽量パッケージ | ピアノ | MIDI |
| **Yujia-Yan/Transkun** | 379 | 2024-11 | CRF系のシンプル高精度ピアノ採譜。pip可 | ピアノ | MIDI |
| **spotify/basic-pitch-ts** | 345 | — | basic-pitchのTS/ブラウザ実装 | 多楽器 | MIDI |
| **jsleep/wav2mid** | 326 | 2026-04 | DNNによるAMT(教育寄り) | ピアノ | MIDI |
| **BShakhovsky/PolyphonicPianoTranscription** | 265 | — | RNNベースのポリフォニックピアノ採譜 | ピアノ | MIDI |
| **jongwook/onsets-and-frames** | 244 | 2026-07 | MagentaのOnsets&FramesのPyTorch移植 | ピアノ | MIDI |
| **HemantKArya/Melodfy** | 120 | 2026-07 | AI搭載ピアノaudio→MIDI(GUI) | ピアノ | MIDI |
| **sony/hFT-Transformer** | 119 | 2023-07 | 2階層 周波数-時間Transformer。SOTA級 | ピアノ | MIDI |
| **jdasam/online_amt** | 85 | 2026-07 | **リアルタイム**ピアノ採譜＋Web可視化 | ピアノ | MIDI(streaming) |
| **sony/DiffRoll** | 81 | 2026-06 | 拡散モデルによる生成的AMT | ピアノ | piano-roll |
| **EleutherAI/aria-amt** | 70 | 2025-12 | seq-to-seqの効率的・頑健なピアノ採譜 | ピアノ | MIDI |

### マルチ楽器・マルチトラック採譜
| リポジトリ | ★ | 最終push | 機能概要 | 対応楽器 | 出力 |
|---|---|---|---|---|---|
| **magenta/mt3** | 1,728 | 2026-07 | Multi-Task Multitrack採譜。複数楽器を同時採譜するT5系 | 多楽器・多トラック | MIDI |
| **omnizart** (Music-and-Culture-Technology-Lab) | 1,940 | 2026-05 | 「全部採譜」統合(ボーカル/ドラム/コード/ビート/楽器) | 総合 | MIDI/各種 |
| **muscriptor/muscriptor** | 624 | 2026-07 | **Kyutai+Mirelo**の新マルチ楽器採譜モデル(活発) | 多楽器 | MIDI |
| **mimbres/YourMT3** | 237 | 2024-11 | MT3後継のマルチタスク・マルチトラック採譜 | 多楽器 | MIDI |
| **BreezeWhite/Music-Transcription-with-Semantic-Segmentation** | 151 | 2026-06 | セマンティックセグメンテーション。MAPS/MusicNetでSOTA | 多楽器 | MIDI |
| **gudgud96/MR-MT3** | 57 | 2026-07 | MT3の楽器リーク緩和・メモリ保持版 | 多楽器 | MIDI |
| **anime-song/instrument-agnostic-amt** | 29 | 2026-07 | Semi-CRFによる楽器非依存AMT(活発) | 楽器非依存 | MIDI |

### audio→楽譜(score/MusicXML/PDF)
| リポジトリ | ★ | 最終push | 機能概要 | 出力 |
|---|---|---|---|---|
| **wei-zeng98/piano-a2s** | 41 | 2024-09 | 実世界ポリフォニックpiano audio→score、階層デコード(IJCAI 2024) | MusicXML/score |
| **LIMUNIMI/MMSP2021-Audio2ScoreAlignment** | 45 | 2026-06 | AMTを用いたaudio-to-score alignment | アライメント |
| **mariaalfaroc/a2s-transformer** | 14 | 2026-03 | ポリフォニックA2SのTransformer(ICASSP 2024) | score |

### ドラム採譜
| リポジトリ | ★ | 最終push | 機能概要 | 出力 |
|---|---|---|---|---|
| **CarlSouthall/ADTLib** | 209 | 2026-07 | 自動ドラム採譜ライブラリ | tab/onset |
| **keunwoochoi/DrummerNet** | 137 | 2026-06 | 教師なしドラム採譜(ISMIR 2019) | onset |
| **MZehren/ADTOF** | 91 | 2025-09 | 非合成音の大規模ドラム採譜データセット＋モデル | MIDI |
| **xavriley/ADTOF-pytorch** | 25 | 2026-07 | 最小依存(torch/librosa)のドラムaudio→MIDI | MIDI |

### コード認識・ビート・ボーカル/歌唱採譜
| リポジトリ | ★ | 最終push | 機能概要 | 出力 |
|---|---|---|---|---|
| **adamstark/BTrack** | 423 | 2026-07 | リアルタイムビートトラッカー(C++) | beat |
| **ptnghia-j/ChordMiniApp** | 347 | 2026-07 | コード認識＋ビート＋ギター図＋歌詞、LLM解析付きWebアプリ(活発) | コード/解析 |
| **CPJKU/beat_this** | 331 | 2026-07 | 高精度・汎用ビートトラッカー | beat/downbeat |
| **jayg996/BTC-ISMIR19** | 201 | 2026-07 | Transformerによるコード認識(ISMIR 2019) | コード列 |
| **cjbayron/autochord** | 162 | 2026-06 | 自動コード認識ツール | コード列 |
| **keums/icassp2022-vocal-transcription** | 158 | 2022-05 | ポリフォニック中の歌唱をnote単位で採譜 | note/MIDI |
| **gwx314/STARS** | 85 | 2025-11 | 歌唱の採譜・アライメント・スタイル注釈の統合(活発) | note+style |
| **B05901022/VOCANO** | 72 | 2026-05 | ポリフォニック中の歌声note採譜フレームワーク | note |
| **s603122001/Vocal-Melody-Extraction** | 67 | 2026-04 | セマンティックセグメンテーションによる主旋律抽出 | melody/MIDI |

### 音源分離(採譜の前処理として頻用)
| リポジトリ | ★ | 最終push | 機能概要 |
|---|---|---|---|
| **sigsep/open-unmix-pytorch** | 1,496 | 2026-07 | PyTorchの定番ソース分離 |
| **ZFTurbo/Music-Source-Separation-Training** | 1,445 | 2026-07 | ソース分離モデル学習の総本山(活発) |
| **bytedance/music_source_separation** | 1,381 | 2026-07 | ByteDanceのソース分離 |
| **SUC-DriverOld/MSST-WebUI** | 1,192 | 2026-07 | MSST+UVRのWebUI統合 |
| **lucidrains/BS-RoFormer** | 873 | 2026-07 | SOTAのBand-Split RoFormer実装 |

## Issueから見えた失敗例・限界報告

**「MIDIが汚い/音楽的に使えない」— 最も根深い不満（basic-pitch #170）**
> "The resulting MIDI is often noisy and cluttered with extraneous notes, making it musically unpleasant to listen to. Even with significant parameter tuning, it is difficult to achieve a clean, high-quality result."

このユーザーは商用の**MelodyScanner（Klangio技術）の"Arrangement Mode"**を「試した中で最高、譜面が即演奏可能なほどクリーン」と絶賛。**採譜精度そのものより「note列の後処理・整譜（arrangement）」が最大のギャップ**という重要な示唆。

**サステインペダルによる音符の過剰分割（bytedance #12, Transkun #23）**
- ByteDance #12: ペダル多用曲で「単音が何度も繰り返し検出され、実際は2音しか鳴っていないのに大量の音符が同時に鳴っているような譜面になる」
- Transkun #23: 「明らかにサステインされている箇所でnoteがサステインより手前で切れ、非常にchoppy（ブツ切れ）に聞こえる」

**音符のタイミング/長さの不正確さ（Transkun #13）**
> "the notes appear too close together. This results in a short and abrupt sound, regardless of the input audio or MIDI synthesizer used."

**高音域の誤検出（Transkun #30）**: 「C9がA#8として誤検出される」「本来検出されるべき音符が検出されない」とスクリーンショット付き報告。ピアノ最高音域の精度低下。

**pitch bendの過剰検出（basic-pitch #162）**: 「実際にはピッチ変化がない/わずかな箇所まで表現豊かさとしてpitch bendに識別してしまう」

**ローカルとオンラインデモで結果が食い違う（Transkun #21）**: 同じ音源でも環境により採譜結果が再現しない信頼性の問題。

**インストール地獄 = 実質的な最大の「失敗」**（精度以前にそもそも動かない、が圧倒的多数）
- **magenta/mt3**: Colab障害issueが延々。#134「colab is not working anymore」コメント26件、#172 flax/optax依存衝突、#159 モデルロード失敗、#145 CUDA初期化失敗、#141 CPU実行不可。**Colab依存が事実上唯一の入口で、依存関係の腐敗により定期的に全ユーザーが動かせなくなる**
- **omnizart**: #114「未メンテに見える、フォーク/代替を薦めてほしい」、#92「単純に動かない」、#107「インストール不可能」、#108/#105 Cython関連、Colab破損多数
- **bytedance/piano_transcription**: #1がコメント94件と炎上、Windows/Mac-M1/librosa非互換が全面。**リポジトリ自体がarchived（2023-08凍結）**
- **Transkun**: #20 コメント11件、#7 コメント14件、#4 メタデータ衝突、`pkg_resources`/`audioop`など新Python環境で破綻
- **NeuralNote**（VST）: Cubase/FL Studio/Ardourで読込不可、M1/macOS Tahoeで起動不可、Linux音声読込不可、スクリーンリーダー非対応(#169)

## Issueから見えた機能要望リスト

**「クリーンな整譜・アレンジ」機能（最重要・最頻出）**
- basic-pitch #170/#169: MelodyScanner/Klangio風「Arrangement Mode」（Easy/Intermediate/Fullの難易度別に、音楽理論を理解したAIが曲全体を聴いて弾ける譜面に再構成）。YouTubeリンク入力、MIDI/MusicXML/PDF出力

**リアルタイム/ストリーミング採譜**
- basic-pitch #171: 実時間ストリーミングMIDI出力（ライブ演奏・教育・DAW連携、詳細提案書付き）
- basic-pitch #156, Transkun #32（レイテンシ懸念）, ByteDance #2（2秒スライス）

**楽譜/MusicXML出力（MIDIでは不十分の声）**
- ByteDance #25「.xml出力してSibeliusで編集したい」、ByteDance #37/MT3 #137「MIDI→スタッフ譜変換のミス」

**入力の利便性**: basic-pitch #157（Spotify曲直接入力）、#168（iOSで.wav/.mp3拒否）、YourMT3 #21（リードシート生成）

**楽器拡張・声のみ採譜**: Transkun #14（ボーカル採譜）、YourMT3 #10（歌声のみ、コメント11件で関心高）

**モデル配布形式**: Transkun #33（ONNX/Unityアセット）、#22（Apple Metal対応）、#24（fine-tuning用重み公開）、ByteDance #35/azuwis #18（MAESTRO 3.0.0学習の新モデル）

**テンポ/BPM・ビート統合**: NeuralNote #151（BPM検出）、ByteDance #29（ビート検出統合）、azuwis #17/#7（テンポ100固定への不満、BPM設定）

**インストール簡易化**: NeuralNote #176(Pinokio)/#154(Windows)、qiuqiangkong #4(Windows一体GUI)、basic-pitch #188(Python 3.12対応)

## 活発 vs 停滞プロジェクトの傾向分析

**活発（プロダクトとして生きている）**
- **spotify/basic-pitch（★5,297）**＋派生**NeuralNote（★2,820）**が事実上のデファクト。issueが「バグ報告」でなく「機能要望」中心＝製品として成熟した証拠
- **muscriptor（★624, Kyutai+Mirelo）**が新興注目株。2026-07に活発push、Rust/candle移植PRやHuggingFaceデモがコミュニティ発で出る勢い
- **magenta/mt3（★1,728）**はGoogle継続メンテだがColab依存の構造的脆さで「動かない」issueが恒常発生。研究水準は高いがUXは不安定
- Webアプリ系(ChordMiniApp)、ソース分離系(ZFTurbo/MSST-WebUI/BS-RoFormer)、ビート系(beat_this)は活発で周辺エコシステムは健全

**停滞・凍結（学術リポジトリの典型的末路）**
- **bytedance/piano_transcription**: 高精度で今なお引用・利用されるが**2023-08でarchived**。pianotrans等が推論ラッパーとして延命
- **omnizart（★1,940）**: 野心的コンセプトで高スターだが、#114でユーザー自身が見切りを付けつつある。Cython/Colab破損で新規参入困難
- **YourMT3, hFT-Transformer, DiffRoll, VOCANO**等の論文付随リポジトリは論文採択時点でpushが止まり著者応答が乏しい

**構造的傾向（重要な洞察）**
1. **精度の壁ではなく「使えるMIDIにする後処理」の壁が本質。** 音符検出は十分実用的でも、サステインの過剰分割・整譜の欠如で「聴くに堪えない/演奏できない」MIDIが量産される。商用のKlangio/MelodyScanner「Arrangement Mode」がここを解決してリードしており、**OSS側の最大の空白地帯**
2. **企業製プロダクトは生き、単発論文リポジトリは死ぬ。** メンテ体制の有無が寿命を決め、スター数と現役度は必ずしも一致しない
3. **「動かない」問題がUXを支配。** 高精度でもColab依存・依存パッケージ腐敗・OS非互換で新規到達不可。GUIラッパー(pianotrans, MSST-WebUI, TranskunGUI)やプラグイン化(NeuralNote)が溝を埋め実質的な普及役
4. **ピアノは飽和、フロンティアはマルチ楽器・歌唱・リアルタイム・audio→score。** 勢いは楽器非依存採譜(MT3系)、歌唱採譜(STARS)、リアルタイム化、MIDIを超えたMusicXML/PDF楽譜出力へ移行中
