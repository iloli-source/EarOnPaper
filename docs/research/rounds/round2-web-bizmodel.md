> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

# Round 2 Web調査：AI採譜の事業モデル実データ検証

調査日: 2026-07-18 / 調査手段: WebSearch + WebFetch
目的: Round 2批判「買い切りデスクトップ型のみが権利的に安全だが成長SaaSと両立しない」「Basic Pitch無料ローカルで差別化消失」「生き残る一手は記譜ソフト流通への相乗り」を実データで検証する。

**凡例**: 【事実】= 出典で確認できた記述 / 【推測】= 事実から導いた解釈で出典に明記なし

---

## 総括（結論を先に）

Round 2批判は部分的に外れている。実データが示すのは以下の3点。

1. **「買い切り専業は成長SaaSと両立しない」は前提が古い。** AnthemScore(Lunaverus)は買い切りデスクトップを維持したまま、既にWebサブスク（Free/Plus/Pro, 月$9.99〜$29.99）を並走させている。両立は「できない」のではなく「既に競合がやっている」。むしろ買い切り一本足のほうが少数派になりつつある。
2. **「記譜ソフト流通への相乗り」は先行者に押さえられている。** MuseScoreは自社OMRエンジンを2025年7月に投入し1日1,000ファイル超を処理、無料枠＋Pro Plus課金で囲い込み中。Klangioは既にMuseScore/Sibelius/Finaleへの連携を確立済み。「相乗り」枠は空いていない。
3. **「Basic Pitch無料で差別化消失」は誇張。** Basic Pitchはpip/CLI前提でPython知識が必須。一般ユーザーには依然として障壁が高く、「OSSある=解決済み」は成立しない。ただしMuseScore無料枠やSongscription($5M調達・15万ユーザー)がその隙を急速に埋めつつあるのが本当の脅威。

「小さく続く」実例（Neuratron約30年、Lunaverus10年以上）は確かに存在するが、いずれも参入当時に競合が少なかった時代の産物。2025年以降は資金調達済みスタートアップと無料の記譜ソフト自社機能が市場を挟み撃ちにしている、というのが実像。

---

## 1. 買い切りデスクトップ採譜ソフトの事業持続性

### AnthemScore / Lunaverus

【事実】買い切り価格（AnthemScore 5）: Lite $31 / Professional $42 / Studio $107（一度きり、サブスク不要）。Lite/Proは1年間のアップデート、Studioは生涯無料アップデート付き。ライセンスキーは最大4台で使用可。（出典: softwaresuggest, lunaverus.com/purchase）

【事実・重要】Lunaverusは買い切りデスクトップに加え、**Webサブスク版「AnthemScore Web」を並走させている**。Free $0/月（月3曲・1曲3分まで）、Plus $9.99/月（月30曲・6分）、Pro $29.99/月（月100曲・10分）。（出典: lunaverus.com/transcribe/pricing）

→ これはRound 2批判「買い切りとSaaSは両立しない」への直接の反証。Lunaverusは買い切り資産を捨てずにSaaSを追加している。

【推測】Lunaverusは少人数（おそらく1〜数名）の会社。ZoomInfo等の企業DBにも詳細な従業員数・売上は出ておらず、大規模組織ではない。「dedicated development team」という自社表現はあるが規模不明。AnthemScoreは2016年前後から継続しており、少なくとも**10年程度は小規模で存続**している。（出典: zoominfo.com, aitoptools.com。売上・人数は非公開のため推測）

### Neuratron（AudioScore, PhotoScore）

【事実】創業者Martin Dawe。1993年に最初の製品Optical Professional（OCRソフト）をリリース。楽譜認識(PhotoScore)・音声認識(AudioScore)へ発展。コピーライト表記は1999-2019、2020年版まで更新確認。（出典: neuratron.com/about.htm, scoringnotes.com）

【推測】創業者が今もCEOを務める小規模（家族経営/少人数）会社が**約30年**続いている。AudioScore/PhotoScoreはSibelius・Finaleへのバンドル/連携で流通してきた。従業員数・売上は非公開。

→ 「小規模で長期存続」の最良の実例。ただし成長ではなく「細く長く」のモデル。

### カワイ スコアメーカー

【事実】2023年7月27日にスコアメーカーVer.11（買い切り版）の販売を終了。開発はVer.11で停止し、**サブスク型「スコアメーカーZERO」へ移行**。最後の買い切り版はソースネクストがダウンロード販売。ZEROは継続アップデート中（Ver.12.2.014でPDF楽譜ドロップ対応、VST3・Synthesizer V・VOCALOID・CeVIO AI連携）。（出典: dtmstation.com, kawai.co.jp/news, cm.kawai.jp）

【事実】カワイは2023年に**スコアメーカー無料版も公開**。（出典: kawai.co.jp/news/20230727/）

→ 大手（河合楽器）ですら買い切り→サブスク＋無料版へ舵を切った。「買い切りのみが安全」という前提は業界全体が既に放棄している。

**項目1の結論**: 買い切り専業で「小さく続く」ことは可能（Neuratron約30年、Lunaverus10年+）だが、それは低成長・小規模を受け入れる場合。成長を狙う各社（Lunaverus, カワイ）は例外なく買い切りを維持しつつSaaS/サブスクを追加している。「両立しない」は誤り。

---

## 2. 記譜ソフトエコシステム相乗りの実例

### MuseScore（Muse Group）自身の採譜AI

【事実・最重要】MuseScoreは**2025年7月に自社OMRエンジン「NoteVision」を投入**。PDF等の楽譜画像を編集可能な形式に変換（=楽譜スキャン系OMR）。技術は「MuseScore's own OMR engine」で自社開発、Klangioや買収ではない。1日1,000ファイル超を処理、2025年7〜9月で月間アップロード数が前年比130%増。当初無料だが、無料枠にアップロード上限を設け、Pro Plus加入者は無制限アクセスへ。（出典: mu.se/posts/ai-powered-score-converter）

→ 注意: これは**画像OMR（楽譜スキャン）であり音声採譜(audio-to-score)ではない**。音声採譜はMuseScore自社ではまだ提供していない。ただしフォーラムでは音声採譜要望が多数あり（musescore.org/en/node/379835）、自社化は時間の問題と見られる。

【推測】音声採譜の「相乗り」枠は現時点で空いているが、MuseScoreがOMRを自社化した実績を見ると、音声採譜も自社化する可能性が高い。外部プラグインとして採譜を提供しても、いずれ本体機能に飲まれるリスク大。

### MuseScoreプラグイン市場・MuseHubの実態

【事実】Muse Groupは「MuseHub」を運営（"Steam/App Store for music and audio tools"）。**有料プラグイン市場は実在**し、開発者は純収益の70%を取得。LANDR、Baby Audio等のVSTを販売中。（出典: blog.musehub.com, developer.musehub.com）

【事実・注意】ただしMuseHubで売れるのは主に**VST（音源・エフェクト）**。MuseScore用に深く統合できるのはMuseSampler形式の音源のみで、これはMuseScore外では使えない。VST3は使えるが統合は浅い。（出典: vi-control.net, blog.musehub.com）

→ 採譜機能を「MuseScoreプラグイン」として売る道は、VSTと違い統合APIが限定的。楽譜notation本体への機能追加はサードパーティに開かれていない（本体側が握る）。相乗り可能なのは音源/エフェクト分野で、採譜はプラットフォーマー(Muse Group)側の領域。

### Klangioの記譜ソフト連携（相乗りの実在例）

【事実】Klangio（独Karlsruhe, 2018年〜, 従業員7名前後）は、音声ファイルをMusicXMLで数秒エクスポートし**MuseScore / Sibelius / Finale へ直接インポート**できる連携を提供。（出典: klang.io/solutions/music-notation-softwares/）

→ これが「記譜ソフト相乗り」の実在する先行者。ただし相乗りといっても「MusicXMLエクスポート経由」であり、記譜ソフト本体に組み込まれているわけではない。Klangio単体がAPI/アプリで採譜し、出力を記譜ソフトが読む形。参入障壁は低いが、既にKlangioが先行し関係を築いている。

### Dorico / Sibelius / Finale のAI採譜連携の現状

【事実】Finaleは2024年8月26日、MakeMusicが35年の歴史に幕を下ろし開発終了を発表。新バージョンは今後一切なし。認証は無期限維持。FinaleユーザーはDorico Proへ$149のクロスグレード割引（通常$579）。MakeMusicはSteinberg(Dorico)と提携。（出典: makemusic.com/press-room, slate.com, digitalmusicnews.com）

【事実・訂正注意】「Sibelius/FinaleがAIで自動作曲」という記事(scoringnotes.com)は**2024年4月1日のエイプリルフール記事**であり事実ではない。当初の検索では実機能のように見えたが、原文を確認したところジョーク記事だった。DoricoやSibeliusに音声採譜が本体標準搭載されたという確かな事実は今回の調査では確認できなかった。（出典: scoringnotes.com/news/new-versions-of-sibelius-finale/ を精読して判明）

**項目2の結論**: 「記譜ソフト相乗り」戦略は理論上有効だが、(a)音源/エフェクトのプラグイン市場(MuseHub)はサードパーティに開かれているが採譜のような本体機能領域はプラットフォーマーが握る、(b)MusicXMLエクスポート経由の連携ならKlangioが既に先行、(c)MuseScore本体がOMRを自社化した実績から採譜も自社化する公算が大きい。「空いている一手」ではなく「先行者と本体機能化リスクに挟まれた枠」というのが実像。

---

## 3. 音楽系マイクロSaaS/インディー開発の成功事例

【事実】音楽/音声隣接のインディー成功例:
- **AudioPen**（音声→テキスト整形）: 個人開発Louisが15〜20個作った中で当たった1本。安定収益に到達。（出典: medium.com/@AIBites。具体MRR額は記事タイトルで「meaningful revenue」止まり、正確な数字は本文未確認）
- **Bannerbear**（画像自動生成API、音楽外だが個人ブートストラップ）: $15k MRRに数年かけて到達=元の給与相当。（出典: indiehackers.com）
- **Diego Roshardt**: 2週間で製品を作り12ヶ月で$10k MRR（分野は音楽と限らず）。（出典: 同上）

【事実】インディーSaaS一般の「小さく儲かる」ライン: $10k MRR到達は少数の成功者、$15k MRRで「フルタイム給与相当」と表現される水準。（出典: indiehackers.com, rethinklab.co）

【推測】音楽ツール分野に限定した個人開発の公開MRR事例は、汎用SaaSに比べ乏しい。採譜のようなニッチは市場が小さく、$5k〜$15k MRR規模（=年商60万〜180万円/月では日本円で月数十万〜200万円弱）が現実的な「小さく儲かる」上限帯と推測される。それ以上を狙うと資金調達型（下記Songscription）との競合になる。

**項目3の結論**: 音楽インディーSaaSで「フルタイム給与相当（月$15k=約230万円）」は到達可能だが容易ではなく、多くは複数プロダクトの打率勝負。採譜単体で月商数百万円規模の個人事業は成立しうるが、それが上限帯。

---

## 4. Basic Pitch / OSS採譜の実運用の壁（「OSSある=解決済み」への反証）

【事実】Spotify Basic Pitchは`pip install basic-pitch`でインストールし、**主にコマンドラインインターフェース(CLI)で操作**。MIDI出力（オプションでWAV/NPZ/CSV）。「この CLI 要件は端末操作に不慣れな一般ユーザーには障壁となりうる(may present a barrier for general users)」と明記。venv/conda仮想環境の利用推奨、pip権限エラー対処など**Python環境の知識が前提**。（出典: github.com/spotify/basic-pitch, deepwiki.com）

→ 反証成立。「無料OSSがある=一般ユーザーの問題は解決済み」は誤り。Basic Pitchはエンジニア/開発者向けで、一般の音楽学習者・演奏者がターミナルとPython環境を扱うのは大きな障壁。GUIラッパーやWeb化で「使える形」にすることに依然として価値がある。

【事実・ただし注意】その隙を無料/低摩擦のプロダクトが急速に埋めている:
- **MuseScore無料枠**（OMRだが無料でGUI、上限付き）
- **Klangio**（Web/アプリでGUI、無料お試しあり）
- **Songscription**（後述、Webで即使える「Shazam for sheet music」）

**項目4の結論**: 「OSSある=無料で解決済み」への反証は明確に成立（Basic PitchはCLI/Python前提で一般ユーザーに不向き）。ただし差別化の源泉は「GUI/Web化・UX」であり、そこは既に無料〜低価格の競合が殺到している領域。技術ではなくUXと配布チャネルが勝負どころ。

---

## 5. Klangio APIのビジネス（B2B2Cの実績規模）

【事実】Klangio GmbH、独Karlsruhe、2018年設立、従業員7名前後（1-10名）。創業者Sebastian Murgul(CEO, KITでAI×音楽の博士研究)、Alexander Lüngen(CTO)。（出典: crunchbase, pitchbook, karlsruhe.digital）

【事実】資金調達は情報が錯綜。「まだ調達なし」とする情報源と、Start-up BW / Ideenstark / CyberLab（地域アクセラレータ/助成）が出資したとする情報源が併存。少なくとも大型VC調達はしていない。（出典: crunchbase, startup-atlas.de）

【事実】製品構成: API（音声→MIDI/MusicXML/PDF/GP5、ピアノ/ギター/ベース/ボーカル対応、音源分離・BPM検出・コード進行認識も）、Transcription Studio（複数楽器）、単一楽器アプリ群（Piano2Notes/Guitar2Tabs/Sing2Notes/Drum2Notes）、Scan2Notes(OMR)、Melody Scanner、DAWプラグイン。（出典: klang.io/api/, 検索結果）

【事実】API/B2Bの実装先として公表されているのは記譜ソフト連携（MuseScore/Sibelius/Finaleへのインポート）とバルク処理サービス（100曲以上の一括転写）。（出典: klang.io/solutions, songscription.ai/blog）

【事実】料金: サブスク制。Universe（月250チケット）、Klangio Pro（月50チケット）等のチケット課金。B2B API価格は個別見積もり型で公開価格の詳細は未確認。（出典: klang.io/help/klangio-subscriptions/）

【推測】Klangioは7名規模でAPI・複数アプリ・DAWプラグインを展開する「小さく多角化」型。大型調達なしでこの製品幅を維持できている点は、採譜B2B2Cが少人数で成立することの証左。ただし「B2B2Cの大型実績（有名記譜ソフトへの本体OEM組込み等）」は今回の調査では確認できず、規模は限定的と推測。

**項目5の結論**: Klangioは7名・地域助成レベルの資金で、API+複数C向けアプリを10年弱運営する「小さく成立している」実例。B2B APIは存在するが、公開されている大型OEM実績は乏しく、収益の中心はC向けサブスク＋APIの組み合わせと推測される。

---

## 補足：Round 2以降で注視すべき本当の脅威（Songscription）

【事実】**Songscription**（"Shazam for sheet music"）が2025年6月ローンチ、**2025年11月に$5M(約7.5億円)をReach Capital主導で調達**。ローンチ5ヶ月で150カ国15万ユーザー、月次成長60%。（出典: musically.com, musicbusinessworldwide.com, billboard.com）

→ これがRound 2批判が見落としている本当の競争環境。「買い切りvsSaaS」の二項対立ではなく、**資金調達済みの高成長Web採譜（Songscription）と無料の記譜ソフト自社機能(MuseScore)が市場を挟み撃ち**にしている。個人/小規模で参入するなら、この2者が届かないニッチ（特定ジャンル特化・特定楽器・日本語UX・特定ワークフロー統合等）を狙うのが現実解。

---

## 出典一覧

- Lunaverus/AnthemScore価格: https://lunaverus.com/transcribe/pricing / https://lunaverus.com/purchase / https://www.softwaresuggest.com/anthemscore
- Neuratron: https://www.neuratron.com/about.htm / https://www.scoringnotes.com/news/neuratron-releases-photoscore-8-including-notateme/
- カワイ スコアメーカー: https://www.dtmstation.com/archives/62843.html / https://www.kawai.co.jp/news/20230727/ / https://cm.kawai.jp/products/sm/
- MuseScore OMR(NoteVision): https://www.mu.se/posts/ai-powered-score-converter
- MuseHub有料プラグイン: https://blog.musehub.com/musehub-plugin-distribution/ / https://developer.musehub.com/muse-partners-help/introduction/what-is-musehub
- Klangio連携: https://klang.io/solutions/music-notation-softwares/ / https://klang.io/api/
- Klangio企業情報: https://www.crunchbase.com/organization/melody-scanner / https://pitchbook.com/profiles/company/499947-76 / https://karlsruhe.digital/en/2025/09/klang-io-ki-musik/
- Finale開発終了: https://www.makemusic.com/press-room/press-releases-2024/makemusic-sunsets-finale/ / https://slate.com/technology/2024/09/finale-music-notation-software-shutting-down-how-the-program-became-so-widely-used.html
- Sibelius/Finale AI記事=エイプリルフール: https://www.scoringnotes.com/news/new-versions-of-sibelius-finale/
- Basic Pitch: https://github.com/spotify/basic-pitch / https://deepwiki.com/spotify/basic-pitch/4-usage-guide
- Songscription調達: https://musically.com/2025/11/14/ai-music-transcription-startup-songscription-raises-5m/ / https://www.musicbusinessworldwide.com/songscription-raises-5m-in-funding-as-shazam-for-sheet-music-platform-reaches-150k-users/
- インディーSaaS: https://www.indiehackers.com/ / https://medium.com/@AIBites/this-founder-built-a-15k-mrr-saas-in-12-hours-82dd65e0be0a
