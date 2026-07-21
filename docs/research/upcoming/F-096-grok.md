# 音楽採譜／記譜の「中間資産の再利用」  
## X（旧Twitter）実務・研究・開発者投稿調査（英語・中国語中心）

**調査日:** 2026-07-21  
**対象機能:** 手直し済み**拍グリッド／テンポマップ**と**音符（MIDI／MusicXML）**を、別プロジェクト・別DAW・別記譜ソフトへ持ち込むこと  
**方針:** 実投稿ベース。**失敗例を厚め**に。引用は投稿原文の要旨＋出典リンク  

---

## 0. この機能が実務で指しているもの

実務者の会話では、だいたい次の層が「中間資産」として語られる。

| 中間資産 | 典型フォーマット | 再利用先 |
|---|---|---|
| 手直し拍グリッド／テンポマップ | MIDI tempo track、DAW markers、.als内部 | 別曲プロジェクト、他DAW、stem納品先 |
| 手直し音符 | MIDI、MusicXML、自前JSON | 記譜ソフト、DAW、AIエージェント |
| 構造メタ | BPM、拍子、マーカー、調、バー単位ノート | コラボ納品、LLM可読スコア |

**核心の痛み:** 手直しは時間がかかるのに、**プロジェクト固有形式に閉じ込められ、持ち出せない／崩れる**。

---

## 1. 失敗例（重点）

### 1.1 Abletonはテンポマップを出せない——「15年フォーラムで懇願」

開発者／プロダクト側が、業界の詰まりを直球で書いている。

> **「Ableton can't export tempo maps. 15 years of forum threads begging for it. So I built Unableton. Upload your .als, get a MIDI file Pro Tools and Logic can actually read.」**  
> — @polsia（2026-04-16）  
> https://x.com/polsia/status/2044874260792193147

> **「Tempo map purgatory: spend 2 hours recreating what Ableton already knows.」**  
> — @polsia（2026-04-21）  
> https://x.com/polsia/status/2046606473262993478

**失敗の型:** プロジェクト内では完璧なテンポ情報があるのに、**中間資産としてexportできない** → 別プロジェクト／他DAWで**2時間かけて再作成**。

関連需要（ユーザー側）:

> **「ARA2 in 2026 or tempo map files export and import?」**  
> — @yulucosound（2026-06-02）  
> https://x.com/yulucosound/status/2061943289884922243

→ **ネイティブなテンポマップI/OとARA連携**が、いまも未解決要求として残っている。

---

### 1.2 AI転写MIDIが「全部120BPM／グリッド外れ」

MuScriptor（Kyutai×Mirelo）など最新audio→MIDIを**別プロジェクト（FL Studio等）にimport**した瞬間の失敗。

> **「Playing with this now and all the midi is off the grid? I think its just exporting at 120pm for everything? Are you getting outputs that recognize bpm?」**  
> — @whatdotcd（2026-07-15）  
> https://x.com/whatdotcd/status/2077467751631986886  
> （親スレ: Suno → MuScriptor → FL Studio 試験投稿）

**失敗の型:** 音符ピッチは取れても、**BPM／テンポマップが失われデフォルト120に落ちる** → 拍グリッドが全滅。

同系統の実務報告（精度は高くてもBPMが崩壊）:

> 曲をMIDIにした結果「**BPMが笑**」になる。最終的にAbletonのMIDIタイムストレッチで合わせている。  
> — @DJ_OMKT（2026-07-20 / 21）  
> https://x.com/DJ_OMKT/status/2079238420829008245  
> https://x.com/DJ_OMKT/status/2079374724967407621

**含意:** 転写精度（ピッチ）と、**再利用可能な拍グリッドの品質は別問題**。

---

### 1.3 コラボMIDIのテンポ／拍子がズレてプロジェクトに乗らない

> **「Best way to import multiple MIDI tracks to FL studio? Every time I import this file from a collaborator it's all weird with the tempo and time signature. It won't line up with the FL project」**  
> — @MonochroMenace（2024-08-02）  
> https://x.com/MonochroMenace/status/1819484741034561637

**失敗の型:** 複数トラックMIDIを**既存プロジェクトに差し込む**と、テンポ／拍子解釈が衝突し、**ノートはあるが拍グリッド上に乗らない**。

---

### 1.4 MusicXMLは「橋」だが、手直し成果を壊すことが多い

Finale終了時に噴出した**資産移行失敗**は、中間資産再利用の最大級ケーススタディ。

> **「The pathway is: save as MusicXML → import into Dorico → fix all the f\*\*\*ed up formatting and stuff that was lost. There's no import tool… Do it all yourself.」**  
> — @TheRealTomahawk（2024-08-27）  
> https://x.com/TheRealTomahawk/status/1828540672384659494

> 同一Finale内でもMusicXML export→importで崩れ、「**doesn't work**」。非西洋／グラフィカル記譜ではさらに使えない。  
> — @bathorykitsz（2024-08-26〜27）  
> https://x.com/bathorykitsz/status/1828250466641121465  
> https://x.com/bathorykitsz/status/1828254617668407646  
> https://x.com/bathorykitsz/status/1828092168680218845

MusicXML発明者本人も、テンポ要素の解釈差を指摘:

> Finaleが出した**playback-only tempo**を、相手ソフトが正しくimportしないケースがある。  
> — @MichaelDGood（2020-05-26）  
> https://x.com/MichaelDGood/status/1265321840446017539

**失敗の型:**

1. レイアウト／記譜装飾の喪失（手直し浄書が消える）  
2. テンポが「再生専用」扱いで消え、見た目テンポと再生テンポが分裂  
3. 複雑な記譜では**中間形式自体が成立しない**

---

### 1.5 MusicXMLとMIDIで「残る情報」が違う（誤った形式選択）

Dorico → Logic の実務比較（記譜側→制作側への中間資産移送）:

> **MusicXML:** 音楽記号は移るが、音符／スラー表示はLogic既定、**繰り返しは展開されない**、**テンポざっくり**  
> **スタMIDI:** 繰り返し展開・テンポ・音価・強弱が設定通り  
> — @takuyah（2026-07-19）  
> https://x.com/takuyah/status/2078691801943445613

Dorico製品側も同じ線引き:

> **演奏を残すならMIDI／記譜を残すならMusicXML（display quantise後）**  
> — @dspreadbury（2022-10-06）  
> https://x.com/dspreadbury/status/1577940910461308929

**失敗の型:** 「全部MusicXMLで持っていけばOK」という前提が、**テンポ・リピート・演奏ニュアンス**で破綻する。

---

### 1.6 納品時にテンポ資産が欠落する（コラボの日常事故）

制作現場のチェックリスト級の失敗列挙:

> **「テンポチェンジする曲なのにそのデータがない」**／BPM未記載／MIDI重複／頭が揃わない…  
> — @TomoyaKinoshita（2024-09-26）  
> https://x.com/TomoyaKinoshita/status/1839225406517555488

業界バイラル（stem納品）:

> **「PUT THE BPM IN THE FILE NAME WHEN YOU SEND STEMS」**（連呼）  
> — @swamisound（2025-10-21）  
> https://x.com/swamisound/status/1980490028263657477

> **「Who tf isn’t sending a midi tempo map with their stems!?」**  
> — @RossBeagan（2025-10-22）  
> https://x.com/RossBeagan/status/1981026070338904080

**失敗の型:** オーディオstemだけ渡すと、受け手が**拍グリッドを再推定**せざるを得ない。手直し済みテンポが**社会的に中間資産化されていない**。

---

### 1.7 拍間隔誤差の累積（中国語・理論寄り実務）

中国語圏で「扒带（耳コピ／拍合わせ）」の限界を数学的に述べる投稿:

> **拍間隔が測れない／表現が不正確だと誤差は必ず逐拍累積する。** 単位がBPMか対数かは関係なく、**精度**が鍵。**扒带でも原曲がどうしても合わない**ことがよくある。譜面は拍間隔の積分だから、単拍の時間誤差は累積する。  
> — @miumcii（2026-02-27）  
> https://x.com/miumcii/status/2027367264681693484

**失敗の型:** 手直しグリッドを別プロジェクトに移しても、**元のグリッド自体が累積誤差を抱えている**と、どこへ持ってもズレが再発する。

---

### 1.8 その他の「持ち込み」失敗パターン

| 失敗 | 投稿要旨 | 出典 |
|---|---|---|
| サンプレート不一致でimport不能 | VOCALOIDで「imported WAV… sampling rate is different」 | [@jaxonloid](https://x.com/jaxonloid/status/1945269239004164538) |
| 記譜ソフト側のテンポ操作バグ | MuseScoreでAndanteが全音符に付く等 | [@Tantacrul](https://x.com/Tantacrul/status/1521757175445692416) |
| ライブ／CDJの2倍速テンポ事故 | double time、sync offが応急処置 | [@dirtmonkeymusic](https://x.com/dirtmonkeymusic/status/1779855394744983782) |
| Audacity側のテンポ記憶汚染 | あるファイルを40にして以降、importが全部40 | [@ken_linke](https://x.com/ken_linke/status/2078659391235240264) |

---

## 2. 成功例（少ないが実在）

### 2.1 「MIDIテンポマップをDoricoへ」＋見た目テンポ維持

Grammyノミネート作曲家／プロデューサー:

> custom **MIDI tempo map を Dorico に import**しつつ、演奏者向けの**visual tempo markings**も残す手順を動画で公開。  
> — @daviddas（2026-02-06）  
> https://x.com/daviddas/status/2019610060318728375

**成功の型:** 再生用テンポ（機械）と表示用テンポ（人）を**分離して持ち込む**。

---

### 2.2 可変テンポ曲に対するReaperテンポトラック作成

> Suno／AI／人間演奏でテンポが揺れる曲に対し、**Reaperでtempo trackを作り、曲がクリックに乗っていなくてもマップを合わせる**方法。  
> — @KaiLaigo（2025-12-22）  
> https://x.com/KaiLaigo/status/2003192701618094244

**成功の型:** まず**1曲専用の手直しテンポ資産を作る** → 以降の編集・MIDI作業の土台にする。

---

### 2.3 AI転写後に「グリッド付き中間表現」へ変換して再利用

> MuScriptorで楽器別MIDI → **moe-fumenがLLM可読バンドル（beat grid, chords, piano-roll）を生成** → AIアシスタントが「bars 12–16のベース」を議論できる。  
> — @mochi_mochi_lab（2026-07-14）  
> https://x.com/mochi_mochi_lab/status/2077075103779840129

> Basic Pitchでローカル転写 → Claudeが**gridにマップ** → セルへ直リンク。  
> — @loopclubxyz（2026-06-23）  
> https://x.com/loopclubxyz/status/2069431955624456331

**成功の型:** 生MIDIをそのまま別プロジェクトに投げず、**拍グリッド付き中間IR（JSON／バンドル）を一回噛ませる**。

---

### 2.4 ライブラリ／ツール側の「tempo map round-trip」改善

> **「tempo maps now round-trip through MIDI import」**  
> — @kennethreitz42 / PyTheory（2026-06-30）  
> https://x.com/kennethreitz42/status/2071983887383765399

**成功の型:** 開発者側が「importでテンポが死ぬ」問題を**往復保証**として扱う方向。

---

### 2.5 中国語圏の実用パイプライン（成功だが「手直し前提」）

> PianoTransでピアノ音源→MIDI。**ただし「配合编曲软件量化校准」必須**。  
> — @ishowproduct（2026-05-16）  
> https://x.com/ishowproduct/status/2055502076449534128

> 扒谱が辛いなら、**既存MIDIを探してimportして填词**する選択肢。  
> — @Monodi_13（2026-05-19）  
> https://x.com/Monodi_13/status/2056686394953838936

**成功の型:** AI一発完結ではなく、**自動転写 → 量化／手直し → 別用途へ再利用**。

---

## 3. 限界（投稿から抽出される合意）

1. **拍グリッドは「音」より壊れやすい**  
   ピッチは残ってもBPM/tempo mapが落ちる（120BPM問題、MusicXML tempo要素問題）。

2. **中間形式のセマンティクス分裂**  
   - MIDI: 演奏寄り（テンポ、展開、CC）  
   - MusicXML: 記譜寄り（記号、レイアウトの一部）  
   - DAWネイティブ: 最強だが**閉じた資産**

3. **手直しの再現コストが高い**  
   Ableton内部に知っている情報を、受け側が2時間かけて再構築（tempo map purgatory）。

4. **誤差の不可逆性**  
   単拍誤差の累積（中国語投稿の積分モデル）。ズレたグリッドを別プロジェクトにコピーすると**ズレもコピー**される。

5. **記譜の複雑度でMusicXMLが死ぬ**  
   グラフィカル／前衛記譜ではexport自体が機能しない。

6. **コラボ文化の欠落**  
   BPMファイル名すら付けない／tempo mapを付けない納品が常態化。

---

## 4. ベストプラクティス（投稿ベース）

| # | 実務ルール | 根拠投稿 |
|---|---|---|
| 1 | **stem納品はファイル名にBPM** | @swamisound |
| 2 | **可能ならMIDI tempo mapを同梱** | @RossBeagan |
| 3 | **用途で形式を分ける**（演奏=MIDI／記譜=MusicXML） | @dspreadbury, @takuyah |
| 4 | **テンポチェンジ曲はテンポデータを必須チェック** | @TomoyaKinoshita |
| 5 | AI転写後は**必ず量化・手直し**してから再利用 | @ishowproduct, @DJ_OMKT |
| 6 | 可変テンポ曲は**先にテンポマップを作る**（Reaper等） | @KaiLaigo |
| 7 | Doricoでは**MIDI tempo map importとvisual tempoを分離運用** | @daviddas |
| 8 | プロプライエタリDAWは**中間抽出ツールを許容**（.als→MIDI等） | @polsia / Unableton |
| 9 | 将来の移行用に**MusicXML一括exportを保険として残す**（ただし過信しない） | @hidetakumi, @georgenagata, @benmorss |
| 10 | AI／LLM連携なら**beat grid付き中間バンドル**を用意 | @mochi_mochi_lab, @loopclubxyz |

---

## 5. 最新トレンド（2025–2026のX上）

### 5.1 マルチ楽器AI転写 → DAW持ち込みが急増
Kyutai **MuScriptor** リリース（楽器別MIDI）。デモは多いが、**BPM/グリッド保持が次の戦場**（off-grid報告が既に出ている）。  
https://x.com/kyutai_labs 関連スレ／@dotslashgabut のSuno→MuScriptor→FL試験

### 5.2 「閉じたDAW資産」をこじ開けるブリッジ製品
Ableton .als から tempo/time sig/markers 付きMIDIを抜く Unableton など。  
**ネイティブ未提供機能をサードパーティが埋める**構図が続く。

### 5.3 中間IR（JSON／LLM可読スコア）の台頭
- Melogen: `{ tempo, key, bars, notes:[{bar, offset_beats…}] }` でMIDI化  
  https://x.com/adamli0526/status/2026652092077863347  
- moe-fumen: beat grid + chords + piano-roll をLLMに渡す

→ **「手直し済みグリッド＋音符」を、プロジェクトファイルではなく構造化データとして再利用する**方向。

### 5.4 AI音楽ツールのMIDI export競争
Murekaの「real MIDI export」、Suno周辺のworkstation/MIDI export言及など。  
ただし現場では **「exportできてもグリッドが信用できない」** が次の苦情層。

### 5.5 NeuralNote / Basic Pitch 系の「転写後調整」UX
polyphony、pitch bend、**scale/time quantizationを聞きながら調整** → DAWへD&D。  
https://x.com/DanKornas/status/2079357160400580624  

**「自動→手直し→export」を同一UIに閉じる**のが製品トレンド。

### 5.6 中国語圏の論調
X上の**専門的な「拍网格复用」議論は英語より薄い**。代わりに:

- 扒谱の苦痛と**既存MIDI流用**  
- PianoTrans等の**一键转MIDI＋必须量化校准**  
- 拍間隔誤差の累積理論  

が中心。WeChat／Bilibili／小红书側に深い議論が逃れている可能性が高い（本調査の限界）。

---

## 6. 失敗モード・カタログ（実装／プロダクト設計向け）

採譜・記譜ソフトで「中間資産再利用」を設計するなら、X上の失敗は次の**チェックリスト**になる。

1. **固定BPMデフォルト落ち**（特に120）  
2. **可変テンポマップの非export**  
3. **テンポと表示記号の分離失敗**  
4. **拍子・小節線の解釈差**  
5. **リピート展開の有無**  
6. **複数MIDIトラック一括import時のプロジェクトテンポ衝突**  
7. **MusicXMLのplayback-only要素無視**  
8. **サンプルレート／単位（tick vs 実時間）の不一致**  
9. **手直しマーカーがプロジェクト固有で消失**  
10. **コラボ納品でメタデータ欠落（BPM/tempo map無し）**  
11. **累積誤差を持ったグリッドの無批判コピー**  
12. **複雑記譜の非対応（中間形式が表現不能）**

---

## 7. 総括（投稿から言えること）

- **成功例は「ワークアラウンドの共有」が中心**で、**ワンクリックで安全に再利用できる体験はまだ稀**。  
- **失敗例は圧倒的に多い**。特に  
  (a) DAWがテンポ資産を閉じ込め  
  (b) AI転写が音符は出してもグリッドを殺す  
  (c) MusicXMLが「全部持っていける」という過信を裏切る  
  の三点が繰り返し出る。  
- 実務のベストプラクティスは技術より**運用**: BPMをファイル名に、tempo mapを同梱、用途別にMIDI/MusicXMLを使い分け、AI後は必ず手直し。  
- 2026年の先端トレンドは、**AI転写そのもの**より **「手直し済みグリッド＋音符を、プロジェクト非依存の中間IRとして持つ」** 側にある。

---

## 8. 主要出典一覧（クリック用）

| テーマ | 投稿者 | URL |
|---|---|---|
| Ableton tempo map 非export | @polsia | https://x.com/polsia/status/2044874260792193147 |
| Tempo map purgatory | @polsia | https://x.com/polsia/status/2046606473262993478 |
| MIDI全部off-grid / 120BPM | @whatdotcd | https://x.com/whatdotcd/status/2077467751631986886 |
| 転写BPM崩壊＋ストレッチ救済 | @DJ_OMKT | https://x.com/DJ_OMKT/status/2079238420829008245 |
| FLへMIDI importでテンポ破綻 | @MonochroMenace | https://x.com/MonochroMenace/status/1819484741034561637 |
| MusicXML移行の地獄 | @TheRealTomahawk | https://x.com/TheRealTomahawk/status/1828540672384659494 |
| MusicXML self-roundtrip失敗 | @bathorykitsz | https://x.com/bathorykitsz/status/1828250466641121465 |
| playback-only tempo | @MichaelDGood | https://x.com/MichaelDGood/status/1265321840446017539 |
| MusicXML vs MIDI（Dorico→Logic） | @takuyah | https://x.com/takuyah/status/2078691801943445613 |
| MIDI vs MusicXML方針 | @dspreadbury | https://x.com/dspreadbury/status/1577940910461308929 |
| BPMファイル名必須 | @swamisound | https://x.com/swamisound/status/1980490028263657477 |
| MIDI tempo map同梱要求 | @RossBeagan | https://x.com/RossBeagan/status/1981026070338904080 |
| 納品チェック（テンポデータ欠落） | @TomoyaKinoshita | https://x.com/TomoyaKinoshita/status/1839225406517555488 |
| 拍誤差累積 | @miumcii | https://x.com/miumcii/status/2027367264681693484 |
| Dorico tempo map手順 | @daviddas | https://x.com/daviddas/status/2019610060318728375 |
| Reaper tempo track | @KaiLaigo | https://x.com/KaiLaigo/status/2003192701618094244 |
| beat grid中間バンドル | @mochi_mochi_lab | https://x.com/mochi_mochi_lab/status/2077075103779840129 |
| 量化校准必須（中国語） | @ishowproduct | https://x.com/ishowproduct/status/2055502076449534128 |
| tempo map I/O要求 | @yulucosound | https://x.com/yulucosound/status/2061943289884922243 |

---

### 調査上の注意
- Xのアルゴリズム／言語バイアスで、**英語のDAW・記譜移行トークは厚い**一方、**中国語の「拍网格复用」専門投稿は相対的に薄い**（扒谱・量化校准・誤差累積に散在）。  
- 日本語投稿も実務密度が高いもの（納品チェック、Dorico↔Logic）を補助的に採用した。  
- 本レポートは**実投稿の観測**であり、各製品の公式仕様書の網羅調査ではない。製品ロードマップ断定は避けている。

必要なら次の深掘りも可能です。  
1. **Ableton / Logic / Reaper / Dorico 別の「テンポ資産I/O」機能ギャップ表**  
2. **採譜プロダクト向け要件定義**（失敗モード→受け入れテストケース）  
3. **中国語圏をB站／小红书／知乎まで広げた補完調査**
