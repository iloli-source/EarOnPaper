# X調査レポート：多声部一括採譜（バンド／アンサンブル・フルスコア／小編成2–3パート）

**調査日**: 2026-07-21  
**調査対象**: X（旧Twitter）上の実務者・研究者・開発者投稿（英語中心、中国語・日本語実務投稿を補完）  
**機能定義**: フルミックス（または少数ステム）から**複数声部を同時に**MIDI／五線譜相当へ起こし、パート別スコアや小編成フルスコアを得る一連の処理（AMT: Automatic Music Transcription）

---

## 1. 結論サマリー（実務視点）

| 観点 | 現状（X上の合意に近い像） |
|------|---------------------------|
| **成功の定義** | 「完成譜の一発生成」ではなく、**編集可能なパート別MIDIの下書き**が取れること |
| **最難所** | ポリフォニー（同一スペクトルを争う複数楽器）、打楽器マッピング、ベロシティ／アーティキュレーション、大域構造 |
| **2026年の転換点** | **MuScriptor**（Kyutai × Mirelo）：フルミックスから多楽器MIDIを返す「オープン重み」モデルが話題の中心 |
| **失敗の主因** | 単楽器モデルをフルミックスに無理当て／ステム分離のbleed→採譜連鎖／量子化前提の破綻／データ不足とジャンル偏り |
| **現場の定石** | **下書き→手修正**、楽器リスト条件付け、BPM合わせ、スケール／時間量子化、ドラムは別ワークフロー |

開発者側の定型フレーズは一貫している。

> *Music transcription really has been missing its whisper moment. Polyphony is the hard part, n instruments fighting over the same spectrum.*  
> — [@helloLizZhang](https://x.com/helloLizZhang/status/2075615962091729343)（2026-07-10）

> *Music is missing its "openai-whisper". … Are we there yet?*  
> — [@honualx](https://x.com/honualx/status/2075560798684873052)（Kyutai / MuScriptor公開時）

---

## 2. 技術・製品マップ（投稿で繰り返し出るもの）

| 系統 | 代表 | 多声部一括との関係 |
|------|------|-------------------|
| **単楽器／狭域** | Onsets & Frames（ピアノ）、Basic Pitch / NeuralNote | ポリフォニー可だが「フルバンド一括」ではない |
| **多タスク多トラックAMT** | **MT3**（Google, 2021–22） | 多楽器の基線。データ規模で単一楽器CNNを圧倒した「苦い教訓」投稿あり |
| **フルミックス多楽器** | **MuScriptor**（2026-07） | 現状X上で最も語られる「一括採譜」本命 |
| **分離→採譜パイプライン** | Demucs / Moises → Melodyne / Basic Pitch | 小編成〜バンドの実務定番。MIDI化がボトルネックという失敗談多数 |
| **下流** | Decomposer（MIDI→Strudelコード）、DAWインポート | 採譜後の「使える譜」への変換が別問題 |

---

## 3. 成功例（実投稿ベース）

### 3.1 フルミックス→楽器別MIDI（MuScriptor）

**Kyutai公式**が「任意ジャンルの録音を楽器ごとにMIDI化」と発表。従来ボトルネックだった**実録音付き大規模データ**を強調。

> *Give it a recording in any genre: pop, classical, metal, jazz, whatever, and it transcribes the individual instruments into MIDI.*  
> — [@kyutai_labs](https://x.com/kyutai_labs/status/2075540047613276197)

> *The main improvement comes from data, the lack of which has bottlenecked automatic music transcription since MT3 (2022). We collected a dataset of 170k music recordings (11k hours)…*  
> — 同スレ続報

**Mirelo公式**も「ステム不要でフルミックスから voice / drums / bass / keys 等を分離MIDI化」と主張。

> *Unlike most existing solutions, our model works directly from the full mix rather than requiring separate stems.*  
> — [@MireloAI](https://x.com/MireloAI/status/2075536492177354771)

**中国語ユーザーの成功報告**（管弦楽テクスチャ）:

> *MuScriptor — 音频直接转 MIDI，刚才拿一段管弦乐试了下，效果出乎意料地好，复杂的多乐器织体也能扒得七七八八*  
> （管弦楽を試したら意外と良く、複雑な多楽器テクスチャもだいたい扒れる）  
> — [@YMike59492](https://x.com/YMike59492/status/2075840791281619050)

※「七七八八＝だいたい」は、成功報告でも**完全自動スコアではない**ニュアンスを含む重要な表現。

### 3.2 研究コミュニティの「苦い成功」：MT3とデータ量

> *spend months implementing complicated chord-aware audio model… beat transcription baseline… wake up to new Google paper on music transcription… MT3… zero explicit structure… just a transformer + lots of data… blows my (piano-specific) CNN out of the water… bitter_lesson.png*  
> — [@jxmnop](https://x.com/jxmnop/status/1927385194601886065)（Jack Morris, 2025-05）

多声部一括の「成功条件」は構造的特徴量より**スケールとデータ**だ、という実務的教訓として広く共有されている。

### 3.3 小編成・単パート寄りの成功（下書き用途）

**Basic Pitch / NeuralNote**（トーン系・声含むポリフォニー）:

> *Turning a melody or chord recording into editable MIDI shouldn’t mean rebuilding every note by hand.*  
> — [@DanKornas](https://x.com/DanKornas/status/2079357160400580624)（NeuralNote紹介）

**日本語実務者**（精度は限定的でも有用）:

> *精度はめちゃ高いわけではないけど、打ち込みに慣れていない場合は0から打ち込むよりは絶対に楽*  
> — [@NoR3_Music](https://x.com/NoR3_Music/status/2077725459601928277)

**Abletonのハーモニー用Audio-to-MIDI**を「だいたい合ってからスケールに押し込む」運用:

> *Ableton often gets it slightly wrong, adding bad notes. instead of manually fixing it, just forcing it into scale tends to be a quick way to get close.*  
> — [@dj_irl](https://x.com/dj_irl/status/2016891106236256452)

### 3.4 成功パイプライン事例

| パイプライン | 投稿 | 示唆 |
|--------------|------|------|
| Suno → MuScriptor → FL Studio | [@dotslashgabut](https://x.com/dotslashgabut/status/2075736401606500711) を [@honualx](https://x.com/honualx/status/2075894629728154054) が引用 | 生成音源の「再編集可能化」 |
| MuScriptor → Decomposer → 手書き修正（Doobie Bros） | [@haiyewon](https://x.com/haiyewon/status/2079240520942154062) | **自動→数日の手作業**でグルーヴを取り戻す |
| Demucs Split + piano roll + score generation（Gradio） | [@fffiloni](https://x.com/fffiloni/status/2078128083995963779) | 分離を前処理に戻すハイブリッドUI |
| ステム分解 → MelodyneでBass/Drums MIDI | [@SchrgeMusic0626](https://x.com/SchrgeMusic0626/status/2074443907702915410) | 小〜中規模制作で現実的 |

---

## 4. 失敗例・限界（重点：投稿＋公式限界の突合）

> **注**: 「一括採譜でフルスコア完成」を期待した失敗は、デモ成功投稿より**散発的・断片的**に出やすい。以下は（A）利用者の明示失敗、（B）開発側が認める構造限界、（C）隣接工程（分離・MIDI編集）で爆発する失敗、を分けて記載。

### 4.1 失敗類型A — ポリフォニー／スペクトル衝突

| 失敗モード | 内容 | 出典 |
|------------|------|------|
| **同一帯域の楽器奪い合い** | 多楽器が同じスペクトルを争い、パート同定が崩れる | [@helloLizZhang](https://x.com/helloLizZhang/status/2075615962091729343) |
| **密なジャズ** | 高密度ジャズで「Whisper相当」未達を検証する、という開発者／ビルダーの姿勢 | 同上（“Testing on some dense jazz recordings tonight”） |
| **局所正解・大局崩壊** | 部分的には正しいが大域構造（声部・様式）が破綻 | [@Blarg08125613](https://x.com/Blarg08125613/status/1896355878338748716)（スコア生成系への批判として） |

### 4.2 失敗類型B — 「MIDIは取れるが譜として使えない」

| 失敗モード | 内容 | 出典 |
|------------|------|------|
| **誤音の混入** | Ableton Audio-to-MIDIが少しずれ、**余計な音を足す** | [@dj_irl](https://x.com/dj_irl/status/2016891106236256452) |
| **精度不足の公認** | Basic Pitch系は「精度は高くない」がゼロからの入力より楽 | [@NoR3_Music](https://x.com/NoR3_Music/status/2077725459601928277) |
| **手修正が本体** | MuScriptor出力でも「days of hand-writing … until it grooved」 | [@haiyewon](https://x.com/haiyewon/status/2079240520942154062) |
| **MIDI化が最遅工程** | ステム分離後も「MIDIが一番時間がかかる」 | [@SchrgeMusic0626](https://x.com/SchrgeMusic0626/status/2074443907702915410) / 反応 [@sorane_aimusic](https://x.com/sorane_aimusic/status/2074614727788143038) |
| **AI説明が音と乖離** | 楽譜テキストの調性を誤読し「耳で確認してよかった」 | [@riverxriverx](https://x.com/riverxriverx/status/2077363412980404635) |

### 4.3 失敗類型C — ドラム／打楽器（バンドスコア最大の落とし穴）

**開発元自身**がドラムMIDIの未完成を認める:

> *The drums come as a consolidated midi stem, so there is still some manual mapping to be done at this stage.*  
> — [@MireloAI](https://x.com/MireloAI/status/2075624374338465847)

コミュニティ側の冷ややかな失敗予測:

> *ppl gonna ask “can i map drums to different kicks” … MuScriptor is cool until you realize we’re just hot-glueing middleware instead of fixing the real problem*  
> — [@Jasonwang1211](https://x.com/Jasonwang1211/status/2076431520269832693)

**表現の構造的限界**（Sonic Fieldの技術解説＋モデルカード）: ドラムは **onset-only**、**velocity非出力**、同一楽器・同一ピッチの同時2音を表現できない。

→ バンド／アンサンブルのフルスコア用途では、**ドラム譜・強弱・ユニゾン重複**がそのまま欠落する。

### 4.4 失敗類型D — トークン化・楽器分類の上限（フルスコア生成の根本限界）

Kyutai公式ブログの限界記述（投稿で「open source」と誤読されがちな点とセットで重要）:

| 限界 | 実務インパクト |
|------|----------------|
| 転写は **still far from perfect** | 本番譜には手修正必須 |
| **楽器リスト条件付けを推奨** | 無指定一括は不安定 |
| 同一ピッチ＋同一楽器の重なり不可 | 2ギターの同音、ユニゾンパートが潰れる |
| 楽器は **36グループ** の分類 | 細かいオーケストレーション（ヴィオラ vs ヴァイオリン第2等）は粗い |
| Pop／西欧クラシック偏り | 非西洋・希少楽器・金属系歪み等で劣化しやすい（Sonic Field要約） |
| **velocity/dynamicsなし** | 強弱付きフルスコアは別工程 |
| 合唱など **offset精度が低い** | 持続音・合唱アンサンブルで譜面が「ブツ切れ」 |

論文側の自己診断も厳しい:

> *Existing methods … fail on complex, real music mixes.* / *… usually too error-prone to be used for downstream applications.*  
> — MuScriptor論文 abstract 要約

### 4.5 失敗類型E — ライセンス／プロダクト失敗（技術以外）

> *Code is MIT… Weights are CC-BY-NC… You can’t ship a paid product on those weights… “Open weights” and “free to build a business on” are two different sentences.*  
> — [@nikskld](https://x.com/nikskld/status/2076316488529564070)

採譜ソフト機能として商用組み込みする場合、**重みの非商用制限**は「技術的成功→製品失敗」の典型。

### 4.6 失敗類型F — ステム分離→採譜の連鎖失敗（2–3パートでも起きる）

研究者コミュニティでは「source separationは解けた」皮肉が定番:

> *Music source separation is a solved problem and no one should work on it, right?*  
> — [@csteinmetz1](https://x.com/csteinmetz1/status/1716807614061756619)（2023, WASPAA文脈の皮肉）

実務パイプラインでは:

1. 分離時の **bleed（他パート混入）**  
2. 歪みギター・リバーブで **音色境界の消失**  
3. 分離後の単パート採譜でも **オクターブ誤り・ゴーストノート**  
4. 量子化で **グルーヴ破壊**

→ 小編成2–3パートでも「分離が汚い＝採譜が死ぬ」。MuScriptorは「フルミックス直接」でこの失敗モードを回避しようとしているが、**表現トークン側の失敗**が残る（上記D）。

### 4.7 失敗類型G — 楽器固有・文化固有

> *AI cannot accurately draw a saxophone / generate the sound of a saxophone / MIDI saxophone still sounds like trash… may it forever break every algorithm.*  
> — [@themikecasey](https://x.com/themikecasey/status/1805725441430598121)

> *audio to midi for piano is genuinely hard polyphony pedal and overlapping notes wreck most models*  
> — [@irshit0](https://x.com/irshit0/status/2071641834087215303)

> *PitchBench*：Audio-languageモデルが基本的なピッチ聴取テストに失敗する、という研究投稿  
> — [@OrchestralPit](https://x.com/OrchestralPit/status/2059636448232362428)

### 4.8 失敗例チェックリスト（機能設計向け）

多声部一括採譜機能のQA／仕様に使える「X由来の失敗カタログ」:

1. **密なジャズ・ポリフォニー**でパートが混線する  
2. **歪みギター＋ベース**が同帯域で誤同定  
3. **ドラム**が1ステムに潰れ、GMマップと不一致  
4. **同音ユニゾン**（2本のギター等）が1音に潰れる  
5. **ベロシティ／クレッシェンド**が全部フラット  
6. **合唱・持続音**のオフセットが短すぎ／長すぎ  
7. **希少楽器**が近い36クラスに丸められる  
8. **テンポ揺れ**で量子化後に拍がずれる  
9. **BPM未設定**でBasic Pitch系が全滅（運用失敗）  
10. **商用ライセンス**で製品に載せられない  
11. デモ曲では成功、**実バンド生録**で崩壊  
12. MIDIは正しいが **五線譜の声部分け・記譜法**が破綻（スラー、連符、多声1段）  
13. 局所F1は高いが **楽曲構造（Aメロ/サビ）**が読めない  
14. 分離前処理を入れると **タイムストレッチ／位相**で拍位置がずれる  
15. ユーザーが「完成譜」を期待し **手修正UI不足**で離脱  

---

## 5. ベストプラクティス（投稿から抽出）

### 5.1 期待値の置き方

- **目標は「完成フルスコア」ではなく「編集可能なマルチトラックMIDI下書き」**  
  - 成功報告の語彙: “七七八八” / “slightly wrong” / “days of hand-writing”
- 開発側も Whisper 完全到達を主張せず *Are we there yet?* とユーザー検証を促す（[@honualx](https://x.com/honualx/status/2075560798684873052)）

### 5.2 入力・条件付け

| プラクティス | 根拠 |
|--------------|------|
| **楽器リストを与える** | Kyutai公式: 一貫性向上のため推奨 |
| 可能なら **クリーンなマルチマイク／ステム** | 小編成2–3パートでは分離不要でも「パート別音源」が最強 |
| **BPMを先に固定**してからMIDI化 | [@NoR3_Music](https://x.com/NoR3_Music/status/2077725459601928277) |
| フルミックス一括がダメなら **Demucs前処理** | [@fffiloni](https://x.com/fffiloni/status/2078128083995963779) のデモ設計 |

### 5.3 出力後処理

1. **スケール量子化**で誤音を一括掃除（[@dj_irl](https://x.com/dj_irl/status/2016891106236256452)）  
2. **時間量子化は弱め**（グルーヴ優先）— 強量子化は失敗報告の温床  
3. **ドラムは別UI**（キットマップ、キック／スネア再割当）— [@MireloAI](https://x.com/MireloAI/status/2075624374338465847)  
4. 強弱・アーティキュレーションは **人間 or 別モデル**  
5. フルスコア化は **MusicXML/MuseScore工程を分離**（MIDI≠記譜）

### 5.4 モデル学習・製品設計（研究者投稿由来）

| プラクティス | 出典 |
|--------------|------|
| 合成MIDI大量 pretrain → **実録音 fine-tune** が品質の本丸 | [@kyutai_labs](https://x.com/kyutai_labs/status/2075540049337155964) スレ / 論文 |
| 人手検証300曲級の **RL post-train** | 同上 |
| 明示コード構造より **データ＋Transformer** が勝ちやすい | [@jxmnop](https://x.com/jxmnop/status/1927385194601886065) |
| 「オープン」の定義を **コード／重み／データ／商用** に分解して表示 | [@nikskld](https://x.com/nikskld/status/2076316488529564070) |

### 5.5 小編成2–3パート向け推奨フロー

```text
[理想] パート別録音 → 各パートAMT（Basic Pitch/Melodyne/専用） → 手動整譜 → スコア結合
[現実的] フルミックス → (任意)軽量分離 → 多楽器AMT → 楽器条件付き再推論
         → スケール量子化 → ドラム手マップ → MusicXMLで声部分け
[避ける] 「フルスコア一発生成」をUXの約束にする
```

---

## 6. 最新トレンド（2025–2026、X上）

1. **フルミックス直接多楽器MIDI**がメインストリーム話題（MuScriptor, 2026-07）  
2. **「音楽のWhisper」未達**が共通フレーム（開発者・起業家が同じ言葉を使う）  
3. **生成AI曲の再編集**（Suno → MIDI → DAW）が新しいユースケース  
4. **採譜→コード化**（Decomposer / Strudel）で「可読・編集可能な音楽表現」へ  
5. **デモUIの民主化**（HF Gradio: Demucs + piano roll + score）  
6. **エージェント型制作**（Songbird等が MuScriptor を内部利用と主張）  
7. **中国語圏「扒谱」文化**とOSS多楽器モデルの接続（七七八八評価）  
8. **ライセンス・リテラシー**（CC-BY-NC重み vs MITコード）が炎上／注意喚起ネタに  
9. 研究指標: syntheticのみでは **F1が大きく落ち、実データで+20pt級**という物語が拡散  
10. 依然として **source separation と AMT は別プロブレム**として併存

---

## 7. 機能仕様への示唆（「多声部一括採譜」を製品化するなら）

| 優先 | 仕様案 | 理由（X根拠） |
|------|--------|----------------|
| P0 | 出力を **「下書きMIDI」** と明示 | 過大期待＝失敗レビューの主因 |
| P0 | **楽器プリセット**（2–3パート / バンド / ジャズ） | 条件付け推奨・密集ジャズの難易度 |
| P0 | パート別 **誤りハイライト＋クイック修正** | 手修正が本体 |
| P0 | **ドラム専用マップUI** | 公式も consolidated stem と認めた |
| P1 | ベロシティ推定 or ユーザーダイナミクス | トークンに無い |
| P1 | 同音ユニゾンの警告 | 表現不能の既知限界 |
| P1 | フルスコアは **MusicXML後工程** | MIDI≠記譜 |
| P2 | 商用利用可能な重み／自前学習 | NC制限の製品事故 |
| P2 | ジャンル別品質バッジ（pop◎ / 密ジャズ△） | 偏りと失敗の可視化 |

---

## 8. 主要出典一覧（クリック可能な投稿）

### 英語・開発／研究

| 投稿者 | 内容 | URL |
|--------|------|-----|
| @kyutai_labs | MuScriptor公開・データがボトルネック | https://x.com/kyutai_labs/status/2075540047613276197 |
| @MireloAI | フルミックス多楽器Audio-to-MIDI | https://x.com/MireloAI/status/2075536492177354771 |
| @honualx | 「音楽のWhisper」未達 | https://x.com/honualx/status/2075560798684873052 |
| @MireloAI | ドラムは手動マップ必要 | https://x.com/MireloAI/status/2075624374338465847 |
| @helloLizZhang | ポリフォニーが本質的難所 | https://x.com/helloLizZhang/status/2075615962091729343 |
| @jxmnop | MT3に負けた苦い教訓 | https://x.com/jxmnop/status/1927385194601886065 |
| @nikskld | 重みNC・商用不可の注意 | https://x.com/nikskld/status/2076316488529564070 |
| @haiyewon | 自動MIDI後に数日手修正 | https://x.com/haiyewon/status/2079240520942154062 |
| @dj_irl | Ableton誤音→スケール押し込み | https://x.com/dj_irl/status/2016891106236256452 |
| @csteinmetz1 | 分離「解けた」皮肉 | https://x.com/csteinmetz1/status/1716807614061756619 |
| @fffiloni | Demucs+採譜デモ | https://x.com/fffiloni/status/2078128083995963779 |
| @sonic_field | 何を保存し何を捨てるか | https://x.com/sonic_field/status/2078880397920731383 |
| @Jasonwang1211 | ドラムマッピング＝ミドルウェア糊付け | https://x.com/Jasonwang1211/status/2076431520269832693 |
| @irshit0 | ピアノ：ペダルと重なりがモデル破壊 | https://x.com/irshit0/status/2071641834087215303 |
| @themikecasey | サックスがアルゴリズムを壊す | https://x.com/themikecasey/status/1805725441430598121 |

### 中国語

| 投稿者 | 内容 | URL |
|--------|------|-----|
| @YMike59492 | 管弦楽多楽器「七七八八」成功 | https://x.com/YMike59492/status/2075840791281619050 |

### 日本語（実務補完）

| 投稿者 | 内容 | URL |
|--------|------|-----|
| @NoR3_Music | Basic Pitch精度限定＋BPM注意 | https://x.com/NoR3_Music/status/2077725459601928277 |
| @SchrgeMusic0626 | ステム→Melodyne、MIDIが最遅 | https://x.com/SchrgeMusic0626/status/2074443907702915410 |

### 外部（投稿が参照する一次情報）

| 資料 | URL |
|------|-----|
| MuScriptor論文 | https://arxiv.org/abs/2607.08168 |
| Kyutaiブログ（Limitations） | https://kyutai.org/blog/2026-07-10-muscriptor/ |
| Sonic Field解説 | https://sonicfield.org/muscriptor-audio-to-midi |
| HF model card（velocity/drums） | https://huggingface.co/MuScriptor/muscriptor-large |

---

## 9. 調査上の限界（本レポート自身）

1. X検索はノイズが多く、「採譜失敗」の**長文ポストモーテム**より、**成功デモと公式限界文**が相対的に強い。  
2. 中国語「扒谱」はBilibili・小紅書側に厚く、X単体では英語のMuScriptor周辺に集中。  
3. AnthemScore / ScoreCloud 等の**古典商用採譜ソフト**の失敗談は、2026年タイムラインではMuScriptor話題に埋もれがち（追加調査候補）。  
4. 「フルスコア＝五線譜整形」まで含む失敗は、MIDI採譜成功の**次工程**として別途UI調査が必要。

---

## 10. 一行で言うと

**多声部一括採譜は2026年に「使える下書き」段階に入ったが、バンド／アンサンブルのフルスコア自動完成には程遠く、失敗の本体はポリフォニー衝突・ドラム表現・強弱欠落・手修正コスト・商用ライセンスに集中している。** 小編成2–3パートでも、成功条件は「モデルの賢さ」より **入力の分離度・楽器条件・後処理UI** 側にある、というのがX実務者コミュニティの実像である。
