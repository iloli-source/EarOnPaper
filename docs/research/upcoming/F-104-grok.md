音楽採譜ソフトの「全出力形式・プラグイン型エクスポート」について、X上の実務者・開発者投稿を英語・中国語中心に集めます。まず関連キーワードで広く検索します。MusicXML互換の失敗例と、記譜プラグイン／エクスポート周りをさらに掘ります。# X調査レポート：記譜ソフトの「全出力形式オプション対応」（プラグイン型網羅出力）

**調査日**: 2026-07-21  
**対象**: X（旧Twitter）上の実務者／研究者／開発者投稿（英語・中国語中心、関連日英含む）  
**テーマ**: 音楽採譜・記譜ソフトにおける、記譜法（五線／タブ／簡譜など）とファイル形式（MusicXML / MIDI / PDF / ABC 等）の**プラグイン型・網羅的エクスポート**  
**方法**: キーワード検索＋セマンティック検索。実投稿ベース。宣伝投稿は区別して記載。

---

## 1. 結論サマリ

| 観点 | 現場の合意に近い像 |
|------|-------------------|
| **何が「価値」か** | 編集・再生より **「正しく、用途別に出せる」** が商品そのもの（中文界隈の強主張） |
| **標準の実態** | MusicXMLは業界標準だが **lossy intermediary（損失ありの中間形式）**。論理構造は比較的残るが、レイアウト／奏法詳細は壊れやすい |
| **失敗の主戦場** | ①移行時のMusicXML ②アーティキュレーション／強弱 ③MIDIの意味喪失 ④DAW↔記譜の往復 ⑤簡譜など地域記譜の未対応 |
| **プラグイン型の意味** | 「全形式をコアに直書き」より、**Dolet型のエクスポート強化プラグイン／簡譜プラグイン／外部変換器**が現実解として繰り返し現れる |
| **最新トレンド** | Finale終了後の移行需要、AI OMR→MusicXML/MIDI、ABC/LilyPondをLLM生成先に、簡譜・教育向け軽量符号化 |

**コア洞察**: 「全出力形式対応」はチェックボックス機能ではなく、**互換性の泥沼を製品化した護城河（moat）**として語られる。成功は「全部出せる」より **「用途ごとに何が失われるかを明示し、損失を最小化・修復可能にする」** 設計。

---

## 2. 失敗例（特に多い・実投稿）

### 2.1 移行失敗：Finale → Dorico「道はあるが地獄」

Finale終了（2024-08）後、公式が推す「pathway」への実務反応は厳しい。

- **@TheRealTomahawk（2024-08-27）**  
  経路は「FinaleをMusicXML保存 → Dorico import → **崩れた書式を全部自分で直す**」。専用importツールはなく、実質セルフ修復。# 音楽記譜ソフト「全出力形式オプション対応」  
## X（旧Twitter）実務・研究・開発者投稿ベース調査

**調査日:** 2026-07-21  
**対象機能の定義:** 記譜法（五線・タブ・簡譜・ABC 等）とファイル形式（MusicXML / MIDI / PDF / 固有形式）を、コア固定ではなく**プラグイン／エクスポート層で網羅的に出す**設計  
**言語偏重:** 英語中心 + 中国語補完（日本語投稿は補助）  
**方法:** X セマンティック／キーワード検索。**実投稿のみ**を根拠とし、各節に出典リンクを付す

---

## 1. 結論（実務で繰り返し出る合意）

| 観点 | 現場の合意 |
|------|------------|
| **交換の本丸** | 編集可能交換の事実上の標準は **MusicXML**。再生・DAW連携は **MIDI**、配布は **PDF** |
| **最大の嘘** | 「全形式対応」「MusicXMLで完全移行」は**マーケティング語**。多くは**lossy（情報欠落）中継** |
| **失敗が常態** | レイアウト崩壊、アーティキュレーション破損、連符・強弱・リピートの欠落、移調バグ、MIDIチャンネル/BPM強制 |
| **価値の源泉** | 中国語圏では「編集より**导出（エクスポート）**が本丸」「フォーマット互換の泥臭い仕事が堀」と明言される |
| **プラグイン化の必然** | 簡譜・タブ・ABC・特殊記譜はコアに載せず**後付け**になりやすい。コア未対応はコミュニティの不満源 |
| **トレンド** | Finale終了後の移行圧力で MusicXML 品質競争が再燃 / OMR・AI が MusicXML・MIDI を吐く / ABC・LilyPond が軽量表現として再評価 |

---

## 2. 失敗例（本調査の中心）

### 2.1 ソフト間移行：MusicXML は「通路」だが「完成品」ではない

**Finale → Dorico の公式「pathway」への現場反応**

> The "pathway" is: save your Finale score as MusicXML → import into Dorico → **fix all the f\*\*\*ed up formatting and stuff that was lost**. There's no import tool or anything. Do it all yourself.

— [@TheRealTomahawk](https://x.com/TheRealTomahawk/status/1828540672384659494)（2024-08-27、Finale終了議論への返信）

**大曲の Sibelius → Dorico は「インポートはできるが情報過多欠落」**

> any attempts to move big pieces in from Sibelius via musicxml have been unsuccessful. I can import the files, but **too much info is lost**, it’s easier just to keep old pieces in Sib.

— [@MichaelZapruder](https://x.com/MichaelZapruder/status/1286679859692015617)（2020-07-24）

**連符修正のために往復すると、翻訳ミスの修正地獄**

> had to export it to musicxml, send to finale to change the durations, export back to musicxml and send into dorico, now I have to **fix every mistake the translations caused**

— [@_rwgarvey](https://x.com/_rwgarvey/status/1740545689933746236)（2023-12-29）

**パース自体が毎回失敗**

> Having trouble getting Dorico to import musicXML (**parsing fails every time**).

— [@mugloch](https://x.com/mugloch/status/1233300208571817985)（2020-02-28）

**実装側（作曲家）の肌感:** 「多少（わずか）は流用できる」程度で、**完全移行を期待しない**

— [@hidetakumi](https://x.com/hidetakumi/status/1828258708880830475)（2024-08-27）

---

### 2.2 論理構造は通る／見た目と表現記号が壊れる

**物理レイアウトは弱い（古くからの定番認識）**

> my previous experience with MusicXML is that it captures **logical structure well, physical not so well**.

— [@sc3d](https://x.com/sc3d/status/1010574078942629891)（2018-06-23）

**アーティキュレーションが壊れたまま再生され、意味不明ノイズに**

> PSA – if you’re moving old Sibelius scores to MS4 via MusicXML **remember to check the articulations have carried over correctly**… (i’ve been laughing for a solid 5 minutes thank you for including this ungodly noise in Muse Sounds)

— [@eddardmackey](https://x.com/eddardmackey/status/1604814328062001159)（2022-12-19）  
MuseScore 側（Tantacrul）も「最新 MusicXML への追従とクリーンな import は大きな課題」と返信。

**Finale 由来の全音符が全部タイ付き二分音符に化ける**

> the guy exported to MusicXML from Finale, but it was a mess on the import. **ALL the whole notes were tied half notes. ALL!**

— [@yodaclaus](https://x.com/yodaclaus/status/1641095493)（2009-04-28、Daniel Spreadbury 宛て）

**テンポが playback-only 扱いになり、インポート側で欠落**

> The starting tempo is being exported from Finale as a **playback-only element**. Lots of programs import this correctly. Please submit bug reports to those that don't.

— MusicXML 発明者 [@MichaelDGood](https://x.com/MichaelDGood/status/1265321840446017539)（2020-05-26）

**MusicXML 仕様そのものに設計欠陥がある、という技術者見解**

> a lot of these types of glitches are caused by **design flaws in the MusicXML spec**.

— [@MJDucharme](https://x.com/MJDucharme/status/1828313935235158221)（2024-08-27）

**「一般目的フォーマットではなく lossy intermediary」**

> MusicXML exists but … **it is a lossy intermediary**.

— Naughty Dog の作曲・オーディオプログラマ [@michaelrmmiller](https://x.com/michaelrmmiller/status/1621587034694615040)（2023-02-03）

---

### 2.3 MIDI と MusicXML の役割混同・往復バグ

**Dorico → Logic：用途別に壊れる場所が違う（実測比較）**

- **MusicXML:** 記号は移るが音符・スラーは Logic デフォルト表示、**繰り返しは展開されない**、テンポはざっくり  
- **スタ MIDI:** リピート展開・テンポは通りやすいが、記譜記号の意味は別問題  

— [@takuyah](https://x.com/takuyah/status/2078691801943445613)（2026-07-19）

**自作ソフトで MIDI→MusicXML が勝手に移調**

> なーんで Midi インポートして MusicXML で書き出したら移調してんだ自作ソフト

— [@zutq74](https://x.com/zutq74/status/2077519354401628191)（2026-07-15）

**DAW 側 MIDI エクスポートの慢性バグ（BPM 強制・全トラック 1ch）**

> Studio One から MIDI エクスポートすると強制 BPM120 … 全トラックの MIDI チャンネルが 1ch で書き出される問題は残る

— [@caponyan](https://x.com/caponyan/status/2078602493148479685)（2026-07-18）

**Logic の MusicXML：右手しか読まれない／Finale でもおかしい**

— [@take2002](https://x.com/take2002/status/991484667512610817)（2018-05-02）

**Guitar Pro：MIDI は「相互運用できるはず」なのに実は破綻**

> In Guitar Pro 5, importing midi files was okay, but after 6 it was a mess… When bending strings or portamento… the pitch is not accurate. **Isn't midi supposed to be interoperable?**

— [@pPR4tT7ZoVQcoLb](https://x.com/pPR4tT7ZoVQcoLb/status/1707794246596763971)（2023-09-29）

**XG MIDI とソフト互換（中国語実務）**

> voicevox… MIDI 格式后来死活都导入出错… 怀疑是不太兼容 yamaha 的 xg midi

— [@DraTohru_XLN](https://x.com/DraTohru_XLN/status/1868380166617203189)（2024-12-15）

---

### 2.4 「全形式／多形式」をうたっても、需要の薄い出力は放置される

- MIDI エクスポートは「需要が少ないので直す気がないのか」という開発文化批判（[@caponyan](https://x.com/caponyan/status/2078602493148479685)）
- **オープンソースでも MusicXML を出さない**記譜エディタがある（「オープンソース ≠ オープンデータ」）

> One of the open source tools (not MuseScore) has an extremely proprietary mindset, perhaps the only music notation editor that **doesn't export to MusicXML**. Open source does not mean open data.

— [@MichaelDGood](https://x.com/MichaelDGood/status/1828152948939202771)（2024-08-26）

- LilyPond 側の古典的ギャップ: **MusicXML エクスポートが弱い／無い**認識（[@Poulpette_D](https://x.com/Poulpette_D/status/868503892228796416), 2017）

---

### 2.5 記譜法プラグイン層の失敗・不満（簡譜・中国語圏）

**コアが簡譜を更新しないことへのコミュニティ不満**

> musescore 一直不更新简谱，还被贴吧老哥说「洋人不照顾中国人很正常」，你倒是写啊

— [@last_sue](https://x.com/last_sue/status/1850403652122656951)（2024-10-27）

**「簡譜プラグインはあるが自分は未検証」**というパイプライン説明（正確性未保証のまま流通）

— [@uniswap12](https://x.com/uniswap12/status/2063520228051755187)（2026-06-07）: Basic Pitch → MuseScore MIDI インポート → 簡譜プラグイン。**「结果都不理想」「准确性一直没调好」**

**AI パイプラインで MIDI が出せない／譜面がトンチンカン**

- GPT プラグイン環境で MIDI が出せない（[@Fevenrrr](https://x.com/Fevenrrr/status/1957449031979761670)）
- LLM は画像処理は強いのに「楽譜→MIDI/MusicXML はいつもとんちんかん」（[@Uroak_Miku](https://x.com/Uroak_Miku/status/2076492986649866295)）

---

### 2.6 失敗パターン早見表

| パターン | 典型症状 | 投稿上の主因 |
|----------|----------|--------------|
| A. レイアウト損失 | 段組・スペーシング・改ページ崩壊 | MusicXML は論理寄り／物理弱 |
| B. 記号損失 | アーティキュレーション・強弱・ヘアピン | インポータ実装差・仕様の解釈差 |
| C. リズム崩壊 | 全音符→タイ二分、連符往復ミス | エンコーディング／量子化 |
| D. 再生専用情報 | テンポ欠落 | playback-only 要素 |
| E. 役割混同 | 記譜が欲しいのに MIDI だけ、逆も | 用途別エクスポート未設計 |
| F. 方言 MIDI | XG/GM、ベンド、チャンネル | 仕様方言 |
| G. 記譜法方言 | 簡譜・タブ・特殊譜 | コア非対応／プラグイン品質差 |
| H. ロックイン | MusicXML 非出力 | プロプライエタリ志向 |

---

## 3. 成功例・部分成功

### 3.1 エコシステム側が「互換」に本気を出す瞬間

**Finale 終了で MusicXML 品質競争が公式に加速**

> when we merged with HL, **Music XML import became an even bigger priority**… Now… we’ll be stepping that effort up big time.  
— [@Tantacrul](https://x.com/Tantacrul/status/1828188131557810647)（引用元スレッド内、2024-08）

> MuseScore really cares about MusicXML import!  
— [@brieflyhenryiv1](https://x.com/brieflyhenryiv1/status/1828274901842829692)（実装経験から）

**MusicXML 発明者の期待**

> With Dorico, MuseScore Studio, and Sibelius all competing for people switching from Finale, I hope we'll see a **big leap forward in MusicXML import quality** from all three.  
— [@MichaelDGood](https://x.com/MichaelDGood/status/1829580539537572008)（2024-08-30）  
議論の場として [W3C MusicXML CG](https://github.com/w3c-cg/musicxml/discussions) を推奨。

### 3.2 プラグインによるエクスポート拡張（成功アーキテクチャ）

- **Dolet for Sibelius**（MusicXML エクスポート強化プラグイン）継続リリース  
  — [@MichaelDGood](https://x.com/MichaelDGood/status/1610693419399262209) / [@MusicXML](https://x.com/MusicXML/status/1610691916353654784)（2023-01）
- **Sibelius 公式バッチ:** PDF + XML 一括エクスポート用プラグインがある、と Dorico 側が案内  
  — [@dspreadbury](https://x.com/dspreadbury/status/1332068586119159815)（2020-11-26）
- **MuseScore 簡譜プラグイン**を親子で vibecode（コミュニティ拡張の現実解）  
  — [@jhsu](https://x.com/jhsu/status/2004332723696283672)（2025-12-25）→ [github.com/jhsu/musescore-doremi](https://github.com/jhsu/musescore-doremi/)
- **ハープ弦名スペリング付き MusicXML** を複数ソフト向けに吐く専用アプリ  
  — [@tshiraiwa_o](https://x.com/tshiraiwa_o/status/2068602854651445495)（2026-06-21）

### 3.3 用途分離がうまくいったケース

> If you need to preserve the **played performance, use MIDI**. If you want the **notation**… use MusicXML.  
— Dorico PM [@dspreadbury](https://x.com/dspreadbury/status/1577940910461308929)（2022-10-06）

Cubase ↔ Dorico の MIDI/MusicXML 往復は「普通にできる」と公式が主張（問題は個別ファイル依存）  
— [@dspreadbury](https://x.com/dspreadbury/status/1602719866099752964)

### 3.4 ビジネス的成功（「导出が堀」）

中国語圏の議論（Notion 風楽譜アプリが累計約 200 万ドル、という話題への解釈）:

> 写乐谱这种软件最值钱的地方根本不是编辑播放，**是导出**。  
> MusicXML 和 MIDI 那套格式标准乱得要命，同一个谱子在 Finale 和 Sibelius 里打开经常错位，**光把这些大厂格式吃干净就能挡住 99% 想抄的人**。  
> …一年到头就为了能把手写谱干净导出成 PDF 发给学生…

— [@yangyue992125](https://x.com/yangyue992125/status/2066066602420781076)（2026-06-14）  
元ネタ: [@siantgirl](https://x.com/siantgirl/status/2065971539615576345)

→ **「全出力をきれいにやる」こと自体がプロダクトの差別化**、という現場認識。

### 3.5 部分成功：見た目が「意外と良い」ケースもある

> I just opened a musicXML score in #Dorico… IT LOOKS AMAZING  
— [@mikesperone](https://x.com/mikesperone/status/832046540483084290)（2017-02-16）

※ 成功談は**曲種・複雑さ・エクスポート元の品質**に強く依存。失敗談の方が圧倒的に多い。

---

## 4. 限界（仕様・法・アーキテクチャ）

| 限界 | 根拠 |
|------|------|
| **論理 vs 物理** | 論理は通るがレイアウトは弱い（[@sc3d](https://x.com/sc3d/status/1010574078942629891)） |
| **lossy 中継** | 一般用途の正本ではなく intermediary（[@michaelrmmiller](https://x.com/michaelrmmiller/status/1621587034694615040)） |
| **仕様欠陥／実装差** | 同じ MusicXML でもアプリごとに壊れる（[@MJDucharme](https://x.com/MJDucharme/status/1828313935235158221)、中国語「标准乱得要命」[@yangyue992125](https://x.com/yangyue992125/status/2066066602420781076)） |
| **プロプラ形式の直読は不可** | Sibelius 固有形式のリバースは技術的に困難かつ DMCA 等の法的問題 → **必ず MusicXML 経由**（[@dspreadbury](https://x.com/dspreadbury/status/1332068586119159815)） |
| **方言記譜はコア外** | 簡譜はプラグイン依存・コア停滞批判（[@last_sue](https://x.com/last_sue/status/1850403652122656951)） |
| **OMR/AI の下流品質** | スキャン→MusicXML/MIDI は宣伝多いが、実務では「結果不理想」連発（[@uniswap12](https://x.com/uniswap12/status/2063520228051755187)、[@Uroak_Miku](https://x.com/Uroak_Miku/status/2076492986649866295)） |

---

## 5. ベストプラクティス（投稿から帰納）

### 5.1 データ保全

1. **ベンダー固有形式 + MusicXML + PDF の三重バックアップ**（Finale 終了時の定石）  
   — [@hidetakumi](https://x.com/hidetakumi/status/1828258708880830475), [@TheChrMaestro](https://x.com/TheChrMaestro/status/976769640197120001)
2. **移行は「一発変換」ではなく「修復プロジェクト」として見積もる**  
   — [@TheRealTomahawk](https://x.com/TheRealTomahawk/status/1828540672384659494)
3. 大曲・旧曲は**無理に新ソフトへ移さず旧環境を維持**する判断も合理的  
   — [@MichaelZapruder](https://x.com/MichaelZapruder/status/1286679859692015617)

### 5.2 エクスポート設計（製品・プラグイン）

| 原則 | 内容 |
|------|------|
| **用途別出力** | 記譜交換=MusicXML／演奏再現=MIDI／配布=PDF（[@dspreadbury](https://x.com/dspreadbury/status/1577940910461308929)） |
| **コア + プラグイン** | 共通骨格はコア、方言記譜・特殊出力はプラグイン（Dolet / 簡譜 / ハープ特化） |
| **バッチ一括** | ライブラリ移行は「1ファイル手動」では死ぬ → PDF+XML バッチ（[@dspreadbury](https://x.com/dspreadbury/status/1332068586119159815)） |
| **エクスポート前の正規化** | Sibelius Magnetic Layout を Freeze してから MusicXML（[@robertpuff](https://x.com/robertpuff/status/1042216439791288320)） |
| **回帰チェックリスト** | アーティキュレーション・強弱・連符・リピート・テンポ・移調・チャンネルを**目視＋再生**（[@eddardmackey](https://x.com/eddardmackey/status/1604814328062001159)） |
| **オープンデータ** | OSS でも MusicXML 非出力は致命的評価（[@MichaelDGood](https://x.com/MichaelDGood/status/1828152948939202771)） |
| **品質競争への参加** | 仕様議論は W3C CG（[@MichaelDGood](https://x.com/MichaelDGood/status/1829580539537572008)） |

### 5.3 開発者が踏むべき地雷（失敗投稿の裏返し）

- MIDI→記譜で**量子化・移調・タイ展開**を暗黙にやらない  
- dynamics の MusicXML 値と MIDI velocity の対応は**アプリ依存**で逆算が必要、という泥臭い現実（[@marudebot](https://x.com/marudebot/status/1828794349607665847)）  
- 「全形式対応」を UI に並べるなら、**需要の薄い形式ほどテストが薄く壊れやすい**と自覚する  

---

## 6. 最新トレンド（2024–2026 投稿から）

### 6.1 Finale 終了（2024-08）＝最大の互換性ストレステスト

- サポート終了・Dorico 誘導が世界中で拡散（例: [@Piascore_store](https://x.com/Piascore_store/status/1828075664823742882), [@Komaniecki_R](https://x.com/Komaniecki_R/status/1828098556173173176)）
- 各社が **MusicXML import 強化**を公言・期待される局面
- ユーザー実態は「XML 吐き → 手直し」がデフォルト

### 6.2 プラグイン型・軽量記譜の再評価

| トレンド | 投稿例 |
|----------|--------|
| **ABC** を巨大 XML の対極として採用 | ScoreTail「not everything needs to be a giant XML file」([@ScoreTail](https://x.com/ScoreTail/status/2033885221867937989)) |
| **LilyPond を LLM の出力言語に** | 「Just use LilyPond as a language, not MusicXML」([@Lari_island](https://x.com/Lari_island/status/2034850676845764950)) |
| **簡譜・数字譜プラグイン** | MuseScore プラグイン自作・番茄简谱など多形式导出宣伝 |
| **タブ PDF/ASCII** | Ableton MIDI クリップ→ギタータブ ([@mekayama](https://x.com/mekayama/status/2078500145550004356)) |

### 6.3 OMR / AI → MusicXML + MIDI が「表の約束」

- Flat の Opuscan: 写真/PDF → 編集可能譜 → **MusicXML or MIDI**（[@flat_io](https://x.com/flat_io/status/2077069446087077893)）
- DeepMusic-OCR 等の宣伝（[@Mathias_don001](https://x.com/Mathias_don001/status/1983957745989537932)）
- 中国語: OMR プラットフォームが MusicXML+MIDI、さらに**軽量符号化**で MusicXML 冗長を圧縮（[@gaoren7716](https://x.com/gaoren7716/status/2057469965452591460)）
- ただし**品質・手修正前提**は変わらず（失敗例 2.5 参照）

### 6.4 パイプライン自動化（作曲→歌詞→記譜）

Cubase のコード/メロ MusicXML+MIDI と Synthesizer V を束ねて Dorico で歌詞入りメロ譜にする自作ツール  
— [@kento0716](https://x.com/kento0716/status/2078085688872890379)（2026-07-16）

→ **単一「全対応エクスポート」より、目的別複数形式をオーケストレーション**する流れ。

### 6.5 中国語圏のプロダクト観

- 「編集・再生より**导出**」
- 大メーカー互換の泥が**参入障壁**
- ピアノ教師・小編成向け **きれいな PDF** が課金ポイント  
（[@yangyue992125](https://x.com/yangyue992125/status/2066066602420781076)）

---

## 7. 機能設計への示唆（「プラグイン型網羅出力」を作るなら）

X 上の実務言説を、機能要件に落とすと次の通り。

```
[内部正本: 論理楽譜 IR]
        │
        ├─ Exporter: MusicXML  (交換・編集可能)  ← 最重要・回帰テスト厚く
        ├─ Exporter: MIDI      (演奏・DAW)       ← チャンネル/BPM/ベンド仕様を明記
        ├─ Exporter: PDF/SVG   (配布・印刷)       ← レイアウトはここが正
        ├─ Plugin: 簡譜 / タブ / ABC / LilyPond / ChordPro …
        └─ Plugin: ドメイン特化 (ハープ弦名, 教育用軽量符号化, OMR後処理…)
```

**必須 UX**

1. エクスポート時に **「何が失われるか」** を事前警告（lossy を隠さない）  
2. 形式ごとの **オプション**（レイアウト含む/除く、リピート展開、量子化、移調固定 等）  
3. 移行用 **バッチ + チェックリスト**  
4. プラグイン API: 「記譜法レンダラ」と「ファイルシリアライザ」を分離  
5. ゴールデンファイル回帰（Finale/Sibelius/Dorico/MuseScore 相互）

---

## 8. 主要出典インデックス（クリック用）

### 英語・開発/実務
| 投稿者 | 役割 | リンク |
|--------|------|--------|
| Michael Good | MusicXML 発明者 | [1829580539537572008](https://x.com/MichaelDGood/status/1829580539537572008), [1828152948939202771](https://x.com/MichaelDGood/status/1828152948939202771), [1265321840446017539](https://x.com/MichaelDGood/status/1265321840446017539) |
| Daniel Spreadbury | Dorico PM | [1332068586119159815](https://x.com/dspreadbury/status/1332068586119159815), [1577940910461308929](https://x.com/dspreadbury/status/1577940910461308929) |
| Tantacrul / MuseScore | プロダクト | [1828188131557810647](https://x.com/Tantacrul/status/1828188131557810647)（引用スレ） |
| Ted Mackey | 実務ミュージシャン | [1604814328062001159](https://x.com/eddardmackey/status/1604814328062001159) |
| M.R. Miller | ゲーム作曲/プログラマ | [1621587034694615040](https://x.com/michaelrmmiller/status/1621587034694615040) |
| The Tomahawk | 移行実務 | [1828540672384659494](https://x.com/TheRealTomahawk/status/1828540672384659494) |
| Robert Puff | 記譜ブログ | [1042216439791288320](https://x.com/robertpuff/status/1042216439791288320) |
| Flat | SaaS 記譜 | [2077069446087077893](https://x.com/flat_io/status/2077069446087077893) |
| ScoreTail | 協業エディタ | [2033885221867937989](https://x.com/ScoreTail/status/2033885221867937989) |

### 中国語
| 投稿者 | トピック | リンク |
|--------|----------|--------|
| 先手 · Ahead | 导出が堀・フォーマット混沌 | [2066066602420781076](https://x.com/yangyue992125/status/2066066602420781076) |
| 唐华斑竹 | AI→MIDI→MuseScore→簡譜パイプラインの不満 | [2063520228051755187](https://x.com/uniswap12/status/2063520228051755187) |
| last_sue | MuseScore 簡譜未更新批判 | [1850403652122656951](https://x.com/last_sue/status/1850403652122656951) |
| 小海豚笔记 | OMR+軽量符号化 | [2057469965452591460](https://x.com/gaoren7716/status/2057469965452591460) |
| DraTohru | XG MIDI 互換地獄 | [1868380166617203189](https://x.com/DraTohru_XLN/status/1868380166617203189) |

### 補助（日英混在の実務）
- [takuyah Dorico↔Logic 比較](https://x.com/takuyah/status/2078691801943445613)  
- [caponyan Studio One MIDI バグ](https://x.com/caponyan/status/2078602493148479685)  
- [zutq74 移調バグ](https://x.com/zutq74/status/2077519354401628191)

---

## 9. 調査上の限界

1. X の検索は**エンゲージメントとキーワードに偏る**。フォーラム（MuseScore/Dorico forum, Reddit r/composer）の方が技術詳細は厚い場合がある。  
2. 中国語の「全失敗事例」は英語ほどハッシュタグが揃わず、**製品宣伝投稿がノイズ**になりやすい。  
3. 一部は古い（2009–2018）が、**同じ失敗クラスが 2024–2026 でも再発**している点が重要。  
4. 本調査は**投稿の主張の真偽検証（ファイル再現実験）までは未実施**。設計判断にはゴールデンファイル試験を推奨。

---

## 10. 一言でまとめると

> **「全出力形式対応」はチェックボックス機能ではなく、lossy な現実を前提にした“エクスポート・プラットフォーム”問題である。**  
> 成功しているのは「全部完璧に変換する」製品ではなく、**用途別に正しい形式を出し、プラグインで方言を増やし、失われるものを隠さない**製品／ワークフローである。  
> 失敗例の大半は、MusicXML を lossless 正本だと信じたこと、MIDI と記譜を混同したこと、コアに無い記譜法を「対応済み」と誤認したことに帰着する。

---

*調査のみ（読み取り）。コード変更なし。*  
*注: グローバルルールの Slack `#倉田_ログ` 投稿は、本環境に Slack MCP／CLI が未接続のため実行できていません。接続可能になれば同内容で追記投稿できます。*
