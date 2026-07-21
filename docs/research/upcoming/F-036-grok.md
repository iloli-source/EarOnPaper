# ドラム譜記譜（Percussion Clef / Unpitched / キット音色マップ / MusicXML Percussion）  
## X（旧Twitter）実務者・研究者・開発者投稿 調査レポート

**調査日:** 2026-07-21  
**対象:** X上の実投稿（英語中心＋中国語／日本語の実務ポスト補完）  
**範囲:** 採譜／記譜ソフトの**ドラム譜機能**に関する成功・失敗・限界・BP・トレンド  
**注意:** X上で「MusicXML percussion 仕様」そのものを深く議論する英語・中国語ポストは**希少**。議論の中心は **(1) 入力UXの苦痛 (2) MIDI/キットマップのズレ (3) 再生・ノートオフ (4) 交換フォーマットの限界 (5) AI自動採譜の期待** に寄っている。

---

## 1. エグゼクティブサマリー

| 観点 | X上の実務者コンセンサス（要約） |
|------|----------------------------------|
| **Percussion / Neutral clef** | 概念は広く理解されている（無固定音高＝譜線位置が音色ID）。問題は clef 自体より **位置・符頭・奏法記号の非標準化** |
| **Unpitched note** | 記譜理論上は「難しくない」との作曲家意見もあるが、**ソフト実装と交換（MIDI/MusicXML）で崩れる** |
| **キット音色マップ** | **最大の失敗源**。GM／DAW／記譜ソフト／VST がそれぞれ別マップ。手作業マップ or 変換プラグインが定番回避策 |
| **MusicXML percussion** | **カスタムパーカッションマップは通りにくい**。交換の「最低限の骨格」止まりになりやすい |
| **入力UX** | MuseScore の perc 入力批判が特に強い（改善期待も大きい）。Sibelius は速いが重い／有料 |
| **最新トレンド** | 専用 perc パネル刷新、AI audio→MIDI→譜面、軽量ドラム専用アプリ、練習アプリの MusicXML 読込 |

**一言で言うと:**  
「ドラム譜は**見た目の五線**より、**位置＝音色＝MIDIノート＝再生サンプル＝MusicXML unpitched** の**4〜5層マップ**が壊れる問題」として語られている。

---

## 2. 機能別：実投稿で見えた論点

### 2.1 Percussion Clef / Neutral Clef

**成功・教育的説明**

- 英語の用語解説アカウントが、neutral clef を「確定ピッチを持たない楽器用。1〜5線、線／間に楽器を割り当てる」と整理。# ドラム譜記譜機能調査レポート  
**対象:** percussion clef / unpitched note / キット音色マップ / MusicXML percussion  
**情報源:** X（旧Twitter）実務者・研究者・開発者投稿（英語中心＋中国語／参考として日本語）  
**調査日:** 2026-07-21  

---

## 1. 要約

X上の実務会話を横断すると、**ドラム譜は「五線譜の特殊ケース」ではなく、譜面表現・再生・交換フォーマットの三重の意味付けがズレる問題**として語られている。

| 軸 | 現場の実感 |
|---|---|
| **percussion clef / neutral clef** | 概念は広く共有。OMR・教育・ポップカルチャーでも認知が進む |
| **unpitched** | 「譜に書く」は可能。だがソフト間の**意味付けと再生**が崩れる |
| **キット音色マップ** | 最大の摩擦点。GM / DAW / 各記譜ソフトで座標系が違う |
| **MusicXML percussion** | 「運ぶ箱」はあるが、**カスタムマップや電子音・舞台指示が落ちる** |

**失敗談の密度が突出して高い。** 成功例の多くは「公式機能が完璧」ではなく、**Pitch Mapプラグイン／自作MIDI変換／GM前提インポート**といった**迂回ワークフロー**である。

---

## 2. 調査方法と限界

- 検索軸: `MusicXML + percussion/drum`、`MuseScore/Dorico/Sibelius + drum input/map`、`percussion clef / unpitched`、中文 `鼓谱/打击乐/五线谱` など  
- 偏り: Xは**不満・バグ・ワークアラウンド**が過剰表現されやすい。論文・仕様書級の厳密さは期待しない  
- 中文: **開発者の深い技術議論は少なく**、学習者・教育・用語解説が多い。キットマップ／MusicXMLの失敗談は**英語＋日系実務**に寄る  

---

## 3. 機能軸ごとの現場像

### 3.1 Percussion clef（中立譜号 / 打击乐谱号）

**成功・普及側**

- OMR製品 **PlayScore 2** が MusicXML 出力改善とともに **Percussion clef 対応**をリリース告知（認識・再生・エクスポート一式の延長線）。
- 教育・一般説明: neutral clef は「確定音高を持たない楽器のリズム記譜」であり、線／スペースが **特定のドラム／シンバルに対応**する、という実務説明が英語で繰り返される。
- 中文圏では「percussion clef = 打击乐谱号 / 无固定音高谱号」と定義する投稿があり、用語の**ローカル翻訳は定着しつつある**。

**限界**

- 譜号自体は「無音高」を示す記号にすぎず、**どの線が snare / kick / hi-hat か**はソフト／出版社／ジャンル規約依存。  
- 中文学習者側では「五线谱を見た瞬間に怖がる」「节奏跟不上」など、**記譜言語のコスト**が先に立つ。

---

### 3.2 Unpitched note（無固定音高）

**理論上は「書ける」**

- 作曲家 Aaron Lee: Xenakis 等の例を挙げ、**unpitched 材料それ自体は記譜の本質的障壁ではない**と指摘。
- Dorico ユーザーが XML 上の `<pitch>` / `<unpitched>` タグを数えて分析する例があり、**MusicXML 上では unpitched が一次市民**であることは実務でも意識されている。
- Dorico 4.2 で unpitched percussion 向け機能強化が話題に（「DAW in notation」への温度差はあるが、リスト編集の利便は評価）。

**失敗・摩擦**

- Sibelius → MuseScore 移行者が、**unpitched percussion のシステム差**で「書き直し／直し方の再学習が必要」と明言。他声部は移行できても打楽器が最後の地雷になる、という構図。
- つまり **unpitched は「概念の問題」ではなく「ソフト固有のキット／グリッド表現の問題」**として噴出する。

---

### 3.3 キット音色マップ（percussion / drum map）

**ここが失敗例の主戦場。**

#### 失敗・苦痛

1. **MIDI インポートで自作 percussion map が地獄**  
   Dorico 利用者: *「midi import into dorico sucks ass if you have to make your own percussion map」*。

2. **MusicXML 経由で custom percussion map が落ちる**  
   室内オペラ級スコアで舞台指示・電子音・**custom percussion map** を MusicXML で運ぼうとして **失敗**（「That didn't work thru musicxml」）。大きなスコア向きソフト自体は評価しても、**交換経路がボトルネック**。

3. **譜面上の位置と再生音が一致しない**  
   日本語圏の作曲実務: 再生モードで楽器設定はできるが、**置きたい音符位置と鳴らしたい音が一致しない**ため、音源側の打楽器キット設定が必要、という指摘。

4. **MuseScore のドラム入力 UX が「最悪」級**  
   - *「worst perc note input ever conceived」*（軽量ノート用に Sibelius の速さは欲しいが PC が重い／MuseScore は打楽器入力が最悪）。  
   - *Finale と Sibelius の最悪部分を混ぜて自前の slop を足したよう*で、**1音にクリックとキー操作が5回**。  
   - 期待側: 「MuseScore 4.5 の percussion update が救い」という返信（後に 4.5 で percussion panel が実装報道）。

5. **UI 退行の体感**  
   Mac 上で percussion view が巨大化し、**ノートクリックのたびに出て閉じられない**という苦情。

6. **ノート長・Note Off が無視される再生モデル**  
   MuseScore / Dorico とも、打楽器で **note-on は来るが note-off を尊重せず音源のフル長を鳴らす**、という報告。表記と再生のセマンティクス乖離。

7. **音色バリエーション不足**  
   frame drum / hand drum など、**鍵盤上のノート数より奏法が多い**のにソフト側音色が足りない、という要望。

8. **品質の悪い「MIDI→総譜」サービス**  
   中文ユーザー（作曲実務）: 高額で MIDI 転写したバンド総譜が、**鼓譜に升降号が付き、譜面エラーだらけ**——「外围产业」への怒り。  
   → **ピッチ付き声部の記法を unpitched ドラムに誤適用**した典型失敗。

9. **MIDI を MuseScore に食わせると乱れる／でもドラムはまだマシ**  
   中文: *「直接把 midi 餵給 MuseScore 亂成一團但鼓比較好整理」*（ギター／ベースは「鬼画符」）。ドラムでも**手動整理前提**。

10. **DAW 側のキー割当ラベルが保存されない**  
    FL Studio 更新で **どの percussion がどのキー／オクターブか**のラベルがプリセット保存で消える——「キットマップ」の**隣接領域**でも同じ認知負荷。

#### 成功・迂回（ベストプラクティスの原型）

| パターン | 内容 | 出典 |
|---|---|---|
| **Sibelius + Percussion Pitch Map** | FL Studio 等のドラム MIDI を一括で譜面位置へ。*「最強」* | 日本語実務 [@2d_m_t](https://x.com/2d_m_t/status/1816823178922250401) |
| **EZ Drummer 向け Pitch Map** | Studio One → MIDI → Sibelius で「ちょっと手直し」で綺麗なドラム譜 | [@xRYO_SUKEx](https://x.com/xRYO_SUKEx/status/1227748507710214144) |
| **自作 MIDI 変換器 → MuseScore** | DAW のドラム MIDI が MuseScore でドラム譜にならないので**変換ソフト自作** | [@nyoro_wrl](https://x.com/nyoro_wrl/status/2009547599054028843) |
| **Dorico GM インポート変換** | GM 標準音名の MIDI を **Dorico 式（F4=Kick, C5=Snare 等）に自動変換**（便利だが stem 向きはデフォルト下向き等の妥協） | [@k1oku](https://x.com/k1oku/status/2016403420627059132) |
| **公式 percussion map の二段構え** | Dorico 側: (1) Edit Percussion Playing Techniques で符頭／奏法 (2) Play > Percussion Maps で音色対応——**記譜と再生を明示的に分離して定義** | Daniel Spreadbury [@dspreadbury](https://x.com/dspreadbury/status/1098230169695858689) |
| **カスタム percussion grid** | 特定線・ギャップのグリッドを Edit Percussion Kit で自作 | [@dspreadbury](https://x.com/dspreadbury/status/1353391228470128644) |
| **MuseScore MIDI Tips** | CH10、ゴーストを別ピッチで一括小音符化、open HH を選択→記号→位置を close に合わせる | [@NUSH06](https://x.com/NUSH06/status/1487837662581248000) |

**含意:** 成功は「ソフトが賢い」より **マップを資産として固定し、パイプラインに載せる**こと。

---

### 3.4 MusicXML percussion

**成功・進展**

- PlayScore 2: 認識改善と **MusicXML export**、Percussion clef 対応を同時に打ち出す——OMR → 交換フォーマットの線。  
- 練習アプリ **Drumr**: キット／マーチング snare・tenors・bassline スコアを **MusicXML インポート**し、無音 follow-along 練習に使う、という製品訴求。  
- Dorico ユーザーが XML の `<unpitched>` を機械集計——**交換層に unpitched が載っている**ことの実務利用。  

**失敗・限界（実投稿ベース）**

1. **カスタム percussion map が MusicXML で運ばれない**（前述・室内オペラ）。  
2. 公式側の約束と現場: Dorico は flexible percussion / map を強みとして訴求するが、**外部から「全部そのまま」は入らない**。  
3. MusicXML は「音高／無音高／譜号」は運べても、**DAW 固有キット・奏法レイヤ・電子音記譜・DTP 的配置**は欠損しやすい——失敗は「パースエラー」より **意味の半減**として語られる。  

---

## 4. 失敗例カタログ（厚め）

| # | 失敗モード | 誰が | 何が起きるか | 出典 |
|---|---|---|---|---|
| F1 | **入力コスト爆発** | ドラマー実務 | 1音に多数操作；「最悪の perc input」 | [burningssbm](https://x.com/burningssbm/status/1828506869154902171) |
| F2 | **軽量環境が無い** | スタジオ下書き | 紙は湿気でダメ、Sibelius は重く有料、MuseScore 入力が使えない | [burningssbm](https://x.com/burningssbm/status/1808514766849118643) |
| F3 | **MIDI→マップ自作地獄** | Dorico ユーザー | 自作 percussion map 前提の MIDI import が最悪 | [Rurakay](https://x.com/Rurakay/status/1936938720378388738) |
| F4 | **MusicXML でカスタムマップ喪失** | 作曲家 | 舞台指示・電子音・custom map が落ちる | [MichaelZapruder](https://x.com/MichaelZapruder/status/1286747013154058240) |
| F5 | **譜位置 ≠ 再生音** | 作曲／編曲 | 見た目と音源キットが噛み合わない | [0608be_](https://x.com/0608be_/status/2062200880829726951) |
| F6 | **Note length / note-off 無視** | MuseScore & Dorico | 表記の長さと発音が一致しない | [DavkasPlays](https://x.com/DavkasPlays/status/1854317157196181845) |
| F7 | **MIDI 一括投入で乱譜** | 中文制作 | 全体が乱れる；ドラムは相対的にマシだが手直し必須 | [FXmjGA3uF5o8uyK](https://x.com/FXmjGA3uF5o8uyK/status/1965118545047765291) |
| F8 | **外注 MIDI→総譜の品質事故** | 中文作曲 | 鼓譜に升降号、誤り多数、高額 | [LinningInMono](https://x.com/LinningInMono/status/1936114696488468699) |
| F9 | **ソフト間 unpitched モデル差** | 編曲家 | Sibelius から MuseScore で打楽器だけ再学習 | [MastachiJoshua](https://x.com/MastachiJoshua/status/1588398589859876864) |
| F10 | **MIDI import 後の符幹方向** | MuseScore | 手打ちは自動分離、MIDI 変換だと hat/snare と kick の幹がまとまる | [sai31saiha](https://x.com/sai31saiha/status/1388771578536620034) |
| F11 | **地域記譜体系の衝突** | 学習者 | 韓国式ドラム記譜が嫌で MuseScore で写譜中に「死にそう」 | [dead_vape_maree](https://x.com/dead_vape_maree/status/1926282265836835033) |
| F12 | **教育の前提ブレ** | 中文学習 | 「リズムだけ覚えれば譜は不要」→欠席で五线譜授業、意味不明 | [L7zYhtSJ8hWZmNp](https://x.com/L7zYhtSJ8hWZmNp/status/2029034320309215362) |
| F13 | **UI 回帰** | Mac ユーザー | percussion view が巨大・常時表示 | [peterpeter1651](https://x.com/peterpeter1651/status/1904031560224870593) |
| F14 | **音色スロット不足** | 奏者 | フレームドラム等の奏法 > ノート数 | [bstinso3](https://x.com/bstinso3/status/1983346132572103012) |

**横断パターン**

1. **座標系の非互換**（GM / ソフト固有 / DAW キット）  
2. **記譜セマンティクスと再生セマンティクスの二重管理**  
3. **交換フォーマット（MusicXML/MIDI）が「半分だけ正しい」**  
4. **入力 UX が pitched 声部の延長で設計され、unpitched に最適化されていない**  
5. **地域・ジャンル記譜規約の多様性をソフトが吸収しきれない**  

---

## 5. 成功例・ベストプラクティス（投稿から抽出）

### 5.1 製品・ワークフロー成功

- **Dorico GM MIDI インポートの自動キット変換**（音名→Dorico 式位置）は「便利」と明示評価。ただし stem 規約は妥協。  
- **Sibelius Percussion Pitch Map** で DAW→譜面の一括正規化。  
- **MuseScore 4.5 新 percussion panel** が FOSS コミュニティで報道され、長らく批判されていた入力層への応答と見なされている。  
- **PlayScore 2** の OMR + percussion clef + MusicXML。  
- **Drumr** の MusicXML インポート練習。  
- プロドラマー（Luke Holland 等）はソフト議論より **PDF/.gp 納品の転写品質**で価値を出す——「記譜エンジン」より **完成譜の正確さ**が市場価値。  

### 5.2 実務 BP（投稿の「うまくいった人」が共通してやっていること）

1. **マップを先に固定**（GM か、DAW キットか、Sibelius/Dorico テンプレか）  
2. **MIDI は CH10 / キット正規化後に記譜ソフトへ**  
3. **MusicXML は「骨格」用。カスタム奏法・舞台指示はネイティブ形式で持つ**  
4. **記譜（符頭・線位置・奏法）と再生（percussion map / VST）を二層で編集**（Dorico 公式説明と同型）  
5. **ゴースト／open HH は別 MIDI ピッチで打ってから一括整形**（MuseScore Tips）  
6. **外注 MIDI→譜は unpitched 規約を契約書に書く**（升降号事故の予防）  

### 5.3 記譜哲学側

- unpitched 自体は「書ける」。問題は **ソフトウェア・交換・教育の摩擦**  
- スイス rudimental では **Bravura フォントの flam / doublé グリフ**が Dorico 5 で改善、と engraver 寄りの成功談。  
- 現代記譜 engraver は MuseScore の **規則の緩さ**を評価（ただし drum input 改善は別トラック）。  

---

## 6. 限界（投稿が合意する天井）

| 限界 | 説明 |
|---|---|
| **規約の非標準** | キット線配置は出版社／ジャンルで揺れる。GM は再生の近似であって記譜の世界標準ではない |
| **MusicXML の表現力** | unpitched 要素はあるが、**完全なキット定義・奏法・電子音・レイアウト**は運べない場面が多い |
| **再生モデル** | 打撃音は「音価＝発音長」と一致しないことが多い |
| **入力 UX** | pitched 五線のメタファーが unpitched にそのまま載ると破綻 |
| **自動転写（AI）** | 需要は巨大（「スティックのグルーヴを即座に classical drum notation / MusicXML に」）だが、**キット意味付け・記譜規約までは未解決** |
| **教育格差** | 中文圏では「譜を見ないリズム教育」と「突然の五线谱」が衝突 |
| **地域記譜** | 韓国式など非西洋キット記法との dual system が写譜コストを跳ね上げる |

---

## 7. 最新トレンド（2024–2026 付近の X 観測）

1. **記譜ソフトの percussion UI 刷新**  
   MuseScore 4.5 percussion panel、Dorico の percussion editor 改善・unpitched 強化の系譜。

2. **「マップ資産」エコノミー**  
   Pitch Map プラグイン、自作 MIDI 変換、GM→ソフト固有変換——**個人がツールを書く時代**。

3. **MusicXML を「練習アプリ入口」にする**  
   Drumr 等、出版総譜ではなく **モバイル練習**へのブリッジ。

4. **AI: audio→MIDI は急加速、audio→正しいドラム譜はまだ**  
   全ミックスから drums 等を分離 MIDI 化するモデル（MuScriptor / Mirelo 等）がバズる一方、  
   **五線上の unpitched 配置・MusicXML percussion 規約・出版社スタイル**への橋は薄い。  
   「Grok にパッドを叩かせて classical drum notation / MusicXML」は**願望ツイート**として存在。  

5. **AI ビート生成 vs 記譜神器**  
   中文スレで「AI ドラム生成が MuseScore を殴る」vs「MuseScore は管弦総譜の神器で別レース」という**用途分離**が明示。  

6. **OMR の percussion clef 対応**は「紙のドラム譜→デジタル」需要の継続を示す。

---

## 8. 中文投稿の位置づけ

| タイプ | 内容 | 示唆 |
|---|---|---|
| 用語解説 | percussion clef＝打击乐谱号 | 概念の普及は進む |
| 学習感情 | 五线鼓谱に恐怖、眼睛赶不上节奏 | **可読性 UX** が未解決 |
| 教育失敗 | リズム暗記 vs 突然の五线谱 | ソフト以前の **教授法ギャップ** |
| 制作事故 | MIDI 転写に升降号、MIDI→MuseScore 混乱 | **マップ／unpitched 無理解**が商用事故に |
| 成功感情 | 「直接会看架子鼓的五线谱了」 | 一度マップが頭に入れば読める |

**深い MusicXML / kit map 開発議論は中文 X では希薄**。失敗の「質」は英語・日系実務の方が仕様に近い。

---

## 9. プロダクト／研究への示唆（投稿からの帰納）

1. **キットマップを第一級オブジェクトに**（インポート・エクスポート・編集・共有）  
2. **MusicXML で percussion キット定義をロスレスに近づける**か、**付随マニフェスト**を標準化  
3. **入力は pitched 五線の流用を捨て、パッド／リスト／ワンキー＝1楽器**をデフォルトに  
4. **記譜と再生のセマンティクスを UI 上で常に並置**（「この線＝この MIDI ノート＝この音」）  
5. **AI 転写の評価指標に「譜面規約適合」を入れる**（onset 精度だけでは足りない）  
6. **地域記譜（韓国式等）の dual map**  
7. **ゴースト／open-close HH／リム**など、実務が毎回手で直しているパターンのプリセット化  

---

## 10. 主要出典一覧（実投稿）

| 投稿者 | 役割感 | トピック | リンク |
|---|---|---|---|
| @burningssbm | ドラマー | MuseScore perc input 最悪／軽量ソフト願望 | [1828506869…](https://x.com/burningssbm/status/1828506869154902171) / [1808514766…](https://x.com/burningssbm/status/1808514766849118643) |
| @Rurakay | 制作 | Dorico MIDI + 自作 map 地獄 | [1936938720…](https://x.com/Rurakay/status/1936938720378388738) |
| @MichaelZapruder | 作曲 | MusicXML で custom percussion map 失敗 | [1286747013…](https://x.com/MichaelZapruder/status/1286747013154058240) |
| @dspreadbury | Dorico PM | percussion map / kit / techniques 手順 | [1098230169…](https://x.com/dspreadbury/status/1098230169695858689) 他 |
| @DavkasPlays | 音楽家 | note-off 無視（MS/Dorico） | [1854317157…](https://x.com/DavkasPlays/status/1854317157196181845) |
| @PlayScoreMusic | OMR 開発 | Percussion clef + MusicXML | [1318142564…](https://x.com/PlayScoreMusic/status/1318142564478951425) |
| @MastachiJoshua | 編曲 | unpitched が移行の最後の壁 | [1588398589…](https://x.com/MastachiJoshua/status/1588398589859876864) |
| @xpagescorella | 作曲 | XML `<unpitched>` 集計 | [1565583763…](https://x.com/xpagescorella/status/1565583763287015424) |
| @FredrikHathen | ユーザー | Dorico 4.2 unpitched percussion | [1554409440…](https://x.com/FredrikHathen/status/1554409440178315264) |
| @LinningInMono | 作曲 | 鼓譜に升降号の外注事故 | [1936114696…](https://x.com/LinningInMono/status/1936114696488468699) |
| @FXmjGA3uF5o8uyK | 制作 | MIDI→MuseScore 混乱 | [1965118545…](https://x.com/FXmjGA3uF5o8uyK/status/1965118545047765291) |
| @huajin0805 | 中文 | percussion clef 用語 | [1999690105…](https://x.com/huajin0805/status/1999690105435619384) |
| @mockingnonsense | ユーザー | AI→drum MusicXML 願望 | [1997376373…](https://x.com/mockingnonsense/status/1997376373439300019) |
| @drumrapp | 製品 | MusicXML 練習インポート | [1985778870…](https://x.com/drumrapp/status/1985778870604149188) |
| @k1oku | 業界実務 | Dorico GM→キット変換成功 | [2016403420…](https://x.com/k1oku/status/2016403420627059132) |
| @nyoro_wrl | 開発 | MIDI→MuseScore 変換ソフト自作 | [2009547599…](https://x.com/nyoro_wrl/status/2009547599054028843) |
| @2d_m_t / @xRYO_SUKEx | 実務 | Percussion Pitch Map 成功 | [1816823178…](https://x.com/2d_m_t/status/1816823178922250401) 等 |
| @NUSH06 | 実務 | MuseScore ドラム MIDI Tips | [1487837662…](https://x.com/NUSH06/status/1487837662581248000) |
| @linuxiac | テック | MuseScore 4.5 percussion panel | [1901711507…](https://x.com/linuxiac/status/1901711507592806541) |
| @MireloAI | AI | audio→multi-instrument MIDI | [2075536492…](https://x.com/MireloAI/status/2075536492177354771) |

---

## 11. 結論

X の実務言説をまとめると、**ドラム譜機能の本質課題は「符を置く UI」ではなく、「線位置・奏法・MIDI ノート・MusicXML unpitched・音源サンプル」という五つの名前空間の同期」**である。

- **失敗が特に多いのはキットマップと交換（MIDI/MusicXML）**、次いで **入力 UX**、次いで **再生セマンティクス**。  
- **成功はほぼ常にマップを外部資産化したパイプライン**（Pitch Map、自作変換、GM 前提）。  
- **最新トレンドは panel 改善と AI→MIDI と練習アプリへの MusicXML**だが、**正しい classical / 出版社ドラム譜へのラストマイルは未完**。

---

### 補足（調査の制約）

- X 検索はセマンティック／キーワードで多角的に行ったが、**投稿の削除・非公開・アルゴリズム偏り**により網羅ではない。  
- 中国語は用語・学習・品質事故は拾えたが、**W3C MusicXML 仕様級の開発者議論は X 上では薄い**（英語フォーラム／GitHub の方が厚い可能性）。  
- 本レポートは**実投稿ベースの現場センサ**であり、仕様の正誤判定は各公式ドキュメントと突合が必要。

---

**Slack 作業ログ:** 本環境に Slack MCP／送信手段が接続されていないため、`#倉田_ログ` への自動投稿は未実施。接続がある場合は同内容の要約を投稿可能。
