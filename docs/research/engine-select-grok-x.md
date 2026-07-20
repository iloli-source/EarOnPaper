# X調査レポート: 音楽採譜（AMT）における mono/poly 判定と音源分離の失敗・限界

- **調査日**: 2026-07-21
- **対象**: X（旧Twitter）投稿（英語・中国語中心。実務上有用な日仏投稿も少数含む）
- **方針**: 憶測禁止・実投稿ベースのみ。各知見に出典（主旨・アカウント種別・投稿ID/URL）を付す
- **検索範囲の限界（先に明記）**:
  - 「pYIN / CREPE を混合音源に当てた失敗」「mono/poly 自動切替のしきい値」を**そのまま議論する英語・中国語投稿は極めて少ない**
  - 代わりに、(a) 多声採譜の難しさ自体、(b) 単音前提トラッキングの製品仕様、(c) フルミックス直接採譜が「まだハード」と語られる文脈、(d) 分離→MIDI 前処理の限界、が実務・研究の実投稿として観測された
  - 中国語は「扒谱」が耳コピ・手作業文脈に偏り、AMT技術失敗の議論は相対的に薄い

---

## エグゼクティブサマリー

| テーマ | X上で実際に多く観測された失敗・限界 | 観測密度 |
|--------|--------------------------------------|----------|
| (1) mono/poly・多声採譜 | 多声は「難しい・データ不足」が定型句。フルミックスからの直接採譜はハード問題。単音前提ツールは mono を仕様として明示 | 中（直接の pYIN/CREPE 失敗談は希少） |
| (2) 音源分離前処理 | bleed / artifact / 位相問題 / 6-stem 実験モデルの漏れ / Demucs単体のVo漏れ / 周波数分離の pad ghosting / 古い録音・残響 / 「きれいに分かっても不安定」 | 高（開発者本人の限界告白を含む） |

---

## 1. 単音/多声・ポリフォニー推定まわり

### 1.1 多声採譜は「かなり難しい」——データがボトルネック

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| 多声音楽の自動採譜はかなり難しい。主因はデータ問題。Google MT3 はまあまあ。ノート信頼度でフィルタすると疑似的な難易度調整になる | シート譜生成AIを求める投稿への返信 | 実務寄りML（@Anthropic 解釈性 / 元 Scale AI） | [post](https://x.com/kamath_harish/status/1901319546339791115) `@kamath_harish` 2025-03-16 |
| AMT は MT3（2022）以降、**データの欠如がボトルネック**。17万曲・1.1万時間の実データ収集が品質改善の主因。合成MIDI→実データ微調整→RL後処理 | MuScriptor 発表スレッド | 研究ラボ公式 | [post](https://x.com/kyutai_labs/status/2075540049337155964) `@kyutai_labs` 2026-07-10 |
| 実データ微調整が品質の最大ドライバー | 同上 | 同上 | [post](https://x.com/kyutai_labs/status/2075540052700954997) |
| ポリフォニーがハードパート。n 楽器が同じスペクトルを争う。dense jazz で試す予定 | MuScriptor 反応 | AI起業家・コミュニティ | [post](https://x.com/helloLizZhang/status/2075615962091729343) `@helloLizZhang` 2026-07-10 |
| オーディオ→MIDI空間は10年ほど mediocre なツールが支配。ポリフォニック分離を実録音で解けたなら大きい。**complex jazz の精度はどうか？**（未検証の疑問提起） | MuScriptor 反応 | 開発者 | [post](https://x.com/saen_dev/status/2075895527124631928) `@saen_dev` 2026-07-11 |

**読み取れる実務含意（投稿内容の範囲内）**  
「多声 vs 単音の自動判定アルゴリズムのしきい値」よりも、**多声採譜そのものが未解決寄り**として語られている。しきい値調整の細かい失敗談より、「データ不足」「密なジャズ」「スペクトル衝突」が失敗条件として挙げられている。

---

### 1.2 「フルミックス直接採譜」はハード問題（= 単音器や stem 前提の歴史的制約の裏返し）

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| 既存の大半の解は**別stemを要求**する。新モデルは finished recording（フルミックス）から楽器別MIDIを返す | 製品発表 | 製品/研究コラボ | [post](https://x.com/MireloAI/status/2075536492177354771) `@MireloAI` 2026-07-10 |
| stem分離なし・フルミックス直取りは hard problem。**dense mixes** でどう持つか気になる | 同上への反応 | エンジニア | [post](https://x.com/IamPranavJ/status/2075799077669998881) `@IamPranavJ` 2026-07-11 |
| フルミックス多楽器→MIDI、stem不要が「静かに大きい」 | テック広報的紹介 | テックインフルエンサー | [post](https://x.com/EvanKirstel/status/2076162132073173315) `@EvanKirstel` 2026-07-12 |
| in-the-wild 録音向けのリアルタイム多声ピアノ採譜を研究発表（MOBILE-AMT） | 学会発表告知 | ヤマハ研究リード（MIR） | [post](https://x.com/zawazaw/status/1826526455712604379) `@zawazaw` 2024-08-22 |

**読み取れる実務含意**  
「単音ピッチ追跡器を伴奏付きに突っ込む」という失敗は、X上では**用語として直接書かれにくい**一方、製品側が「stem 必須だった」「フルミックスは hard」と述べることで、**混合音源に単一声部トラッカーを適用する限界**が間接的に裏付けられている。

---

### 1.3 単音前提のピッチ追跡が製品仕様として残っている例

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| SurferEQ 2 は **monophonic instrument or vocal** のピッチを追従して EQ バンドを動かす | 製品紹介（ピッチ追従EQ） | オーディオプラグイン企業公式 | [post](https://x.com/soundradix/status/1897679215958630513) `@soundradix` 2025-03-06 |

**読み取れる実務含意**  
「mono で動くトラッカーを poly/混合に誤適用すると壊れる」は学術常識だが、X上では**研究失敗談より製品の使用前提（mono 指定）**として現れることが多い。

---

### 1.4 単音/多声「自動切替」・しきい値そのもの

| 調査結果 | 内容 |
|----------|------|
| **直接ヒットほぼなし** | `polyphony estimation` / `monophonic detection` / `mono vs poly` / pYIN・CREPE 失敗談の組み合わせ検索では、関係ない語義（関係性の mono/poly、野球の pitch、宗教の monotheism 等）に大量ノイズ |
| 間接的な関連 | ノート信頼度フィルタで「疑似難易度」を作る（§1.1 `@kamath_harish`）——しきい値操作の実務に近いが、mono/poly 切替そのものではない |
| 中国語 | 「单音/多音/复调/音高跟踪」でのAMT失敗議論はほぼ見つからず。「扒谱」は耳コピ・手作業の文脈が中心 |

**正直な結論（投稿ベース）**  
「mono/poly エンジン自動切替のしきい値落とし穴」を**実務者がスレッドで詳しく語っている英語・中国語投稿は、今回の検索では十分な母集団を得られなかった**。これは「存在しない」証明ではなく、**X上では論文・製品発表・stem議論に比べて顕在化していない**という調査結果である。

---

### 1.5 音声ファイル品質が audio-to-MIDI 精度を壊す（単音旋律でも）

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| SynthV の audio-to-MIDI が不正確なとき、**SynthV のせいではなく vocal ファイルが scuffed（汚れている）**ことが多い | 実務Tips | ボカロ/シンセVカバー作者 | [post](https://x.com/WasThatZero/status/1803180840647561294) `@WasThatZero` 2024-06-18 |

**読み取れる実務含意**  
「エンジン選択」以前に、入力のノイズ・処理痕・品質が単音旋律抽出すら壊す、という現場観測。

---

## 2. 採譜前処理としての音源分離（stem separation）の失敗・限界

### 2.1 開発者本人による限界告白（最重要一次情報）

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| Demucs v4: 実験的 6-source モデル `htdemucs_6s`（piano/guitar 追加）で **bleeding + artifacts を観測** | リリース告知 | Demucs 作者・研究者 | [post](https://x.com/honualx/status/1600551855972663316) `@honualx` 2022-12-07 |
| 新デフォルト（HTDemucs）でも、**一部トラックでは旧モデル `mdx_extra_q` の方がまだ良い**可能性 | 同上 | 同上 | 同上 |
| SDX23 向けに **corrupted labels / bleeding** 学習のベースラインを公開 | チャレンジ向けベースライン | 同上 | [post](https://x.com/honualx/status/1628436176787890176) 2023-02-22 |
| 話者分離は、**エフェクト・リバーブ多めの録音に必ずしも汎化しない**。多くは 16kHz/8kHz | ユーザー質問への回答 | 同上 | [post](https://x.com/honualx/status/1697327081103962570) 2023-08-31 |

**失敗条件（投稿から直接）**  
- 4-stem を超えて piano/guitar を分けると **bleed と artifact が増える**  
- 曲依存で「新モデル＝常に最善」ではない  
- 残響・エフェクトの多い実録音は分離系の弱点

---

### 2.2 実務者: Demucs 単体の漏れ、二段処理、アーティファクト嫌悪

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| **Demucs 単体だと Vo が他ステムに漏れる**。先に Roformer 系で Vo/Inst を分け、Inst を Demucs（htdemucs_ft）に渡す二段処理でクリーン度が上がる | Suno曲のステム分離Tips | AI音楽・DTM制作者 | [post](https://x.com/yonagip/status/2053176652252008661) `@yonagip` 2026-05-09 |
| Demucs / BSRNN / BS-Roformer の **artifact を嫌うあまり mashup が作れない**（「#1 artifact hater」自認） | 自虐的実務観測 | 音楽ファン/制作寄り個人 | [post](https://x.com/oomfatuated/status/1843309355611095413) `@oomfatuated` 2024-10-07 |
| **AI stem separation は常に artifacts がある**。気にしない。古いモデル（Spleeter 初期）は今よりずっと悪かった | 制作議論への返信 | プロデューサー/DJ/開発者 | [post](https://x.com/thecollegehill/status/1931019780049301533) `@thecollegehill` 2025-06-06 |
| 1971年カセット（安マイクにギター・ボンゴ・歌）：分離は**時々**動くが、**楽器 bleed が望むより多い**。技術は新しい | 限界を試す実験 | ソングライター/元SFX編集 | [post](https://x.com/DinoDiMuro/status/1826654444077154797) `@DinoDiMuro` 2024-08-22 |
| 楽器の**きれいな分離が最も不確実**。DEMUS（Demucs）が最善だと思うが **pas fou（大したことない）**。その後は周波数と長さの認識で十分、という見解 | 技術議論（仏語） | 一般ユーザー（技術意見） | [post](https://x.com/indestwas/status/2078974770553487812) `@indestwas` 2026-07-19 |

---

### 2.3 「分離が採譜/リミックスを悪化・不安定にする」具体例

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| Suno 内ステム分解は楽器ごとに分かれるのは重要だが、**音質が非常に不安定**。場合によっては Demucs の素直な **other に大半がまとまる**方が大崩れせずリミックスできる | プロ目線の実務判断 | 作曲家・レーベル経験者 | [post](https://x.com/juliendausset/status/2079206480759415221) `@juliendausset` 2026-07-20 |
| Auto Split（旧・周波数分離）は **background leaks**。**pad ghosting under the guitar**。Advanced Split（再生成）は no frequency bleed / no pad ghosting を売り | Suno 新機能の対比宣伝 | マーケ/個人（製品比較の主張） | [post](https://x.com/VK_ROXy/status/2077367072451965179) `@VK_ROXy` 2026-07-15 ※製品宣伝色が強いが、**旧分離の失敗モードを言語化している**点で有用 |
| Suno 公式: 周波数分離ではなく stems を **regenerate from scratch**。結果として artifact-free を主張（= 従来分離に artifact があった前提） | 製品アップデート | 企業公式 | [post](https://x.com/suno/status/2065862499765821916) `@suno` 2026-06-13 |
| 市場プロダクトが「Most AI stem splitters introduce **phase artifacts** when recombine」と訴求（= 業界に広く認識された失敗モード） | 製品宣伝 | ツール開発者 | [post](https://x.com/gyqgtgt/status/2066696478949581037) `@gyqgtgt` 2026-06-16 |
| 中国語マーケ: 消音ソフトは**消不干净**、**乐器也跟着糊**（伴奏も一緒に濁る） | 製品訴求（失敗の一般認識を利用） | 同上系統 | [post](https://x.com/gyqgtgt/status/2071045172088156649) 2026-06-28 |

**分離→採譜パイプラインとの接続（投稿ベース）**  
- 分離後に MIDI 化するワークフローは普及しているが（下表）、分離の artifact/bleed が残るとピッチ・オンセット推定に悪影響しうる、という**直接因果の定量報告はXでは少ない**  
- 代わりに「Demucs 作者が full-mix MIDI を出した」「stem 不要が売り」という形で、**分離前処理依存への不満/限界**が語られる

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| ステム分離トップ（Demucs/HT-Demucs）作者側が、**分離せず一気に MIDI 化**する仕組みを出してきた | 実務者が分離→MIDI にトークンを費やしていた文脈 | ユーザー（日本語） | [post](https://x.com/virtualmep/status/2075729283297980788) `@virtualmep` 2026-07-10 |
| UVR で抜いたボーカルを MIDI 変換するワークフローが効く | SynthV 実務 | 個人 | [post](https://x.com/CabbageLettuce1/status/2069505490112094453) `@CabbageLettuce1` 2026-06-23 |
| 6-stem Demucs / bs-roformer は音楽やる人間なら問題ないレベル。**今は midi 化精度を上げる調整中** | 実務 | バンドギタリスト | [post](https://x.com/ga_ya_kamo/status/2075891044403859495) `@ga_ya_kamo` 2026-07-11 |
| MuScriptor Gradio demo に **Demucs Split option for audio preparation** がある（= 分離は任意の前処理として残る） | デモ作者 | HF Fellow / ML demo | [post](https://x.com/fffiloni/status/2078128083995963779) `@fffiloni` 2026-07-17 |

---

### 2.4 どういう音源で分離が破綻しやすいか（投稿から抽出した条件）

投稿に**明示された条件**のみ列挙（推測で補完しない）。

| 破綻・劣化条件 | 根拠投稿 |
|----------------|----------|
| 6-stem（piano/guitar 細分化） | `@honualx`: bleeding + artifacts |
| 曲によっては新モデルより旧モデルが良い | `@honualx`: `mdx_extra_q` 推奨の可能性 |
| エフェクト・リバーブの多い録音（話者分離文脈だが分離系一般） | `@honualx` |
| Demucs 単体の Vo→他ステム漏れ | `@yonagip` |
| 周波数分離型: 背景リーク、ギター下のパッド・ゴースト | `@VK_ROXy` / Suno 対比 |
| 音質が不安定で、細かく分けすぎるとリミックスが大崩れ | `@juliendausset` |
| 古い安録音（1971 cassette, 同一マイクに複数音源） | `@DinoDiMuro` |
| dense mix / full mix からの楽器同定（分離なし採譜の難しさとしても言及） | `@IamPranavJ`, `@helloLizZhang`（jazz） |
| 位相アーティファクト（再合成時） | 複数の製品訴求投稿が「業界の既知問題」として言及 |

---

### 2.5 研究側: bleed は未解決課題として論文化されている

| 知見 | 投稿の主旨 | アカウント種別 | 出典 |
|------|------------|----------------|------|
| 小編成アンサンブルの多ch分離で **Reducing Bleeding** を扱う論文が arXiv に | 論文ボット | 論文フィード | [post](https://x.com/ArxivSound/status/2072564974506201465) 2026-07-02（arXiv:2606.16551） |

---

## 3. 中国語圏の観測メモ

| 観測 | 内容 | 代表例 |
|------|------|--------|
| 「扒谱」 | ほぼ**人手の耳コピ**文脈。自動採譜の失敗分析ではない | 例: 単曲公開前に譜を起こした報告など |
| 技術的失敗の密度 | 英語に比べ、**Demucs/UVR/AMT の失敗条件を詳述する投稿が少ない**（本調査範囲） | — |
| 関連する中文マーケ言説 | 消音が消不干净、楽器も糊る | `@gyqgtgt` 中文投稿 |
| 日中混合の実務 | UVR/Demucs 二段、Suno ステム不安定、分離せず MIDI 化への関心 | `@yonagip`, `@juliendausset`, `@virtualmep` 等（日本語だが近隣実務） |

中国語で「音源分离 / 分轨 / 自动记谱」を失敗語と組み合わせても、今回の検索ではノイズが多く、**英語の研究者・製作者クラスの一次情報には届きにくかった**。

---

## 4. テーマ横断: 実務で繰り返し現れた「うまくいかない条件」マップ

```
入力がフルミックス（伴奏・多楽器）
        │
        ├─[経路A] 単音トラッカー / mono 前提処理
        │     → 製品側は mono 指定（SurferEQ 等）
        │     → 多声・密なスペクトルは「hard / data problem」（研究者・実務）
        │     → 直接の pYIN/CREPE 失敗スレは X 上希少
        │
        └─[経路B] stem 分離 → 各 stem を MIDI/採譜
              → bleed / artifact / phase / Vo漏れ
              → 6-stem 細分化で悪化（作者観測）
              → 細分しすぎて不安定 → other まとめの方が安全な場合（実務）
              → 周波数分離: pad ghosting, background leak
              → 古い録音・同一マイク・残響で bleed 増加
              → そのため「full mix 直 MIDI」が売りになる
```

---

## 5. 投稿ベースで**言えなかったこと**（誠実なギャップ）

以下は調査意図にあったが、**実投稿の十分な根拠が得られなかった**ため断定しない。

1. pYIN / CREPE を混合音源に適用したときの具体的失敗パターン（オクターブジャンプ、伴奏へのロック等）の**当事者スレ**
2. mono/poly **自動切替**のアルゴリズムと**しきい値**の実務落とし穴（誤 mono 判定で和音が単旋律化、等）の詳細
3. 「分離したことで採譜 F-measure が下がった」という**定量的**な現場報告
4. 中国語の研究者アカウントによる AMT 限界の体系的スレッド

これらは論文・GitHub issue・Reddit/Discord に多い可能性があり、**X だけを母集団にすると過少**になりやすい。

---

## 6. 出典一覧（主要投稿・時系列）

| 日付 | アカウント | 種別 | 要点 | URL |
|------|------------|------|------|-----|
| 2022-12-07 | `@honualx` | 研究者（Demucs作者） | 6s モデル: bleeding + artifacts; 曲により旧モデル推奨 | https://x.com/honualx/status/1600551855972663316 |
| 2023-02-22 | `@honualx` | 同上 | bleeding / corrupted labels 学習ベースライン | https://x.com/honualx/status/1628436176787890176 |
| 2023-08-31 | `@honualx` | 同上 | 残響・エフェクト多い録音への分離の汎化不足 | https://x.com/honualx/status/1697327081103962570 |
| 2024-06-18 | `@WasThatZero` | カバー制作者 | audio-to-MIDI 不正確さは入力 vocal 品質の問題が多い | https://x.com/WasThatZero/status/1803180840647561294 |
| 2024-08-22 | `@zawazaw` | ヤマハ MIR 研究 | in-the-wild 多声ピアノリアルタイム採譜 | https://x.com/zawazaw/status/1826526455712604379 |
| 2024-08-22 | `@DinoDiMuro` | 音楽家 | 1971 cassette: bleed 多め | https://x.com/DinoDiMuro/status/1826654444077154797 |
| 2024-10-07 | `@oomfatuated` | 個人 | Demucs/BSRNN/Roformer artifact 嫌悪 | https://x.com/oomfatuated/status/1843309355611095413 |
| 2025-03-06 | `@soundradix` | 製品 | monophonic 楽器/ボーカル前提の pitch tracking | https://x.com/soundradix/status/1897679215958630513 |
| 2025-03-16 | `@kamath_harish` | ML実務 | 多声採譜は難・データ問題 | https://x.com/kamath_harish/status/1901319546339791115 |
| 2025-06-06 | `@thecollegehill` | 制作者 | AI stem は常に artifact | https://x.com/thecollegehill/status/1931019780049301533 |
| 2026-05-09 | `@yonagip` | DTM/AI音楽 | Demucs Vo漏れ → 二段分離 | https://x.com/yonagip/status/2053176652252008661 |
| 2026-06-13 | `@suno` | 企業 | 周波数分離から再生成へ（artifact 前提） | https://x.com/suno/status/2065862499765821916 |
| 2026-07-10 | `@MireloAI` / `@kyutai_labs` | 製品・研究 | stem 必須だった既存解; データ不足がボトルネック | https://x.com/MireloAI/status/2075536492177354771 ほか |
| 2026-07-10 | `@helloLizZhang` | AI起業家 | ポリフォニーが hard; dense jazz | https://x.com/helloLizZhang/status/2075615962091729343 |
| 2026-07-11 | `@IamPranavJ` | エンジニア | full mix 無分離は hard; dense mixes | https://x.com/IamPranavJ/status/2075799077669998881 |
| 2026-07-11 | `@saen_dev` | 開発者 | 10年 mediocre; jazz 精度への疑問 | https://x.com/saen_dev/status/2075895527124631928 |
| 2026-07-15 | `@VK_ROXy` | 個人（宣伝色） | frequency bleed / pad ghosting | https://x.com/VK_ROXy/status/2077367072451965179 |
| 2026-07-19 | `@indestwas` | 一般 | きれいな分離が最不確実; Demucs も pas fou | https://x.com/indestwas/status/2078974770553487812 |
| 2026-07-20 | `@juliendausset` | 作曲/レーベル | 細分ステム不安定; other まとめの方が安全な場合 | https://x.com/juliendausset/status/2079206480759415221 |

---

## 7. 調査方法（再現用）

- X semantic search: monophonic/polyphonic pitch, Demucs bleed, stem separation transcription 等
- X keyword search（Latest/Top）:  
  `Demucs OR Spleeter OR UVR` × `bleed OR artifact`  
  `"audio to MIDI"` × fail/bad  
  `"polyphonic transcription"`  
  中文: `扒谱` `音源分离` 等  
  from: `@honualx` `@zawazaw` `@kyutai_labs`
- スレッド取得: Demucs v4 告知、MuScriptor 発表、多声採譜コメント

---

## 8. まとめ（投稿から言えることだけ）

1. **多声採譜の難しさ**は、研究者・実務ML・制作者の間で共通認識（データ不足、スペクトル競合、dense jazz/dense mix）。
2. **単音前提**は、今でも製品仕様として残り（例: monophonic pitch-tracking EQ）。pYIN/CREPE 固有の失敗談は X 上では表に出にくい。
3. **音源分離の限界**は、Demucs 作者自身が bleeding/artifacts・曲依存・残響汎化を認めており、実務側も Vo漏れ・artifact 常在・細分不安定・周波数分離の ghosting を報告。
4. 分離が「必ずしも採譜前処理の最善」ではない、という方向の言説が 2026 年時点で強まっている（full-mix 直 MIDI の製品訴求、other まとめの方が安全、等）。
5. **中国語の技術失敗ログは薄い**。英語の研究/製品アカウントと、日英の DTM 実務投稿が情報の中心。

---

*本レポートは X 公開投稿のみに基づく。論文結果や未公開実験の補完は行っていない。*
