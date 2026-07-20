# 記譜形式の相互変換（五線⇄TAB・五線→简谱の可逆性）  
## X（旧Twitter）実務者・研究者・開発者投稿調査レポート

**調査日**: 2026-07-21  
**対象**: 英語・中国語中心（実務に直結する日英混在投稿も含む）  
**収集軸**: 成功例 / **失敗例（重点）** / 限界 / ベストプラクティス / 最新トレンド  
**注意**: すべて実投稿ベース。投稿は実務経験・観測・開発者の発言であり、学術的な完全可逆性の証明ではない。

---

## 0. 調査サマリ（先に結論）

| 変換経路 | 可逆性の実務評価 | X上の支配的トーン |
|---|---|---|
| **五線 ⇄ TAB** | **半可逆**。音高は戻せるが、弦・フレット・ポジション選択は一意でないため **情報損失が本質** | 失敗・手直し報告が圧倒的に多い |
| **TAB → 五線（via MusicXML/MIDI）** | ある程度成功しやすい | 「sheet music になる」成功談はある |
| **五線 → TAB（自動）** | 失敗しやすい（アルゴリズムが「弾ける譜」を保証しない） | ポジション違い・TAB非引き継ぎ |
| **五線 → 简谱（Jianpu）** | 表示層としては成功例増。**逆方向の完全可逆はほぼ語られない** | プラグイン/AI/自作ツールの成功と「手変換が面倒」の両面 |
| **MusicXML 全般** | 形式はあるが **方言互換** で壊れやすい | Finale終了後の移住談で失敗が集中 |

**一言でいうと**:  
「形式変換」はできるが、「演奏情報・レイアウト・方言の完全往復」は現場ではほぼ諦められており、**手直し前提の一方向パイプライン**が標準運用になっている。

---

## 1. 失敗例（重点・多め）

### 1.1 MusicXML 経由でも「綺麗に受け渡せない」（Guitar Pro → Dorico）

**実務者**: @YasunariNishio（作曲・リリース活動）  
**内容**: Guitar Pro 8 → Dorico SE を MusicXML で受け渡し「やっぱり上手くいかない」。他ソフトでも同様で、「MusicXML で綺麗に受け渡すことってできるのか？」と根本疑問。

> Guitar Pro 8からDorico SEへMusicXMLで受け渡ししてみたがやっぱり上手くいかないな  
> 他のソフトでもそうだがMusicXMLで綺麗に受け渡すことってできるのか？  
> — [Yasu / @YasunariNishio, 2025-11-20](https://x.com/YasunariNishio/status/1991322204676714585)

**示唆**: TAB中心ソフトから版面重視ソフトへの橋渡しは、**成功より「期待外れ」がデフォルト**。

---

### 1.2 TAB の導入・五線→TAB コピーが不親切／MusicXML で TAB が表示されない（Dorico）

**実務者**: @gensoumusa（多弦ギター・両手タッピング研究）  
**内容**:
- TAB 導入 UI が一見解りにくい  
- 五線→TAB のコピーも不親切  
- MusicXML 読込時に TAB が表示されない（設定の問題か、XML側/受け側の問題か不明）

> TAB譜の導入は一見解りにくい。五線→TABへのコピーも不親切。  
> MusicXMLファイルを読み込んだ時にTAB譜が表示されないのは…MusicXMLファイルがTAB譜表示を受け渡せていないのかDoricoが受け取っていないのかは不明。  
> — [yoshiharu / @gensoumusa, 2025-06-22](https://x.com/gensoumusa/status/1936719093908034012)

**示唆**: 同じ「TABサポート」でも、(a) 表示設定、(b) エクスポート側の TAB 要素、(c) インポート側の解釈 が揃わないと **「無いのと同じ」** になる。

---

### 1.3 MIDI / MusicXML では TAB データを正しく引き継げない（ベース実務）

**実務者**: @KAZUAKI_virgiL（ジャズベーシスト、年間100本以上演奏）  
**内容**: MIDI・MusicXML で TAB を正しく引き継げず、別手法を探すと明言。

> MIDIデータやMusicXMLではTAB譜のデータを正しく引き継ぐことができませんでした…。  
> — [高橋和明 / @KAZUAKI_virgiL, 2023-02-26](https://x.com/KAZUAKI_virgiL/status/1629775345292570624)

**示唆**: **TAB の本質情報（弦・フレット）は pitch-only 交換では落ちる**。可逆性の最大の落とし穴。

---

### 1.4 楽譜 OCR → MusicXML はできても TAB は無理

**実務者**: @yasai_murasaki  
**内容**: 画像→MusicXML の OCR は有用だが、TAB は「さすがに無理」。MusicXML 化できれば MuseScore / TuxGuitar で再生できる、と利点も併記。

> 楽譜の画像を読み込んでMusicXMLに変換してくれるOCRソフトです、Tab譜はさすがに無理でした…  
> — [anthem / @yasai_murasaki, 2024-06-03](https://x.com/yasai_murasaki/status/1797456542314508461)

**示唆**: 光学認識パイプラインは **五線優位**。TAB は別問題空間。

---

### 1.5 Finale 終了ショック：MusicXML は「経路」だがフォーマットは壊れる

**実務者複数**（2024-08 Finale 終了直後に失敗談が集中）

**(a) 経路自体は決まっているが手直し地獄**  
@TheRealTomahawk:

> save your Finale score as MusicXML → import into Dorico → **fix all the f\*\*\*ed up formatting and stuff that was lost**. There's no import tool…  
> — [The Tomahawk / @TheRealTomahawk, 2024-08-27](https://x.com/TheRealTomahawk/status/1828540672384659494)

**(b) 同一ソフト往復でも壊れる（自己エクスポート→インポート）**  
作曲家 @bathorykitsz（Finale 33年）:

> There's no "Save as..." for XML in Finale. It's export to MusicXML. **And it doesn't work.** Observe original file and import of MusicXML exported from it (by the same program).  
> — [Dennis Bathory-Kitsz / @bathorykitsz, 2024-08-27](https://x.com/bathorykitsz/status/1828250466641121465)

**(c) グラフィカル譜・前衛記譜は MusicXML が使えない**  
同氏:

> thousands of scores with no conversion app (**MusicXML doesn't work for graphical scores.**)  
> — [@bathorykitsz, 2024-08-26](https://x.com/bathorykitsz/status/1828092168680218845)

**(d) 連符まわりの往復翻訳で「毎小節ミス修正」**  
@_rwgarvey:

> export it to musicxml… export back… **now i have to fix every mistake the translations caused**  
> — [ryan w garvey / @_rwgarvey, 2023-12-29](https://x.com/_rwgarvey/status/1740545689933746236)

**(e) 大作の Sibelius→Dorico は「情報落ちすぎて諦める」**  
@MichaelZapruder:

> any attempts to move big pieces in from Sibelius via musicxml have been unsuccessful… **too much info is lost**, it’s easier just to keep old pieces in Sib.  
> — [@MichaelZapruder, 2020-07-24](https://x.com/MichaelZapruder/status/1286679859692015617)

**(f) 独自 TAB システムを Finale で組んでいた場合、XML 後の全小節チェックが恐怖**  
@sternie_howard:

> piano piece that is all a **tablature system I set up in finale**… wouldn’t be fond of having to check every bar… if I was to simply import xml!  
> — [Samuel / @sternie_howard, 2024-08-27](https://x.com/sternie_howard/status/1828232423215374641)

---

### 1.6 MusicXML の「規格なのに方言」問題（設計欠陥の指摘）

**技術寄り実務者**:

> The design flaws mean that two programs can have slightly incompatible dialects of MusicXML but they are still both officially correct, but they can't necessarily understand the other. There's a new format called **MNX** to replace MusicXML… but it doesn't exist yet.  
> — [Michael J. Ducharme / @MJDucharme, 2024-08-27](https://x.com/MJDucharme/status/1828314169000505726)

> MusicXMLが一応あるが、それで、各楽譜ソフトで認識が違うって、何のための規格なんだよ…。規格が悪いのかソフト側が悪いのか。W3CのMNX…に期待  
> — [Y.N. / @nktener, 2025-11-29](https://x.com/nktener/status/1994749819756425567)

**示唆**: 「MusicXML 対応」＝「相互運用できる」ではない。**互換性は実装依存**。

---

### 1.7 TAB 専用ソフト内の破壊的操作（拍子変更で音が消える）

**実務者**: ギタリスト @marceatsfood  

> i accidentally tabbed a song out in 4/4. tried to switch it to 3/4 and it just **deleted all the extra notes** in the bars… i want to delete guitarpro.  
> — [marc okubo / @marceatsfood, 2022-01-12](https://x.com/marceatsfood/status/1481338400619835396)

**示唆**: 相互変換以前に、**時間軸メタデータの変更がノート破壊を起こす**。可逆性以前の安全モデル問題。

---

### 1.8 Guitar Pro の MusicXML 完全サポートへの不信

**実務者**: @sarariiman（ギター解説系）  

> ChatGPTだと「Guitar Proが完全にMusicXMLをサポートしているわけではないため、表示に問題が生じることがあります。」…本当にそうなのだろうか…  
> — [@sarariiman, 2023-06-06](https://x.com/sarariiman/status/1666064438720593920)

（投稿時点で検証中トーンだが、**現場で「完全ではない」説が流通**していること自体が重要）

---

### 1.9 移行時の TAB 不安（Finale 離脱）

**実務者**: ウクレレ @hebizou  

> コンバートはMusicXMLを使えばある程度可能かと思いますが、**TABはどうなのかな…**。過去のファイルについては、当面、Finaleを使えるパソコンを…大事に使う  
> — [@hebizou, 2024-08-29](https://x.com/hebizou/status/1829021884450541689)

**示唆**: 弦楽器ユーザーは **MusicXML 一般論より TAB 存続可否が移住判断のボトルネック**。

---

### 1.10 五線→简谱は「需要はあるが面倒」／認知コストの失敗

**中国語圏実務・生活者**:

> 每次学新歌，我都得把五线谱翻成简谱  
> （新曲のたび五線を简谱に手で翻す／視認速度と紙枚数削減が動機）  
> — [Luobi / @Luibitao, 2026-03-26](https://x.com/Luibitao/status/2036984718122770801)

> 啊，我就是习惯了五线谱，看不惯简谱，觉得还要转换很麻烦  
> — [@q1ngyang, 2026-04-27](https://x.com/q1ngyang/status/2048799795998064839)

> 小时候学的简谱数字刻在了我的基因里…对着五线谱说哪个音符我脑海里出现的都是数字，需要停两秒转换一下  
> — [@tonptitchaaa, 2025-02-07](https://x.com/tonptitchaaa/status/1887883466848543104)

**示唆**: 软件以前に **二重記譜リテラシーの認知スイッチ** が失敗コスト。可逆性より「どちらか一方で完結したい」圧力。

---

### 1.11 导入侧の情報落ち（指板情報以外も）

**作曲家**: @nellshawcohen  

> MusicXML import… certain information doesn't make the transition… (**rehearsal letters, guitar fingerings**, et al)  
> — [Nell Shaw Cohen / @nellshawcohen, 2020-07-23](https://x.com/nellshawcohen/status/1286354735491174402)

**示唆**: ギター文脈では **fingering 落ち＝TAB 品質の直接劣化**。

---

### 1.12 開発者視点：非西洋記譜は主要3ソフトでも弱い

**研究者**: @anabelmaler（音楽理論 Ass. Prof.）  

> None of these 3 programs handle **non-Western notation** well…  
> — [Dr. Anabel Maler / @anabelmaler, 2022-05-03](https://x.com/anabelmaler/status/1521602862891024386)

**示唆**: 简谱は「変換機能の有無」以前に、**本体サポートが周辺（プラグイン）依存**しやすい。

---

### 1.13 プラグインのバグ修正がコミュニティ依存（Jianpu）

**開発者**: @tcbnhrs（MuseScore 数字譜プラグイン提供者）  

> MuseScoreの数字譜プラグイン…のバグを修正しました…**複数の台湾の方からの指摘**でした。  
> — [Tachibana H. / @tcbnhrs, 2020-09-23](https://x.com/tcbnhrs/status/1308779997985820673)

**示唆**: 简谱は **一次市民権がなく、バグ発見がユーザー依存**。可逆性保証の工業品質に届きにくい。

---

### 1.14 AI による「読譜」は構造は取れるが内容精度が低い（Jianpu/Sargam）

**開発者**: @AbhiDasOne（Google AI DevTools）  

> task: reading… **Jianpu (简谱)** and Sargam…  
> Honest result: reads structure well, the notes only partially (**~9% content, ~29% with structure**)  
> — [Abhi Das / @AbhiDasOne, 2026-07-19](https://x.com/AbhiDasOne/status/2078943934483677225)

**示唆**: 最新トレンドでも **内容精度は実用閾値に遠い**。「変換できた」≠「正しい」。

---

### 1.15 OMR 精度は「まだまだ」、修正労働が前提

**実務者**: @hiyomeki  

> バンドスコア…OMRからMusicXMLに書き出してポチポチ修正…**現状の読み取り精度はまだまだ**  
> — [@hiyomeki, 2026-01-26](https://x.com/hiyomeki/status/2015651762422862190)

---

### 1.16 DAW 連携でも MusicXML は「記号は来るが音符表現・リピートが崩れる」

**実務者**: @takuyah  

> Dorico+NP5 → Logic  
> MusicXML：音楽記号は移行されるが音符やスラーはLogicデフォルト表示、**繰り返しは展開されない**、テンポざっくり  
> — [@takuyah, 2026-07-19](https://x.com/takuyah/status/2078691801943445613)

（※五線⇄TABではないが、「記譜情報の相互変換の失敗パターン」として同型）

---

## 2. 成功例

### 2.1 TAB/MIDI → 五線（MuseScore 経由）は「定番成功ルート」

**開発者・教育**: @kjw_audio（ゲーム音声 PhD / 講師）  

> in tuxguitar and guitar pro, you can export… midi or musicXML and if you import this to Musescore **it will be sheet music**  
> — [Kyle Worrall / @kjw_audio, 2023-05-24](https://x.com/kjw_audio/status/1661324970490724354)

**示唆**: **TAB→五線**（音高投影）は成功しやすい。問題は逆方向と細部。

---

### 2.2 MuseScore で TAB 追加／GP インポートが現実的ワークアラウンド

- @willfox_tt: MuseScore は tab があり Guitar Pro ファイルを import できる  
  ([2021-08-10](https://x.com/willfox_tt/status/1425205036527849474))  
- @kantenor_0307: ScoreMaker 等 → MusicXML → MuseScore で TAB 追加できるはず  
  ([2026-03-04](https://x.com/kantenor_0307/status/2029171720758935921))  
- @OldBayMason: MuseScore を自前ソフトに出して **“convert to TAB”**  
  ([2022-02-03](https://x.com/OldBayMason/status/1489332143100727305))

---

### 2.3 五線上に Jianpu を載せるプラグイン成功例

**開発者**:
- @jhsu: 父と MuseScore 3 用 Jianpu プラグインを vibe code  
  ([2025-12-25](https://x.com/jhsu/status/2004332723696283672) / [GitHub](https://github.com/jhsu/musescore-doremi/))  
- @tcbnhrs: MuseScore v4 対応 数字譜（Jianpu）プラグイン公開  
  ([2023-06-25](https://x.com/tcbnhrs/status/1672886024928894976))

**示唆**: 成功の型は **「五線をソース・オブ・トゥルースにし、简谱は表示レイヤ」**。  
→ これは **可逆変換というより「同期表示」** に近い。

---

### 2.4 中国語圏：多形式対応の自作／AI 製譜ツール

- @william40152988: AI で曲譜ソフト。**简谱・五線・和弦譜・级数譜**、移調・メトロノーム対応  
  ([2026-07-14](https://x.com/william40152988/status/2077061069906837857))  
- @pluwen: 国人開発「8谱」— 简谱/功能简谱/和弦譜、転調・级数和弦変換  
  ([2025-11-17](https://x.com/pluwen/status/1990231742050148479))  
- @xi_du22154: 「AI简谱转换」起業事例の言及（5週でキャッシュフロー黒字という二次情報）  
  ([2026-07-05](https://x.com/xi_du22154/status/2073776552509321277))

---

### 2.5 ASCII Tab → 再生可能譜（Soundslice）の「幻覚駆動」実装

ChatGPT が「Soundslice は ASCII tab を再生できる」と誤案内 → 創業者が**本当に実装**。

> ChatGPT's hallucination about @Soundslice turned into reality… convert ASCII tablature…  
> — [@otticmusic, 2025-07-10](https://x.com/otticmusic/status/1943251501574471984)  
> 元報道共有: [@slashdot, 2025-07-10](https://x.com/slashdot/status/1943112190447210962)

**示唆**: TAB の「テキスト遺産」を正規譜に引き上げる需要が実在。成功は **専用パーサ** による。

---

### 2.6 MuseScore 開発側の TAB 表現強化（bend 等）

**MuseScore 系プロダクト責任者** @Tantacrul:

> entirely new system for **notated bends and tab bends**… 1/4 tones… edit the speed of the sounding bend  
> — [@Tantacrul, 2023-12-05](https://x.com/Tantacrul/status/1732161045173534857)

また、**notation + tab の combined stave** が人気、という UX 示唆  
([@Tantacrul, 2023-11-03](https://x.com/Tantacrul/status/1720491816745623996))

---

### 2.7 歴史的 TAB → MIDI → Sibelius の救出

**研究者ネットワーク**: ビウエラ TAB を MIDI 経由で Sibelius へ  
@theorymeg が「music twitter at its best」と評価  
([2021-04-06](https://x.com/theorymeg/status/1379515567904714753))

---

## 3. 限界（投稿から抽出される構造的制約）

### 3.1 情報理論的限界（可逆性の核心）

| 情報 | 五線 | TAB | 简谱 |
|---|---|---|---|
| 音高・リズム | ○ | ○（弦フレット経由） | ○（相対階名中心） |
| 弦・フレット・ポジション | △/×（一意でない） | ○ | × |
| 運指・奏法記号 | ソフト依存 | TAB 特有記号が豊富 | 限定的 |
| 調性感（do=1） | 調号 | 弱い | 強い |
| 多声・オーケストラ | 強い | 弱い | 弱い（中国語投稿でも議論） |

**五線→TAB が不可逆になりやすい理由**（投稿群の暗黙合意）:
1. 同一音高に複数の弦フレット解がある  
2. 自動変換は「音は合っても弾きにくい／ポジションが違う」  
3. MusicXML/MIDI が pitch-first だと TAB 属性が落ちる（@KAZUAKI_virgiL 等）

**五線→简谱 が可逆になりにくい理由**:
1. 简譜は **調相対**、五線は **絶対音高＋調号**（転調・変化音の表現差）  
2. 実装がプラグイン/表示レイヤ中心で、**第一級データモデルでない**ことが多い  
3. 複声部・オーケストラでは简譜の情報圧縮が不利（@JoyBoyFrank の認知論投稿）

---

### 3.2 規格の限界

- MusicXML は普及（発明者 @MichaelDGood: 240 アプリ級）だが **レイアウト/方言/特殊記譜**で破綻  
- **MNX** が後継として期待されるが「まだ無い／普及途上」（@MJDucharme, @nktener）  
- オープンソースでも **MusicXML 非エクスポート** がある（@MichaelDGood, 2024-08-26）  
- @Tantacrul: 見た目（glyph/style/engraving）を捨てる MusicXML だけでは不十分、という別軸批判  
  ([2023-11-05](https://x.com/Tantacrul/status/1721085621094019236))

---

### 3.3 プロダクト境界の限界

- 主要 engraving ソフトは **non-Western が弱い**（@anabelmaler）  
- 简谱需要は中国語圏で大きいが、**世界標準の可逆エンジンとしては未成熟**  
- OMR・AI は補助線であり、**人手修正が必須**（@hiyomeki, @AbhiDasOne）

---

## 4. ベストプラクティス（投稿から帰納）

### BP-1. **正本（source of truth）を1つ決める**
- 弦楽器演奏配布 → **Guitar Pro / TAB 正本**  
- 出版・合奏・版面 → **Dorico / MuseScore 五線正本**  
- 中国語教育・合唱個人練習 → **简谱正本**（@Luibitao の手翻し動機）

### BP-2. 変換は「完了」ではなく「**下書き生成**」
- Finale→Dorico の定石: MusicXML → **壊れた formatting を直す**（@TheRealTomahawk）  
- OMR: MusicXML 化 → **ポチポチ修正**（@hiyomeki）

### BP-3. TAB を守るなら **MusicXML 丸投げを避ける**
- TAB 属性が落ちる報告が複数（@KAZUAKI_virgiL, @gensoumusa, @hebizou）  
- 可能なら **ネイティブ形式**（gp, mscz）または **同一エコシステム内 linked staff/tab**

### BP-4. 五線⇄TAB は **linked / combined stave** を優先
- @Tantacrul: combined stave（notation + tab）が人気  
- 「変換して捨てる」より「**並列同期表示**」が実務的可逆性に近い

### BP-5. 简谱は **五線正本＋数字表示レイヤ** が現実解
- MuseScore Jianpu プラグイン群（@tcbnhrs, @jhsu）  
- 完全双方向エンジンを期待しない

### BP-6. パイプラインを明示的に組む（成功している人の型）
例（声楽・歌詞寄りだが参考）:  
SynthV → MIDI → Studio One → Finale NotePad → MusicXML → Guitar Pro  
（@SoundsCocktail, 2024-02-15）  
→ **得意な処理をソフトごとに分業**。一発可逆を求めない。

### BP-7. 大作・特殊記譜は **移行しない**
- 「情報落ちすぎて Sibelius に残す」（@MichaelZapruder）  
- グラフィカル譜は MusicXML 不可（@bathorykitsz）

### BP-8. 変換前に **メタデータ破壊操作を避ける**
- 拍子変更でノート削除（@marceatsfood）のような、**時間構造変更はバックアップ必須**

---

## 5. 最新トレンド（2023–2026 の投稿から）

| トレンド | 内容 | 代表投稿 |
|---|---|---|
| **Finale 終焉 → 移住パニック** | MusicXML 経由の失敗が大量可視化 | 2024-08 周辺の移住スレ一群 |
| **MNX 期待** | MusicXML 方言問題の次世代 | @MJDucharme, @nktener, W3C 議事共有 |
| **ASCII Tab 正規化** | ChatGPT 幻覚 → Soundslice 実装 | @slashdot / @otticmusic 2025-07 |
| **Jianpu の「表示プラグイン」定着** | MuseScore 3/4 系 | @tcbnhrs, @jhsu |
| **中国語圏 AI 製譜・多形式同時サポート** | 简谱+五線+和弦+级数 | @william40152988, 8谱, AI简谱转换言及 |
| **AI 読譜はまだ低精度** | Jianpu 内容 ~9% | @AbhiDasOne 2026-07 |
| **OMR as a service** | Soundslice 等が「修正前提」で普及 | @hiyomeki, @shimizu_trb |
| **TAB 表現の高度化** | bend 1/4音・再生速度制御 | @Tantacrul / MuseScore 系 |
| **交換フォーマット vs 版面フォーマット論争** | MusicXML だけでは見た目が足りない | @Tantacrul 2023-11 |

---

## 6. 「可逆性」についての実務定義（投稿群からの再定式化）

X 上の実務者は、数学的な可逆性ではなく、次の **段階的可逆性** で語っている:

1. **音高・リズムの往復** … 比較的達成しやすい（成功例の中心）  
2. **奏法・運指・TAB位置の往復** … しばしば失敗（本調査の失敗例の中心）  
3. **版面・レイアウトの往復** … ほぼ諦め（Finale 移住談）  
4. **特殊記譜・グラフィカル** … 変換経路が存在しない  
5. **简谱との往復** … 「表示」や「学習用簡略化」としては成功、**完全双方向はほぼ未踏**

**機能仕様に落とすなら**:
- 「可逆」と謳うなら、少なくとも  
  - (A) pitch/rhythm round-trip  
  - (B) string/fret/fingering round-trip  
  - (C) jianpu octave dots / underline duration / key context  
  を **別々の合格基準** で測る必要がある。  
- X の失敗談の大半は、(A) は通るが (B)(C) で落ちるパターン。

---

## 7. 出典インデックス（主要投稿）

### 失敗・限界
| # | 投稿者 | 日付 | URL |
|---|---|---|---|
| F1 | @YasunariNishio | 2025-11-20 | https://x.com/YasunariNishio/status/1991322204676714585 |
| F2 | @gensoumusa | 2025-06-22 | https://x.com/gensoumusa/status/1936719093908034012 |
| F3 | @KAZUAKI_virgiL | 2023-02-26 | https://x.com/KAZUAKI_virgiL/status/1629775345292570624 |
| F4 | @yasai_murasaki | 2024-06-03 | https://x.com/yasai_murasaki/status/1797456542314508461 |
| F5 | @TheRealTomahawk | 2024-08-27 | https://x.com/TheRealTomahawk/status/1828540672384659494 |
| F6 | @bathorykitsz | 2024-08-27 | https://x.com/bathorykitsz/status/1828250466641121465 |
| F7 | @bathorykitsz | 2024-08-26 | https://x.com/bathorykitsz/status/1828092168680218845 |
| F8 | @_rwgarvey | 2023-12-29 | https://x.com/_rwgarvey/status/1740545689933746236 |
| F9 | @MichaelZapruder | 2020-07-24 | https://x.com/MichaelZapruder/status/1286679859692015617 |
| F10 | @sternie_howard | 2024-08-27 | https://x.com/sternie_howard/status/1828232423215374641 |
| F11 | @MJDucharme | 2024-08-27 | https://x.com/MJDucharme/status/1828314169000505726 |
| F12 | @nktener | 2025-11-29 | https://x.com/nktener/status/1994749819756425567 |
| F13 | @marceatsfood | 2022-01-12 | https://x.com/marceatsfood/status/1481338400619835396 |
| F14 | @hebizou | 2024-08-29 | https://x.com/hebizou/status/1829021884450541689 |
| F15 | @nellshawcohen | 2020-07-23 | https://x.com/nellshawcohen/status/1286354735491174402 |
| F16 | @anabelmaler | 2022-05-03 | https://x.com/anabelmaler/status/1521602862891024386 |
| F17 | @tcbnhrs | 2020-09-23 | https://x.com/tcbnhrs/status/1308779997985820673 |
| F18 | @AbhiDasOne | 2026-07-19 | https://x.com/AbhiDasOne/status/2078943934483677225 |
| F19 | @hiyomeki | 2026-01-26 | https://x.com/hiyomeki/status/2015651762422862190 |
| F20 | @takuyah | 2026-07-19 | https://x.com/takuyah/status/2078691801943445613 |
| F21 | @Luibitao | 2026-03-26 | https://x.com/Luibitao/status/2036984718122770801 |
| F22 | @sarariiman | 2023-06-06 | https://x.com/sarariiman/status/1666064438720593920 |

### 成功・トレンド・BP
| # | 投稿者 | 日付 | URL |
|---|---|---|---|
| S1 | @kjw_audio | 2023-05-24 | https://x.com/kjw_audio/status/1661324970490724354 |
| S2 | @jhsu | 2025-12-25 | https://x.com/jhsu/status/2004332723696283672 |
| S3 | @tcbnhrs | 2023-06-25 | https://x.com/tcbnhrs/status/1672886024928894976 |
| S4 | @william40152988 | 2026-07-14 | https://x.com/william40152988/status/2077061069906837857 |
| S5 | @pluwen | 2025-11-17 | https://x.com/pluwen/status/1990231742050148479 |
| S6 | @otticmusic / @slashdot | 2025-07 | https://x.com/otticmusic/status/1943251501574471984 |
| S7 | @Tantacrul | 2023-12-05 | https://x.com/Tantacrul/status/1732161045173534857 |
| S8 | @Tantacrul | 2023-11-03 | https://x.com/Tantacrul/status/1720491816745623996 |
| S9 | @Tantacrul | 2023-11-05 | https://x.com/Tantacrul/status/1721085621094019236 |
| S10 | @theorymeg | 2021-04-06 | https://x.com/theorymeg/status/1379515567904714753 |
| S11 | @MichaelDGood | 2018-10-20 | https://x.com/MichaelDGood/status/1053439807630659584 |
| S12 | @MichaelDGood | 2024-08-26 | https://x.com/MichaelDGood/status/1828152948939202771 |

---

## 8. 調査上の限界（メタ）

1. **X は英語・中国語でも「深い技術 deb ug はフォーラム/GitHub に流れる**」傾向があり、投稿は症状報告中心。  
2. 中国語の「简谱変換失敗」は、**政治・雑談ノイズが多く、純技術投稿が相対的に少ない**（本調査では開発・教育・自作ツール投稿を優先抽出）。  
3. 「成功」投稿は宣伝・プラグイン公開が多く、**失敗は移住イベント時に偏在**（特に Finale 終了 2024-08）。  
4. 可逆性の定量ベンチマーク（差分率）を X 投稿から直接得ることはほぼ不可。@AbhiDasOne の % 報告は例外的に有用。

---

## 9. プロダクト示唆（採譜/記譜ソフト向け）

もし機能要件が **『記譜形式の相互変換（五線⇄TAB・五線→简谱の可逆性）』** なら、X 実務知は次を勧める:

1. **「可逆」を機能名に使うなら、層別 SLA を公開**（pitch / fret / layout / jianpu-context）  
2. **五線⇄TAB は変換より linked dual view + 手動ポジション上書き**  
3. **MusicXML は交換用下書き**、正本はネイティブ  
4. **简谱は export-only（五線→简谱）を先に堅く**し、逆方向は「再構築（再記譜）」とラベル  
5. 失敗時は **何が落ちたかのレポート**（lost: string, fret, articulations, repeats…）を出すと、X 上の最大の怒り（黙って壊れる）を避けられる

---

### 補足
Slack `#倉田_ログ` への自動投稿は、この環境で Slack MCP/CLI が利用できなかったため未実施です。接続があれば同内容の作業ログを投稿できます。
