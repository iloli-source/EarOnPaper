# 採譜結果のLLM/エージェント可読エクスポート  
## X実務者・研究者・開発者投稿調査（英語・中国語中心 / 失敗例厚め）

**調査日:** 2026-07-21  
**対象機能:** 採譜結果を小節・コード・音符列などの**構造化テキスト**として出し、LLM/エージェントが読み・編集・再レンダリングできること  
**収集方針:** 実投稿ベース / 成功・失敗・限界・BP・トレンド / 失敗を厚く / 英語・中国語中心（関連が強い日本語投稿は補足）

---

## 0. 調査サマリ（先に結論）

| 軸 | 実務コミュニティの合意に近い像 |
|---|---|
| **何が動いているか** | Audio→MIDI が急加速。その先に **MIDI↔LLM可読テキスト**（leadsheet, 譜面バンドル, MusicXML, ABC, ChordPro）を載せる流れ |
| **成功の型** | 「人間向け記譜」ではなく **AI-native 正準フォーマット + 往復検証（roundtrip）** |
| **失敗の型（多い）** | ①MusicXMLが複雑になると**不正XML** ②画像譜面OCRは**局所は合って大局が崩れる** ③ABCは表現不足＋**無音/破損** ④LLMが**見た目は楽譜なのに中身が違う** ⑤実環境音でAMTが崩れる |
| **BP** | 画像より構造化テキスト / 小節単位ページング / コード生成はmusic21経由 / 生JSON・XMLを必ず検査 / 人間の耳で最終確認 |
| **トレンド** | full-# 採譜結果の LLM／エージェント可読エクスポート  
## X（旧Twitter）実務者・研究者・開発者投稿調査レポート

**調査日:** 2026-07-21  
**対象機能:** 採譜結果を「小節・コード・音符列」などの**構造化テキスト**として出力し、LLM／エージェントが読・編・修・往復できること  
**収集言語:** 英語中心＋中国語（関連が強い日本語実務投稿は補足）  
**出典方針:** 実投稿ベース。各主張の直後に出典リンク／投稿IDを付す  

---

## 0. 調査サマリ（先に結論）

| 軸 | 実務コミュニティのコンセンサス |
|---|---|
| **成功パターン** | Audio→（多楽器）MIDI → **AI-native な可逆テキスト**（leadsheet / 小節単位バンドル）→ LLMが小節単位で議論・編集 → MIDI/音源に戻す |
| **失敗の多発点** | ①MusicXMLの妥当性・冗長性 ②ABCの表現力不足 ③画像楽譜（OMR）誤読 ④局所は正しいが大局構造が崩れる ⑤「演奏指示」や無関係トークンの混入 ⑥ノイズ／伴奏下の認識崩壊 |
| **ベストプラクティス** | 人間向け記譜より**機械検証可能な可逆フォーマット**；roundtrip F1；トークン節約（music21コード生成等）；人間による耳と編集のループ |
| **最新トレンド（2025–2026）** | フルミックス多楽器 Audio-to-MIDI（MuScriptor/Mirelo+Kyutai）、leadsheet、「DAW for LLMs」、ABC継続学習（ChatMusician系） |

---

## 1. 成功例（Success）

### 1.1 leadsheet：MIDI を「LLMが読めるソースコード」にする（決定的成功例）

**@voidtarget**（Giovanni P.）は、Mirelo/KyutaiのAudio-to-MIDI発表を受けて **leadsheet** を公開。

> They taught machines to hear music. I wanted source code.  
> So I built leadsheet: **MIDI ↔ text a frontier LLM can read, edit, repair, and render back into sound. No fine-tuning.**  
> Canonical. Fuzzed. **Roundtrip F1 0.9997 on 3,463 notes.**  
> MIDI is the executable. .ls is the source.  
> — [x.com/voidtarget/status/2076519729351811572](https://x.com/voidtarget/status/2076519729351811572) · 2026-07-13

補足スレ:

- GitHub: `https://github.com/sinkingsugar/leadsheet`  
- 設計思想: 「人間／人間ツール向けではなく **AI native format**」  
  — [reply](https://x.com/voidtarget/status/2076551891677560917)
- 効率: 3,463 notes / 149 bars → **25 KB**、生イベントダンプより **6.4× 小さい**、かつ **双方向＋roundtrip oracle**  
  — [reply](https://x.com/voidtarget/status/2076531056468209800)
- 「ようやく Claude が MIDI テキスト経由で音楽を聴ける」  
  — [https://x.com/voidtarget/status/2075699346130223583](https://x.com/voidtarget/status/2075699346130223583)

**採譜ソフト機能への示唆:**  
「MusicXMLをそのまま吐く」より、**小節／トラック単位で可逆・検証可能な独自テキスト**の方が LLM 連携に直結する、という実務証明。

---

### 1.2 moe-fumen：「DAW for LLMs」— beat grid・コード・ピアノロールのバンドル

**@mochi_mochi_lab**（英語投稿）:

> I built a "DAW for LLMs" around it: self-hosted MuScriptor turns my songs into per-instrument MIDI, and **moe-fumen renders an LLM-readable bundle (beat grid, chords, piano-roll pages)**. Now my AI assistant can discuss **the bass in bars 12-16**  
> — [https://x.com/mochi_mochi_lab/status/2077075103779840129](https://x.com/mochi_mochi_lab/status/2077075103779840129) · 2026-07-14  
> Demo: https://fumen.nagi-soul.com/en

**示唆:** エージェント可読性の単位は「曲全体の巨大XML」ではなく、**小節レンジ＋パート（bass bars 12–16）を指名できるページ／バンドル**。

---

### 1.3 Audio-to-MIDI が上流を閉じる（Mirelo + Kyutai / MuScriptor）

**@MireloAI**（バズ投稿、約43万 view）:

> … Audio-to-MIDI model.  
> It takes a finished recording, identifies the instruments … separate MIDI tracks … voice, drums, bass, keys …  
> works **directly from the full mix** rather than requiring separate stems.  
> It also detects **chords, key, and tempo**  
> — [https://x.com/MireloAI/status/2075536492177354771](https://x.com/MireloAI/status/2075536492177354771) · 2026-07-10

**@kyutai_labs 周辺:** Claude Fable + Muscriptor でライブ可視化実験  
— [https://x.com/royaleerieme/status/2077304564244447339](https://x.com/royaleerieme/status/2077304564244447339)

**示唆:** 「LLM可読エクスポート」は単独機能ではなく、**AMT（自動採譜）→ 構造化テキスト → LLM** のパイプの中間層。

---

### 1.4 MusicXML／コード譜の「そこそこ使える」成功（条件付き）

- ChatGPTがコード譜を MusicXML で出力 → Sibelius で開ける  
  — **@Nu_Match1986** [https://x.com/Nu_Match1986/status/2062848248105377827](https://x.com/Nu_Match1986/status/2062848248105377827)（※音源からのコード判別ではない）
- ざっくりコード譜 → ChatGPT → マスターリズム譜相当の MusicXML（MuseScoreで整形）  
  — **@m_ishibashi_** [https://x.com/m_ishibashi_/status/2058495504309465441](https://x.com/m_ishibashi_/status/2058495504309465441)
- AI抽出 MusicXML を Claude Code に渡し、両手用に分割・精査して再出力  
  — **@tamezo_pf** [https://x.com/tamezo_pf/status/2076659396281770352](https://x.com/tamezo_pf/status/2076659396281770352)
- ChordPro を貼る／ChatGPTで PDF 歌本を一括変換  
  — **@nlevin** [https://x.com/nlevin/status/2078888839821828189](https://x.com/nlevin/status/2078888839821828189)
- Claude で作曲 → MIDI エクスポート → 自分でピアノ学習  
  — **@marinusklasen** [https://x.com/marinusklasen/status/2077337922345312587](https://x.com/marinusklasen/status/2077337922345312587)

成功条件はだいたい共通: **入力が既に半構造（コード譜・ChordPro）／人間が後編集する前提／単純〜中程度の複雑さ**。

---

### 1.5 研究系：ABC を「第二言語」にする ChatMusician

**@_akhaliq** 経由の論文紹介:

> ChatMusician … continual pre-training … on a text-compatible music representation, **ABC notation**, and the music is treated as a second language …  
> LLMs can be an excellent compressor for music, **but there remains significant territory to be conquered.**  
> — [https://x.com/_akhaliq/status/1762339575299551316](https://x.com/_akhaliq/status/1762339575299551316) · 2024-02-27

**@WenhuChen:** 共同研究として ChatMusician 発表  
— [https://x.com/WenhuChen/status/1821911860037230933](https://x.com/WenhuChen/status/1821911860037230933)

**MusicAgent:** LLM が音楽ツール群を分解・呼び出し  
— [https://x.com/_akhaliq/status/1714877890725110022](https://x.com/_akhaliq/status/1714877890725110022)

---

## 2. 失敗例（Failure）— 重点収集

### 2.1 MusicXML：複雑になると **valid を吐けない**

**@MathdeProf**（仏／英語圏開発者実務に直結）:

> … assez impressionnant pour un LLM, **mais on est vite bloqué par le format d'échange: dès que c'est un peu complexe, il n'arrive pas à produire du musicXML valide.**  
> （印象的だが、少し複雑になると **valid な MusicXML を出せない** ので交換フォーマットで即行き詰まる）  
> — [https://x.com/MathdeProf/status/2064767030041931858](https://x.com/MathdeProf/status/2064767030041931858) · 2026-06-10

---

### 2.2 「最新LLMでも」超単純タスクが落ちる

**@resnant**（研究者）:

> 最新のLLM使っても、**chord wikiからルートなぞってベースの譜面をMusicXMLで書かせるだけのシンプルなタスクが解けない**  
> — [https://x.com/resnant/status/2063624201416925612](https://x.com/resnant/status/2063624201416925612) · 2026-06-07

→ 「小節＋ルート＋ベースライン」程度でも **構造化エクスポート品質は保証されない**。

---

### 2.3 MusicXML にゴミトークン／不気味な演奏指示

**@helixspiral1**:

> ChatGPTに作曲させてmusicXMLを吐き出させると、演奏指示として **「answer」が頻出** して怖い  
> — [https://x.com/helixspiral1/status/2052737641351970927](https://x.com/helixspiral1/status/2052737641351970927) · 2026-05-08

→ スキーマは通っても **意味論が壊れる** 典型失敗。

---

### 2.4 Claude が書ける ≠ プロダクトが動く（UI／統合が EXTREMELY broken）

**@nullchecks**:

> **it is EXTREMELY broken right** …  
> TLDR: Claude can write MusicXML, so Claude and I made a tab … load sheetmusic in MusicXML/midi … **Interface is very broken** …  
> — [https://x.com/nullchecks/status/1896307864752255471](https://x.com/nullchecks/status/1896307864752255471) · 2025-03-02

---

### 2.5 ABC 経路の古典的失敗セット（ChatGPT プラグイン時代）

**@CidVisionz** チュートリアル内の警告（今も再発するクラス）:

> ⚠️ BE AWARE OF LIMITATIONS  
> 1. **ABC notation system is limited, it can't add all details of a song**  
> 2. **ABC Music Notation plugin will sometimes generate broken files, 0 sec or silent tracks**  
> 3. **GPT is not a music producer or a music notation writing tool**  
> — [https://x.com/CidVisionz/status/1660007890223022080](https://x.com/CidVisionz/status/1660007890223022080) · 2023-05-20  

同スレ:

> GPT … **usually will output bad songs if you leave too many decisions for it**  
> — [thread parent](https://x.com/CidVisionz/status/1660007864847433731)

---

### 2.6 画像楽譜／OMR：構造は拾えても音符中身が壊滅

**@AbhiDasOne**（Google AI DevTools）週末実験:

> task: reading music notation models are bad at — **Jianpu (简谱) and Sargam** …  
> Honest result: **reads structure well, the notes only partially (~9% content, ~29% with structure)**  
> — [https://x.com/AbhiDasOne/status/2078943934483677225](https://x.com/AbhiDasOne/status/2078943934483677225) · 2026-07-19

**@togo_soundbag**（英語圏と同型の実務失敗）:

> … 分析させたりするんですが、**画像だとめちゃくちゃ読み間違える**ので MusicXML で渡すようにしてます。  
> 出力も画像だと「正確」より「それっぽくする」方面に寄りがち  
> — [https://x.com/togo_soundbag/status/2074407741121343949](https://x.com/togo_soundbag/status/2074407741121343949)

**@grok** による OMR 精度の整理（引用的）:

> LLM systems with vision … convert old sheet music … accuracy is limited …  
> ChatGPT-5 ~47% / Gemini 2.5 Pro ~49% / Claude Opus 4 ~42% textual, 24% visual …  
> — [https://x.com/grok/status/2024647636188365109](https://x.com/grok/status/2024647636188365109)

---

### 2.7 「局所的には正しいが大局構造が壊れる」

**@Blarg08125613**（高エンゲージ）:

> It has the same issue with music as it has with image generation: **everything is kind of locally correct but it can’t figure out larger-scale structure.**  
> — [https://x.com/Blarg08125613/status/1896355878338748716](https://x.com/Blarg08125613/status/1896355878338748716) · 2025-03-03

**@riverxriverx**（プロデューサー）が AI の誤分析を一蹴:

> "Why I Got It Wrong I was looking at the sheet music text globally in the key of F Major…"  
> **shut up stupid ai thank god i got ears**  
> — [https://x.com/riverxriverx/status/2077363412980404635](https://x.com/riverxriverx/status/2077363412980404635) · 2026-07-15

→ 構造化テキストを渡しても、**調性感・コーラス中心・歌詞シラブル**で盛大に誤読する事例。

---

### 2.8 中国語圏：簡譜・演奏認識パイプラインの現場失敗

**@llsswssw3243**:

> 想尝试用claude用音频生成**陶笛简谱**的，感觉**效果不太行**  
> 还不如多听几遍跟着感觉就能吹出来了  
> — [https://x.com/llsswssw3243/status/2070348940856483964](https://x.com/llsswssw3243/status/2070348940856483964) · 2026-06-26

**@cups_table**（楽器演奏評価 × LLM 助言）:

> 做乐器音频信号识别 … 最大问题是**噪音** …  
> 环境音、伴奏、节拍器等都可能导致识别结果出现差异 …  
> 结合LLM大模型生成对应的建议和评价 … 当时也是做的很痛苦  
> — [https://x.com/cups_table/status/2032651377412067539](https://x.com/cups_table/status/2032651377412067539) · 2026-03-14

**示唆:** 簡譜／演奏フィードバック系は「LLMがテキストを読む」以前に、**信号→記号の誤差が下流 LLM を汚染**する。

---

### 2.9 ベンチマーク不在・時間見積もり失敗

**@headinthebox**（Erik Meijer）:

> **We need a benchmark for converting music scores into musicxml.**  
> (GPT-5.6 high, said it worked for 10m 42s, but more like **40 m wall clock time**)  
> — [https://x.com/headinthebox/status/2075637635033477463](https://x.com/headinthebox/status/2075637635033477463) · 2026-07-10

---

### 2.10 研究の苦い教訓：手書きの「コード構造」はスケールに負ける

**@jxmnop**（Jack Morris）:

> get obsessed with polyphonic music transcription …  
> brilliant idea: **explicitly encode chord structure** …  
> wake up to new Google paper … **MT3** … zero explicit structure … just a transformer + lots of data … blows my … model out of the water  
> **bitter_lesson.png**  
> — [https://x.com/jxmnop/status/1927385194601886065](https://x.com/jxmnop/status/1927385194601886065) · 2025-05-27

→ 「小節・コードを構造化する」は **LLM 入出力の設計**としては有効でも、**AMT モデル内部の表現として人間設計を押し込む**のは別問題、という教訓。

---

### 2.11 上流 MIDI 抽出側の未解決（ドラム等）

**@MireloAI** 自身の返信:

> The drums come as a **consolidated midi stem**, so there is still **some manual mapping** to be done at this stage.  
> — [https://x.com/MireloAI/status/2075624374338465847](https://x.com/MireloAI/status/2075624374338465847)

→ エクスポートが綺麗でも **楽器マッピング／GM ドラム配置** は人手。

---

### 2.12 失敗パターン早見表

| ID | 失敗クラス | 典型症状 | 代表投稿 |
|---|---|---|---|
| F1 | Schema 破綻 | invalid MusicXML | @MathdeProf |
| F2 | 意味論破綻 | `answer` が演奏指示 | @helixspiral1 |
| F3 | 表現力不足 | ABC で細部を載せられない | @CidVisionz |
| F4 | レンダ死 | 0秒／無音ファイル | @CidVisionz |
| F5 | 単純タスク不能 | chordwiki→ベース譜失敗 | @resnant |
| F6 | OMR 低精度 | 音符中身 ~9% | @AbhiDasOne |
| F7 | 大局崩壊 | 局所OK・構造NG | @Blarg08125613 |
| F8 | 自信満々の誤分析 | 調・シラブル誤読 | @riverxriverx |
| F9 | 信号汚染 | ノイズ／伴奏で認識崩壊 | @cups_table |
| F10 | 簡譜失敗 | 音→簡譜が耳に負ける | @llsswssw3243 |
| F11 | 統合破綻 | UI EXTREMELY broken | @nullchecks |
| F12 | 評価系不在 | score→MusicXML ベンチ要望 | @headinthebox |

---

## 3. 限界（Limitations）

1. **人間向け記譜フォーマット ≠ エージェント向け**  
   MusicXML は DAW／記譜ソフト向けに冗長。複雑度が上がると生成が壊れやすい（F1）。
2. **可逆性がなければ「編集して戻す」が成立しない**  
   leadsheet 陣営が roundtrip F1 を前面に出す理由。
3. **テキストは音楽に非直感的**（非技術者向け）  
   — [https://x.com/Artificially999/status/2077904231462269293](https://x.com/Artificially999/status/2077904231462269293)
4. **トークン／文脈窓**  
   長尺多声部を全部投げるとコストと誤差が膨張。ページ分割（moe-fumen）や music21 生成が対抗策。
5. **ABC の表現力天井**  
   細部（アーティキュレーション、高度な記譜）を載せ切れない（F3）。
6. **画像入力は「それっぽさ」バイアス**  
   正確さより見た目尤度（@togo_soundbag）。
7. **評価ベンチ不足**（@headinthebox）。
8. **ドラム等のセマンティクス標準が弱い**（@MireloAI）。

---

## 4. ベストプラクティス（Best Practices）

| # | 実践 | 根拠投稿 |
|---|---|---|
| BP1 | **AI-native 可逆テキスト**（MIDI↔text、roundtrip 検証） | @voidtarget leadsheet |
| BP2 | **小節・パート・ビートグリッド単位のバンドル**（「bars 12–16 の bass」） | @mochi_mochi_lab |
| BP3 | **画像より構造化（MusicXML/MIDI text）を入力に使う** | @togo_soundbag |
| BP4 | **MusicXML を直接吐かせず、music21 等のコード生成で複雑譜を作る（トークン節約）** | @kkpattern [https://x.com/kkpattern/status/1996486421448908814](https://x.com/kkpattern/status/1996486421448908814) |
| BP5 | **半構造入力**（ChordPro／ざっくりコード譜）から起こす | @nlevin, @m_ishibashi_ |
| BP6 | **LLM 出力は生 XML/JSON を必ず目視デバッグ** | @NFTMansa [https://x.com/NFTMansa/status/2076926508200054800](https://x.com/NFTMansa/status/2076926508200054800) |
| BP7 | **人間の耳で最終判定**（AIの理論説明を信じない） | @riverxriverx |
| BP8 | **決定論的 pass/fail ループ**（生成物を機械検証して再生成） | leadsheet oracle; 一般論として @nateberkopec の deterministic loops |
| BP9 | **上流 AMT はフルミックス多楽器を前提に設計**しつつ、ドラム等は人手マッピング余地を残す | @MireloAI |
| BP10 | **エージェント＋CLI／GUI で二次編集**（転写結果を人が直せる UI）— 字幕領域の類推だが構造化結果全般に転用可 | @dotey 系ワークフロー（音声転写だが「結果をエージェントが編集できない」問題の解） |

---

## 5. 最新トレンド（2025–2026）

```text
[Audio mix]
    → Multi-instrument AMT (MuScriptor / Mirelo+Kyutai)
    → Per-instrument MIDI (+ key/tempo/chords)
    → LLM-readable structured text
         • leadsheet (.ls)  — AI-native, roundtrip
         • moe-fumen bundle — beat grid / chords / piano-roll pages
         • MusicXML / ABC   — legacy interop (fragile)
    → Frontier LLM (Claude etc.): discuss / edit / repair
    → Render back to MIDI / DAW / score
```

| トレンド | 内容 | 代表 |
|---|---|---|
| T1 | フルミックス多楽器 Audio→MIDI | @MireloAI × @kyutai_labs |
| T2 | AI-native 可逆記号フォーマット | leadsheet |
| T3 | 「DAW for LLMs」／小節指名会話 | moe-fumen |
| T4 | ABC 継続学習（音楽を第二言語） | ChatMusician |
| T5 | LLM ツールオーケストレーション | MusicAgent |
| T6 | エージェントが MIDI／MusicXML を書く日常化 | FL/Claude 作曲→DAW 取り込み多数 |
| T7 | 評価・ベンチマーク要求の顕在化 | @headinthebox |
| T8 | 非西洋記譜（簡譜 Jianpu 等）への拡張需要と低精度 | @AbhiDasOne, @llsswssw3243 |

---

## 6. 採譜／記譜ソフト機能設計へのインプリケーション

製品機能「**採譜結果の LLM／エージェント可読エクスポート**」を出すなら、X 実務知からの優先順位は:

1. **必須:** 小節番号・拍グリッド・パートID・コード記号・音符列（ピッチ×開始×長さ）を含む **コンパクトな構造化テキスト**  
2. **必須:** **往復検証**（export → import → F1 / note-level diff）  
3. **推奨:** MusicXML は「互換エクスポート」、エージェント用は **別スキーマ**（leadsheet 思想）  
4. **推奨:** 長い曲は **ページ／小節レンジ分割**（bars 12–16 を議論可能に）  
5. **避ける:** 「MusicXMLをLLMに丸投げ生成」を主経路にしない（F1/F2/F5）  
6. **避ける:** 画像楽譜を唯一のエージェント入力にしない（F6）  
7. **UI:** 生テキストの検査ビュー＋人間修正（BP6, 二次編集）  
8. **メトリクス:** schema valid 率、roundtrip F1、小節境界一致、コード一致、人間評価（大局構造）

---

## 7. 出典インデックス（主要投稿）

| 投稿者 | 日付 | 言語 | 分類 | URL |
|---|---|---|---|---|
| @voidtarget | 2026-07-13 | EN | 成功 | https://x.com/voidtarget/status/2076519729351811572 |
| @mochi_mochi_lab | 2026-07-14 | EN | 成功 | https://x.com/mochi_mochi_lab/status/2077075103779840129 |
| @MireloAI | 2026-07-10 | EN | 成功／トレンド | https://x.com/MireloAI/status/2075536492177354771 |
| @_akhaliq | 2024-02-27 | EN | 研究成功／限界 | https://x.com/_akhaliq/status/1762339575299551316 |
| @MathdeProf | 2026-06-10 | FR | **失敗** | https://x.com/MathdeProf/status/2064767030041931858 |
| @resnant | 2026-06-07 | JA | **失敗** | https://x.com/resnant/status/2063624201416925612 |
| @helixspiral1 | 2026-05-08 | JA | **失敗** | https://x.com/helixspiral1/status/2052737641351970927 |
| @CidVisionz | 2023-05-20 | EN | **失敗** | https://x.com/CidVisionz/status/1660007890223022080 |
| @nullchecks | 2025-03-02 | EN | **失敗** | https://x.com/nullchecks/status/1896307864752255471 |
| @AbhiDasOne | 2026-07-19 | EN | **失敗** | https://x.com/AbhiDasOne/status/2078943934483677225 |
| @Blarg08125613 | 2025-03-03 | EN | **失敗** | https://x.com/Blarg08125613/status/1896355878338748716 |
| @riverxriverx | 2026-07-15 | EN | **失敗** | https://x.com/riverxriverx/status/2077363412980404635 |
| @llsswssw3243 | 2026-06-26 | ZH | **失敗** | https://x.com/llsswssw3243/status/2070348940856483964 |
| @cups_table | 2026-03-14 | ZH | **失敗** | https://x.com/cups_table/status/2032651377412067539 |
| @headinthebox | 2026-07-10 | EN | 限界 | https://x.com/headinthebox/status/2075637635033477463 |
| @jxmnop | 2025-05-27 | EN | 研究教訓 | https://x.com/jxmnop/status/1927385194601886065 |
| @kkpattern | 2025-12-04 | EN | BP | https://x.com/kkpattern/status/1996486421448908814 |
| @togo_soundbag | 2026-07-07 | JA | BP／失敗 | https://x.com/togo_soundbag/status/2074407741121343949 |

---

## 8. 調査上の注意

- X 検索はセマンティック／キーワード混合。**中国語の「采谱＋LLM」直球失敗投稿は英語より密度が薄く**、簡譜・楽器認識・一般 LLM 幻覚の隣接投稿を含めた。  
- 日本語投稿は英語・中国語中心指定の**補足**として、MusicXML 実務失敗が濃いものを採用。  
- プロモ／論文RT は「成功」より「トレンド信号」として扱う。  
- Slack `#倉田_ログ` への自動投稿は、本環境で Slack MCP が接続されておらず未実施。必要なら投稿文を用意可能。

---

### 一行でいうと

> **2026年の実務前線は「MusicXMLをLLMに読ませる」ではなく、「採譜→可逆なAI-native構造化テキスト→小節単位でエージェントが編修→MIDIに戻す」**。失敗の大半は、人間向け記譜の冗長・脆弱スキーマと、局所正しさに隠れた大局崩壊に集中している。
