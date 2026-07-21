# X調査レポート：採譜結果の共有用ビジュアルカード  
（波形 + 抽出音符重畳 / audiogram 形式 SNS 共有）

**調査日**: 2026-07-21  
**対象**: X（旧Twitter）上の実務者・研究者・開発者投稿（英語中心、中国語・日本語補足）  
**範囲**: 成功例 / **失敗例（重点）** / 限界 / ベストプラクティス / 最新トレンド  
**方法**: 実投稿キーワード・セマンティック検索 + 関連業界ガイド（補助）

---

## 1. 結論サマリ（製品示唆）

| 観点 | 現場の実感 |
|------|------------|
| **需要** | ある。X上で「audio→MIDI の piano roll を SNS に直接共有」が 2026-07 に急浮上（Mirelo × Kyutai） |
| **最大リスク** | 見た目は派手でも **採譜が間違っていると“公開の恥”** になる。波形/音符の重畳は「正しさの証明」にも「誤りを増幅する看板」にもなる |
| **失敗の主因** | ① 不正確な MIDI の可視化 ② 情報過多で読めない ③ 共有カード自体が使われない ④ ミュート視聴で内容が伝わらない ⑤ 12-TET/ジャンル偏り |
| **勝ち筋** | 短尺・1フック・キャプション必須・信頼度/編集余地の明示・「自分語り」可能な identity デザイン・ゲーム化（曲当て等） |

> **定義の注意**: X 上の「audiogram」は (A) 聴力検査図 と (B) 音声+波形+字幕の SNS 動画、の両義がある。本レポートは **(B) ソーシャル共有用ビジュアル**、および **採譜 piano roll / 音符オーバーレイ共有** に限定する。

---

## 2. 成功例（実投稿ベース）

### 2.1 採譜結果そのものを SNS コンテンツにした例（2026-07、最重要）

**Mirelo × Kyutai「Audio-to-MIDI → ソーシャル共有」**  
- [@MireloAI](https://x.com/MireloAI/status/2075536492177354771)（2026-07-10）: フルミックスから楽器別 MIDI を返すモデル発表。**約 4.3k likes / 62万 views** 級の拡散。  
- 続報で **「Share で piano roll プレビューを SNS に出せる」** を明示。  
  - 「You can now share your audio-to-MIDI tracks directly from the Mirelo studio」[@AUllen40713](https://x.com/AUllen40713/status/2077335210853597541)  
  - 「share your favourite tracks on socials… challenge others to guess your songs」[@MireloAI](https://x.com/MireloAI/status/2077337264204423636)  
  - 運営も「Share ボタンで piano-roll プレビューを作って投稿して」と促す [@cjsimongabriel](https://x.com/cjsimongabriel/status/2076077108149809213)

**成功の型**  
1. **可視化がデモそのもの**（piano roll = プロダクト証拠）  
2. **ソーシャルループ設計**（曲当て / コラボ探し）  
3. **ワンクリック Share**（ツール外編集を要求しない）

### 2.2 実務現場での「解けた問題」成功談

- スタジオ実務者が「故人の複雑なフィンガーピッキング伴奏（録音品質が悪い）」をデモで起こし、Ample Guitar で検証。「他では解けなかった」[@SpacklMarketing](https://x.com/SpacklMarketing/status/2075606950641840340)  
  → 共有カード用途でも、**「復元できた」という物語**が強い。

### 2.3 中国語圏でのポジティブ反応

- 「管弦楽でも七七八八扒れる」「开源・本地・隐私」[@YMike59492](https://x.com/YMike59492/status/2075840791281619050)  
- 「开源这点挺加分，音乐转录终于能多点可复现的东西了」[@ajs6888](https://x.com/ajs6888/status/2076092628941324584)

### 2.4 ポキャスト系 audiogram の成功インフラ

- Headliner の Automatic Audiogram wizard を使いクリップ投稿を継続 [@headlinerapp_](https://x.com/headlinerapp_/status/2077457295546479084)  
- Apple Podcasts × Headliner 無料テンプレ協業 [@ElissaBiz](https://x.com/ElissaBiz/status/2071613005096272257)  
- 歴史的に Anchor が「audio → transcribed shareable video」を打ち出しプラットフォーム側が共有を標準化 [@spotifycreator](https://x.com/spotifycreator/status/894922568276357120)（2017）

### 2.5 開発者視点：波形ビューの技術成功

- 4分曲を <1s ロード、>3000fps の **動的 LOD 波形** [@ENDESGA](https://x.com/ENDESGA/status/1736932538483134879)  
  → 共有カード生成の裏方（長尺波形の軽量レンダ）として参照価値大。  
- ゲーム charter 向け「複数波形・低メモリ・toaster 向け low detail」[@FNFCodenameEG](https://x.com/FNFCodenameEG/status/1772436480620691803)

### 2.6 実験的ビジュアル成功

- 3D + 五度圏配置の音可視化ツール（Three.js / Web MIDI）[@measure_plan](https://x.com/measure_plan/status/2072044774211637359)  
- Images that Sound（画像=スペクトログラムの dual canvas）[@iScienceLuvr](https://x.com/iScienceLuvr/status/1792807445422641516)

---

## 3. 失敗例（重点・多め）

### 3.1 失敗クラス A：採譜精度が可視化で「丸見え」になる

| # | 失敗内容 | 出典 |
|---|----------|------|
| A1 | **audio-to-MIDI は長年 mediocre**。「jazz の複雑アレンジ精度は？」と懐疑 | [@saen_dev](https://x.com/saen_dev/status/2075895527124631928) |
| A2 | 実ユーザー評価：**「まだ there yet ではない」**。現代シンセで false trigger、**ドラム検出が驚くほど悪い**。メロディは dense mix でも良いが | [@SubarcticRec](https://x.com/SubarcticRec/status/2076210993487655356) |
| A3 | 同ユーザー過去評：Ableton/Logic の audio-to-MIDI は **quite bad / very inaccurate** | [@SubarcticRec](https://x.com/SubarcticRec/status/2020164809648492894) |
| A4 | ミュージシャン [@JOHNMAUS](https://x.com/JOHNMAUS/status/1986174329449570713)：**「Melodyne 等に載っているはずなのに all pretty bad」**。Chordino（数年前）の方が和声では良かった、と |
| A5 | Ableton は **少しずれた bad notes を足す**。スケール強制でごまかす運用 | [@dj_irl](https://x.com/dj_irl/status/2016891106236256452) |
| A6 | Melodyne autosnap で **wrong notes → 変な pitchiness**（公開カバーでも発生） | [@aida_lyra](https://x.com/aida_lyra/status/1969148734941327673) |
| A7 | SynthV audio-to-MIDI：ノート検出は改善したが **pitch line transfer が壊れた** という tradeoff | [@vibraslapathon](https://x.com/vibraslapathon/status/1904905428368040159) |
| A8 | **Microtonality 非対応**（12-TET 前提）。MIDI は任意周波数を持てるのにモデルが追従しない | [@nselmi](https://x.com/nselmi/status/2075987643624493519) |
| A9 | 哲学的批判：**音符転写は tone / velocity / human imperfection を落とす。wrong prize** | [@Jasonwang1211](https://x.com/Jasonwang1211/status/2076325067777265875) |

**製品への直撃**:  
「波形 + 抽出音符重畳」カードは、**誤検出を静的・動的に増幅する**。成功デモ動画とユーザー実試のギャップが X 上で既に言語化されている。

### 3.2 失敗クラス B：共有カード機能が「誰にも使われない」

| # | 失敗内容 | 出典 |
|---|----------|------|
| B1 | 収益トラッカー v2 で **「removed the share card nobody was using」** を明示的に削除 | [@cartist00](https://x.com/cartist00/status/2047694517579452810) |
| B2 | shareability cards は飽和。**「別の personalized card では足りない。first or best でなければ埋もれる」** | [@pixelandpump](https://x.com/pixelandpump/status/2079106720404767110) |
| B3 | Apple Music の Twitter 共有カード欠如への不満（プラットフォーム側の穴） | [@roberthaverly](https://x.com/roberthaverly/status/1947780181860470975) |

**示唆**: 機能を作っても **シェア動機（identity / 自慢 / ゲーム / コラボ）が弱いと死蔵** → 後で削除される。

### 3.3 失敗クラス C：audiogram フォーマット自体の運用失敗

業界ガイド（X 外だが投稿と整合）で繰り返し挙がる典型失敗:  
- フックが遅いクリップ  
- 字幕がモバイルで読めない  
- 波形だけ・キャプションなし（ミュート視聴で死ぬ）  
- 長尺で離脱  
出典: Recast / Campaign Donut 等の audiogram best practices ガイド。

関連 X 観察:  
- 音声は動画より情報量が少なく **シナリオ投入が難しい**、パッシブ視聴では「どのクリップが良い」か測れない [@thepanta82](https://x.com/thepanta82/status/2079095087045169250)  
- 静的画面は retention を殺す（「visual problem」）[@Josh_netics](https://x.com/Josh_netics/status/2078021858981544110)  
- 既存ツールが **sucked or paid** で自作に走った開発者 [@sire_ralph](https://x.com/sire_ralph/status/2051791026025632122)

### 3.4 失敗クラス D：可視化・レンダリングの技術失敗

| # | 失敗内容 | 出典 |
|---|----------|------|
| D1 | 波形プレゼン実験：**「looked better in my head」**（L/R absolute 表示が期待外れ） | [@ENDESGA](https://x.com/ENDESGA/status/1737052500333916381) |
| D2 | マルチ voice MIDI で **Voice 割り込み → レンダリング不良** | [@hmking_works](https://x.com/hmking_works/status/2077027936977526827) |
| D3 | 波形だけでは見えない成分があり **スペクトログラムが必要**（編集実務） | [@ewzzy](https://x.com/ewzzy/status/1648731794634686464) |
| D4 | 低品質 USB-MIDI 変換器で **遅延・データエラー**（周辺機器だが「MIDI 可視化信頼」を壊す） | [@DraTohru_XLN](https://x.com/DraTohru_XLN/status/2078729215604867218) |

### 3.5 失敗クラス E：モデル/データ限界の「公開バイアス」

- Kyutai 公式スレでも **データ不足が AMT の長年ボトルネック** と明言（MT3 2022 以来）[@kyutai_labs](https://x.com/kyutai_labs/status/2075540049337155964)  
- 外部まとめでも **pop / 西洋クラシック寄りバイアス、レア楽器・過小代表ジャンルは信頼性低下** と記載。  
- 中国語紹介でも「七七八八」＝**完全ではない**含意 [@YMike59492](https://x.com/YMike59492/status/2075840791281619050)

### 3.6 失敗クラス F：「共有の物語」と著作権・商用曲

- Mirelo の「favorite tracks を SNS に share」は **商用楽曲の採譜可視化公開**になり得る → X 上では盛り上がる一方、**権利・Content ID・教育的利用範囲**の失敗モードが未消化（投稿は宣伝寄り、批判側は精度・哲学に偏る）。  
- 失敗パターン予測（投稿から外挿）: 誤譜を「公式っぽく」見せて炎上 / 著作権者から削除 / 学習用途と宣伝用途の混同。

---

## 4. 限界（X 上のコンセンサス）

1. **フルミックス多楽器 AMT は未解決問題に近い**  
   - 10年 mediocre という実務感 [@saen_dev](https://x.com/saen_dev/status/2075895527124631928)  
   - 2026 の MuScriptor でも「advancement であって solved ではない」[@SubarcticRec](https://x.com/SubarcticRec/status/2076210993487655356)  
   - 対して HF デモ作者は「zero-shot in the wild → solved」と楽観 [@fffiloni](https://x.com/fffiloni/status/2076624097124008301) → **マーケ言説と実ユーザー評価が分裂**

2. **可視化できる ≠ 音楽が伝わる**  
   - 音符は texture / feel を落とす [@Jasonwang1211](https://x.com/Jasonwang1211/status/2076325067777265875)  
   - 波形は時間振幅、スペクトログラムは pitch×time で情報量が違う [@ewzzy](https://x.com/ewzzy/status/1648731794634686464)

3. **共有カード飽和**  
   - Spotify Wrapped 型が強すぎて、中途半端なカードは埋もれる [@pixelandpump](https://x.com/pixelandpump/status/2079106720404767110)

4. **プラットフォーム制約**  
   - X は生音声アップロードが弱い → audiogram/video 化が必須、という運用知識（Grok 回答にも定番化）  
   - ミュート視聴が支配的 → 字幕なし波形は「動く壁紙」で終わる。

5. **信頼の非対称性**  
   - デモ曲（クリーンな mix）では美しい piano roll 共有が回る  
   - ユーザーの messy real-world 録音では false triggers が目立つ → **カードを出すほど信頼が下がる**

---

## 5. ベストプラクティス（投稿から抽出）

### 5.1 プロダクト UX

| 推奨 | 根拠 |
|------|------|
| **ワンクリック Share（piano roll / waveform preview）** | Mirelo が明示的に採用・促進 |
| **「曲当て」「コラボ探し」などゲーム/社会的動機** | Mirelo share 発表の文言 |
| **編集可能であることが前提**（確認後に共有） | piano roll で note 調整してから export する公式導線。 |
| **信頼度インジケータ**（自信スコア / 楽器別 reliability） | 失敗談 A 群への直接対策（投稿では未実装が多い＝機会） |
| **楽器レイヤの on/off** | Gradio デモで instrument switch / Demucs prep が評価 [@fffiloni](https://x.com/fffiloni/status/2078128083995963779) |
| **使われない share は削る** | [@cartist00](https://x.com/cartist00/status/2047694517579452810) |

### 5.2 ビジュアル設計

| 推奨 | 根拠 |
|------|------|
| **短尺・1フック** | audiogram best practices の中核。 |
| **キャプション必須（しかも校正必須）** | ミュート視聴 92% 説・自動字幕は固有名詞を落とす。 |
| **波形は画面の約 1/3、安全余白** | 同上 |
| **音符重畳は「全部載せ」禁止** | dense polyphony は読めない（失敗 A2, D2）→ **メロディ or 選択楽器のみ**、またはヒートマップ化 |
| **スペクトログラム切替** | 波形だけではピッチが読めない実務談 [@ewzzy](https://x.com/ewzzy/status/1648731794634686464) |
| **LOD / 低詳細モード** | 長尺共有生成のパフォーマンス [@ENDESGA](https://x.com/ENDESGA/status/1736932538483134879), [@FNFCodenameEG](https://x.com/FNFCodenameEG/status/1772436480620691803) |

### 5.3 コンテンツ戦略

| 推奨 | 根拠 |
|------|------|
| **identity 共有**（「これが私の採譜 / 私の分析」） | Wrapped 型成功論 [@pixelandpump](https://x.com/pixelandpump/status/2079106720404767110) |
| **1 → 多 formal 再配布**（clips / audiogram / quote card） | マーケ実務投稿の定番 [@TheElderCreativ](https://x.com/TheElderCreativ/status/2066777831607001562), [@Jai_Bhatia_](https://x.com/Jai_Bhatia_/status/2068755834486526015) |
| **プラットフォーム別アスペクト**（9:16 / 1:1 / 16:9） | Headliner・ClipSync 系の前提 [@polsia](https://x.com/polsia/status/2073420801748214230) |
| **「七七八八」レベルの正直さ**（完全自動を約束しない） | 中国語圏の表現が現実的 [@YMike59492](https://x.com/YMike59492/status/2075840791281619050) |

### 5.4 採譜ドメイン固有

| 推奨 | 根拠 |
|------|------|
| 共有前に **scale-lock / 手動修正** | [@dj_irl](https://x.com/dj_irl/status/2016891106236256452) |
| **ドラム・電子音・マイクロトーン**は別 UI か警告 | A2, A8 |
| 共有画像に **「AI 推定・要校正」ラベル** | 失敗の公開炎上防止 |
| 可能なら **stem 分離 → 単旋律カード** をデフォルト | 単音の方が「正しそう」に見え、失敗が少ない（歴史的 mediocre ツール群の教訓） |

---

## 6. 最新トレンド（2025–2026）

### 6.1 「採譜結果の SNS 共有」がプロダクト機能になった

- 2026-07: MuScriptor / Mirelo が **研究モデル + Studio Share + X 直投稿** を一気に接続  
  - 発表 [@MireloAI](https://x.com/MireloAI/status/2075536492177354771) / 研究 [@kyutai_labs](https://x.com/kyutai_labs/status/2075540047613276197)  
  - Yann LeCun も反応 [@ylecun](https://x.com/ylecun/status/2075903521149297129)  
- 「Share → 曲当て / コラボ」は **transcription をソーシャルグラフの種**にする新トレンド

### 6.2 デモ UX の高度化

- HF Gradio: Demucs split / 高速 piano roll / crossfade original↔MIDI / score 生成 [@fffiloni](https://x.com/fffiloni/status/2078128083995963779)  
- 「LLM が読める fumen バンドル」（beat grid + chords + piano-roll pages）[@mochi_mochi_lab](https://x.com/mochi_mochi_lab/status/2077075103779840129)

### 6.3 audiogram の産業成熟とテンプレ協業

- Headliner × Apple Podcasts テンプレ  
- 「1 episode → 20 assets」（clips / X / LinkedIn / audiogram…）の自動化競争

### 6.4 共有カードの「飽和後」デザイン

- 単なる stats card は死ぬ → **侮辱的ユーモア・触覚・物語**で差別化（Zero University の学位→紙船例）[@pixelandpump](https://x.com/pixelandpump/status/2079106720404767110)  
- 採譜カードも同様に、**波形テンプレ量産では埋もれる**可能性が高い

### 6.5 中国語圏

- 開源・本地部署・隐私 が評価軸 [@YMike59492](https://x.com/YMike59492/status/2075840791281619050)  
- MuseScore は「乐谱社区」として残るが、**波形+自動音符の SNS カード**という語彙はまだ薄い（X 中国語検索では直接ヒットが少）  
- ファンアート文脈で「波形=五线谱メタファー + 自分で扒的谱」の画像共有は存在 [@ho4core](https://x.com/ho4core/status/2021329154550182296)

---

## 7. 失敗モード・チェックリスト（実装前に潰す）

共有カード出荷前に、X 上の失敗から作ったゲート:

1. **このカード、ミュートで 1 秒で意味が伝わるか？**（キャプション / タイトル）  
2. **誤検出が「公式っぽく」見えないか？**（推定ラベル・confidence）  
3. **全音符を載せてインクの海になっていないか？**  
4. **ドラム / シンセ / マイクロトーンで恥をかかないか？**  
5. **シェアする社会的動機はあるか？**（自慢 / 当てっこ / 学習ログ / コラボ）  
6. **誰も使わない機能になっていないか？**（2 週間で使用率を見て死蔵なら削る）  
7. **商用曲の公開採譜で権利リスクはないか？**  
8. **モバイル 9:16 で波形と音符が潰れていないか？**  
9. **「looked better in my head」実験を本番に載せていないか？**  
10. **編集導線なしのワンショット共有になっていないか？**

---

## 8. 製品への具体的示唆（採譜ソフト向け）

### 推奨 MVP

1. **15 秒以内の縦型動画カード**  
   - 背景: 波形（LOD）  
   - 重畳: **選択した 1 パートの音符のみ**（色分け、velocity = 不透明度）  
   - 必須: 曲名 / キー・テンポ / 「AI 推定」バッジ / 大字幕フック  
2. **共有前レビュー**（間違った音をタップで消す）  
3. **2 モード**  
   - *Flex*: Wrapped 型 stat（難易度・音域・テンポ変化）  
   - *Proof*: 波形+音符の authenticity デモ  
4. **ゲーム CTA**: 「この riff 当てて」リンク  

### 避けること

- フルミックス全楽器を一度に重ねた静止画  
- 精度を保証するコピー（「perfect transcription」）  
- キャプションなし波形ループだけ  
- シェア動機のない「Export PNG」だけ置いて放置  

---

## 9. 主要出典一覧（実投稿）

| 種別 | 投稿 |
|------|------|
| プロダクト成功 | [Mirelo 発表](https://x.com/MireloAI/status/2075536492177354771), [Share 機能](https://x.com/MireloAI/status/2077337264204423636), [Kyutai](https://x.com/kyutai_labs/status/2075540047613276197) |
| 精度失敗 | [SubarcticRec 試用](https://x.com/SubarcticRec/status/2076210993487655356), [John Maus](https://x.com/JOHNMAUS/status/1986174329449570713), [Ableton bad notes](https://x.com/dj_irl/status/2016891106236256452), [Melodyne wrong notes](https://x.com/aida_lyra/status/1969148734941327673), [microtonality](https://x.com/nselmi/status/2075987643624493519) |
| 共有カード死蔵 | [cartist remove share card](https://x.com/cartist00/status/2047694517579452810), [shareability 飽和](https://x.com/pixelandpump/status/2079106720404767110) |
| 哲学/限界 | [notes miss texture](https://x.com/Jasonwang1211/status/2076325067777265875), [decade of mediocre](https://x.com/saen_dev/status/2075895527124631928) |
| 中国語 | [MuScriptor 试用](https://x.com/YMike59492/status/2075840791281619050), [开源可复现](https://x.com/ajs6888/status/2076092628941324584) |
| 波形技術 | [ENDESGA LOD](https://x.com/ENDESGA/status/1736932538483134879), [looked better in head](https://x.com/ENDESGA/status/1737052500333916381) |
| audiogram 産業 | [Headliner](https://x.com/headlinerapp_/status/2077457295546479084), [Anchor 2017](https://x.com/spotifycreator/status/894922568276357120) |
| 補助ガイド | Recast audiogram best practices (2026) , Campaign Donut captions  |

---

## 10. 調査上の限界（正直ベース）

- X 上で **「採譜ソフト専用の波形+音符 audiogram カード」** というニッチは、**2026-07 の Mirelo Share 以前は語彙がほぼ存在せず**、議論は  
  (1) ポッドキャスト audiogram  
  (2) AMT / audio-to-MIDI 精度  
  (3) 一般 share card  
  に分裂していた。  
- 中国語は **开源 AMT 紹介が中心**で、共有カード UX 議論は薄い。  
- 医療用語 audiogram ノイズが多く、検索は高精度語彙が必須。  
- 「失敗例」は精度・死蔵・フォーマット運用に偏り、**大規模 A/B 数値**は X 投稿だけでは取りにくい（WNYC の「audiogram 付きの方が engagement 高い」系はブログ経由）。

---

### 一行で製品方針

**「正しいかもしれない音符を、美しく見せて拡散する」より、「編集可能な短尺フックを、信頼ラベル付きで、人が自慢したくなる identity に包む」**—X 上の成功/失敗はほぼこの分岐に収束する。
