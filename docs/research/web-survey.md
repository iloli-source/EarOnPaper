> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

# AI採譜（AMT）Web網羅調査レポート

**調査日:** 2026-07-18
**手法:** WebSearch / WebFetch（英語・日本語）。比較記事・製品公式・レビューメディア・技術論文（arXiv/ISMIR）を横断。
**補足:** 当初 codex(gpt-5.5) / gemini による外部CLI調査を試みたが、いずれも認証エラー（codex は GitHub Copilot MCP の `invalid_token`、gemini はブラウザ認証プロンプトで停止）で完走できず。担当（Claude）が WebSearch/WebFetch で代替実施した。

---

## 1. 既存AI採譜ツール・サービスの網羅リスト

### 商用サービス（Web/アプリ型）

| ツール | 提供形態 | 価格（2026時点） | 対応楽器 | 出力形式 | 強み | 弱み |
|---|---|---|---|---|---|---|
| **Songscription** | ブラウザアプリ | 無料は30秒無制限（回数制限なし）＋有料トライアル | ピアノ最優先、ギター/ベース/ドラム/バイオリン/フルート/サックス/トランペット/ボーカル | MIDI + 編集可能な楽譜（広い書き出し範囲） | 単一楽器（特にピアノ）で高精度、内蔵ピアノロールエディタ、パイプライン一気通貫 | 複数楽器・複雑リズムで崩れる、表現的タイミングに弱い |
| **Klangio**（klang.io） | アプリ群 + API + DAWプラグイン | フリーミアム（約20秒プレビュー）→ 年額課金で $11.99/月〜、チケット制（Pro 50枚/月、Universe 250枚/月）、最長15分 | Piano2Notes / Guitar2Tabs / Drum2Notes / Sing2Notes / Violin2Notes / Wind2Notes + 統合Transcription Studio | PDF / MIDI / MusicXML / GuitarPro | 楽器別特化アプリ、**API・DAWプラグイン提供（他社との最大の機能差）**、2018年からの老舗（独） | ピアノ単体ではSongscriptionに劣る、ドラム(Drum2Notes)は精度低いとの報告、無料枠が短い |
| **AnthemScore** | デスクトップアプリ（オフライン） | **買い切り**（フル版 約$34、Studioは生涯無料アップデート）、30日トライアルは1曲30秒まで・保存/書き出し制限 | ピアノ・器楽が得意 | PDF / MusicXML / MIDI | サブスク不要・ローカル完結・大量処理で元が取れる | 技術がやや古い、後段で手修正必要 |
| **Ivory**（ivory-app.com） | Web/アプリ | — | **ピアノ専用**（ポリフォニックピアノ特化学習） | MusicXML / PDF / MIDI | ピアノソロで最高精度を狙う、クリーンな楽譜＋エディタ | ピアノのみ |
| **Melody Scanner** | モバイル(iOS/Android)中心 | 無料プランあり | 単一楽器メロディ中心（複数パートも一部対応） | PDF / MIDI | スマホで手軽、初心者向け | 単純メロディ向き |
| **ScoreCloud** | デスクトップ/クラウド notation | 無料10曲まで、有料 $4.99/月〜 | 音声・MIDI入力→記譜 | 楽譜（notation中心） | 演奏を弾いて記譜、notationソフトとして完成度高い | 音声採譜精度は限定的 |
| **Samplab** | プラグイン/アプリ | Premium $7.99/月（100秒）、Complete $9.99/月 | audio→MIDI（音声をMIDIのように編集） | MIDI | 「音声をMIDIのように編集」が売り | クリップ長制限 |
| **Moises** | アプリ/Web | フリーミアム | 音源分離＋コード検出（後付け） | コード名（tab/fret位置は出さない） | 分離が優秀、分離後のコード検出は精度向上 | tab出力なし |
| **Chordify** | Web | フリーミアム | 音声・YouTubeからコード検出 | コード名のみ | 手軽なコード取得 | tab/fret位置・歌詞・採譜なし |
| **Songsterr（+AI）** | Web | Plus課金 | ギター/ベース/ドラム tab生成 | tab（リズム付き） | 100万曲超のtabライブラリ＋AI生成 | **YouTubeリンクのみ入力可、MP3/音声アップロード不可・リアルタイム録音不可** |
| **audio2guitar** | Web | 無料/有料 | ギター tab | tab | 音声→fret単位tab生成 | ギター特化 |
| **Tabtify** | Web | 無料tab editor | ギター tab | tab | 無料オンラインtabエディタ | — |
| **Drumscrib** | Web（beta） | — | ドラム | ドラム譜 | 初中級曲は使える | 2年間beta停滞、変拍子に弱い、Dynamics/アクセント/セクション無し |
| **PlayDrumsOnline** | Web | — | ドラム | ドラム譜 | 初級曲は許容範囲 | 中上級で「完全に不正確」（AIハルシネーション） |

### OSS・研究モデル（Webからも参照される主要どころ）

| ツール | 形態 | ライセンス | 対応 | 出力 | 特徴 |
|---|---|---|---|---|---|
| **Spotify Basic Pitch** | 無料Web/ライブラリ | Apache-2.0 | 多楽器 | **MIDIのみ** | 無料・ブラウザ・スクリプト可。「速く無料でMIDIが欲しい、後で自分でクリーンアップ」用途の定番 |
| **MuScriptor**（Kyutai + Mirelo） | OSSモデル | コードMIT / 重みCC-BY-NC | 多楽器（voice/drums/bass/keys等を**トラック別**） | MIDI（楽器別） | **2026-07公開の新星**。decoder-only Transformer、mel-spectrogram入力で pitch/timing/instrument トークンを自己回帰生成。**17万曲（クラシック〜ヘヴィメタル）で学習した初の大規模モデル**。フルミックスを一度に全楽器採譜。small(100M)/medium(300M)/large(1.3B)。応用でコード/キー/テンポ検出。Mirelo Studio に無料ツール同梱、Pinokioワンクリック導入あり |
| **MT3**（Magenta/Google） | OSS研究 | Apache-2.0 | 多楽器・多トラック | MIDI | マルチ楽器採譜のベースライン的存在 |
| **Transkun** | OSS | MIT | ピアノ | MIDI | シンプル高精度ピアノ採譜 |
| **Omnizart** | OSS | MIT | ボーカル/ドラム/コード/ビート/楽器 | MIDI/各種 | 「全部採譜」統合。ただし現在ほぼ未メンテ |
| **YourMT3 / YourMT3+** | OSS研究 | GPL-3.0 | 多楽器 | MIDI | MT3強化版。Transformer改良＋クロスデータセットstem augmentation |
| **PianoTrans**（ByteDanceモデルGUI） | OSS GUI | — | ピアノ | MIDI | ByteDance高精度モデルの非技術者向けGUI |
| **AudioJam** | アプリ | — | コード/採譜補助 | — | 練習支援寄り |

---

## 2. ユーザー報告の成功例・失敗例（具体的に）

### MusicRadar によるSongscription実地レビュー（最も詳細な検証）
結論の見出しがそのまま業界の現状を言い表している ―
> **「Humans will be doing all the serious music transcription for the foreseeable future」（当面、本格的な採譜は人間がやることになる）**

総括: 「**初級クラシックのレパートリー**と**ソロピアノ録音の非常に単純なポップス**で最もよく機能する」。複数楽器・表現的タイミング・複雑な曲では崩れる。最も痛烈な一言 ―
> **「It's helpful in situations where you don't need help, and unhelpful in situations where you do need help.」（助けが要らない場面では役立ち、助けが要る場面では役立たない）**

**成功例**
- Ray Charles「What'd I Say」: 装飾音（grace notes）まで含めて音程を正しく取得。ただしリズムが8分音符分後ろにずれる。
- ベートーヴェン「エリーゼのために」: 同じ8分音符ずれを除けば非常に正確。
- Elizabeth Cotten のブルースギター: リズムが2拍ずれるが「テスト中で最良の採譜」。
- バッハ ヴァイオリンソナタ: 拍子は間違えるが概ね良好。ただし奏者が微妙な表現的ボウイングをした瞬間にタイミングが完全に崩壊。

**失敗例**
- Patsy Cline「Crazy」: 明快な4/4なのに「リズムが全く理解できず、3/4→4/4→11/8 と書く」。
- バッハ プレリュード ハ長調: 「理由なくフレーズ丸ごと、次に小節丸ごとをスキップし始める」。
- Thelonious Monk「Functional」: 音程は概ね合うが「リズムは完全に迷子、コード記号もめちゃくちゃ」。
- Beach Boys「Good Vibrations」: 旋律・和声は概ね保つが「タイミングは完全な混沌」。
- Rolling Stones「Jumpin' Jack Flash」: 一部コードは取れるが「メロディが全く見つけられない」。

### ドラム採譜の比較検証（Francis' Drumming Blog）
- **Drumscrib**: 初中級は使えるが上級で失敗。「Harridan」（実際は5/4）を4/4と誤認し変な結果。Dynamics/アクセント/セクションマーカー欠落。2年間betaのまま進歩なし。
- **Klangio Drum2Notes**: 「totally inaccurate（全く不正確）」。出力が奇怪すぎて「最初はピアノ譜かと思った」。
- **PlayDrumsOnline**: 初級曲は許容範囲だが中上級で「completely incorrect」。必要な音を落とし、無意味な音を挿入する（AIハルシネーションの典型）。
- 共通の結論: 「耳コピは今も必須の音楽的技能」で、AIは代替でなく補助。

### コミュニティ全般の声
- 「音楽採譜ソフトを使うのは大きく苛立たしい間違い」「単純なメロディすら正確に取れない。人間の演奏をソフトが確実に理解することはできない」（mysheetmusictranscriptions ほか）。
- ギター/ジャズ系フォーラム（JustinGuitar、jazzguitar.be）でも「採譜がうまくいかない」体験談が継続的に投稿。

### 日本語圏（成功寄りの評価軸）
- 日本語比較記事群（Vidnoz / みはまクラブ / Qiita / note）では、**精度・簡単さ・対応力のバランスで Melody Scanner** を推す論調が目立つ。初心者は Klangio/Melody Scanner無料枠、コスト重視は ScoreCloud無料版/Dorico SE、高精度志向は AnthemScore Professional/Studio、という**用途・予算別の使い分け**が定着。
- 「ピアノ演奏音声からの自動採譜は大幅に精度向上、音高認識（機械学習）＋リズム認識（統計的性質）の統合が進む」との技術認識。
- MIDI変換は Basic Pitch / Omnizart / Klangio、記譜化は MuseScore / ScoreCloud、という**役割分担**で語られる。

---

## 3. 採譜ツール/サービスに必要な機能の網羅カタログ

### 入力
- 音源ファイル（WAV/MP3/FLAC/M4A 等）アップロード
- **YouTube URL 入力**（Songsterr は YouTube のみ等、需要が非常に高い）
- リアルタイム録音（マイク/ライン）
- Spotify等ストリーミング曲の直接指定（要望あり、権利面の壁）
- 対応時間長（無料枠20〜30秒 → 有料で最長15分等）

### 前処理
- **音源分離（stem separation）**: ボーカル/ドラム/ベース/その他。Moises型。採譜精度を大きく左右（分離後にコード検出精度が上がる実例あり）
- ノイズ除去・リバーブ抑制
- テンポ/ビートへの整列（後段の記譜品質を決める）

### 解析（コア）
- ピッチ検出（ポリフォニック対応）
- オンセット/オフセット検出、**サステインペダル処理**（過剰分割問題の元凶）
- テンポ推定・**拍子（time signature）推定**（最頻出の失敗箇所）
- キー推定
- **コード認識**（Chordify/Moises型）
- 歌詞トランスクリプション（歌唱同期）
- ドラム採譜（キット要素分解）
- ギター tab / fret位置・**運指（fingering）**生成
- 楽器識別（multi-instrument、トラック別分離）
- velocity/dynamics・アーティキュレーション（現状ほぼ未対応で欠落報告多数）

### 出力
- MusicXML（notationソフト連携の要）
- MIDI
- PDF（印刷用楽譜）
- GuitarPro / tab
- 移調（transpose）
- パート別書き出し、難易度別アレンジ（Easy/Intermediate/Full の再構成）

### 編集
- **人手修正UI（ピアノロール/譜面エディタ）** ― レビュー曰く「最後の数%の精度より実務ではこれが重要」
- DAW連携（プラグイン/VST・AU）
- MuseScore/Sibelius等 notationソフト連携（MusicXMLインポート＆量子化アーティファクトの後始末）
- クリーンな「整譜・アレンジモード」（GitHub側調査でも最重要要望）

### 事業面
- 著作権処理（YouTube/ストリーミング取り込みの権利、生成譜の扱い）
- API 提供（Klangioの差別化要因）
- 課金（買い切り vs サブスク vs チケット制）、無料枠設計
- オフライン/ローカル動作（プライバシー・大量処理）

---

## 4. 技術的な現状の限界と最新研究動向（2024–2026）

### 現状の限界（2025 AMT Challenge が明示）
- **2025 Automatic Music Transcription Challenge**（ai4musicians.org）: 8チーム参加、うち2チームが MT3ベースラインを上回る。新作テストセットは8楽器・各約20秒76曲、1曲最大3楽器。
- 露呈した持続的弱点: **密なポリフォニー（dense polyphony）**、**音色の似た楽器（timbrally similar instruments）**、**データ多様性の不足**。
- ピアノ単独では大幅向上したが、**マルチ楽器のクラシックでは性能がばらつく**。
- 実地レビューが示す最大のボトルネックは**リズム/拍子/量子化**（音程は取れてもリズムで崩壊するパターンが支配的）。

### 最新研究動向
- **リズム量子化の再フレーム化（2025–2026）**: Murgul et al. が performance MIDI のビートトラッキングを Transformer のシーケンス翻訳タスクとして再定式化。ビート注釈を用いた Transformer 量子化は ASAP データセットで **オンセットF1 97.3%／音価精度 83.3%**、未学習の拍子にも汎化。「ビート検出は研究が進むが、リズム量子化は相対的に未開拓」でギャップを埋める重要領域。
- **performance MIDI → score 変換**の統合: リズム量子化＋音価予測＋キー推定＋声部分離＋記譜（beaming、奏法注記）まで含む一連の工程として扱う流れ。
- **マルチ楽器強化アーキテクチャ**: YourMT3+（Transformer改良＋クロスデータセットstem augmentation）、note-level contrastive clustering による軽量2ブランチ方式（2509.12712）など。
- **大規模学習データへのシフト**: MuScriptor が17万曲で学習。「今後の進歩はアーキテクチャ革新と同等に、豊富な学習リソースに依存する」との認識。将来はジャズ・ポピュラー音楽への拡張と堅牢な楽器検出を重視。
- **リアルタイム化 + スコアフォロー**: リアルタイムピアノ採譜と記号レベルトラッキングを組み合わせた高精度スコアフォロー研究（2505.05078）。
- **歌唱メロディのnote-level採譜**: 時間整列した楽譜生成（2502.12438）。

---

## 出典（主要）
- Songscription 比較ブログ群: best-music-transcription-software-2026 / songscription-vs-klangio-vs-anthemscore / best-audio-to-midi-converters / klangio-alternatives / anthemscore-alternatives / best-ai-guitar-tab-generators / best-ai-piano-transcription-software
- MusicRadar「Songscription review（Humans will be doing all the serious music transcription…）」
- Francis' Drumming Blog「AI Generative Drum Transcriptions: A Comparative Analysis (Updated 2026)」
- klang.io（Klangio subscriptions / 日本語ブログ）、ivory-app.com、scorecloud.com、Samplab(SoundCloud Help)、Songsterr、audio2guitar、Tabtify
- Mirelo AI Blog / MarkTechPost / VP-Land / AlphaSignal（MuScriptor）、Hugging Face(MuScriptor weights)
- arXiv 2603.27528（2025 AMT Challenge）、2407.04822（YourMT3+）、2604.22290（Transformer Rhythm Quantization）、2505.05078、2502.12438、2509.12712、ISMIR2022 000047
- 日本語: Vidnoz / みはまクラブ / Qiita(qwer123123) / note(syogaku, calm_marten90) / app-liv / audio2score.github.io
