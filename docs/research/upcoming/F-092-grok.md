# 生成AI楽曲向け採譜プリセット  
## X実務調査レポート（合成音色・クリーンミックス前処理／量子化）

調査日: 2026-07-21  
対象: X（旧Twitter）の実務者・研究者・開発者投稿（英語・中国語中心、関連の日英混在含む）  
観点: 成功例 / **失敗例（重点）** / 限界 / ベストプラクティス / 最新トレンド  
方針: **実投稿ベース・出典つき**

---

## 1. 調査スコープと機能定義

本レポートが扱う「生成AI楽曲向け採譜プリセット」は、次のようなパイプラインを指す。

| 層 | 内容 | 実務での言い方 |
|---|---|---|
| 入力 | Suno / Udio 等の **Text-to-Audio 出力**（合成音色・高圧縮・クリーンだが“楽器境界が曖昧”なミックス） | AI track / generated mix |
| 前処理 | 分軌（stem）、ノイズ除去、テンポ/キー推定、帯域整理 | stem split / clean mix prep |
| 採譜 | Audio→MIDI（単音/多楽器/フルミックス） | AMT / audio-to-MIDI |
| 後処理 | **時間量子化・音階量子化・プログラムマップ・ベロシティ整形** | quantize / scale lock / drum map |

X上では「プリセット」という製品用語より、  
**stem→MIDI、full-mix multi-instrument transcription、quantize after Basic Pitch** という**ワークフロー単位**で議論されている。

---

## 2. エグゼクティブサマリー（投稿から見える構造）

1. **最大の失敗パターンは「人力と逆向きの制作フロー」**  
   人力: MIDI → オーディオ  
   AI楽曲: オーディオ → MIDI（復元問題）  
   → 抑揚・楽器帰属・重なり帯域で破綻しやすい。

2. **合成データで強いモデルは実録音で崩れる**（domain gap）  
   逆に、**合成音色のAI楽曲**は「合成分布に近い」ため、クリーンミックス前処理＋量子化が効きやすい一方、**非音高パーカッション・重ね音色・グライド**で破綻。

3. **2026年の主戦場は full-mix multi-instrument AMT**（MuScriptor 等）と、**Suno系の stem + MIDI export** の二系統。

4. 中国語圏は技術ディテールより、**「AI譜を扒る（耳コピ/MIDI化）ことへの倫理・規約・自己満足批判」**が強い。

---

## 3. 失敗例（重点・投稿ベース）

### F1. Audio→MIDI 自体が「期待と全く違う」  
**実務者（DTM/プロデュース）の典型失敗談**

> 「未だにAUDIO to MIDIは上手くいかない」  
> AIミュージックは人力と逆（オーディオをMIDIに戻す）。  
> **抑揚がいまいち**、**周波数のカブる帯域で声か楽器か判別できず**、再生すると**ぜんぜん期待通りじゃない**。  
> — @TaccsNoName（2026-07-17）  
> 出典: https://x.com/TaccsNoName/status/2077939092369842370

**示唆（プリセット設計）**
- フルミックス直投入はデフォルトにしない  
- 声/楽器の帯域衝突に対する **instrument prior / stem 前処理** を必須化  
- 出力は「完成譜」ではなく **編集用下書きMIDI** と位置づける

---

### F2. AI生成器が「MIDIに対して dumb」  
**音楽側の根本批判**

> Suno を使い込むと欠点が見える。**effectively dumb to MIDI**。  
> ミュージシャンがなぜ問題か説明する。**どのAI音楽生成器も説得力ある形で解けていない。baffling**。  
> — @faraway_lights（2026-05-28）  
> 出典: https://x.com/faraway_lights/status/2059959751836938410

**示唆**
- 「生成AI楽曲向け採譜」は生成器の内部構造を読むのではなく、**波形からの推定**であり、情報欠落が本質  
- プリセットのKPIは **「原曲再現率」ではなく「編集可能MIDI到達率」** に置くべき

---

### F3. 合成訓練で高スコア → 実録音で崩壊（研究者/技術解説）

> **Most multi-instrument music transcription is trained on synthesized MIDI. It scores well on synthetic test sets — and then falls apart on a real recording.**  
> — @Marktechpost（MuScriptor解説, 2026-07-10）  
> 出典: https://x.com/Marktechpost/status/2075689501855457545

開発側も同趣旨を自認:

> 合成 150万MIDIで pre-train → **real data fine-tune が最大の品質ドライバー** → 人手検証300曲で RL post-train  
> — @kyutai_labs（2026-07-10）  
> 出典: https://x.com/kyutai_labs/status/2075540052700954997

**示唆（逆説的な重要点）**
- 生成AI楽曲は「合成音色寄り」なので **合成pretrain系モデルと相性が良い**  
- しかし **実機録音・ライブ・爵士密聚** には別プリセットが必要  
- 1プリセットで両用途を兼ねると **両方中途半端** になりやすい

---

### F4. 多声・ペダル・重なりでピアノすら壊れる

> audio to midi for piano is **genuinely hard**  
> **polyphony, pedal and overlapping notes wreck most models**  
> — @irshit0（2026-06-29）  
> 出典: https://x.com/irshit0/status/2071641834087215303

**示唆**
- 合成ピアノでも sustain/ペダル残響は onset を汚す  
- プリセットに **pedal strip / harmonic suppression / max polyphony cap** が必要

---

### F5. Basic Pitch 系の実務失敗（変換不能・待ち地獄・精度トレードオフ）

**変換不能/待ちすぎ**

> THE ALFEE「Starship…」を Basic Pitch で **全然MIDI変換出来ない**。  
> 数時間待っても気配なし → OPEN MUSIC AI に切替（精度は低いが速い）  
> — @kykukaz32768（2026-07-14）  
> 出典: https://x.com/kykukaz32768/status/2077021737850704240  

> Basic Pitch は便利だが **MIDI変換に時間かかりすぎ**。曲によってエンドレス待機。  
> 質を落としてでも Open Music AI に鞍替え。  
> — 同アカウント（2026-07-14）  
> 出典: https://x.com/kykukaz32768/status/2077016718749392973

**精度は高くないが「0よりマシ」**

> Melodyne / BASIC PITCH でMIDI化。**精度はめちゃ高いわけではない**が、打ち込み未経験なら0からより楽。**BPMを必ず合わせてから**。  
> — @NoR3_Music（2026-07-16）  
> 出典: https://x.com/NoR3_Music/status/2077725459601928277

**示唆**
- プリセットに **timeout / フォールバックモデル**  
- **BPMロック必須**（量子化前にテンポ確定）  
- UX上「高精度1モデル」より **速い低精度 + 手動修正** が選ばれる

---

### F6. 単音ツールの限界 / 音色・抑揚転送の失敗

> SV2 の audio-to-midi: ノート検出は改善したが、**pitch line transfer が完全に動かない**トレードオフ  
> — @vibraslapathon（2025-03-26）  
> 出典: https://x.com/vibraslapathon/status/1904905428368040159

> ACE Studio は **平打ちMIDIに抑揚を乗せる**方向が面白いが、**単音楽器限定**  
> — @TaccsNoName（前掲）

**示唆**
- 「ノート列の正しさ」と「表現（bend/portamento/velocity curve）」は別問題  
- 合成音色プリセットは **note-only モード** と **expression モード** を分離

---

### F7. ドラムMIDIは「取れても使えない」

Mirelo 側の実務認識:

> drums は **consolidated midi stem** なので **manual mapping がまだ必要**  
> 標準ユニバーサルな drum plugin mapping はあるか？  
> — @MireloAI（2026-07-10）  
> 出典: https://x.com/MireloAI/status/2075624374338465847

**示唆**
- 採譜成功 ≠ 制作で使える  
- プリセットに **GM / Ableton Drum Rack / Addictive Drums 等のマップ変換** を同梱すべき

---

### F8. 電子音楽・非音高素材への不安（質問として頻出）

> how well does it handle **electronic music**?  
> — @armandsumo（MuScriptor発表への反応, 2026-07-10）  
> 出典: https://x.com/armandsumo/status/2075596864208953386

**示唆**
- シンセリードのグライド、ノイズヒット、ワブル、ワンショット系は MIDI 表現が難しい  
- 生成AI楽曲プリセットは **tonal tracks only / unpitched FX を除外** を明示

---

### F9. 中国語圏: 「扒AI譜」への倫理・規約・自己満足批判

> 用正常的音乐制作流程去 **扒AI的谱**，评价为跟描改AI图的坐一桌，**纯纯的自我满足**  
> — @tech635（2026-06-19）  
> 出典: https://x.com/tech635/status/2068048445177524565

> 兴趣社群一刀切禁止生成式AI… 想把魔性歌做成 ROM Hacking 素材。但70%がAI生成なので **不能去扒谱、制作素材并投稿**  
> — @tcdwww（2026-07-21）  
> 出典: https://x.com/tcdwww/status/2079392204766982582

**示唆（製品/機能外だが重要）**
- 技術的成功と **コミュニティ規約・倫理的受容** は別  
- プリセットUIに「学習/投稿ポリシー注意」「生成曲の権利不確定」警告が必要

---

### F10. 失敗の周辺（混同されやすいが関連）

| 失敗 | 投稿要旨 | 関連度 |
|---|---|---|
| 圧縮アーティファクト学習 | YouTubeリップ訓練で出力が crunchy（@RoyalCities） | 生成側品質→採譜難易度 |
| 局所は正しいが大局構造がない | 音楽生成の構造破綻（@Blarg08125613） | 量子化グリッドが曲中でずれる遠因 |
| Melodyne がノートを見失う | 歪み/誤ピッチで「どうしていいか分からない音」に（@TomoAriesVT） | 表現付き転写の限界 |

出典例:  
- https://x.com/RoyalCities/status/2077820242911220139  
- https://x.com/Blarg08125613/status/1896355878338748716  

---

## 4. 成功例（投稿ベース）

### S1. 難録音のフィンガーピッキングを実用レベルでMIDI化（MuScriptor demo）

> 故バンドメンバーの **poorly recorded complicated fingerpicking** を demo で採譜 → Ample Guitar で再生。  
> 実ギタリスト置換ではないが、**学習用/暫定パートとして道が開けた**。他に解けなかったパズル。  
> — @SpacklMarketing（2026-07-10）  
> 出典: https://x.com/SpacklMarketing/status/2075606950641840340

**成功条件**
- 単一/主役楽器寄り  
- 音高が明確  
- 「完成演奏」ではなく「学習・代替の下書き」

---

### S2. フルミックス多楽器を一括MIDIトラック化（開発者側・成功物語）

> full mix から voice / drums / bass / keys 等を **separate MIDI tracks**  
> stem 不要が従来との差  
> — @MireloAI / @kyutai_labs（2026-07-10）  
> 出典: https://x.com/MireloAI/status/2075536492177354771  
> 出典: https://x.com/kyutai_labs/status/2075540047613276197

技術メトリクス（第三者要約）:
- Multi F1 48.2 vs YourMT3+ 21.9 等（@Marktechpost 前掲）

**ただし** 成功は「ベンチ・デモ」で、現場は F1–F8 の失敗が併存。

---

### S3. Suno → Stem → MIDI → メロ追加（クリエイター実運用）

> 前半: Suno Instrumental/Stem分解  
> 後半: MIDI変換してメロディ追加  
> — @kogxto（2026-07-05）  
> 出典: https://x.com/kogxto/status/2073627936645931303

同様の設計思想（英語）:

> one-shot AI track は slop  
> **stem-separation-to-midi で MIDI を高速イテレーション**するのが alpha  
> — @joe__touring（2026-06-21）  
> 出典: https://x.com/joe__touring/status/2068775828352098695

---

### S4. NeuralNote（Basic Pitch + 量子化UI）—「手で全部打ち直さない」

> polyphonic + pitch-bend + **scale and time quantization** + DAWへD&D  
> — @DanKornas（2026-07-21）  
> 出典: https://x.com/DanKornas/status/2079357160400580624

**生成AI楽曲プリセットとの親和点**
- クリーンな単一音色/ボーカル/コード弾きに強い  
- 量子化を **採譜後の別段** として明示している点が実務的

---

### S5. ステム単体投入で精度が上がる（実務の定石）

> Ultimate Vocal Remover / Audacity OpenVINO で **ステム分割してから** 読ませると MIDI検出精度が上がる、と聞き及ぶ  
> — @RE_DO（2026-07-07）  
> 出典: https://x.com/RE_DO/status/2074450860453855696

---

## 5. 限界（投稿が共有する「ここまで」）

| 限界 | 根拠投稿 | プリセットへの含意 |
|---|---|---|
| 復元問題（Audio→MIDIは不可逆） | @TaccsNoName, @faraway_lights | 100%再現を約束しない |
| 合成/実録音の domain gap | @Marktechpost, @kyutai_labs | 用途別プリセット分割 |
| ポリフォニー・ペダル | @irshit0 | poly cap / pedal処理 |
| 楽器帰属の曖昧さ | @TaccsNoName, @pagarciadom（単音時代の限界指摘） | stem or instrument conditioning |
| ドラムマップ非標準 | @MireloAI | map 変換必須 |
| 表現（bend/抑揚） | @vibraslapathon, ACE Studio言及 | note-only default |
| データ不足が長年のボトルネック | @kyutai_labs「MT3以来 data が bottleneck」 | モデル更新よりデータ戦略 |
| 倫理・投稿規約 | 中文 @tech635, @tcdwww | 機能外のガードレール |

研究文化の「苦い教訓」:

> 和声構造を手で入れたモデルが、**MT3（transformer + 大量データ）** に負けた  
> — @jxmnop（2025-05-27）  
> 出典: https://x.com/jxmnop/status/1927385194601886065

→ プリセットの複雑ルールより **データ適合と後処理の組み合わせ** が勝つ、という現場感。

---

## 6. ベストプラクティス（投稿から抽出した「効く手順」）

### BP1. 生成AI楽曲専用の標準パイプライン（実務合意に近い形）

```
[AI mix] 
  → ① BPM/Key 固定（必須）
  → ② Stem 分離（vocal / bass / drums / other）
  → ③ トラック種別ごとに採譜モデル
  → ④ 時間量子化（1/16 or 1/8、スウィングは後）
  → ⑤ 音階量子化（検出キー or ユーザー指定）
  → ⑥ ドラムマップ / プログラム変更
  → ⑦ 人手で「ゴーストノート削除・オクターブ誤検出修正」
```

根拠の組み合わせ:
- BPM合わせ: @NoR3_Music  
- Stem first: @RE_DO, @joe__touring, @kogxto  
- Quantize UI: NeuralNote (@DanKornas)  
- Drum map: @MireloAI

### BP2. 「クリーンミックス向け前処理」でやるべきこと / やらないこと

| やる | やらない |
|---|---|
| 軽いハイパスで泥を減らす | 過度なマスタリングEQ（倍音を削り音高手がかりを消す） |
| stem 分離後に再採譜 | フルミックス1パスで全楽器を信じ切る |
| onset を立てる軽い transient 強調 | 強コンプでダイナミクスを潰す |
| 無音/FX区間のマスク | ノイズ床を「ノート」として通す |

（クリーンミックス一般論の背景: マスキング除去の重要性 — @natemixing  
https://x.com/natemixing/status/1735070213496803717 ）

### BP3. 量子化の段階分け（失敗を減らす）

1. **Hard quantize（1/16）**: 電子/ループ系AI曲向け  
2. **Soft quantize（strength 50–70%）**: 人間味残し  
3. **Scale quantize only**: 時間は触らずピッチだけ直す（グライド多用曲）  
4. **No quantize + manual**: ジャズ/ルバート/表情重視

NeuralNote が「listen → adjust → scale & time quantize」と順序を示している点が参考（前掲）。

### BP4. 成功しやすい入力条件（プリセットの「適合チェック」）

- 単旋律 or 明確な主メロ  
- 合成ピアノ/シンセリード（倍音が安定）  
- ドラムとメロの帯域が分離  
- 固定テンポ（AI曲でも途中でBPMドリフトしないもの）  

逆に失敗しやすい:
- 重ね厚みマキシマイズ済み  
- ボイスとシンセが同帯域  
- 非音高FX大量  
- ジャズ密聚、ペダル多用ピアノ

### BP5. 生成AI楽曲なら「MIDI直出し」を優先、無理なら stem→MIDI

市場の需要側:
- Mureka が **real MIDI export + 12-stem** を売りに（@pillitterip）  
  https://x.com/pillitterip/status/2071122348011352507  
- 「Suno が MIDI メインなら DAW 勢に浸透」（@com2561）  
  https://x.com/com2561/status/2078455330279940423  
- 中文: 「Suno Studio は分轨+MIDI抽出できたが、**版权诉讼と音质模糊**がボトルネック」（@luyun0120）  
  https://x.com/luyun0120/status/2073048401730806250

---

## 7. 最新トレンド（2025–2026, X上）

### T1. Full-mix Multi-instrument AMT の「Whisper モーメント」願望

> Music transcription really has been missing its **whisper moment**. Polyphony is the hard part  
> — @helloLizZhang（2026-07-10）  
> 出典: https://x.com/helloLizZhang/status/2075615962091729343

MuScriptor（Kyutai × Mirelo, 2026-07）がこの文脈の中心:
- synthetic pretrain → real finetune → RL  
- instrument conditioning（drums only 等）

### T2. AI音楽プラットフォームの「Studio化」: stem + MIDI export

Suno Studio 系の語り:
- multitrack / stem / MIDI export を DAW 寄せに（@SidKingsley 等）  
- 一方「dumb to MIDI」批判は残存（@faraway_lights）

### T3. ワークフロー思想の分断

| 陣営 | 主張 | 代表的投稿 |
|---|---|---|
| 生成完結 | 1プロンプトで曲 | （多数の宣伝投稿） |
| ツール利用 | stem/MIDI は合法的な制作部品 | @Cheeze_Coolman, @joe__touring |
| 倫理忌避 | 扒AI譜＝描改AI図 | @tech635 |

> AI to separate stems / audio to midi は production の道具。  
> SUNO で丸ごと曲を作るのは production ではなく LLM の slop。  
> — @Cheeze_Coolman（2026-07-09）  
> 出典: https://x.com/Cheeze_Coolman/status/2075284053906141333

### T4. オープンソース実装のDAW埋め込み

- NeuralNote = Basic Pitch をプラグイン化 + 量子化（前掲）  
- Basic Pitch 以降、DAW/シーケンサに Audio→MIDI が急増したという観測（@RE_DO）  
  https://x.com/RE_DO/status/2074550154053800158

### T5. 「合成データは敵ではなく、pretrain用燃料」

MuScriptor 以降の共通言語:
- 合成だけで閉じると **falls apart on real**  
- 合成は pretrain、本物は finetune、少量検証で RL

→ **生成AI楽曲プリセット**は、合成分布に寄せた **「Synthetic/Clean Mix profile」** を明示した製品が次の差別化点。

---

## 8. 機能設計への落とし込み（調査結果→仕様示唆）

| プリセット項目 | 推奨デフォルト（生成AI楽曲） | 根拠 |
|---|---|---|
| 入力モード | Stem-first（Full-mix は advanced） | F1, S3, S5 |
| 前処理 | BPM lock → light HP → optional stem | BP1–2 |
| モデル | multi-instrument or per-stem monophonic | T1, F4 |
| 時間量子化 | 1/16 strength 80%（電子寄り） | NeuralNote 系運用 |
| 音階量子化 | 検出キーへ snap（ON） | ghost notes 削減 |
| 表現 | pitch bend OFF（note-only） | F6 |
| ドラム | GM map + 手動 remap 警告 | F7 |
| タイムアウト | 30–120s → 低精度フォールバック | F5 |
| 出力ラベル | “Draft MIDI / not master notation” | F1, F2 |
| 規約 | AI楽曲の再配布・投稿リスク注意 | F9 |

---

## 9. 出典インデックス（主要投稿）

| ID | 種別 | URL |
|---|---|---|
| 失敗・逆フロー | @TaccsNoName | https://x.com/TaccsNoName/status/2077939092369842370 |
| MIDI-dumb | @faraway_lights | https://x.com/faraway_lights/status/2059959751836938410 |
| 合成→実録崩壊 | @Marktechpost | https://x.com/Marktechpost/status/2075689501855457545 |
| 学習レシピ | @kyutai_labs | https://x.com/kyutai_labs/status/2075540052700954997 |
| データボトルネック | @kyutai_labs | https://x.com/kyutai_labs/status/2075540049337155964 |
| ポリフォニー難 | @irshit0 | https://x.com/irshit0/status/2071641834087215303 |
| Basic Pitch 失敗 | @kykukaz32768 | https://x.com/kykukaz32768/status/2077021737850704240 |
| BPM必須 | @NoR3_Music | https://x.com/NoR3_Music/status/2077725459601928277 |
| 成功: フィンピ | @SpacklMarketing | https://x.com/SpacklMarketing/status/2075606950641840340 |
| MuScriptor発表 | @MireloAI | https://x.com/MireloAI/status/2075536492177354771 |
| Stem→MIDI 思想 | @joe__sourcing | https://x.com/joe__sourcing/status/2068775828352098695 |
| NeuralNote+量子化 | @DanKornas | https://x.com/DanKornas/status/2079357160400580624 |
| Stemで精度↑ | @RE_DO | https://x.com/RE_DO/status/2074450860453855696 |
| ドラムmap | @MireloAI | https://x.com/MireloAI/status/2075624374338465847 |
| 中文倫理批判 | @tech635 | https://x.com/tech635/status/2068048445177524565 |
| 中文規約 | @tcdwww | https://x.com/tcdwww/status/2079392204766982582 |
| 中文ボトルネック | @luyun0120 | https://x.com/luyun0120/status/2073048401730806250 |
| Bitter lesson | @jxmnop | https://x.com/jxmnop/status/1927385194601886065 |
| Whisper moment | @helloLizZhang | https://x.com/helloLizZhang/status/2075615962091729343 |

---

## 10. 調査上の限界（透明性）

1. **中国語の「技術失敗ディテール」投稿は相対的に少ない**（規約・倫理・ビジネス語りが優勢）。技術失敗の厚みは英語＋日本語実務者に偏る。  
2. Xはデモ成功がバズりやすく、**失敗はスレ返信に散在**。本レポートは検索で拾えた実投稿に限定。  
3. 「生成AI楽曲向けプリセット」という製品名そのものの議論は少なく、**等価ワークフロー（stem/quantize/AMT）から再構成**している。  
4. MuScriptor は新しく、**長期運用の失敗ログはまだ薄い**（発表直後の期待と質問が中心）。

---

## 11. 結論（プロダクト視点）

X上の実務知を一言で圧縮すると:

> **生成AI楽曲の採譜は「きれいに聞こえるから簡単」ではない。**  
> クリーンでも楽器境界が曖昧で、Audio→MIDI は構造的に失敗しやすい。  
> 勝つのはフルオート完成譜ではなく、  
> **Stem前処理 → 用途別モデル → 強めの時間/音階量子化 → 人が直せる下書きMIDI** というプリセット設計。

失敗を減らす最短の製品方針は次の3点:

1. **Full-mix 直叩きをデフォルトにしない**  
2. **量子化を「オプション」ではなく生成AI用プリセットの中核にする**  
3. **成功指標を「原曲再現」から「DAWで編集可能なMIDI」へ変える**

---

必要なら次のステップとして、上記を **機能仕様書（プリセットJSON案・パラメータ表・失敗テスト曲セット）** に落とすこともできます。
