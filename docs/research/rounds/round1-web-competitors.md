# Round 1 Web調査 — 競合・市場（多言語）

調査日: 2026-07-18
調査手法: WebSearch / WebFetch（英語・日本語・中国語・ヒンディー語）
目的: 4モデル批判の裏取り。「整譜（arrangement/editing）のOSS空白＝勝ち筋」が事実誤認との指摘を検証しつつ、競合実態と反批判材料を両面で深掘りする。

---

## 0. エグゼクティブサマリー（批判の裏取り結論）

**批判は概ね正しい。** 「AI採譜＋整譜」は既に商用化され、資金も付いている領域である。
- **Songscription**: 2025年11月に**$5M調達**（リード: Reach Capital）、150カ国15万ユーザー。「Arrangement Mode」（原曲にない楽器パートを旋律・和声から自動生成）を**実装済み**。Ron "Bumblefoot" Thal（元Guns N' Roses）がアドバイザー。
- **Klangio**: 「Transcription Studio」で**8楽器同時採譜**（世界初主張、MusicRadar報道）、VST3/AUのDAWプラグイン、API、月額$8.49〜。
- **したがって「整譜OSS空白＝勝ち筋」という単純な立論は崩れる。** ただし後述の通り、両者とも**精度（特にリズム・多楽器・非西洋音楽）に明確な弱点**があり、日本語・sargam・簡譜など**ローカライズ／非西洋記譜**は空白が残る。ここが反批判＝残存機会の芯になる。

---

## 1. Songscription 徹底調査

### 資金・成長
- **$5M シード**（2025年11月13日発表）。リード **Reach Capital**、参加 Emerge Capital / 10x Founders / Dent Capital、エンジェルに Ron "Bumblefoot" Thal（元Guns N' Roses、アドバイザー兼任）。
- 2025年6月ローンチ → 5ヶ月で**15万ユーザー / 150カ国**。「Shazam for sheet music」を標榜。
- 資金使途: 対応楽器と出力フォーマットの拡張。

### 機能全量
- 入力音声 → 楽譜 / MIDI / ギタータブ / MusicXML に変換。
- 対応楽器: piano, guitar, bass, violin, flute, trumpet, saxophone, drums, vocals（**ただしpiano以外の多くはbeta**）。
- 出力: PDF楽譜 / MIDI（DAW向け）/ MusicXML（MuseScore・Sibelius向け）/ Guitar Pro。
- **内蔵楽譜エディタ**＋インタラクティブpiano roll。
- **Arrangement Mode**: 原曲に無い楽器でも、旋律・和声からその楽器用のオリジナルパートを生成。マルチ楽器録音を「ピアノ演奏」に集約する編曲も可能。
- **Leveling（難易度調整）**: 演奏者のレベルに合わせて出力の難易度を調整。

### 価格（2026-07-17更新）
| プラン | 価格 | クレジット/上限 | 主な機能 |
|---|---|---|---|
| Free | $0 | 30秒（無制限回数）※MusicRadar旧記載では「3分×10回/月」 | エクスポート不可 |
| Plus | **$9.99/月** | 600クレジット=60分/月、1曲最大15分 | 全形式エクスポート、AI学習オプトアウト。"MOST POPULAR" |
| Pro | **$29.99/月** | 3000クレジット=300分/月、1曲最大15分 | ＋優先サポート |
| Enterprise | Custom | Custom | **API access**、バルク採譜、専用サポート |

（注: 旧MusicRadarレビューでは Plus=5×6分/月, Pro=100×15分/月 と記載。プラン改定で分単位クレジット制へ移行した模様。）
- 14日間無料トライアル（カード不要、2分採譜）。友人5人紹介でPlus1ヶ月無料。

### for-transcribers（人手ハイブリッド）の仕組み
- **プロ向けツール**として位置づけ（マーケットプレイスというより「採譜を生業とする人のワークフローツール」）。楽器分離→必要パートだけ採譜→内蔵エディタで修正→各形式で書き出し。
- **Human transcription option を内蔵**: AIの即時ドラフトから始め、精緻な手作業スコアが必要な曲だけ「人に仕上げてもらう」導線を同一アプリ内に用意。別サービスへ移らずに済む設計。
- **単価**: 具体的マーケットレートは非開示。ただし業界一般では1曲の人手採譜は**数百ドル・数日**、対してSongscriptionのAIは**数ドル（多くは$5未満）・数分**で編集可能スコアを返すと訴求。

### 弱点（MusicRadarレビュー: Ethan Hein / 「本気の採譜は当面人間の仕事」）
- **総評**: 初級クラシックには有効だが複雑な曲では破綻。出力は「実用化に大幅な編集が必要」。
- **リズム問題（最大の弱点）**: 音符が8分音符〜数拍ずれる。4/4の曲に3/4・11/8・6/4など**無意味な拍子**を連発。表情的タイミング・微細リズムに弱い。
- **多楽器**: フル楽曲は正確に採譜できない。**ドラムをベースラインと誤認**。多様な音色の録音で失敗。
- **ピッチは良好**: 装飾音・複雑な和音を含むピッチ検出は正確。
- テスト例: Ray Charles「What'd I Say」はリズムずれ、Bach前奏曲はフレーズ丸ごと欠落、Björk「Isobel」は謎の7/8小節、Elizabeth Cottenのブルースギターが最良の結果。
- 学習データの大半がピアノ録音。flute/acoustic guitar/violin/trumpet/bass guitar は"beta"。
- **日本語対応**: 明示情報なし。UI・記譜は西洋五線譜中心で、日本語簡易表記や国内記譜慣習への対応は確認できず（＝空白）。

---

## 2. Klangio 徹底調査

### 機能・製品
- **Transcription Studio**: ブラウザで**最大8楽器を同時採譜**（MusicRadarが「世界初」主張を報道）。混合音源から各楽器の**非クオンタイズMIDI**を個別生成。<30秒で処理と訴求。
- **DAWプラグイン（VST3/AU）**: リファレンス曲から素早くMIDIを抜きたいプロデューサーに対し「サブスク代を正当化する」実力と評価。
- **API**: 開発者が自社製品に採譜を組み込み可能。バルク採譜でバックカタログ対応。
- 個別製品として Piano2Notes / Guitar2Tabs 等の楽器特化ライン。

### 価格
- サブスク: **$8.49/月（年払い）/ $19.99/月（月払い）** で Plugin＋Studio 両方。
- Studio Pro は £4/月〜、14日返金保証。

### レビュー（Trustpilot 約118件、MusicRadar）
- **最多の不満は精度**: 「録音したギターのタブが正解に程遠い」等。Klangio自身「プロが苦戦する箇所はAIも苦戦する」と限界を認める。
- **サブスク／返金トラブル**: ログイン導線が弱くサブスク状態を忘れ、**自動更新で$99の想定外請求**（2026年7月の投稿）。年払いユーザーが酷評後に返金を受けた例。
- **サポート不足**: 電話・テキストサポートなし、PayPal決済問題の解決手段がない等。
- **好評**: 速度・使いやすさは一貫して高評価。「素晴らしい出発点」「膨大な手間を節約」「驚異的な精度と高速」の声も。
- MusicRadar: 多楽器同時検出は他ツールと一線を画すと評価。

### 反批判材料
- 精度クレームと**サブスク解約・返金の不透明さ**が構造的弱点。UX（ログイン導線・解約体験）と誠実な課金設計は差別化余地。

---

## 3. その他競合の網羅

| サービス | 形態 / 価格 | 特徴・最新状況 | 弱点 |
|---|---|---|---|
| **AnthemScore** (Lunaverus) | デスクトップ買切 Lite$31 / Pro$42 / Studio$107、30日試用 | ニューラルネット採譜。**オフライン・サブスク無し**、Win/Mac/Linux。買切りが根強い支持 | モデルが最新でなくUIが古い |
| **ScoreCloud** (DoReMIR) | Win/Mac＋モバイル。Free=30秒無制限、Plus/Proで分数・尺拡張 | 歌唱・演奏から記譜。老舗 | — |
| **Ivory** | iPhone、ピアノ専用 | iPhoneでピアノだけ採譜する最短ルート | ピアノ限定 |
| **Songsterr (Plus AI)** | $9.95/月 | 100万超のタブ库＋YouTube/音源からAI採譜生成 | タブ中心 |
| **audio2guitar** | Pro $8.99/月、3曲無料 | ギタータブ特化AI | ギター限定 |
| **Moises** | サブスク | 音源分離＋コード検出。**タブ/運指は出さない**。分離した単一楽器を他ツールへの入力として活用 | 記譜出力なし |
| **MuseScore** | OSS | AI音声インポート（audio→楽譜）を統合しつつある | — |
| **国内: スコアメーカーZERO** | 買切ソフト | 音源→楽譜、細部まで編集可、プロ用途対応 | デスクトップ専業 |
| **国内: Chord Tracker (ヤマハ)** | 無料アプリ | 端末内音源からコード進行解析、タブ/五線譜表示 | コード表示中心、フル採譜ではない |

**業界共通の未解決課題**: 主要ツールはいずれも**変則チューニングに非対応**（標準チューニング前提）。フォーラムで最も要望が多い機能（2026年4月時点）。

---

## 4. 中国市場（扒谱系）

- **AudioJam**: 中国発のAI扒谱（耳コピ）アプリ。Spleeter系AIで人声/ベース/ピアノ/ドラム/ギターを分離、**700+コード認識・精度90%+**主張。macOS/Win/Android/iOS。
  - 価格: 年¥98 / 半年¥68 / 月¥13（人民元）。**Pro権益**でAudioAI 5回→100回/月、取込尺5分→20分、プロジェクト無制限、DL/書出、広告除去。
- **NetEase Cloud Music（网易云音乐）**: MAU **約1.5億**（2025年9月、YoY+1.5%）。原創クリエイター**100万人超**、楽曲**560万曲超**（2025末）。音楽サービス収入535億元（2024, YoY+23.1%）。巨大な音楽SNS基盤があり、採譜/簡譜需要の潜在市場は大きいが、**扒谱・曲谱特化の商用データは検索で直接取れず**。
- **市場文脈**: 中国音楽産業総規模は5000億元超（AIが消費を牽引）。音楽教育市場は「規模駆動→価値駆動」へ転換中（双減政策・人口構造の影響で一部縮小）。オンライン録画講座が37.53%で最多形態。
- **簡譜（数字譜）**という非五線記法が主流で、ここは西洋系ツールの空白。

---

## 5. インド市場（sargam / ボリウッド）

- **市場規模**: グローバル音楽学習アプリ市場 **$2.1B（2024）→ $6.8B（2033予測）、CAGR 13.7%**。インドの自己学習者は**推定4500万人**（ネット普及で今後拡大）。
- **Riyaz**（MusicMuni Labs、2019ローンチ。ポンペウ・ファブラ大MTGスピンオフ）: カルナータカ/ヒンドゥスターニー/ボリウッド/宗教/西洋の200ラーガ・曲レッスン、130超エクササイズ。DL100万超・有料5000。**調達は累計$1.33M**（Better Capital, Multiply Ventures 等、シード2021）。学習寄りで**採譜そのものではない**。
- **sargam記譜アプリ群**（ヒンディー語検索で確認）:
  - **Swarlipi / SwarLipi**（web＋iOS, NABENDU SINHA）: インド古典のスワルリピ（sargam記譜）の作成・編集・共有。**五線譜⇄sargam変換**アプリも存在。
  - **NW: Sargam Notes**（人気曲のsargam/piano/guitar/flute）、**Sangeet Book: Sargam Notes**（ハルモニウム/鍵盤/フルート向けヒンディー曲）、**NotesAndSargam.com**（無料sargam譜、多言語）。
- **示唆**: インドは**sargam（स्वरलिपि）という独自記譜**が需要の中心。西洋ツールは非対応で、**音源→sargam自動採譜は明確な空白**。ただし現状は「手打ち・共有」中心で、AI自動採譜プレイヤーは未確認＝参入余地。

---

## 6. 市場規模の一次データ

### Music Notation Software 市場（レポート間でばらつき大、方法論差）
- Verified Market Reports: **$500M（2024）→ $1.2B（2033）、CAGR 10.5%**（2026-2033）。
- 別Notation Softwareレポート: $1.2B（2024）→$2.5B（2033）CAGR 9.5% / $1.5B→$3.2B CAGR 9.5% など。
- 高位推計: $8.56B（2024）→$18.84B（2031）CAGR 14.05%（スコープ広め）。
- ドライバー: 音楽業界のデジタル化、世界的な音楽教育の拡大、効率的作曲需要。
- 主要プレイヤー例: MuseScore, DoReMIR, MakeMusic, Sibelius, LilyPond。

### Music Learning Apps 市場
- **$2.1B（2024）→ $6.8B（2033）、CAGR 13.7%**（採譜の隣接需要として重要）。

### 調達事例（Songscription以外）
- **Riyaz（India）**: 累計$1.33M（プレシード＋シード）。
- Klangio・AnthemScore等の外部調達額は今回の検索では確認できず（要追調査）。
- Songscription $5Mが本領域で突出した最新の大型調達。

---

## 7. 反批判（残存機会）まとめ — Round 2への論点

批判（整譜は空白でない）を認めた上で、以下は依然として空白／弱点:

1. **リズム・拍子の推定精度**が全社共通の弱点（Songscription/Klangio双方でリズムずれ・拍子誤りが酷評）。ここを解けば差別化。
2. **多楽器フル採譜**は「8楽器同時（Klangio）」でも実用精度に届かず（ドラム/ベース誤認等）。
3. **非西洋記譜のローカライズが空白**: 日本語慣習・中国**簡譜**・インド**sargam**は西洋系ツール未対応。
4. **サブスク/返金/解約のUX不信**（Klangio）— 誠実な課金と透明なUXは信頼で勝てる余地。
5. **変則チューニング非対応**（業界共通・最多要望）。
6. **OSSの整譜エディタ空白**の再検証が必要: Songscriptionは内蔵エディタを持つが**プロプライエタリ**。OSSの高品質な「AI採譜＋人手整譜」統合ワークフローは依然として不在の可能性 → Round 2でGitHub/OSS側と突き合わせる。

---

## 参照ソース

- [Pricing & Plans - Songscription](https://www.songscription.ai/pricing)
- [Songscription $5M Seed Announcement](https://www.songscription.ai/blog/seed-funding-announcement)
- [Music Business Worldwide: Songscription raises $5M, 150K users](https://www.musicbusinessworldwide.com/songscription-raises-5m-in-funding-as-shazam-for-sheet-music-platform-reaches-150k-users/)
- [Billboard: Songscription raises $5M](https://www.billboard.com/pro/songscription-raises-5-million-ai-powered-music-notation/)
- [Music Ally: Songscription raises $5m](https://musically.com/2025/11/14/ai-music-transcription-startup-songscription-raises-5m/)
- [Songscription for Transcribers](https://www.songscription.ai/for-transcribers)
- [MusicRadar: Songscription review (Ethan Hein)](https://www.musicradar.com/music-tech/humans-will-be-doing-all-the-serious-music-transcription-for-the-foreseeable-future-songscription-review)
- [MusicRadar: Klang.io Transcription Studio 世界初主張](https://www.musicradar.com/music-tech/klang-io-says-transcription-studio-is-the-worlds-first-ai-music-tool-that-can-transcribe-multiple-instruments-simultaneously)
- [MusicRadar: Klang.io Transcription Studio review](https://www.musicradar.com/music-tech/klang-io-promises-to-turn-audio-into-notated-transcriptions-lead-sheets-and-guitar-tabs-but-does-it-actually-work-klang-io-transcription-studio-review)
- [Trustpilot: Klangio reviews](https://www.trustpilot.com/review/klang.io)
- [Songscription vs Klangio](https://www.songscription.ai/blog/songscription-vs-klangio)
- [AnthemScore / Lunaverus](https://lunaverus.com/)
- [AnthemScore pricing (SoftwareSuggest)](https://www.softwaresuggest.com/anthemscore)
- [audio2guitar: Best AI Guitar Tab Generators 2026](https://audio2guitar.com/blog/best-ai-guitar-tab-generators)
- [Moises AI Audio Transcription](https://moises.ai/features/ai-audio-transcription/)
- [ヤマハ Chord Tracker](https://jp.yamaha.com/products/musical_instruments/pianos/apps/chord_tracker/index.html)
- [自動採譜AIおすすめ5選 2026 (TopMediai)](https://jp.topmediai.com/ai-music/auto-transcription-app/)
- [AudioJam 官方 (中)](https://audiojam.cn/zh-CN/)
- [少数派: AudioJam レビュー (中)](https://sspai.com/post/70647)
- [网易云音乐 2026市场分析 (中)](https://m.chinabgao.com/freereport/115523.html)
- [中国音乐产业规模5000亿超 (中)](https://m.bjnews.com.cn/detail/1781240916129330.html)
- [Swarlipi - Indian Classical Music Notation (印)](https://swarlipi.app/)
- [YourStory: Riyaz music learning app (印)](https://yourstory.com/weekender/music-learning-app-riyaz-hits-right-note-self-learners-technology)
- [Riyaz - Crunchbase](https://www.crunchbase.com/organization/riyaz)
- [Music Learning Apps Market Report 2033](https://marketintelo.com/report/music-learning-apps-market)
- [Music Notation Software Market (Verified Market Reports)](https://www.verifiedmarketreports.com/product/music-notation-software-market/)
