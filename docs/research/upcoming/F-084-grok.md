# 記譜前MIDIクリーンアップ工程：X（旧Twitter）実投稿調査

**調査対象**: 量子化・音価整理・不要音削除を、記譜化（MuseScore / Dorico / Sibelius / Finale 等）の**前**に確定する工程  
**言語**: 英語中心、中国語（繁体含む）を可能な範囲で補完  
**方針**: 憶測を排除し、実投稿の主旨のみを記載。各知見に出典とアカウント種別を付記。

---

## 調査サマリー

| 軸 | 投稿密度（体感） | 主な当事者 |
|---|---|---|
| 成功例 | 中（ワークフロー共有が中心） | 映画/ゲーム作曲家、DAW実務者 |
| **失敗・限界・不満** | **高（最多）** | 作曲家、エンドユーザー、編曲者 |
| ベストプラクティス | 中〜高 | AAA/ゲーム作曲家、スコア準備担当 |
| 最新トレンド | 中（2024–2026に増加） | AI/Music AI開発者・研究者、ツール開発者 |

**横断的な合意（複数投稿で一致）**  
「記譜ソフト側で何とかする」より、**DAWでMIDIを先にクリーンアップしてから記譜に渡す**が実務標準。未量子化・keyswitch・演奏用データ混入・音源マッピング差が、譜面崩壊の主因として繰り返し語られる。

---

## 1. 成功例（ワークフローが機能した事例）

### 1-1. DAWで量子化 → Doricoで記譜
- **主旨**: Cubaseで作曲し、**MIDIを量子化してから** Doricoへ送りスコア化。MIDI cleanupは面倒なので **Doricoに入れる前にDAWで済ませる**のが最善。
- **出典**: [@sam_vandersluis](https://x.com/sam_vandersluis/status/1782516494720499892)（2024-04-22）
- **種別**: 実務者（ゲーム作曲家 / BAFTA Connect、Star Wars / Frozen 音楽部門経歴）

### 1-2. 演奏MIDIを再タイミングする専門工程（製品クレジット）
- **主旨**: キーボード録音の**MIDI cleanup / re-timing**を担当（Deltarune Chapters 3+4 サントラ）。反復負荷の高い「地味だが必須」の工程として明示。
- **出典**: [@Shadolith](https://x.com/Shadolith/status/1941222659989307495)（2025-07-04）、同 [フォローアップ](https://x.com/Shadolith/status/1931752828504007159)
- **種別**: 実務者（ゲーム音楽・MIDI/編曲支援）

### 1-3. チップ曲→楽譜：量子化＋ジャンクノート削除で完走
- **主旨**: Famitracker → WAV → FL Studio（Edison）→ **QUANTIZE** → **inevitable junk notes を削除**（portamentoが特に苦手）→ MIDI export → MuseScore。単純曲でも工数が大きく、複雑曲は恐れていると報告。
- **出典**: [@thehumanthomas](https://x.com/thehumanthomas/status/1235282723817877505)（2020-03-04）
- **種別**: 実務者（ゲーム音楽・サウンドデザイン）

### 1-4. 映画/ゲーム系：DAWクリーンアップ→記譜ソフトが標準
- **主旨**: DAWでMIDIをクリーンアップしてexport → Sibelius/Finale等へ。テンポは基本引き継がれるが、後述の落とし穴がある。テンプレートが非常に効く。
- **出典**: [@WilbertRoget](https://x.com/WilbertRoget/status/1357782930899169286)（2021-02-05）
- **種別**: 実務者（AAAゲーム作曲家：Helldivers 2, Mortal Kombat 等）

### 1-5. 音価と再生位置を分離する「Visual quantize」
- **主旨**: Cubaseの **visual quantize** は、**MIDIの再生位置を変えずに**スコア表示とMusicXML exportだけを整える。常用は「トラック複製してコピーを編集」。
- **出典**: [@GregNicolett](https://x.com/GregNicolett/status/1349407812296744960)（2021-01-13）
- **種別**: 実務者（ディズニー等の作曲家）

### 1-6. ドラム：量子化＋修正後にMuseScoreへ
- **主旨**: パッド録音 → 量子化・修正 → MIDI export → MuseScoreでドラム記譜に「期待する」ワークフロー。
- **出典**: [@RukyDeer](https://x.com/RukyDeer/status/1758873161326571877)（2024-02-17）
- **種別**: 実務者（作曲家）

---

## 2. 失敗例・限界・不満（重点）

### 2-A. 未量子化MIDIを記譜ソフトに入れた結果

| # | 知見（投稿主旨） | 出典 | 種別 |
|---|---|---|---|
| F1 | **「Sibeliusに量子化していないMIDIを入れた結果がこれ」** — 崩壊譜面のミーム/実体験として共有 | [@adelecomposer](https://x.com/adelecomposer/status/1478541341692870656)（2022-01-05） | 実務者（映画作曲・編曲、BAFTA） |
| F2 | 記譜は常に面倒。MIDIを記譜ソフトへ入れる前に **「quantize the heck out of it」** が必須 | [@BenElliottSound](https://x.com/BenElliottSound/status/1419392610234363906)（2021-07-25） | 実務者（サウンド/演奏系） |
| F3 | MuseScore 4：MIDI importが **「好き勝手にする」**。嫌なら自分でmessを直すしかない → **30分でアンインストール** | [@sd_katsu](https://x.com/sd_katsu/status/1767471427052277793)（2024-03-12） | エンドユーザー |
| F4 | MIDI→MuseScoreは可能だが **messy / 完璧ではない**。手動修正が必要 | [@JasaxJazz](https://x.com/JasaxJazz/status/2048731111908405441)（2026-04-27） | 実務者（クラシック作曲・プロデューサー） |
| F5 | 公式MIDIでも **MuseScoreがbig ol mess**。スキル不足で書き起こし不能と訴え | [@goopy_toots](https://x.com/goopy_toots/status/2039458719478501441)（2026-04-01） | エンドユーザー |
| F6 | 中文：**「直接把midi餵給MuseScore亂成一團」**（乱成一团）。ドラム・弦はまだマシ、**ギター/ベースは鬼畫符** | [@FXmjGA3uF5o8uyK](https://x.com/FXmjGA3uF5o8uyK/status/1965118545047765291)（2025-09-08） | 実務者（作曲/ボカロ/楽譜編曲委託） |

### 2-B. 量子化しても足りない／量子化の限界

| # | 知見 | 出典 | 種別 |
|---|---|---|---|
| F7 | 演奏が悪いと **量子化しても意図が読めない**（ピアノロール崩壊画像付き） | [@Komaniecki_R](https://x.com/Komaniecki_R/status/1625590645485195265)（2023-02-14） | 実務者/教育（音楽理論） |
| F8 | 量子化しても **まだoff beatに聞こえる**。制作が止まるレベルの不満 | [@MercuryInVirgo](https://x.com/MercuryInVirgo/status/1854351202315645378)（2024-11-07） | 学習者/制作者 |
| F9 | Dorico側での量子化は **「without success, it's a lot of work」**。Cubaseでトラック作成→Dorico量子化は失敗しやすい | [@eliseufg7](https://x.com/eliseufg7) の返信スレ内（[@sam_vandersluis](https://x.com/sam_vandersluis/status/1782516494720499892) 会話、2024-04-22） | 実務者（作曲・編曲・オーケストレーション） |
| F10 | MIDI cleanup自体が **arduous（骨の折れる作業）**。AIは芸術生成よりこの tedium/QoL に使うべき | [@atelierjoshua](https://x.com/atelierjoshua/status/2018568424180347169)（2026-02-03） | 実務者（ゲーム/商業プロデューサー） |

### 2-C. 演奏用MIDIと記譜用MIDIの構造的不一致

| # | 知見 | 出典 | 種別 |
|---|---|---|---|
| F11 | MIDI cleanup必須の理由：**keyswitches と performance 情報が記譜ソフトに翻訳されない** | [@cellobuddy](https://x.com/cellobuddy/status/1991517376106676727)（2025-11-20） | 実務者（編集/制作寄り） |
| F12 | Finale転送前にMIDI cleanupしないと **bizarre keyswitches** と **inhumane rhythms/rests** が見える | [@faaatsawmusic](https://x.com/faaatsawmusic/status/1451917252127694856)（2021-10-23） | 実務者（ゲーム/アニメ系作曲） |
| F13 | 落とし穴：**keyswitches、アーティキュレーショントラック統合、tempo conversion errors** | [@WilbertRoget](https://x.com/WilbertRoget/status/1357782930899169286) | 実務者（AAA作曲） |
| F14 | Sibelius 2019.9 の「omit keyswitches」相当を **Doricoにも欲しい**（開発者への要望） | [@ShikiSuen](https://x.com/ShikiSuen/status/1174727106787344384)（2019-09-19） | 実務者＋開発者寄り（浄書・作曲・Mac開発、日英中） |

### 2-D. 不要音・変換アーティファクト・マッピング

| # | 知見 | 出典 | 種別 |
|---|---|---|---|
| F15 | オーディオ解釈→MIDIでは **junk notes が不可避**。portamentoが特に壊れる | [@thehumanthomas](https://x.com/thehumanthomas/status/1235282723817877505) | 実務者 |
| F16 | AD2→GMマッピング変換後のMuseScoreドラム譜が **「really fucking messy」**（単純曲なのに） | [@meelzcore](https://x.com/meelzcore/status/1699804169857806459)（2023-09-07） | 実務者（YouTube音楽 / QA） |
| F17 | MuseScore 4のドラム記譜が使いにくい。**MIDI/XML import + 転調**で特に苦痛。ドラム修正だけで **2時間** | [@ruviyamin](https://x.com/ruviyamin/status/1707289205234422102)（2023-09-28、マレー語混じり英語） | 実務者（作曲・サウンドデザイン） |
| F18 | Dorico：MIDI録音で **音価と休符を記録してくれない**（1キー押し=1音固定）への不満 | [@rolanberrypie](https://x.com/rolanberrypie/status/1834000029352157331)（2024-09-11） | エンドユーザー/実務寄り |
| F19 | MuseScore生成MIDI → Logic で **BPMが1拍ずれる** 問題報告（方向は逆だが、MIDI↔記譜往復のテンポ不整合） | [@DeltonDing](https://x.com/DeltonDing/status/1250037445397073920)（2020-04-14） | 中国語話者ユーザー |

### 2-E. 機能ギャップとしての「不満の言語化」

| # | 知見 | 出典 | 種別 |
|---|---|---|---|
| F20 | 欲しい機能：**楽器・スタイルに合わせた musical/intelligent quantization**、より良いtempo envelope | [@agomarmusic](https://x.com/agomarmusic/status/1795080068575662443)（2024-05-27） | 実務者（ゲーム作曲） |
| F21 | スコアエディタは美しいが **「もちろんMIDIを先にcleanupすべき」**（現状の前提条件としての負担） | [@HeoMusic](https://x.com/HeoMusic/status/1947015029842137329)（2025-07-20） | 実務者（DTM/オーケストラ） |
| F22 | スコア準備/MIDI cleanupを他人の作曲に対して行う専門的な雑務として存在 | [@creativegeek](https://x.com/creativegeek/status/2016910970753356190)（2026-01-29） | 実務者（作曲/スコア準備） |

---

## 3. ベストプラクティス（投稿から抽出できる手順）

> 以下は「複数の実務投稿で明示された手順・原則」のみ。一般論の補完はしない。

### BP-1. 場所の原則：**記譜ソフトの前にDAWで片付ける**
- Cubaseでquantize → Dorico（@sam_vandersluis）
- DAW cleanup & export → Sibelius/Finale（@WilbertRoget）
- 「MIDI cleanup is tedious → clean in DAW before Dorico」（@sam_vandersluis）
- Finale前にkeyswitch/異常リズムを除去（@faaatsawmusic）

### BP-2. 工程の分解（チップ/オーディオ起点）
@thehumanthomas の明示手順：
1. チャンネル単位でWAV export  
2. DAWでピッチ解釈→ピアノロール  
3. **QUANTIZE**  
4. **junk notes削除**（portamento対策）  
5. MIDI → MuseScore  

### BP-3. 演奏品質と記譜品質の二系統を分ける
- **Visual quantize / トラック複製編集**で、グルーヴ用MIDIと譜面用MIDIを分離（@GregNicolett）
- 演奏用データ（keyswitch, CC, performance）は記譜に持ちこまない（@cellobuddy, @WilbertRoget, @faaatsawmusic）

### BP-4. テンプレートとマッピングを先に決める
- きれいなスコアテンプレートが「TON」効く（@WilbertRoget）
- ドラムはGM/非GMマッピング差が譜面を壊す（@meelzcore）
- 開発側要望：keyswitch omit の記譜インポート（@ShikiSuen）

### BP-5. 改訂時の作業リズム
- 難しいcueは **セクション分割** → mockupを聴きながらMIDIをclean → 短休憩で視点リセット（@PenkaKouneva, 2024-10-04）
- **種別**: 実務者（映画/商業作曲家）

### BP-6. 中国語圏で共有された周辺フロー（オーディオ→MIDI→譜）
- ステム分離 → Basic Pitch でMIDI → MuseScoreで編集、またはAnthemScore一括。**単轨の方が混音より精度が高い**（@grok 回答投稿 [2061711763398090880](https://x.com/grok/status/2061711763398090880)、2026-06-02）
- ※これはAIボットの回答投稿であり、人間実務者の一次体験ではない点に注意（「実投稿」ではあるが出典強度は弱）

---

## 4. 最新トレンド / 新手法（2024–2026中心）

| トレンド | 投稿上の内容 | 出典 | 種別 |
|---|---|---|---|
| **フルミックス Audio→MIDI（多楽器分離）** | MuScriptor：完成ミックスから楽器別MIDI、コード/キー/テンポ検出。stem不要を売りに | [@MireloAI](https://x.com/MireloAI/status/2075536492177354771)（2026-07-10, Kyutai Labs共同） | 開発者/製品 |
| **モデルの限界の公開検証** | 5秒スペクトログラムをトークン化し onset/offset 等を読む。**何を保ち・分類し・落とすか**を論じる | [@sonic_field](https://x.com/sonic_field/status/2078880397920731383)（2026-07-19） | メディア/音響文化 |
| **MIDI cleanupをAIの「正しい用途」とみなす** | 生成アートより **MIDI cleanupの tedium 解決**に使え、という現場からの反転提案 | [@atelierjoshua](https://x.com/atelierjoshua/status/2018568424180347169) | 実務者 |
| **検出MIDIの後処理としてのcleanup** | Stem→MIDI後の **「offに聞こえる検出ノート」のcleanup** をコア機能候補に列挙 | [@promptsurfer](https://x.com/promptsurfer/status/1850648835032506735)（2024-10-27） | ユーザー/構想 |
| **Intelligent / style-aware quantize 需要** | 楽器・スタイル依存の「本当に音楽的な量子化」への機能要求 | [@agomarmusic](https://x.com/agomarmusic/status/1795080068575662443) | 実務者 |
| **MIDIを「可編集な音楽プログラム」に逆コンパイル** | Decomposer：MIDI → Strudel コード（pattern/harmony/rhythm/voice を露出） | [@haiyewon](https://x.com/haiyewon/status/2075069360478331335)（2026-07-09, CMU Music AI） | 研究者 |
| **楽譜OCR / 専用小モデルへのオフロード** | FrankenOCR：sheet music → MusicXML 等を専用モデルで、LLMコスト回避 | [@doodlestein](https://x.com/doodlestein) / 中文紹介 [@li9292](https://x.com/li9292/status/2074429132159484313)（2026-07） | 開発者 / 中国語テック発信 |
| **中国OSS：楽譜含む複雑文書パース** | Logics-Parsing V2：楽譜・フローチャート等のParsing 2.0 | [@hongming731](https://x.com/hongming731/status/2034850400885776671) 等（2026-03） | テック発信（OCR寄り。MIDIクリーンアップ本体ではない） |

**読み取り（投稿ベースの傾向のみ）**  
- 上流（Audio→MIDI）の自動化は急加速。  
- しかし現場投稿はなお **「検出後/演奏後のクリーンアップがボトルネック」** と述べる。  
- 需要の重心は「全部自動で完璧な譜」より **tedious cleanup の半自動化・楽器別インテリジェント量子化・keyswitch除外**。

---

## 5. 中国語投稿の位置づけ（調査上の制約）

- 「MIDI量化＋记谱/制谱」を直撃する**高エンゲージ実務連投は英語圏に比べ希薄**。
- それでも実務に直結する一次声として有力なのは：
  - **乱成一团 / 鬼畫符**（@FXmjGA3uF5o8uyK）— 楽器依存の失敗差（ドラム・弦 vs ギター/ベース）
  - **BPM 1拍ずれ**（@DeltonDing）— 往復変換のテンポ問題
  - Dorico利用の確認質問（@rcwoad）— 譜→MIDIか再制作MIDIかの関心
- 「量化」単独検索は**金融クオンツ/モデル量子化**に汚染されやすく、音楽文脈のヒット率が低い（調査ノイズとして明記）。

---

## 6. 機能設計への示唆（投稿から帰納できる要件案）

**投稿が繰り返し示唆する「記譜前確定」チェックリスト**（出典は上表に紐づく）：

1. **タイミング量子化**（未実施＝譜面崩壊の定番：F1, F2, BP-1）  
2. **音価/休符の人間可読化**（inhumane rhythms/rests：F12）  
3. **不要音削除**（junk / 検出誤検出 / portamento残骸：F15, F10）  
4. **keyswitch・演奏専用ノートの除外**（F11–F14）  
5. **アーティキュレーショントラック統合**（F13）  
6. **テンポマップ整合**（conversion errors, BPMずれ：F13, F19）  
7. **ドラム等のノートマップ正規化**（F16, F17）  
8. **可能なら再生MIDIと記譜MIDIの二系統**（BP-3, visual quantize）  
9. **記譜側での「後から量子化」に依存しない**（F9）  
10. **楽器・スタイル条件付きの smart quantize が未充足の要望**（F20）

---

## 7. 出典インデックス（主要ポスト）

| アカウント | 種別 | 代表投稿ID / 日付 | 軸 |
|---|---|---|---|
| @sam_vandersluis | ゲーム作曲家 | 1782516494720499892 / 1782517168875151787 (2024-04) | 成功・BP |
| @WilbertRoget | AAA作曲家 | 1357782930899169286 (2021-02) | BP・失敗 |
| @adelecomposer | 映画作曲 | 1478541341692870656 (2022-01) | 失敗 |
| @faaatsawmusic | ゲーム作曲 | 1451917252127694856 (2021-10) | 失敗・BP |
| @thehumanthomas | ゲーム音響 | 1235282723817877505 (2020-03) | 成功・失敗・BP |
| @GregNicolett | 映画/ゲーム作曲 | 1349407812296744960 (2021-01) | 成功・BP |
| @Shadolith | ゲーム音楽支援 | 1941222659989307495 (2025-07) | 成功 |
| @sd_katsu | エンドユーザー | 1767471427052277793 (2024-03) | 失敗 |
| @meelzcore | 音楽制作者 | 1699804169857806459 (2023-09) | 失敗 |
| @ruviyamin | 作曲/SD | 1707289205234422102 (2023-09) | 失敗 |
| @FXmjGA3uF5o8uyK | 作曲/編曲（中文） | 1965118545047765291 (2025-09) | 失敗 |
| @atelierjoshua | 商業/ゲーム音響 | 2018568424180347169 (2026-02) | 失敗・トレンド |
| @agomarmusic | ゲーム作曲 | 1795080068575662443 (2024-05) | 不満・要望 |
| @ShikiSuen | 浄書/開発 | 1174727106787344384 (2019-09) | 要望 |
| @MireloAI / @sonic_field | 製品/メディア | 2026-07 | トレンド |
| @haiyewon | 研究者(CMU) | 2075069360478331335 (2026-07) | トレンド |
| @PenkaKouneva | 映画作曲家 | 1842294151909421205 (2024-10) | BP |

---

## 8. 調査限界（正直な注記）

1. **英語の実務声が圧倒的に豊富**。中国語は「乱成一团」「鬼畫符」「BPMずれ」など有用一次投稿はあるが、英語ほど体系的なスレッドが少ない。  
2. 「quantize」はDJ/CDJ/LLM量子化と語が衝突し、ノイズ除去が必須だった。  
3. 高エンゲージの「譜面崩壊」投稿はミーム（@ThreatNotation 引用など）と実務が混在。本報告は**本人の実務宣言がある投稿を優先**した。  
4. 記譜ソフト**公式アカウント**による「クリーンアップウィザード」の詳細解説投稿は、今回の検索窓ではほぼ捕捉できず、**ユーザー側の痛みとワークアラウンド**が主データ源。

---

### 結論（投稿群が示す一点）

X上の実務者言説はほぼ一方向に収束する：

> **記譜化の品質は、記譜エンジンより「記譜前にMIDIを人間の意図として確定できたか」で決まる。**  
> 未量子化・keyswitch・ジャンクノート・マップ不一致を記譜側に持ち込むと、修正コストが爆発する。  
> 最新AIはAudio→MIDIを前進させたが、**cleanup tedium 自体は未解決のコア問題**として残り、むしろAIの本命用途として現場から名指しされている。

---

※作業ログ用Slack（#倉田_ログ）は本環境にSlack連携（MCP/CLI）が無く投稿不可でした。接続後に再送可能です。
