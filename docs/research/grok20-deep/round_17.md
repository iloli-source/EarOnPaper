日本の採譜AI動向をXで横断検索します。国産ツール、産総研/京大/明治のAMT、耳コピ新サービス、MuScriptor反応を並行で拾います。MuScriptorは十分拾えました。次に国産ツール・研究室AMT・耳コピ系サービスを深掘りします。# Xライブ検索：2026年・日本の採譜AI動向

調査日目安：**2026年7月**（投稿は2025後半〜2026/7末）。実投稿＋リンク中心。

---

## 1. いまの本命：MuScriptor（多楽器フルミックス→MIDI）

**Mirelo × Kyutai Labs** の Audio-to-MIDI。ステム分割なしでフルミックスから楽器別MIDI、コード／キー／テンポも出す、というのが日本語圏の話題の核。

| 日付 | 内容 | リンク |
|------|------|--------|
| 2026/7/10 | 公式発表（多楽器同時MIDI、フルミックス直接、コード・キー・テンポ） | [x.com/MireloAI/status/2075536492177354771](https://x.com/MireloAI/status/2075536492177354771) |
| 2026/7/23 | 最高精度版の **API 公開**（OSSは継続） | [x.com/MireloAI/status/2080342247418048750](https://x.com/MireloAI/status/2080342247418048750) |
| GitHub | モデル本体 | [github.com/muscriptor/muscriptor](https://github.com/muscriptor/muscriptor) |

### 日本語圏の反応（実投稿）

**紹介・バズ系**
- ハカセ アイ：多楽器同時MIDI化を「AI作曲の革命児」として解説（♡252 / RT26 / 約1.8万表示）  
  → [x.com/ai_hakase_/status/2076895214392824152](https://x.com/ai_hakase_/status/2076895214392824152)
- gear machine：ローカル試用＋一時公開デモ。「複雑なボーカルDnBでも取れる」（♡536 / 約11万表示）  
  → [x.com/grmchn4ai/status/2076190087017324581](https://x.com/grmchn4ai/status/2076190087017324581)
- AI速報：API公開を日本語で速報  
  → [x.com/AIMIRAI46487/status/2080494315017802092](https://x.com/AIMIRAI46487/status/2080494315017802092)
- regonn&curry.fm：ポッドキャストで MuScriptor を話題に  
  → [x.com/regonn_curry/status/2080897687709454468](https://x.com/regonn_curry/status/2080897687709454468)

**実務ユーザーの手触り**
- mameshiba：自作 Audio→MIDI アプリ。「実用レベルで衝撃」  
  → [x.com/mameshiba______/status/2079609494930415780](https://x.com/mameshiba______/status/2079609494930415780)
- あにP：ストリングスもMIDI可。ステム分割後の方が精度高い／分析時短が価値  
  → [x.com/kaki_GT/status/2079552514689806661](https://x.com/kaki_GT/status/2079552514689806661)
- 茶P：「割と良いがピアノMIDIは惜しい」  
  → [x.com/Sub_Cha_Sub/status/2080868304722506056](https://x.com/Sub_Cha_Sub/status/2080868304722506056)
- Ekt：「精度が良いという話はジャンル依存では？」  
  → [x.com/Ektmlnum/status/2080153123520409865](https://x.com/Ektmlnum/status/2080153123520409865)
- 没研：「令和曲を自力打ち込みなしでMIDIで聴ける」（♡36）  
  → [x.com/Qto6BshdBJYXdch/status/2079873511284416967](https://x.com/Qto6BshdBJYXdch/status/2079873511284416967)

**反応の要約**
- フルミックス多楽器が一気に「使える」帯に入った、という興奮
- ただし **ピアノ／高密度曲／ジャンル依存** で補正前提
- ステム分割→楽器別の二段構えがまだ強い

---

## 2. 国産・日本語圏で使われているツール／サービス

### A. 個人開発ハイブリッド（国産実装の最前線）

**@2zn01v** のブラウザ完結採譜ツール（2026/7/21 連投）

- ベース：**MuScriptor**
- 強弱・ピッチベンド：**Basic Pitch**
- コード：**ISMIR2019 LVCR**
- 出力：MIDI / MusicXML / Guitar Pro、3Dピアノ運指、リアルタイム録音採譜
- サーバ非送信（ローカルブラウザ）

| 投稿 | リンク |
|------|--------|
| 音源指定／録音採譜、楽器指定で精度UP | [status/2079547395646656911](https://x.com/2zn01v/status/2079547395646656911) |
| ピアノロール・コード・フレット連動 | [status/2079549593310859429](https://x.com/2zn01v/status/2079549593310859429) |
| MIDI / MusicXML / GP 出力 | [status/2079550837966393441](https://x.com/2zn01v/status/2079550837966393441) |
| 3Dピアノモーション | [status/2079551976443138414](https://x.com/2zn01v/status/2079551976443138414) |
| ハイブリッド構成の説明 | [status/2079554048135704732](https://x.com/2zn01v/status/2079554048135704732) |

→ 2026の国産っぽい動きは「独自巨大モデル」より **OSS AMT の組み合わせ製品化**。

### B. ヤマハ Extrack（耳コピ支援アプリ）

パート分離・コード・押さえ方・テンポ／キー変更。無料でもドラム／ベース／ボーカル分離。

- バードくん（エレクトーン層に拡散、♡49）  
  → [x.com/birdkunSTAGEA/status/2080814494675280312](https://x.com/birdkunSTAGEA/status/2080814494675280312)
- 利用者「夢のようなアプリ」  
  → [x.com/u_kyo_u2323/status/2080104381316473022](https://x.com/u_kyo_u2323/status/2080104381316473022)

### C. 定番＋比較（日本語DTM圏）

サウスンの **耳コピ支援ツール比較表**（♡402 / 約2.9万表示）  
→ [x.com/southn_channel/status/2080412642137747762](https://x.com/southn_channel/status/2080412642137747762)

| 用途 | よく出る名前 |
|------|----------------|
| テンポ・スケール | deCoda |
| コード | Cubaseコードトラック、deCoda |
| 音程・採譜 | **WaveTone**、RipX DAW Pro |
| 汎用Audio→MIDI | **Basic Pitch**、Melodyne、Open Music AI |

**WaveTone**（国産寄り定番）
- 導入： [x.com/akuniso315/status/2080608829084254346](https://x.com/akuniso315/status/2080608829084254346)
- 自動採譜デモ： [x.com/Urakocat0103/status/2079940424270221723](https://x.com/Urakocat0103/status/2079940424270221723)
- Basic Pitch と比較する声も： [x.com/kykukaz32768/status/2080303692444844126](https://x.com/kykukaz32768/status/2080303692444844126)

**その他**
- **Uフレット**：コード譜リクエスト文化が継続  
  → [x.com/shenyang81150/status/2079583716557603209](https://x.com/shenyang81150/status/2079583716557603209)
- 人力耳コピ市場（ココナラ等）も健在  
  → [x.com/pianoasachan/status/2080770245053256018](https://x.com/pianoasachan/status/2080770245053256018)
- RipX 日本語レビュー（ステム分解→耳コピ）  
  → [x.com/adsrx/status/2048280320403997087](https://x.com/adsrx/status/2048280320403997087)（2026/4）

### D. 現場の不満・限界

- 「AI譜面化はいい加減、また地道耳コピ」  
  → [x.com/KATa_fp_fr/status/2080970722047062228](https://x.com/KATa_fp_fr/status/2080970722047062228)
- 東方系高密度曲で自動採譜がフリーズ  
  → [x.com/komugiko_sma/status/2080974032468586651](https://x.com/komugiko_sma/status/2080974032468586651)
- iZotope系ステム＋AIは精度出るが **権利的にやりづらい**  
  → [x.com/shimafuri_d/status/2081029619495698739](https://x.com/shimafuri_d/status/2081029619495698739)

---

## 3. 研究室・AMT／音楽情報処理（日本）

X上で **2026に継続発信が濃いのは産総研（後藤真孝系）**。京大・明治の「AMT専用」新成果は、この期間の日本語ポストではほぼ拾えず。

### 産総研（後藤真孝 / 知的メディア）

| 内容 | リンク |
|------|--------|
| コロナ社『音楽情報処理』（編著・後藤）。**自動採譜**を鑑賞・創作の章で扱う書籍 | [x.com/coronasha/status/2023921223244361847](https://x.com/coronasha/status/2023921223244361847)（引用元：産総研公式 [AIST_JP 2026/2](https://x.com/AIST_JP/status/2021904689852191116)） |
| 音学シンポジウム2026・優秀発表賞（知的メディア） | [x.com/AIResearchAIST/status/2076529278670557377](https://x.com/AIResearchAIST/status/2076529278670557377) |
| 後藤：マジカルミライ2026 / TextAlive・Kiite | [x.com/MasatakaGoto/status/2080284294149517803](https://x.com/MasatakaGoto/status/2080284294149517803) |
| 25周年冊子に Songle・音楽体験 | [x.com/MasatakaGoto/status/2062106768038109414](https://x.com/MasatakaGoto/status/2062106768038109414) |

→ 研究の表舞台は「純粋AMT一発」より **Songle / Kiite / TextAlive** など鑑賞・創作支援インフラ。

### 東大・ピアニスト／AMTの文脈

- 角野隼斗：大学院で **AI自動採譜を研究**（AERA UNIV.）  
  → [x.com/AERA_University/status/2000679761027432645](https://x.com/AERA_University/status/2000679761027432645)

### 産総研×筑波大（音響知能／分離寄り）

- 板東芳明：音源分離・ロボット聴覚・生成AI基盤の募集  
  → [x.com/yoshipon0520/status/2072343765235437577](https://x.com/yoshipon0520/status/2072343765235437577)

### 京大／明治について（検索ギャップ）

- **京大・明治の「AMT最新論文・デモ」系の日本語X投稿は、今回のライブ検索ではほぼヒットせず**
- 明治は「明治十七年の上海アリス」MIDIネタ等がノイズとして大量に混ざる
- 研究室AMTは **論文・学会（ISMIR / 音学シンポジウム）側** に偏り、Xの一般話題は製品（MuScriptor / Extrack）に寄っている

---

## 4. 周辺トレンド（採譜AIの生態系）

| テーマ | 要点 | 投稿 |
|--------|------|------|
| 欧州権利データ | GEMA「PLAI」：生成AIではなく **分析・採譜・文字起こし支援AI** 向け学習データ | [x.com/SuzukiTaka/status/2080991357867340246](https://x.com/SuzukiTaka/status/2080991357867340246) |
| AI生成曲の氾濫 | インディー制作の需要感への影響論 | [x.com/mahjong_medlay/status/2080604084311384458](https://x.com/mahjong_medlay/status/2080604084311384458) |
| 生成 vs 採譜 | 菊地成孔工房など「生成AI利用声明」は別軸で活発 | [x.com/SHIN_ON_GAK/status/1933559800371294398](https://x.com/SHIN_ON_GAK/status/1933559800371294398) |

---

## 5. 2026年7月時点の見取り図

```
[フルミックス]
    ├─ MuScriptor（多楽器MIDI・OSS+API） ← 2026の主役
    ├─ Basic Pitch / WaveTone / RipX / Melodyne（単旋律〜精密編集）
    ├─ ステム分離 → 楽器別AMT（精度重視ルート）
    └─ 国産ラッパ
         ├─ YAMAHA Extrack（学習・耳コピ支援）
         └─ 個人開発（MuScriptor+Basic Pitch+コード認識）
```

| レイヤ | 状況 |
|--------|------|
| **研究（産総研）** | 自動採譜を含む音楽情報処理の蓄積＋Songle/Kiite等のサービス化。2026も賞・登壇が続く |
| **製品（世界）** | MuScriptor が「フルミックス多楽器」で議論を上書き |
| **製品（日本）** | Extrack・WaveTone・個人ハイブリッド。巨大国産基盤モデルは見えない |
| **ユーザー感覚** | 「時短・0→1」は革命。「完成譜面」はまだ人手。権利も意識 |

---

## 6. フォロー用リンク一覧（主要）

1. MuScriptor発表: https://x.com/MireloAI/status/2075536492177354771  
2. MuScriptor API: https://x.com/MireloAI/status/2080342247418048750  
3. GitHub: https://github.com/muscriptor/muscriptor  
4. JP解説（高エンゲージ）: https://x.com/ai_hakase_/status/2076895214392824152  
5. ローカル試用デモ: https://x.com/grmchn4ai/status/2076190087017324581  
6. 国産ハイブリッド説明: https://x.com/2zn01v/status/2079554048135704732  
7. 耳コピツール比較: https://x.com/southn_channel/status/2080412642137747762  
8. Extrack: https://x.com/birdkunSTAGEA/status/2080814494675280312  
9. 産総研・音楽情報処理本: https://x.com/coronasha/status/2023921223244361847  
10. 角野・自動採譜研究: https://x.com/AERA_University/status/2000679761027432645  

---

**補足:** 京大／明治のAMT最新を論文単位で追うなら、Xより **音学シンポジウム・ISMIR・IPSJ MUS** のプロシーディング側が本筋。必要なら「研究室・論文側だけ」を別途ウェブ／学会軸で掘れます。
