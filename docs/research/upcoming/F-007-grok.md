# 区間選択採譜（Section / Region / Chunk Transcription）調査メモ

**調査日:** 2026-07-21  
**対象:** X（旧Twitter）上の実務者・研究者・開発者投稿（英語中心、中国語・日本語の周辺言及を補足）  
**テーマ:** 曲全体ではなく、**指定区間だけを採譜/Audio→MIDI化する機能**  
**方針:** 実投稿ベース／失敗例を厚め／出典リンク付き  

---

## 0. 調査上の前提（重要）

X上で「区間選択採譜」という**製品機能名そのもの**で語られる投稿は少なく、実務会話は次の言い方に分散しています。

| 言い方 | 中身 |
|--------|------|
| **chunk-by-chunk transcription** | 長尺を固定長（例: 5秒）に切って逐次採譜 |
| **select / crop / trim → convert** | 先に区間を切ってから Audio→MIDI |
| **loop / clip / selection → MIDI** | DAWの選択範囲やクリップ単位変換 |
| **stem → audio-to-MIDI** | 分離した一部だけを採譜 |
| **片段 / 裁剪 / 一段ずつ** | 中国語・日本語圏の「区間単位」運用 |

つまり製品UIとしての「区間選択」と、研究・実装上の「チャンク処理」は**同じ失敗モードを共有**します。

---

## 1. 最新トレンド（2025–2026）

### 1-1. フルミックス直接・多楽器MIDI（「stem不要」が売り文句）

**Kyutai × Mirelo の MuScriptor** が2026年7月に大きな話題。  
フルミックスから楽器別MIDIへ、という訴求。

> "It takes a finished recording, identifies the instruments playing, and returns separate MIDI tracks for each — voice, drums, bass, keys, and more. Unlike most existing solutions, our model works directly from the full mix rather than requiring separate stems."  
> — [@MireloAI](https://x.com/MireloAI/status/2075536492177354771)（2026-07-10）

> "almost all audio-to-MIDI tools out there handle only one sound at a time. … takes the full mix … and transcribe every instrument at once."  
> — [@pagarciadom](https://x.com/pagarciadom/status/2077344364079042963)（Mirelo側、2026-07-15）

### 1-2. でも中身は「5秒チャンク」＝区間処理そのもの

開発元が明言している点が本調査の核です。

> "MuScriptor is a decoder-only transformer that autoregressively predicts a stream of MT3-like tokens from a mel-spectrogram of **a 5-second audio excerpt**. **Longer samples are transcribed chunk-by-chunk.**"  
> — [@kyutai_labs](https://x.com/kyutai_labs/status/2075540050930991170)（2026-07-10）

**示唆:** 製品が「曲全体を一発で」見せていても、裏側は**区間選択採譜の連続実行**。したがって「区間の切れ目」での破綻が、そのままフル曲採譜の破綻になる。

### 1-3. 評価データも「セグメント」単位

CMU G-CLef の **MulTTiPop**（3.5時間・**572 segments**）。

> "MulTTiPop contains 3.5 hours (**572 segments**) of aligned multitrack pop audio and MIDI"  
> — [@pruynathan](https://x.com/pruynathan/status/2075772813462450389)（2026-07-11）

> "use human labeling to identify a **portion of the MIDI file that matches the audio**"  
> — 同スレ（区間マッチが人手で必要）

> "The new MuScriptor model … is SotA on MulTTiPop but with **plenty of headroom to go!**"  
> — [@chrisdonahuey](https://x.com/chrisdonahuey/status/2075810524609101972)（2026-07-11）

### 1-4. 周辺スタックの定番化

- **Stem分離 → 部分処理**（Lalal/Demucs等）をタイムライン上のクリップ単位で  
  [@DariuszChynek / VU Studio](https://x.com/DariuszChynek/status/2079212219196137604): *「Cut, trim … on part you really want」*
- **NeuralNote + Spotify Basic Pitch** をプラグイン化する層  
  [@DanKornas](https://x.com/DanKornas/status/2079357160400580624)
- **ギター向け**で chord transcription + stem separation を一体製品化  
  [@rivuchakraborty / FretPractice](https://x.com/rivuchakraborty/status/2077241817280692711)

### 1-5. 中国語圏の文脈

「区間選択採譜」専用機能の中国語投稿は少なく、**片段（セグメント）切り出し→下流タスク**として語られることが多い。

- 歌を**15秒以内に切って**処理し、後で結合  
  [@xiaojietongxue](https://x.com/xiaojietongxue/status/2020255780428267716)
- 音楽を**30秒以内に切って**分鏡と対応づけ  
  [@binghe](https://x.com/binghe/status/1987538855525052558)

採譜そのものより「AI音楽/映像パイプラインの**時間窓制約**」として区間操作が現れる。

---

## 2. 成功例（実投稿）

### 成功例 A — 難曲フィンガーピッキングのバックアップ復元

スタジオ持ち込みの悪い録音・故人の複雑なフィンガーピッキングをデモで採譜し、Ample Guitar で確認。

> "It converted perfectly… Obviously it wouldn’t replace a real guitar player… but at least the way is clear… **I haven’t found another solution that would solve this particular puzzle.**"  
> — [@SpacklMarketing](https://x.com/SpacklMarketing/status/2075606950641840340)（Mirelo発表への返信、2026-07-10）

**成功条件の読み取り:** 単一パート中心／復元目的／「置き換え」ではなく「手がかり」。

### 成功例 B — 相対比較での「最良コヒーレンス」

研究側でも MuScriptor は相対的に最良、ただし後述の限界つき。

> "MuScriptor does indeed provide the **most coherency** of any AMT model that we’ve tested"  
> — [@pruynathan](https://x.com/pruynathan/status/2075772820190003374)

### 成功例 C — ハーモニー変換の「スケール強制」で実用圏

Ableton の誤検出を、スケールへ強制して近づける。

> "Ableton often gets it slightly wrong, adding bad notes. instead of manually fixing it, just **forcing it into scale** tends to be a quick way to get close."  
> — [@dj_irl](https://x.com/dj_irl/status/2016891106236256452)（2026-01-29）

### 成功例 D — 区間切り出しのUX自体は評価される（隣接ドメイン）

音声文字起こしでも「必要な区間だけ」は明確な価値。

> "Only need 20 minutes of a 2-hour recording? Don't pay for the whole file."（Trim Audio）  
> — [@scribie_](https://x.com/scribie_/status/2077356484225355963)

音楽採譜でも同様に、**コスト・反復速度・フォーカス**が区間機能の本命価値。

### 成功例 E — 学習用途の「一段ずつ」

耳コピ曲を一段ずつ録音して組み立てる教育的成功（人力だが区間分割の価値を示す）。

> 「一段ずつ録音して三段の形にして…めっちゃ良く出来てる気がした」  
> — [@ukkariyonme](https://x.com/ukkariyonme/status/2072658160117289431)

---

## 3. 失敗例（厚め）— 実務・研究の両側

### 失敗タイプ 1: **チャンク境界で楽器割当がブレる**（区間機能の本丸失敗）

> "… still **sometimes inconsistent in instrument parts across chunks**."  
> — [@pruynathan](https://x.com/pruynathan/status/2075772820190003374)（2026-07-11）

**意味:** 区間Aではピアノ扱い、区間Bではギター扱い、みたいな**トラック同一性の崩壊**。  
「指定区間だけ変換」を複数回つなぐ／内部チャンクでフル曲を切ると、同じ症状が出る。

### 失敗タイプ 2: **アレンジ一貫性の崩壊（MT3）**

> "MT3 **fails to maintain a consistent arrangement between parts**"  
> — [@pruynathan](https://x.com/pruynathan/status/2075772818457813478)

### 失敗タイプ 3: **リズム／アレンジの過剰単純化（YourMT3+）**

> "YourMT3+ will **over-simplify arrangements and rhythms**."  
> — 同上

区間が短いほど「その窓の中で聞こえやすいもの」だけ残り、**フィル・ポリリズム・装飾が消える**。

### 失敗タイプ 4: **実用精度が「人力でギリ」で50%、「絶望帯」で10%**

日本語実務者の試聴メモ（Mirelo）：

> 「自分でも人力でなんとかなる範囲の曲の精度は**50%くらい**／自分だけだと絶望的な範囲は**10%くらい**… 専用モデル使わなくても Cowork に torch と demucs と librosa 握らせた方が精度出そう」  
> — [@CabbageLettuce1](https://x.com/CabbageLettuce1/status/2078348054697246827)（2026-07-18）

### 失敗タイプ 5: **DAW標準の選択範囲変換が「ほぼ使えない」**

> "Ableton gods can you please fix how accurate the convert melody / harmony work? **They are pretty useless** and even free plugin options work better. neuralnote for instance is at least sort of useable."  
> — [@ChadOnikum43466](https://x.com/ChadOnikum43466/status/1993312883917438990)（2025-11-25）

> "I have been doing audio-to-midi for years and it has been very in-accurity. **Ableton and Logic has audio-to-midi but both are quite bad.**"  
> — [@SubarcticRec](https://x.com/SubarcticRec/status/2020164809648492894)（2026-02-07）

> "hopefully a new and improved audio to midi clip that **actually works**."  
> — [@ChadOnikum43466](https://x.com/ChadOnikum43466/status/2051455173793599917)

**区間選択UIがあっても、変換器自体が弱いと区間機能は無価値**、という現場感。

### 失敗タイプ 6: **BPM／タイミングが区間出力でズレる**

スタンドアロン系スライス→MIDI書き出しでテンポ不一致：

> 「書き出されたBPMのタイミングが**全然合ってない**んだ。だから最終的にAbletonのMIDIのタイムストレッチで合わしてるよ！」  
> — [@DJ_OMKT](https://x.com/DJ_OMKT/status/2079374724967407621)（2026-07-21）

### 失敗タイプ 7: **「周波数ダンプ」で理論的に使えない**

> "every existing tool gives you a **raw frequency dump**. **totally useless for real instruments**."  
> — [@LatentDhruva](https://x.com/LatentDhruva/status/2045449645221171588)（2026-04-18）

区間を正しく切っても、出力が「音高の生検出」止まりだと譜面・演奏に落ちない。

### 失敗タイプ 8: **コントロール不能な歪み（意図が壊れる）**

> "Imagine if you'd made a highly advanced audio-to-MIDI program… Instead it **warps those ideas in ways you have no meaningful control over. Useless.**"  
> — [@atelierjoshua](https://x.com/atelierjoshua/status/2019603657944420584)（2026-02-06）

### 失敗タイプ 9: **ポップ楽曲全体の採譜品質ショック**

> "The absolute state of music transcription for popular music is shocking… often in the wrong key, or losing the entire essence… **and AI still suck.**"  
> — [@T_R_E_X_12](https://x.com/T_R_E_X_12/status/1979380334673146295)（2025-10-18）

### 失敗タイプ 10: **プロも「Audio to MIDIはイマイチ→耳コピ回帰」**

元作編曲家：

> 「Sunoで作ったStemで…手直ししたい…（**Audio to MIDIだと精度がイマイチだったんで**）」  
> — [@YUJIRO34160841](https://x.com/YUJIRO34160841/status/2047965174355972534)（2026-04-25）

### 失敗タイプ 11: **ベテラン作曲家の総括「まだ全部わりと悪い」**

> "You think they would’ve cracked audio to midi by now… **but it’s all pretty bad.**"  
> — [@JOHNMAUS](https://x.com/JOHNMAUS/status/1986174329449570713)（2025-11-05）

### 失敗タイプ 12: **Basic Pitchでも同様に未解決感**

> "tried using basic pitch, but it was just as bad. seems like a **surprisingly unsolved space**?"  
> — [@dvsch](https://x.com/dvsch/status/2003161871847985438)（2025-12-22）

### 失敗タイプ 13: **stem-level MIDI は歴史的に half-broken**

> "Stem-level MIDI from a mixed recording has been **half-broken forever**, drums bleed into everything."  
> — [@helloLizZhang](https://x.com/helloLizZhang/status/2075614551895314717)（Mirelo発表への反応、2026-07-10）

区間を切っても**周波数帯の重なり**は残る。

### 失敗タイプ 14: **サンプリング位置の解釈誤差（自作実装）**

波形の「頭／減衰尻」どちらを拾うかで誤差：

> 「サンプリング部位が単音の頭の方か、消えてくお尻の方を拾うかが解釈の誤差…自作だとこの精度が限界」  
> — [@iluust_yamada](https://x.com/iluust_yamada/status/2077665642577355185)

短い区間ほど**アタック切れ**で頭を失いやすい。

### 失敗タイプ 15: **人力扒谱でも音高ミス（区間やり直し）**

> 「昨天的扒谱 删了重新发（有错…音感果然有点失灵…）」  
> — [@XmeowwoemX_017](https://x.com/XmeowwoemX_017/status/2053232807892365751)

AI固有ではなく、**区間単位の反復修正**が採譜ワークフローの本質。

### 失敗タイプ 16: **「先にstem分離すれば…」も前提が崩れる**

> "stem splitter 만 잘 됐다면 … Audio to midi convert 로 악보로 뽑으면 되는거 아닌가"  
> — [@chickenjuice](https://x.com/chickenjuice/status/1998196866719392248)（韓国語、2025-12-09）

区間＋stemの二段構えでも、**分離品質がボトルネック**。

---

## 4. 限界（投稿から帰納）

| 限界 | 根拠投稿 |
|------|----------|
| **チャンク間の楽器一貫性** | MuScriptorでも parts across chunks がブレる [@pruynathan](https://x.com/pruynathan/status/2075772820190003374) |
| **固定窓（例5秒）の文脈欠如** | モデル定義が5秒 excerpt [@kyutai_labs](https://x.com/kyutai_labs/status/2075540050930991170) |
| **混声・密なミックス** | drums bleed / half-broken [@helloLizZhang](https://x.com/helloLizZhang/status/2075614551895314717) |
| **正確な楽器ラベル** | harmonic/percussive統合ではSotAだが exact instrument は中位 [@pruynathan](https://x.com/pruynathan/status/2075772822211756101) |
| **テンポ・グリッド整合** | 書き出しBPMが合わない [@DJ_OMKT](https://x.com/DJ_OMKT/status/2079374724967407621) |
| **理論的な「譜面らしさ」** | raw frequency dump [@LatentDhruva](https://x.com/LatentDhruva/status/2045449645221171588) |
| **ユーザー制御** | 意図が歪む・制御不能 [@atelierjoshua](https://x.com/atelierjoshua/status/2019603657944420584) |
| **難曲での実用率** | 50% / 10% 体感 [@CabbageLettuce1](https://x.com/CabbageLettuce1/status/2078348054697246827) |
| **データボトルネック** | MT3以降データ不足が主因 [@kyutai_labs](https://x.com/kyutai_labs/status/2075540049337155964) |

**Melody transcription 自体が open challenge** という研究側の長期認識：

> "robust *melody transcription* remains an open challenge in MIR research."  
> — [@chrisdonahuey](https://x.com/chrisdonahuey/status/1600012520743239680)（Sheet Sage、2022）

---

## 5. ベストプラクティス（投稿から抽出）

### BP1. **区間は「問題を小さくする」ため**に切る
- 成功例は「難所だけ／単一パート／学習の一段」など**狭い目的**。
- フル曲一発より、**反復修正可能な単位**に切る。

### BP2. **可能なら stem → 単一音源区間 → MIDI**
- 歴史的に full-mix 直変換は弱い（Mirelo以前の定石）。
- ただし stem も bleed するので過信しない [@helloLizZhang](https://x.com/helloLizZhang/status/2075614551895314717)。
- クリップ単位で trim してから分離する運用  
  [@DariuszChynek](https://x.com/DariuszChynek/status/2079212219196137604)

### BP3. **誤検出は「手動修正」より先に制約をかける**
- スケール強制 [@dj_irl](https://x.com/dj_irl/status/2016891106236256452)
- 量子化・音階・時間量子化（NeuralNote系の調整UI）  
  [@DanKornas](https://x.com/DanKornas/status/2079357160400580624)

### BP4. **テンポは後段で合わせる前提で設計**
- 書き出し後に MIDI タイムストレッチ [@DJ_OMKT](https://x.com/DJ_OMKT/status/2079374724967407621)
- 区間境界は**拍・小節にスナップ**した方が後処理が楽（投稿からの帰納）。

### BP5. **アタックを切らない**
- 頭／減衰尻のどちらを拾うかで誤差 [@iluust_yamada](https://x.com/iluust_yamada/status/2077665642577355185)
- 区間開始はノート頭の少し前から。

### BP6. **「置き換え」ではなく「たたき台」にする**
- ギター成功例も「real player の代替ではない」と明言  
  [@SpacklMarketing](https://x.com/SpacklMarketing/status/2075606950641840340)
- プロは精度不足なら耳コピへ [@YUJIRO34160841](https://x.com/YUJIRO34160841/status/2047965174355972534)

### BP7. **難所は人間、平易部は機械**
- 教育現場の「一段ずつ」と同じ分割戦略 [@ukkariyonme](https://x.com/ukkariyonme/status/2072658160117289431)

### BP8. **チャンク間で楽器トラックIDを固定するUXを要求する**
- 研究が明示した弱点＝製品が直すべき点  
  [@pruynathan](https://x.com/pruynathan/status/2075772820190003374)

---

## 6. 区間選択採譜に特化した「失敗パターン辞書」

製品設計・QA観点で、投稿を機能要件に落としたもの。

| ID | 失敗 | 再現しやすい条件 | 投稿根拠 |
|----|------|------------------|----------|
| F01 | 区間またぎで楽器割当が変わる | フル曲／複数チャンク | [pruynathan](https://x.com/pruynathan/status/2075772820190003374) |
| F02 | 短い窓でリズム単純化 | フィル・装飾が多い区間 | [pruynathan MT3/YourMT3+](https://x.com/pruynathan/status/2075772818457813478) |
| F03 | 境界でノートが切れる／二重化 | アタック近傍で切る | [iluust_yamada](https://x.com/iluust_yamada/status/2077665642577355185) |
| F04 | テンポグリッド不一致 | 外部ツール書き出し | [DJ_OMKT](https://x.com/DJ_OMKT/status/2079374724967407621) |
| F05 | 誤音追加 | ハーモニー変換 | [dj_irl](https://x.com/dj_irl/status/2016891106236256452), [Ableton不満](https://x.com/ChadOnikum43466/status/1993312883917438990) |
| F06 | 周波数ダンプ化 | 理論無視の検出 | [LatentDhruva](https://x.com/LatentDhruva/status/2045449645221171588) |
| F07 | 密ミックスでbleed | ドラム＋他楽器 | [helloLizZhang](https://x.com/helloLizZhang/status/2075614551895314717) |
| F08 | 難曲で精度崩壊 | 多声・複雑フィンガリング以外 | [CabbageLettuce1 10%](https://x.com/CabbageLettuce1/status/2078348054697246827) |
| F09 | キー／本質の喪失 | ポップ楽曲 | [T_R_E_X_12](https://x.com/T_R_E_X_12/status/1979380334673146295) |
| F10 | 制御不能な「改変」 | 生成的補正が強すぎる | [atelierjoshua](https://x.com/atelierjoshua/status/2019603657944420584) |

---

## 7. 製品機能としての示唆（投稿の合成）

区間選択採譜を作るなら、X上の議論は次を要求している：

1. **単なるトリムUIではなく、チャンク一貫性エンジン**  
   - 楽器ID・声部・キー・テンポを区間をまたいで固定
2. **境界の音楽的スナップ**（拍・小節・アタック前パディング）
3. **制約付き後処理**（スケール／量子化／単旋律モード）を一等市民に
4. **stem連動**（任意区間で分離→採譜）  
5. **「たたき台」モードの明示**（完成譜面ではない）
6. **区間ごとの信頼度表示**（50%/10%体感をUIに落とす）
7. **再採譜の局所化**（全体再計算ではなく失敗区間だけ）

---

## 8. 出典一覧（主要投稿）

| 区分 | 投稿者 | リンク |
|------|--------|--------|
| 研究/評価 | @pruynathan (MulTTiPop) | https://x.com/pruynathan/status/2075772813462450389 |
| 研究/失敗 | 同上 (MT3 / YourMT3+ / chunks) | https://x.com/pruynathan/status/2075772818457813478 ほか |
| 研究 | @chrisdonahuey | https://x.com/chrisdonahuey/status/2075810524609101972 |
| 開発 | @kyutai_labs (5s chunk) | https://x.com/kyutai_labs/status/2075540050930991170 |
| 開発 | @MireloAI | https://x.com/MireloAI/status/2075536492177354771 |
| 成功 | @SpacklMarketing | https://x.com/SpacklMarketing/status/2075606950641840340 |
| 失敗 | @CabbageLettuce1 | https://x.com/CabbageLettuce1/status/2078348054697246827 |
| 失敗 | @ChadOnikum43466 | https://x.com/ChadOnikum43466/status/1993312883917438990 |
| 失敗 | @SubarcticRec | https://x.com/SubarcticRec/status/2020164809648492894 |
| 失敗 | @LatentDhruva | https://x.com/LatentDhruva/status/2045449645221171588 |
| 失敗 | @atelierjoshua | https://x.com/atelierjoshua/status/2019603657944420584 |
| 失敗 | @T_R_E_X_12 | https://x.com/T_R_E_X_12/status/1979380334673146295 |
| 失敗 | @YUJIRO34160841 | https://x.com/YUJIRO34160841/status/2047965174355972534 |
| 失敗 | @JOHNMAUS | https://x.com/JOHNMAUS/status/1986174329449570713 |
| 失敗 | @dvsch | https://x.com/dvsch/status/2003161871847985438 |
| 失敗 | @helloLizZhang | https://x.com/helloLizZhang/status/2075614551895314717 |
| 失敗 | @DJ_OMKT | https://x.com/DJ_OMKT/status/2079374724967407621 |
| BP | @dj_irl | https://x.com/dj_irl/status/2016891106236256452 |
| BP | @DariuszChynek | https://x.com/DariuszChynek/status/2079212219196137604 |
| 中文周辺 | @xiaojietongxue / @binghe | 15s・30s 片段運用 |
| 中文失敗 | @XmeowwoemX_017 | 扒谱やり直し |

---

## 9. 調査の限界（メタ）

1. **「区間選択採譜」完全一致の製品レビューは希少**。多くは Audio→MIDI / AMT / 片段切り出しの周辺語彙。  
2. **中国語は「扒谱」が人力耳コピも含む**ため、自動区間機能と混同しやすい。  
3. Xは成功デモがバズりやすく、**失敗は短文の不満**として散在。  
4. 2026-07の MuScriptor/MulTTiPop 周辺に投稿が集中しており、**最新トレンドバイアス**あり。

---

## 10. 一行要約

**区間選択採譜の本質的失敗は「切り方」ではなく「区間をまたいだ音楽的一貫性（楽器割当・テンポ・リズム複雑度・ノート境界）」にあり、2026年最先端モデルでさえ 5秒チャンク処理と across-chunks 不整合を公言・観測されている。** 実務の勝ち筋は、狭い区間・stem前提・制約付き後処理・たたき台運用である。

---

必要なら次の深掘りもできます。

1. 上記失敗辞書を**テストケース表（受け入れ条件付き）**に落とす  
2. MuScriptor / Ableton Convert / NeuralNote の**区間UX比較表**  
3. 中国語「自动扒谱」アプリ名を追加でターゲット検索（抖音/小红书語彙含む）
