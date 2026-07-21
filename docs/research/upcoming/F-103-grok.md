音楽採譜ソフトの「出力先別エクスポートプロファイル」周りを、X上の実務者・研究者・開発者投稿から英語・中国語中心に調査します。失敗例を厚めに集めます。ヒットが薄いので、MusicXML方言・相互運用の失敗事例に絞って再検索します。# 調査報告：出力先ソフト別エクスポートプロファイル  
（MuseScore / Dorico / Sibelius / Guitar Pro の方言吸収）

**調査対象**: X（旧Twitter）上の実務者・研究者・開発者投稿（英語・中国語中心、一部日本語補足）  
**調査日**: 2026-07-21  
**論点**: MusicXML を中心とした記譜ソフト間インターチェンジの成功／失敗、限界、ベストプラクティス、トレンド  

---

## 1. 結論サマリ

| 観点 | 実務コミュニティのコンセンサス |
|------|-------------------------------|
| **本質** | 「共通フォーマット」MusicXML は **論理記譜の交換**には効くが、**見た目・方言・高度記譜はソフト固有** |
| **失敗の主因** | 1:1変換幻想／レイアウト喪失／楽器・奏法方言／Guitar Proのタブ文化／Finale終了による一斉移行圧 |
| **成功の条件** | 目的分離（記譜=XML / 演奏=MIDI）・中継ホップ・プリエクスポート整形・ターゲット別プロファイル |
| **開発示唆** | 単一「汎用MusicXML」より **ターゲット別エクスポートプロファイル（方言吸収）** が製品価値そのもの |

中国語圏では「**导出（エクスポート）こそ護城河（堀）**」「FinaleとSibeliusで同じ譜が**错位（ズレ）**する」と明言され、**方言吸収＝競争優位**という認識が強いです。

---

## 2. 失敗例（重点・実投稿ベース）

### 2.1 「MusicXML は 1:1 ではない」——移行の幻滅

Finale 終了発表直後、実務者から一斉に出たのは **「XMLは変換であって復元ではない」** という声です。

> *「On top of that, everybody knows XML is not a 1:1 conversion. Finale uses a proprietary file type and now we face being locked out of decades of work?」*  
> — @walkeri141（2024-08-26）

> *「Music XML is okay, but it's not better than okay.」*  
> — @natehowe（2024-08-26）

> *「Finale files will not open in anything else. You can export a MusicXML but it loses some details and breaks certain formatting things. This archival process is gonna be craaaaazy」*  
> — @fannypackhq（2024-08-27）

**示唆（プロファイル設計）**: 「完全再現プロファイル」を約束すると炎上しやすい。契約上も **「論理内容の移植」と「出版レイアウトの移植」を分けて宣言**すべき。

---

### 2.2 レイアウト／フォーマット破壊——最大の苦情クラス

Finale → MusicXML → Dorico の定番パスについて：

> *「The "pathway" is: save your Finale score as MusicXML → import into Dorico → fix all the f\*\*\*ed up formatting and stuff that was lost. There's no import tool or anything. Do it all yourself.」*  
> — @TheRealTomahawk（2024-08-27）

ページ相対フォーマットの欠落を技術的に指摘する投稿：

> *「MusicXML for example does not include page-relative formatting such as staff height, distance between staves, manual breaks, etc…」*  
> — @joemmac（2023-01-27）

MIDIよりXMLの方が音符はマシだが、**ページ整形の欠落が一気に前景化**する、という実体験：

> *「The import from a MusicXML file works better, but then the complete lack of page formatting becomes the foreground issue.」*  
> — @31r1kur（2024-01-13）

Sibelius公式が後から **余白・リハーサルマーク・マルチレストのMusicXML importを修正**した事実自体が、「長らく壊れていた／不足していた」ことの反証です。

**方言吸収ポイント**:  
- ターゲットが **Dorico** なら「レイアウトは捨てて再浄書前提」  
- **Sibelius** なら「マージン／リハーサル／multirestを意識したXML」  
- プロファイルで **default-x/y や print-object の出し方を切替**するのが実務解

---

### 2.3 マルチホップ地獄（ソフトを何度も経由）

極端だが示唆に富む失敗ワークフロー：

> *「Had to run a musicxml file into finale, do the meter changes, export it into musicxml, run it through Sibelius, download dolet and use it to export musicxml, and finally get it to work correctly in dorico????」*  
> — @_rwgarvey（2023-12-29）

**読み取り**:  
- 単一エクスポートでは足りず、**特定ソフトの「方言修正器」として別ソフトを噛ませる**文化がある  
- 歴史的に Sibelius 向け **Dolet** プラグインが「良いXMLを吐く中継器」として使われてきた（MusicXML発明者 @MichaelDGood も更新を告知）

**製品化示唆**: ユーザーが手でやっている「Finale→Sibelius(Dolet)→Dorico」は、**エクスポートプロファイルの多段変換パイプライン**そのもの。

---

### 2.4 要素サポートの穴（Jazz記譜・特殊奏法）

課題提出で Finale 必須の学生が、Doricoで書いてXML経由にすると **Finaleが一部要素を拒否**：

> *[1/3] …exporting them to MusicXML, finding out that Finale doesn't support certain elements…*  
> *[2/3] then deleting those elements in Dorico, exporting to MusicXML again, copying the parts… then adding back all the elements that Finale couldn't import (slash regions, chord symbols, etc.).*  
> — @viusmusic（2020-08-21）

**失敗パターンの定石化**:
1. ターゲットが読めない要素を **事前に削る**  
2. 再エクスポート  
3. ターゲット側テンプレートへ貼り付け  
4. 欠落要素を **手で戻す**

→ これはまさに **「ターゲット別プロファイル + 欠落レポート + 手動修復ガイド」** が必要な証拠。

---

### 2.5 楽器ロール／プレイヤー種別の誤認

Sibelius → Dorico の具体バグ報告（浄書・開発寄りユーザー）：

> *「…exporting MusicXML from Sibelius 8.4.2 and import it to Dorico Pro 3.0.0.1038: The 2nd Violin Ensemble always gets recognized as a solo player. I have to recreate another violin ensemble and manually migrate the contents…」*  
> — @ShikiSuen → @dspreadbury（2019-10-01）

**方言吸収ポイント**:  
- Sibelius の ensemble / section player 表記  
- Dorico の solo vs section モデル  
- MusicXML の `score-part` / `part-name` / `instrument-name` マッピング

ここは **プロファイルで part mapping テーブル**を持つべき領域。

---

### 2.6 記譜 vs 再生のねじれ（MusicXMLとMIDIの使い分け失敗）

Dorico → Logic での比較実験（実務音屋）：

- **MusicXML**: 記号は移るが、音符・スラーはLogic既定表示、リピート未展開、テンポがざっくり  
- **スタMIDI**: リピート展開・テンポ・音価・強弱が意図通り  

— @takuyah（2026-07-19）

Dorico側（@dspreadbury）も用途分離を明示：

> *「If you need to preserve the played performance, use MIDI. If you want the notation… use MusicXML.」*  
> — @dspreadbury（2022-10-06）

**失敗の型**: 「見た目も演奏もXML一発で」はほぼ破綻。プロファイルは **Notation-profile / Playback-profile** に二分すべき。

---

### 2.7 グラフィカル／非標準記譜はXML圏外

現代音楽・図形楽譜の作曲家：

> *「Because much of my music isn't in 19th century notation, export as MusicXML doesn't work.」*  
> — @bathorykitsz（2024-08-27）

> *「…thousands of scores with no conversion app (MusicXML doesn't work for graphical scores.)」*  
> — 同著者（2024-08-26）

**限界宣言が必要**: 共通西楽記譜（CWMN）外はプロファイル外。PDF/画像/専用フォーマットへの逃げ道を仕様に書く。

---

### 2.8 用語・記譜慣習の方言（8vb 等）

> *「Curious how this gets exported depending on user settings via MusicXML? Sibelius uses "8vb" and Dorico doesn't even have an "8vb" option.」*  
> — @robertpuff（2020-04-20）

**プロファイル設計**: オクターブ記号、リピート、強弱の記法バリエーションを **ターゲット語彙へ正規化**するテーブルが必要。

---

### 2.9 Guitar Pro / タブ系の失敗

Songsterr → Guitar Pro エクスポート：

> *「Guitar Pro export missing lyric extension data (__), causing lyric misalignment in GP8」*  
> — @BrettRocks33（2026-07-09）

中国語圏の位置づけ：

> *「Guitar Pro 是 notation based 的… 如果你有很重的 notation 使用需求，那基本上就是 … Sibelius 或 … Dorico」*  
> — @corrosivepsyche（2026-07-21）

**読み取り**:
- GPは **タブ＋演奏情報**が強く、クラシック浄書系（Sibelius/Dorico）と **モデルが違う**  
- MuseScoreはGP importを持つが、**TAB入力しやすさではGP優勢**という現場感（日本語ユーザー談も多数）  
- プロファイルは **GP向け: bend/slide/palm mute/lyric extension** を特別扱いしないと歌詞・奏法が崩れる

---

### 2.10 中国語圏：標準が「乱」、同一譜が「错位」

> *「写乐谱这种软件最值钱的地方根本不是编辑播放，是导出。  
> MusicXML和MIDI那套格式标准乱得要命，同一个谱子在Finale和Sibelius里打开经常错位，光把这些大厂格式吃干净就能挡住99%想抄的人。」*  
> — @yangyue992125（2026-06-14）

**示唆**:  
- 市場認識として **エクスポート品質＝参入障壁**  
- 「方言吸収」は機能ではなく **ビジネスの堀** として語られている

---

### 2.11 バージョン間破壊（ソフト内ですら壊れる）

MuseScore旧版データが新版で壊れる／開けないため、**最初からMusicXML退避すべきだった**という反省：

> *「多少レイアウトが崩れる問題を許容してでも musicXML に export しておくべきだった。」*  
> — @kz_holiutschi（2025-09-22）

**プロファイル外だが重要**: アーカイブ用「**互換優先プロファイル**」（レイアウト捨てて要素最大化）の需要。

---

### 2.12 失敗パターンの類型まとめ

| ID | 失敗クラス | 典型症状 | 主戦場 |
|----|-----------|----------|--------|
| F1 | 1:1幻想 | 「開いたが別物」 | Finale移行全般 |
| F2 | レイアウト喪失 | 改行・余白・staff間隔消失 | XML共通 |
| F3 | マルチホップ | 3〜4ソフト経由 | プロ浄書・締切案件 |
| F4 | 要素欠落 | slash region, chord, 奏法 | Jazz/ポピュラー |
| F5 | プレイヤー誤認 | ensemble→solo | オーケストラ |
| F6 | 記譜/再生混同 | リピート未展開・テンポ雑 | DAW連携 |
| F7 | 非CWMN | 図形楽譜全滅 | 現代音楽 |
| F8 | 用語方言 | 8vb等 | ソフト差 |
| F9 | タブ方言 | lyric extension, bend | Guitar Pro |
| F10 | 標準の「乱」 | 同譜错位 | 中英コミュニティ |

---

## 3. 成功例・部分成功

### 3.1 目的を分けたエクスポート

- **演奏の忠実性** → MIDI  
- **記譜の移植** → MusicXML  
（@dspreadbury）

### 3.2 バッチXML退避（災害対策）

Finale終了時、プロ作曲家が推奨：

> *「…doing this will give you backups that can be opened in other music notation software. You can convert an entire folder of Finale files at once using File > Export > Translate Folder to MusicXML.」*  
> — @darcyjamesargue（2024-08-28）

MusicXML発明者も **移行動画（Finale→Dorico等）を推奨**。

### 3.3 ベンダー側のimport改善競争

Finale終了後、Michael Good：

> *「With Dorico, MuseScore Studio, and Sibelius all competing for people switching from Finale, I hope we'll see a big leap forward in MusicXML import quality from all three.」*  
> — @MichaelDGood（2024-08-30）

Sibeliusは **margins / rehearsal marks / multirests** のimport改善をプロモ。

### 3.4 ターゲット明示の専用エクスポート

ハープの弦名＋ペダル臨時記号を **MuseScore / Sibelius / Dorico 向けMusicXML**として出す、という開発者投稿。  
— @tshiraiwa_o（2026-06-21）

→ **「出力先を列挙したエクスポート」** は既に現場ニーズとして実装され始めている。

### 3.5 中継としてのDolet

SibeliusのMusicXML export品質向上のための **Dolet for Sibelius** が、発明者引退前まで更新されていた。  
＝ **「汎用XML」より「良い方言で吐くエクスポータ」** が歴史的に価値を持った。

### 3.6 日本語実務者の相対評価（参考）

浄書家 @hidetakumi：Finale XMLコンバートの再現性は **「Sibeliusの方がDoricoより若干よい」** と相対比較。  
（完全成功ではなく「マシな失敗」）

---

## 4. 限界（コミュニティが繰り返し言う境界）

1. **MusicXMLは「共通西楽記譜」中心** — 図形楽譜・実験記譜は対象外  
2. **レイアウトは意図的に捨てられる** — 発明者Good自身も「編集アプリはフォーマットを全部importしない傾向。自前設定で再構築したいから」と説明  
   > *「Editing apps like Finale and Dorico tend to not import all formatting details because often you want to rework those…」*  
   — @MichaelDGood（2019-12-13）  
3. **ソフトのデータモデル差はXMLでは埋まらない** — Doricoのプレイヤー概念、SibeliusのMagnetic Layout、GPのタブ奏法  
4. **「オープンソース＝オープンデータ」ではない** — MusicXMLを出さない記譜ツールも存在（Good）  
   > *「Open source does not mean open data.」*  
   — @MichaelDGood（2024-08-26）  
5. **完璧なクロスアプリ再現は未達成** — ベンダーが今もimportを「改善項目」として売る段階

---

## 5. ベストプラクティス（投稿から抽出した実務知）

### 5.1 エクスポート前（ソース側整形）

| 実践 | 根拠・文脈 |
|------|------------|
| **ターゲットが読めない要素を先に削る** | Jazz課題のDorico→Finale往復 [@viusmusic] |
| **SibeliusでMagnetic LayoutをFreezeしてからXML** | ブログ系Tips [@robertpuff 2018] — export安定化 |
| **バッチでMusicXML退避** | Finale終了時の標準災害対策 |
| **目的でMIDI/XMLを使い分け** | Dorico公式 [@dspreadbury] |

### 5.2 エクスポート設計（製品側）

| 実践 | 内容 |
|------|------|
| **ターゲット別プロファイル** | MuseScore / Dorico / Sibelius / Guitar Pro で要素セット・命名・part mappingを切替 |
| **Notation vs Playback 分離** | 記譜XMLと演奏MIDI（またはplayback XML）を別成果物に |
| **欠落レポート** | import不能要素を警告リスト化（手戻りを減らす） |
| **中継モード** | 「Sibelius-friendly (Dolet-like)」「Dorico-friendly」など実績ある方言を再現 |
| **アーカイブモード** | レイアウト捨て、要素最大化、バージョン耐性優先 |
| **非CWMNの明示拒否** | グラフィカル譜はPDF/画像パスへ誘導 |

### 5.3 インポート後

| 実践 | 内容 |
|------|------|
| **テンプレートへ中身だけ移す** | ターゲット側のJazzテンプレ等に貼る [@viusmusic] |
| **レイアウトは再浄書前提** | 「fix formatting」は仕様、バグ扱いしない |
| **プレイヤー種別の再割当** | ensemble誤認の手動修正をチェックリスト化 |

### 5.4 中国語圏の製品思想

> *「最值钱的地方…是导出」* — 导出品質が堀  
→ 採譜ソフトの差別化は **認識精度より、出口の方言吸収** という位置づけ。

---

## 6. 最新トレンド（2024–2026）

| トレンド | 内容 | 投稿例 |
|----------|------|--------|
| **Finale終了ショック** | 一斉MusicXML退避・移行比較・「XMLはokay止まり」 | 2024-08多数 |
| **import品質競争** | Dorico / MuseScore / SibeliusがFinale難民争奪でXML改善 | Good, Avid |
| **スキャン→XML→各ソフト** | Flat Opuscan等が「export MusicXML… open in Flat, MuseScore, Dorico, Sibelius」と **出力先列挙** | @flat_io 2026-07 |
| **DAW連携の二刀流** | Dorico↔Cubase/LogicでXMLとMIDIを使い分け | Spreadbury, 花岡 |
| **タブ／歌詞拡張のバグ表面化** | Songsterr→GPのlyric extension欠落など | 2026 |
| **AI生成→MusicXML** | ClaudeがMusicXMLを書く実験（UIは壊れているが方向性） | @nullchecks 2025 |
| **専用記譜のターゲット明示export** | ハープ等、出力先名を並べたexport | 2026 |
| **中国語スタートアップ視点** | 「大厂格式を食べ切る」＝堀 | 2026 |

---

## 7. 機能「出力先ソフト別エクスポートプロファイル」への設計示唆

調査結果を機能要件に落とすと：

### 7.1 必須プロファイル（最低4）

1. **MuseScore**  
   - 互換重視、一般記譜、比較的寛容なimport想定  
2. **Dorico**  
   - solo/section player、フロー構造、レイアウト再構築前提、クリーンな論理XML  
3. **Sibelius**  
   - Dolet系の実績ある方言、Magnetic Layout前提の事前整形Tipsをドキュメント化、マージン／リハーサル  
4. **Guitar Pro**  
   - タブ、bend/slide/PM、lyric extension、弦・フレット優先（五線の美しさより演奏情報）

### 7.2 横断オプション

- `strict` / `lossy-compat` / `archive`  
- `include-layout` on/off（onでもターゲットが捨てる可能性をUI警告）  
- `playback-companion-midi` 同梱  
- **変換レポート**（落とす要素・推定マッピング・要手修正リスト）

### 7.3 「やらないこと」の明示（失敗投稿から）

- 図形楽譜の完全XML化  
- 出版レイアウトの1:1保証  
- 「どのソフトでも同じ見た目」の宣伝  

---

## 8. 主要ソース一覧（X投稿）

| 投稿者 | 属性 | テーマ | Post ID（例） |
|--------|------|--------|----------------|
| @MichaelDGood | MusicXML発明者 | import競争、Dolet、フォーマットimport方針 | 1829580539537572008 等 |
| @dspreadbury | Dorico / Steinberg | MIDI vs MusicXML用途 | 1577940910461308929 |
| @viusmusic | 学生・作曲 | Dorico→Finale要素欠落地獄 | 1296621623131267072 |
| @TheRealTomahawk | 実務者 | Finale→Dorico formatting破壊 | 1828540672384659494 |
| @walkeri141 / @natehowe / @fannypackhq | ユーザー | 1:1否定、okay止まり、詳細喪失 | 2024-08 Finale終了スレ |
| @_rwgarvey | 実務 | 4段ホップ+Dolet | 1740559392976642231 |
| @ShikiSuen | 浄書/開発 | ensemble→solo誤認 | 1179077824969199617 |
| @yangyue992125 | 中文・製品視点 | 导出＝堀、错位 | 2066066602420781076 |
| @BrettRocks33 | タブ実務 | GP lyric extension欠落 | 2075284720771063843 |
| @takuyah | 音屋 | Dorico→Logic XML vs MIDI | 2078691801943445613 |
| @Avid / @AvidSibelius | ベンダー | XML import改善 | 1864067124211146900 |
| @flat_io | 製品 | 多ソフト向けXML export訴求 | 2077069446087077893 |
| @darcyjamesargue | 作曲家 | フォルダ一括XML | 1828850043664658526 |
| @hidetakumi | 浄書家（参考・日） | ソフト別XML再現性の相対評価 | 1828937721131462972 |
| @bathorykitsz | 現代音楽 | 図形楽譜でXML不可 | 1828092168680218845 |
| @robertpuff | 記譜ブログ | 8vb方言、Magnetic Layout freeze | 1252316619675594753 等 |

投稿URL形式: `https://x.com/{user}/status/{id}`

---

## 9. 調査上の注意・バイアス

1. **X上の記譜技術ディープトークは相対的に希少** — 深い議論はforum / Discord / W3C MusicXML CG / Scoring Notes に流出しやすい（GoodもW3Cディスカッションを案内）。  
2. **2024-08 Finale終了** で失敗談が一時的に増幅 — 構造問題は以前からだが、サンプルは偏る  
3. **ベンダー公式投稿は成功・改善の宣伝バイアス**  
4. **中国語の高密度技術スレは相対的に少なく**、「导出＝堀」「错位」といった**製品・ビジネス視点**が目立つ  
5. 本調査は **実投稿ベース**。ラボ計測の精度比較ではない

---

## 10. 一行で言うと

> **現場は「MusicXMLで移せる」ではなく「どの方言で、何を捨て、どのソフト向けに吐くか」で勝敗が決まる。**  
> 失敗談の大半は **レイアウト破壊・要素欠落・プレイヤー誤認・タブ奏法・1:1幻想** に集約され、  
> だからこそ **出力先ソフト別エクスポートプロファイル（方言吸収）** は機能ではなく **採譜ソフトの本丸の堀** として語られている。

---

必要なら次の深掘りもできます。

1. 上記を **機能仕様書（プロファイル定義表・マッピング表）** に落とす  
2. W3C MusicXML CG / MuseScore issue / Dorico forum まで広げた **二次調査**  
3. 失敗10類型を **テストケース一覧（acceptance criteria）** 化する
