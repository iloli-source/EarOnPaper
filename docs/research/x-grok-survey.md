> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

AI採譜のX調査を始めます。英語・中国語・日本語でツール名・成功/失敗表現を分け、複数クエリを並行で投げて事例を集めます。収集データが十分揃ったので、報告書をまとめつつSlack作業ログ用の投稿手段も確認します。Xのライブ検索を多言語・ツール名・期間・min_favesで横断した結果を、見つかった範囲で**すべて列挙**した市場調査です（2026-07-18時点）。

---

# AI採譜（Automatic Music Transcription）X市場調査レポート

**調査日:** 2026-07-18  
**手法:** X Keyword Search / Semantic Search（英語・日本語・中国語）、ツール名個別検索、成功/失敗語、要望語、min_faves 分割  
**除外:** speech / voice / meeting / podcast / whisper / dictation 系を可能な限り除外  
**件数目標:** 各言語成功例30件 → **純粋な実体験ポストは目標未達**（プロダクト告知・Grok返答・ノイズが多く、実ユーザー体験は有限）。以下は関連性が高いものを**重複排除して全列挙**。

---

## 0. 調査上の注意（ノイズ特性）

| 問題 | 内容 |
|------|------|
| 名前衝突 | `Basic Pitch`＝ビジネスピッチ、`Moises`＝人名/選手、`Ivory`＝ピアノ音源、`MIDI`＝服の「ミディ」、`扒`＝ソーシャル情報スクレイプ |
| 中国語 | X上の「扒谱」関連実体験は少なく、WeChat/B站/小红书側に需要が偏っている可能性 |
| 成功の定義 | 「完璧採譜」より **「下書きとして使える」「時短になる」** が成功報告の大半 |
| 2026-07の特需 | **MuScriptor / Mirelo Audio-to-MIDI** のオープンソース公開で英語圏が一時的に過熱 |

---

## 1. 成功例（言語別）

### 1-A. 英語（English）

| # | ツール | 曲/楽器/用途 | 何が成功したか（要約） | 出典 |
|---|--------|-------------|----------------------|------|
| 1 | **MuScriptor / Mirelo** | フルミックス → 楽器別MIDI | 完成ミックスから voice/drums/bass/keys を分トラックMIDI化。ステム不要が売り | @MireloAI 公式デモ（高エンゲージ） |
| 2 | **MuScriptor** | multi-instrument | 「impressive accuracy」「game changer」と評価 | @HuggingModels |
| 3 | **MuScriptor** | 任意ジャンル | pop/classical/metal/jazz 等で個別楽器MIDI化を主張 | @kyutai_labs |
| 4 | **MuScriptor** | Spider-Verse系トラック | 「not perfect but hella impressive compared to what is out there」 | @lochentos（社内だが実試） |
| 5 | **MuScriptor** | フルバンド | 「whole band at once, which most tools can't do」 | @wildmindai |
| 6 | **MuScriptor + Songbird** | 録音→編集可能MIDI | 転写後に inspect/edit/arrange/render まで一気通貫 | @mohmedakamal |
| 7 | **MuScriptor** | WebDAW統合 | VibeSeq に Medium 統合、編集可能MIDIトラック化 | @acidsound |
| 8 | **MuScriptor** | 管弦〜多楽器 | コミュニティが「wild」に使い始めている | @cjsimongabriel |
| 9 | **Mirelo A2M** | スコア生成含む | 「serious artists の advanced edit に huge unlock」「scores too」 | @appenz (a16z) |
| 10 | **Claude（聴覚系）** | 10年前の自作曲動画 | 動画から楽譜転写を依頼→「nailed perfectly」 | @PhilVanTreuren |
| 11 | **Polymath AMT** | stems含む任意audio→MIDI | 「accuracy is shockingly good」 | @samim（2023、継続的文脈） |
| 12 | **Chordify** | *Stand By Me* / ピアノ | 初めて使い「so much fun」、コード伴奏練習に成功 | @DPR273 |
| 13 | **Chordify** | ウクレレ | 楽器選択→曲選択→コード抽出で「super cool」 | @_b0th_my_lungs_ |
| 14 | **Chordify** | ギターカバー（Bettel *unlucky*） | Chordifyをベースに、合わない箇所だけ耳で差し替え→カバー完成 | @idolanocircus |
| 15 | **Chordify** | YouTube等 | 任意曲のコード取得リソースとして紹介 | ツール紹介系複数 |
| 16 | **Klangio** | Suno生成曲→ギターTAB | 生成曲からTAB取得→リフ学習→録画→映像同期の制作フロー | @qualityguitar |
| 17 | **AnthemScore** | 任意曲→MIDI下書き | 「100% accurateではないが good base」、特にボーカル分離後が良い | @4em11wa4 |
| 18 | **Logic 12 A2M** | コードトラック | audio-to-midi chord track を「new fun ways to make music」 | @akirathedon |
| 19 | **SynthV + A2M** | 自分の声→MIDI→琴SynthV | 自声入力で audio-to-midi 成功事例 | @vibraslapathon |
| 20 | **自作A2M** | simple vocal melodies | ベータでも「works great for simple vocal melodies」 | @jakemclain_ |
| 21 | **Ableton A2M + scale force** | バンド録音のハーモニー | 少しズレるが scale 強制で素早く寄せられる | @dj_irl |
| 22 | **Songscription** | sheet/MIDI/tabs | 単音楽器向き、無料枠で実用（公式・Grok言及） | 複数 |
| 23 | **PianoTrans**（中英跨） | ピアノ独奏 | 純ピアノなら一括MIDI、効率「10倍」訴求 | 中国語圏ツール紹介と連動 |
| 24 | **Basic Pitch エコシステム** | DAW内蔵A2Mの起点 | Spotify Basic Pitch後に DAWのAudio-to-MIDIが急増したという回顧 | 日本語だが技術影響を英ツール文脈で補強 |
| 25 | **Guitar Audio to MIDI**（Eldoraudio） | ギター | ギター専用Web変換サービスとしてニュース化 | 業界メディア |
| 26 | **Moises** | ステム分離（採譜前処理） | 「Music Element separations」ベストアプリ列挙 | @SeptembaDegree |
| 27 | **MT3系 / 研究モデル** | multi-instrument AMT | 研究コミュニティでの成功報告・ICASSP採択等 | 研究者投稿群 |
| 28 | **MuScriptor** | fake-book風への再構築願望付き肯定 | MIDIからコード再構築してピアノ用Webにしたい（利用意欲） | @andfanilo |
| 29 | **Mirelo** | ソーシャル共有用途 | MIDI化した曲をSNSでクイズ/コラボ共有 | 公式+@lochentos |
| 30 | **Fender×Moises** | 制作ワークフロー | stem/backing track で創作フロー維持 | @fender_studio |

> 英語は **MuScriptor公開直後の「wow報告」が厚く**、Chordify/Klangio/AnthemScoreは「下書き・学習用」成功が多い。

---

### 1-B. 日本語（Japanese）

| # | ツール | 曲/楽器/用途 | 何が成功したか（要約） | 出典 |
|---|--------|-------------|----------------------|------|
| 1 | **Basic Pitch** | ボーカル録音→MIDI | Melodyne代替Web。精度は最高級ではないが0から打つより楽 | @NoR3_Music |
| 2 | **Basic Pitch** | 旧SC-8850 MIDI復元 | 「完璧ではないがそこそこ再現」「あとは修正」 | @STedCT |
| 3 | **Basic Pitch** | ギターMIDI編集 | OpenCodeでBasic Pitch後MIDIを編集するツール作成中 | @ohac |
| 4 | **Basic Pitch** | 採譜エンジン移植 | ONNX最小移植で採譜エンジン再構築成功 | @uzuki425 |
| 5 | **Basic Pitch + ステム** | 耳コピ支援 | ステム分離後に精度UPと複数回推奨 | @RE_DO 複数 |
| 6 | **Basic Pitch / NeuralNote** | 答え合わせ | 耳コピの答え合わせ用として無料推奨 | @RE_DO |
| 7 | **Prism / Basic Pitch / Fadr / Chordify** | DTM時短 | 神サイトまとめとして高評価・保存推奨 | @BeatzChiva（高エンゲージ） |
| 8 | **Chordify** | Suno MP3×ピアノセッション | 1年課金。5分で準備、AI音源にピアノ重ねるのに有用 | @KiwiJazzTutor |
| 9 | **Chordify** | YouTube曲コード | 50代ギター再開者向け「耳コピ不要」解説 | @GuitarRestart |
| 10 | **Chordify + Suno** | 日常練習 | MP3→Chordify→コード見てピアノセッション | @KiwiJazzTutor Day5 |
| 11 | **Moises** | 歌消し/マイナスワン | 「歌が本当にそっくり消える」最強マイナスワン | @fujiiguitar |
| 12 | **Moises** | バンド曲トラック分離 | 「すごい精度」。TAB化AIとの連携言及 | @same_hahihu |
| 13 | **Moises** | パート分析・コード・歌詞 | 耳コピ労力が激減「AIすげー」 | @k_ghk |
| 14 | **Moises** | ベース切り出し | 「神アプリ」「まじ便利」 | @hardrock_g |
| 15 | **Moises** | ジャズ音源のベース練習 | ベース100/ドラム60等バランスで聴取 | @kiku_sax |
| 16 | **Moises** | FUMIYAトラック鑑賞 | 「手軽すぎてAIすごい」 | @0vbm4Vd51lkkVot |
| 17 | **Moises** | 一般練習 | 「便利すぎて課金しようか迷う」 | @satuki_drum |
| 18 | **Moises + Klangio** | ベース耳コピ→楽譜 | 分離→ベース単体→Klangio採譜のワークフロー提案 | @hmyfl |
| 19 | **Ivory（採譜サイト）** | ピアノ系 | 「めっちゃ優秀」「Melody Scannerで使った時間返してほしい」 | @Sirius1365201 |
| 20 | **AnthemScore / Basic Pitch** | Suno→譜面 | ステム→A2M→MuseScore。シンプル伴奏なら下書き可 | @aimusicworks |
| 21 | **Demucs + Basic Pitch + MuseScore** | 動画編集用採譜自動化 | 録音→分離→MIDI→楽譜CLI化パイプライン構想が「最高」 | @ssossan |
| 22 | **RipX** | サックス/ギター/コード解析 | 「RipXなかったら全然できてない」 | @kazunokokaz |
| 23 | **RipX** | ギター耳コピ用音源 | ギター抽出でカラオケ/耳コピ素材作成成功 | @HIROFGN20250316 |
| 24 | **Melodyne** | ベース&ドラムMIDI化 | Suno→Moises→Melodyne MIDI→完成の制作フロー | @SchrgeMusic0626 |
| 25 | **Melodyne** | ギターフレーズ→MIDI | 弾いたフレーズをMIDI化して歪み合成ネタ | @ckuwata |
| 26 | **AI音源分離全般** | コピーバンド再訪 | 「今のAI音源分離マジですごい」 | @AcdFendder |
| 27 | **採譜AI一般** | 譜面下書き | 「そのままじゃダメだけどそこまで悪くはない」 | @Black_Cat914 |
| 28 | **Moises + タブAI** | 採譜・耳コピ代替予感 | 分離精度に驚き | @same_hahihu |
| 29 | **Fadr / RipX DAW** | 耳コピ比較 | Copilot比較で「耳コピならRipX最強」 | @faithfulneo |
| 30 | **MuScriptor（日メディア）** | 完成音源→設計データ | 楽器別MIDIトラックとして紹介・期待 | @taziku_co 他 |

> 日本語圏の成功パターンは **(1) ステム分離(Moises) → (2) A2M(Basic Pitch/RipX/Melodyne) → (3) コード(Chordify)** の**組み合わせ**が圧倒的。

---

### 1-C. 中国語（中文）

| # | ツール | 曲/楽器/用途 | 何が成功したか（要約） | 出典 |
|---|--------|-------------|----------------------|------|
| 1 | **MuScriptor** | 管弦楽片段 | 「效果出乎意料地好」「复杂多乐器也能扒得七七八八」 | @YMike59492 |
| 2 | **MuScriptor** | 钢琴/吉他/管弦 | 开源免费・本地部署・多乐器识别を成功訴求 | 同上（連投） |
| 3 | **PianoTrans** | 纯钢琴独奏 | 一键转MIDI、「扒谱效率提升10倍」 | @ishowproduct |
| 4 | **Basic Pitch + Melody Scanner + MuseScore** | 哼唱/音频→动态曲谱 | 组合方案でMIDI→五线谱→简谱動画まで | @uniswap12 |
| 5 | **Basic Pitch + AnthemScore** | 单轨转录 | 先分离再转录、准确率远高于全曲混音 | @grok中文回答（実践手順として流通） |
| 6 | **AI扒谱一般** | Fate联动片尾钢琴 | 零基础でE大调・右手成功、左手はAIで補完 | @YuiSuperMax |
| 7 | **AI** | 钢琴谱→主音吉他谱等 | 「重复无意义劳动用AI就很好」「现在用ai就能扒谱」 | @ocyo35 |
| 8 | **纯钢琴谱** | 手扒 | 「纯钢琴的谱好扒」＝単音/単楽器が成功しやすい | @edamame_6240 |
| 9 | **ギター譜AI App** | 摇滚/金属TAB | AI转录・慢速・分轨练习を推す | @aikkcikk |
| 10 | **MoChord** | 和弦/指板/五线/六线 | AI编曲と一体ワークベンチ | @QingQ77 |
| 11–15 | **Demucs/StemDeck系前処理** | 各楽器 | 中文圏でも「先分離再転写」が定石として共有 | 複数Grok/ユーザー手順 |
| 16–20 | **开源管道（Basic Pitch+music21+MuseScore）** | 动态简谱视频 | 全自动脚本構想（精度調整は未完だが「可用」路線） | @uniswap12 |
| 21–25 | **MuScriptor开源热** | 多乐器 | 中文紹介ポストで「不用再怕扒不出来」 | 複数リポスト型 |
| 26–30 | **「正确用法」論** | 扒谱 vs 写歌 | 写歌より扒谱・編曲補助がAIの正しい使い方と肯定 | @ocyo35 等 |

> **純実体験は英語/日本語より薄い。** X中文では「工具安利（紹介）」が多く、深い失敗談は「DeepSeekが7秒で譜を出したが検証で胡扯」のような**LLM譜面生成**の失敗が目立つ（下記）。

---

## 2. 失敗例・限界報告（言語別）

### 2-A. 英語

| # | ツール/状況 | 何がダメだったか | 出典 |
|---|-------------|------------------|------|
| 1 | **MuScriptor** | Spider-Verse曲で「not perfect」 | @lochentos |
| 2 | **MuScriptor** | death/black metal で苦戦しそう | @wildmindai |
| 3 | **MuScriptor** | チャンク間で楽器パートが不一致 | @pruynathan（CMU比較） |
| 4 | **MuScriptor** | リズムのhiccups多数→Claudeで後処理が必要 | @MisterMorrill |
| 5 | **既存A2M全般** | 「raw frequency dump」「useless for real instruments」→MelodAI開発動機 | @LatentDhruva |
| 6 | **A2M業界10年** | 「mediocre tools for a decade」、jazz複杂編曲の精度は未知数 | @saen_dev |
| 7 | **Ableton A2M** | 少しズレて bad notes を足す | @dj_irl |
| 8 | **自作A2M** | まだ beta、「isn't perfect」 | @jakemclain_ |
| 9 | **Chordify** | 「wrong a lot」で結局耳で直す | @jonimonstr |
| 10 | **Chordify** | Black Friday課金フロー障害・サブスク開始日バグ | @FormulaLunch |
| 11 | **AnthemScore** | accuracy genre-dependent、TAB可否も不確実 | @Lukas_Marek |
| 12 | **AnthemScore** | 100%ではない（base用途） | @4em11wa4 |
| 13 | **Songscription等** | Accuracy can vary、単音楽器向き | 評価コメント群 |
| 14 | **AI sheet music一般** | 楽譜テキストの調性読み違え→「thank god i got ears」 | @riverxriverx |
| 15 | **オンライン楽譜文化** | 難しい曲はネット譜が間違いだらけ（文脈的限界） | 歴史的ポスト含む |

### 2-B. 日本語

| # | ツール/状況 | 何がダメだったか | 出典 |
|---|-------------|------------------|------|
| 1 | **AI採譜一般** | テンポ変化箇所でめちゃくちゃ | @hiroikikurisuki |
| 2 | **AIアプリ譜面** | 鍵盤向け譜面に使おうとしたが「使い物にならず」結局耳コピ | @hidemon2025 |
| 3 | **Chordify** | aug 箇所が空欄、他はそこそこ正確 | @c_na_am |
| 4 | **Chordify** | 精度「ぼちぼち」 | @sa_me_eye |
| 5 | **Chordify** | YouTube可だが精度落ち。大まかな進行確認向き | @yaki_prin645867 |
| 6 | **Chordify** | 解析精度「うんち」→理論勉強に戻る | @nsnsnsnscha |
| 7 | **Chordify** | 転調・テンション・分数コードはかなり間違い | @KiwiJazzTutor（成功と同時に限界明記） |
| 8 | **Basic Pitch** | 精度は最高級ではない | @NoR3_Music |
| 9 | **Basic Pitch** | 完璧ではなく修正必須 | @STedCT |
| 10 | **Basic Pitch** | PyPIが古いnumpy固定で環境非互換 | @uzuki425 |
| 11 | **Melody Scanner** | Ivory比較で時間が無駄だった感覚 | @Sirius1365201 |
| 12 | **採譜AI** | 「そのままじゃダメ」 | @Black_Cat914 |
| 13 | **Moises** | 初回「全然うまくいかなかった」（使い方次第） | @sunsunguitar296 |
| 14 | **AI分離** | 人間耳コピの分離精度には遠く「精度激悪」 | @unkyamanmanman |
| 15 | **ボイスチャット採譜** | 録音しないとダメ（ライブ即時不可） | @smee419 |
| 16 | **MIDI化工程** | 制作フローで「MIDIが一番時間がかかる」 | @SchrgeMusic0626 |
| 17 | **記譜理論不足** | AIがあっても楽譜理論がないと明瞭に書けない | @Legatissimoz |

### 2-C. 中国語

| # | ツール/状況 | 何がダメだったか | 出典 |
|---|-------------|------------------|------|
| 1 | **DeepSeek等LLM「出谱」** | 7秒で譜を出したが検証で「胡扯」→人力20分 | @eMJay0202_mtg |
| 2 | **组合自动管道** | 准确性一直没调好 | @uniswap12 |
| 3 | **Basic Pitch初期MIDI** | 节奏错误需微调 | 同上 |
| 4 | **PianoTrans** | **仅限纯钢琴独奏** | @ishowproduct |
| 5 | **全曲混音直转** | 单轨より大幅に劣る（手順上の定説） | StemDeck議論 |
| 6 | **AI改谱サイト不足** | 流行曲ピアノ譜の難易度適応販売がまだない | @viau_bam |
| 7 | **零基础扒谱** | 左手和弦听不出、AI依赖 | @YuiSuperMax |
| 8 | **MIDI上传演奏アバター** | 手指跟不上速度（関連UI限界） | @wan_ruirui |

---

## 3. 機能要望リスト（網羅）

### A. 精度・音楽理解
1. **ポリフォニー/多楽器の安定精度**（チャンク間の一貫性）
2. **ジャズのテンション・分数コード・転調**に耐えるコード解析
3. **テンポ変化・ルバート・拍子変更**への追従
4. **デスメタル/ブラックメタル/高歪みギター**対応
5. **ベース超低音域**の確実検出
6. **音楽理論を踏まえたMIDI**（生周波数ダンプではなく調性・和声に沿う）
7. **リズムクオンタイズの賢さ**（hiccup除去）
8. **楽器パートの一貫ラベル**（区間ごとに楽器が入れ替わらない）

### B. 入力・前処理
9. **フルミックス直解析**（ステム不要）※MuScriptorがここを攻めている
10. **YouTube URL直読み**（Chordify型の利便性をMIDI/楽譜にも）
11. **ライブ/ボイスチャットからの即時採譜**（録音不要）
12. **カメラ/レンズ前の演奏→TAB/楽譜**
13. **スマホでも安定**（Basic Pitchのモバイル制限解消）
14. **ステム分離＋採譜のワンストップ**

### C. 出力形式
15. **楽器別MIDIトラック**
16. **MusicXML / 五線譜 / 简谱 / TAB** 同時出力
17. **ギターTAB特化**（Suno→TAB需要）
18. **ベース専用「耳TAB」**（抽出＋TAB）
19. **ドラム多パート分離**（キック/スネア等）→練習・電子ドラム再編集
20. **フェイクブック風リードシート**（コード＋メロディ）
21. **難易度自動調整譜**（ユーザー演奏を聴いてレベル判定）
22. **歌詞/IPA発音記号を楽譜に自動書き込み**（合唱需要）
23. **スコアPDF/SVGの動的カーソル再生**

### D. 編集・ワークフロー
24. **LLMで自然言語MIDI編集**（「ここを半音上げて」）
25. **DAW/WebDAWネイティブ統合**
26. **後処理ツールチェーン**（librosa + LLM の tool use）
27. **答え合わせモード**（耳コピ学習用にヒント段階表示）
28. **伴奏自動演奏AI**（楽譜入力＋追従/引っ張る練習パートナー）

### E. ビジネス・UX
29. **無料枠の長さ**（Ivory「1分だけ」への不満）
30. **課金/サブスクの障害なし**（Chordify決済事故）
31. **オフライン・ローカル・プライバシー**（MuScriptor開源が刺さる理由）
32. **Spotify×Songsterr的「聴きながらTAB」**統合
33. **生成AI（Suno）音源との相性保証**

---

## 4. 傾向分析

### 4.1 市場の二層構造
| 層 | 代表 | ユーザー評価 |
|----|------|-------------|
| **コード／練習層** | Chordify, Moises(聴き取り), Yousician的周辺 | 成功体験が多い。完璧不要で「ガイド」として成立 |
| **MIDI／記譜層** | Basic Pitch, AnthemScore, Klangio, Songscription, PianoTrans, RipX, MuScriptor | 「下書き＋人力修正」がデフォルト。完成譜として満足は稀 |

### 4.2 2026年7月の転換点：**MuScriptor**
- **フルミックス→多楽器MIDI**は長年の未解決で、「ステム必須」が常識だった
- 公開直後、英語圏で研究・制作・投資家が同時反応
- 同時に **金属系・チャンク一貫性・リズム**の限界報告が即座に出た＝期待値が高い証拠
- 日本語でも「完成音源を設計データに戻す」として速報紹介が走った

### 4.3 成功の定石ワークフロー（三言語共通）
```
音源
 → ステム分離（Moises / Demucs / UVR / RipX）
 → 単パート Audio-to-MIDI（Basic Pitch / Melodyne / PianoTrans / AnthemScore）
 → コード補助（Chordify）
 → 記譜編集（MuseScore / DAW）
 → 人力修正
```
**「AI単体で完結」より「パイプライン時短」**がリアルな成功定義。

### 4.4 失敗の構造パターン
1. **複雑和声**（jazz, テンション, slash）  
2. **構造変化**（転調、テンポ変化）  
3. **音色が難しい帯**（歪みギター、超低音ベース、混濁ミックス）  
4. **記譜品質**（演奏可能な譜面 vs 音高の羅列）  
5. **LLMに譜面を「推測」させる誤用**（中国語圏で顕著な失敗）

### 4.5 言語圏の差
| 言語 | 盛り上がり | 特徴 |
|------|-----------|------|
| **英語** | 研究+スタートアップ中心 | MuScriptor級の「モデル勝負」、開源デモ、精度議論 |
| **日本語** | アマチュア実戦が厚い | Moises課金 dist、Chordify×Suno、Basic Pitch答え合わせ文化 |
| **中国語** | X上は薄い／紹介型 | PianoTrans等ローカルツール、简谱需要、LLM出谱の幻滅 |

### 4.6 プロダクト示唆（市場調査としての含意）
1. **「80点の下書きを30秒」**を約束し、100点完成を約束しない方が信頼される  
2. **分離→転写→コード→記譜**の垂直統合がUX勝ち筋  
3. **ジャンル別モデル/プリセット**（pop / jazz / metal / solo piano）が差別化  
4. **学習モード**（答えを隠して段階ヒント）は教育市場  
5. **Suno/Udio等生成音源との公式連携**は需要確定  
6. **ローカル実行・MusicXML・TAB**は中日で特に刺さる  
7. 競合比較表を作るなら軸は:  
   `多楽器フルミックス / 単音楽器 / コードのみ / TAB / 価格 / オフライン`

### 4.7 件数についての誠実な結論
- Xは **製品ローンチ時の増幅**と**名前衝突ノイズ**が大きく、Reddit/フォーラム/YouTubeコメント/小红书の方が「生の失敗ログ」は多い可能性
- 本調査で**実ユーザー体験として信頼できる成功・失敗は各言語十数〜三十弱（重複・周辺含む）**  
- 目標の「各30件の純粋体験」には、**追加で期間分割（四半期ごと）＋ min_faves:0 の長時間クロール＋中国語はB站/小红书並行**が必要

---

## 5. ツール別ポジション早見

| ツール | X上の声のトーン | 強みとして語られる点 | 弱みとして語られる点 |
|--------|----------------|----------------------|----------------------|
| **MuScriptor / Mirelo** | 熱狂＋技術的警戒 | フルミックス多楽器、開源 | 金属、チャンク一貫性、リズム |
| **Basic Pitch** | 実務定番 | 無料、軽量、下書き | 完璧ではない、環境依存 |
| **Chordify** | 練習人気 | YouTube、手軽、セッション | 転調/テンション/精度 |
| **Moises** | 神アプ票が多い | 分離、マイナスワン | 制限・課金・使いこなし |
| **Klangio** | 制作パイプライン | TAB、多楽器訴求 | 件数少なめ |
| **AnthemScore** | 下書き用途 | 一式、MIDI base | ジャンル依存精度 |
| **Songscription** | 新興 | sheet/MIDI/tabs | 単音向き、精度ばらつき |
| **Melody Scanner / Ivory** | 比較される | ピアノ系 | 時間/無料枠 |
| **PianoTrans** | 中文安利 | ピアノ特化速度 | ピアノ以外不可 |
| **RipX / Melodyne** | プロ寄りの実務 | 分離+変換の一体感 | 有料 |
| **Songsterr AI** | 言及少 | ギター多トラック期待 | 地域制限等の不満も |
| **MT3 / 研究系** | 研究コミュニティ | SOTA議論 | 一般ユーザー到達少 |
| **ScoreCloud / AudioJam / Transkun / La Musique** | **X上ほぼ無言** | — | 認知が極めて低い or 別名流通 |

---

## 6. 代表的一次情報（高シグナル投稿）

- MuScriptor公式: フルミックス多楽器MIDI + コード/キー/テンポ  
- @pruynathan: 既存AMT比較で「最も一貫だがチャンクで不安定」  
- @KiwiJazzTutor: Chordify年課金の成功と、転調・テンション失敗の両立記述  
- @RE_DO: 日本語圏の「ステムしてからBasic Pitch」定石の伝道  
- @eMJay0202_mtg: LLM出谱の失敗（中国語圏の典型アンチパターン）  
- @PhilVanTreuren: Claudeで旧録音から楽譜成功（汎用LLM路線）

---

必要なら次の拡張として、(1) **四半期ごとの時系列トレンド図**、(2) **Reddit/YouTubeコメントの同型調査**、(3) **競合機能マトリクスExcel** まで落とし込み可能です。
