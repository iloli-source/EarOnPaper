# X調査報告：採譜における強弱（ベロシティ）推定と譜面の強弱記号化

**調査日:** 2026-07-21  
**対象:** X（旧Twitter）上の実務者・研究者・開発者投稿（英語中心、中国語・日本語実務投稿で補完）  
**収集軸:** 成功例 / **失敗例（厚め）** / 限界 / ベストプラクティス / 最新トレンド  
**方針:** 実投稿ベース・投稿URL付き。このトピックはX上でもニッチで、学術・開発・記譜ツール実務の断片が散在している。

---

## 0. 結論サマリ（先に要点）

| 軸 | 実態（投稿から見える像） |
|---|---|
| **推定（audio→velocity）** | ピッチ/オンセットより一段難しい。最新多楽器モデルでも **velocity未対応・固定velocity** が実務で指摘される |
| **記号化（velocity→p/mf/ff/hairpin）** | 連続値→離散記号の写像が壊れやすい。**クレッシェンド等は特に困難** |
| **失敗の主因** | (1) データ不足 (2) 規格上の mf=64 と聴感の不一致 (3) 量子化の粗さ (4) 記譜ソフトのMIDI入出力バグ (5) 手動補完前提の現場 |
| **研究トレンド** | score-informed velocity refinement、onset/offset/velocityの分離デコード、ギター等楽器特化、大実データ＋合成事前学習＋RL |
| **中国語圏** | 「AI採譜→強弱記号」の専門議論は薄く、**「力度調整は扒譜より難しい」** という実務痛点が目立つ |

---

## 1. 問題の二段構造（投稿が語るレイヤ）

実務・研究投稿を横断すると、機能は実質 **2段** に分かれる。

```
[A] 音響 → MIDIベロシティ推定
        ↓
[B] ベロシティ列 → 譜面記号（p/mp/mf/f/ff、hairpin、スラー隣接表現）
```

- **[A]** は MIR / AMT（Automatic Music Transcription）研究とOSSモデルの領域  
- **[B]** は記譜ソフト・MusicXMLマッピング・人間の編集慣習の領域  

X上では **[A]の失敗・欠落** と **[B]の手作業前提** が特に多く語られる。

---

## 2. 失敗例・不満・事故（重点）

### 2.1 最新オープンモデルでも velocity が無い／固定

**実務者 @ntamotsu_（2026-07-11）**  
MuScriptor は「かなりよい」としつつ、明確に限界を指摘：

> 「velocity推定できないのは惜しいけどMT3より精度高い」

- 投稿: https://x.com/ntamotsu_/status/2075767005538562077  
- 文脈: Kyutai × Mirelo の MuScriptor 試用

**実務者 @yokohamiami（2026-07-12）**  
手元の自作曲を large で MIDI 化した結果：

> 「出てきたMIDIはシンプルで音色情報と**固定velocityのノートのみ**」「テンポは復元されない」「シロフォンを認識しない」「耳コピのネタには使えるか」

- 投稿: https://x.com/yokohamiami/status/2076181368980271378  

**示唆:** 2026年時点の「ベスト級オープン多楽器AMT」でも、**強弱推定はまだ本線に乗っていない**。ピッチ/楽器分離が先、velocityは後回し、という製品・研究の優先順位が現場に直撃している。

---

### 2.2 規格どおりの velocity 写像が「聴感」と合わない

**オーボエ奏者・開発者 @sha_w_（2023-04-30）**  
MIDI規格では mf ≈ velocity 64 とされるが、

> 「Velocity 64位になると、収録されている音色の倍音成分が、ピアノ(p)の域っぽく感じる」  
> 自分の中では ~89 までが mf、90〜 が piu f

- 投稿: https://x.com/sha_w_/status/1652579701419024384  

**示唆:** 譜面記号化で `64→mf` のような固定閾値を置くと、**サンプル音色・楽器・DAW音源ごとに破綻**する。失敗はモデル以前に「記号↔数値の規約」側でも起きる。

---

### 2.3 コンピュータ上の dynamics→velocity が極端に潰れる

**作曲家 @SchumakerA（2023-02-10）**  
「Computer music vs real dynamics as MIDI velocity」として極端な写像を晒し：

```
pppp 0 / ppp 0 / pp 2
mp 67 / mf 76
f 100
ff 127 / fff 127
ffff [digital clipping]
```

- 投稿: https://x.com/SchumakerA/status/1623862296937213953  

**示唆:** 下端は 0 に潰れ、上端は 127 に張り付く。**細かい強弱階層（pppp〜ffff）はMIDI 0–127に載りきらない**。採譜後に記号を復元しても、再生側で再び潰れる。

---

### 2.4 記譜ソフト側の MIDI velocity 出力バグ

**@knoike（2024-07-29 / 2024-03-29）**  
MuseScore の MIDI 出力で **全ノート velocity=1** になる回帰バグを追跡：

> 「the regression (from MS3) is still there.」  
> Issue: *Midi output sets velocity to 1 for all notes* (#22354)

別件でも開発者コメントに失望：

> 「Personally I consider MIDI output as basically "not implemented".」  
> 「それでも Velocity 1 で出力するのはナシだわー。」

- https://x.com/knoike/status/1817896544294896074  
- https://x.com/knoike/status/1773696046520049972  
- 関連Issue: https://github.com/musescore/MuseScore/issues/22354  

**示唆:** 推定が正しくても、**記譜ソフトの import/export で強弱が死ぬ**経路がある。失敗は「AI」単体ではなくパイプライン全体の問題。

---

### 2.5 MusicXML dynamics → MIDI velocity の逆算が泥沼

**@marudebot（2024-08-28）**  
hairpin（`>` `<`）は面倒なので p/f だけに絞り、MuseScore の MIDI 出力から逆算：

> 「dynamics * 0.9 だけだと 71.11 以外で midi と値が合わない」  
> 最終的に part volume と dynamics と base を組み合わせた経験式で「なんとなく合う」

- https://x.com/marudebot/status/1828794349607665847  
- https://x.com/marudebot/status/1828795809200304211  

**示唆:** **記号化の逆問題（記号→数値）でさえベンダー固有・非公開・近似**。自動記号化（数値→記号）はさらに不安定になりやすい。

---

### 2.6 ゲーム音源MIDI化でも dynamics は手動

**ViolinSpeedruns @ViolinSpeedruns（2025-10-23）**  
KH1/2 の MIDI 抽出→譜面化に成功しつつ：

> 「I still have to **add in dynamics and articulations myself** and transcribe some parts」

- 投稿: https://x.com/ViolinSpeedruns/status/1981251527533629729  

**示唆:** ピッチ列が取れても、**強弱・アーティキュレーションは人間の仕事として残る**のが現場の標準感。

---

### 2.7 中国語圏：力度調整は「扒谱より難しい」

**@edamame_6240（2026-06-03）**

> 「感觉**调整力度和延音比扒谱还复杂**」  
> （力度とサスティン調整の方が扒谱より複雑）

- 投稿: https://x.com/edamame_6240/status/2062075681341890989  

**@Dollynx5（2025-07-25）**  
対トラックと音量バランスの難しさ：

> 「本来以为对轨已经够难了，**音量平衡也好难**……还好选的是有现成谱的曲子，**再要自己扒谱我都不敢想**」

- 投稿: https://x.com/Dollynx5/status/1948800681437266049  

**@linyoucha（2020-07-16）**  
扒谱継続時の反省：

> 「这次我会尝试把主旋律提高一个八度，然后**更仔细的调整力度**」

- 投稿: https://x.com/linyoucha/status/1283625074533097473  

**示唆:** 中国語圏でも「自動強弱記号化」の専門スレは少ない一方、**力度は扒谱パイプラインで最も手のかかる後処理**として繰り返し語られる。

---

### 2.8 記譜そのものが現実音と乖離する（強弱含む一般論）

**score follower @incipitsify（2022-02-06）**

> 「something will look absurd about it, whether it’s the tempo too fast, or too “specific,” the meter, the polyrhythms… **most sounds in this world do not care about how it might look when notated**」

- 投稿: https://x.com/incipitsify/status/1490346471773949958  

**示唆:** 強弱記号化の失敗は「アルゴリズムが悪い」だけでなく、**楽音の連続表現 vs 西洋記譜の離散記号**という表現ギャップそのもの。

---

### 2.9 オーディオ→MIDI後も「生感」が無いケース

**@nir_un（2026-03-20）**  
生徒用にドラムを再構築：

> ライブ演奏でタイミングが変で piano roll で決まらない → stem to MIDI → まだダメ → **ezdrummer に入れて初めて swing & velocity が帯で決まった**

- 投稿: https://x.com/nir_un/status/2034904340398272771  

**示唆:** 生の velocity 推定が弱く、**サンプルライブラリ側のグルーヴ/velocity ヒューマナイズで補う**実務がある。自動記号化の前段で既に「推定」ではなく「置き換え」が起きている。

---

### 2.10 記譜ソフトへの機能要望＝現状不足の証拠

**ヴァイオリニスト @issaku_m（2023-09-04）**

> 「Finaleに、もうちょっとだけMIDI編集機能がついていたらなあ。**velocity, sustain, Tempo を単独とカーブでDAWのように**」

- 投稿: https://x.com/issaku_m/status/1698583543390314706  

**示唆:** 採譜後の強弱編集 UX が不足しており、**記号化以前に velocity 編集自体が摩擦**。

---

## 3. 成功例・うまくいっている／改善が見える事例

### 3.1 研究：onset / offset / velocity の分離デコード

**Yongyi Zang @yongyi_zang（2024-12-21, ICASSP 2025）**  
ピアノ転写で、

> pre-trained frame-wise encoder ＋ **onset / offset / velocity の分離デコード**が性能に大きく効く

- 投稿: https://x.com/yongyi_zang/status/1870479053100400988  

**成功パターン:** 強弱を「副産物」ではなく **独立タスク** として設計する。

---

### 3.2 研究：Score-informed な velocity 精密化

**arXiv Sound 経由の論文告知（2026-03-03）**

> *Score-Informed Transformer for Refining MIDI Velocity in Automatic Music Transcription*  
> https://arxiv.org/abs/2508.07757

- 投稿: https://x.com/ArxivSound/status/2028701785666506831  

**QMUL C4DM セミナー（2024-07-30）**  
Hyon Kim:

> *Score Informed Note-level MIDI Velocity Estimation and Its Transcription into Symbolics*

- 投稿: https://x.com/c4dm/status/1818186996021670225  

**成功の方向性:** まず粗い AMT、次に **楽譜情報で velocity を refine**、さらに **symbolics（強弱記号）へ転写**——まさに本調査テーマの研究的中核。

---

### 3.3 研究：ギターの velocity prediction（2026）

**Simon Dixon / Emmanouil Benetos 系**

> *Velocity Prediction in Automatic Guitar Transcription*  
> https://arxiv.org/abs/2606.24912

- https://x.com/ArxivSound/status/2070681391252357149  
- https://x.com/SoundPapers/status/2070051833997939091  

**示唆:** ピアノ以外でも velocity が独立課題化。楽器ごとの攻撃特性・演奏技法が推定を左右。

---

### 3.4 生成・制御側での dynamics 時間変化

**Music ControlNet 系（@_akhaliq, 2023-11）**  
テキスト制御はジャンル/気分向きで、

> **時間変化する dynamics / rhythm / melody の精密制御**が必要、と問題設定

- 投稿: https://x.com/_akhaliq/status/1724277147177541920  

**示唆:** 「採譜」だけでなく「生成」でも **dynamics の時系列制御**がボトルネックとして共有されている。

---

### 3.5 実務ツール：velocity refinement 専用

**@otaseishi（2026-05-04）**  
Narashi（MIDI velocity refinement）:

> Timing stays the same. **Dynamics get smoother.**

- 投稿: https://x.com/otaseishi/status/2051161631296790864  

**成功パターン:** 転写本体に強弱を無理に押し込めず、**後段の refinement 専用ツール**で滑らかにする。

---

### 3.6 商用/デモ：velocity 付き audio-to-MIDI の訴求

**@LEGAL_VST（2025-09-08）**  
Piano Audio to MIDI（Eldoraudio）:

> AI-powered audio-to-MIDI conversion **w/ velocity, timing & expression**

- 投稿: https://x.com/LEGAL_VST/status/1964982116401496452  

**示唆:** マーケティング上は velocity/expression が差別化ポイント。＝ユーザーは「ノートだけMIDI」では足りないと感じている。

---

### 3.7 古典：Magenta ピアノ転写の社会的成功

**Monica Dinculescu @notwaldorf（2018-09-20）**  
magenta.js の piano audio→MIDI:

> 「SUPER awesome」＋デモ公開

- 投稿: https://x.com/notwaldorf/status/1042847899585900544  

**示唆:** ピッチ転写の成功体験は長いが、その後も **velocity/記号化は未解決のまま積み残し** という歴史構造。

---

### 3.8 記譜→MIDI 方向（逆方向）の成功訴求

**DeepMusic-OCR 系（2025-10）**  
楽譜OCRで notes / rhythms / **dynamics** を一括理解、MusicXML/MIDI へ。

- 投稿: https://x.com/Mathias_don001/status/1983957745989537932  

**注意:** これは **印刷譜→デジタル** であり、**音響採譜→記号** とは逆方向。ただし「dynamics をシンボルとして保持できる表現」への需要を示す。

---

## 4. 限界（投稿横断の構造的制約）

| # | 限界 | 根拠投稿・文脈 |
|---|---|---|
| 1 | **データ不足が AMT のボトルネック**（MT3以降も） | Kyutai: 170k録音/11k時間が改善の主因 https://x.com/kyutai_labs/status/2075540049337155964 |
| 2 | **velocity はモデルカード上も「後回し」** | MuScriptor 固定velocity／推定不可 |
| 3 | **0–127 の量子化 vs 演奏表情の連続性** | Schumaker の潰れ例 |
| 4 | **規格値と音色知覚のズレ** | mf=64 が p に聞こえる |
| 5 | **hairpin は離散記号より一段難しい** | marudebot が明示的に後回し |
| 6 | **記譜ソフト I/O の信頼性不足** | MuseScore velocity=1 |
| 7 | **相対的な「ミックス上の大きさ」≠ 楽譜強弱** | 圧縮・ルーム・マスタリングが velocity を汚す（現場実務の含意） |
| 8 | **楽器依存** | ピアノ/ギター/打楽器で別問題化 |
| 9 | **中国語圏の公開議論が薄い** | 扒谱の力度は語られるが「記号自動付与」の設計議論は少ない |

---

## 5. ベストプラクティス（投稿から抽出）

### BP-1. 強弱を「別ヘッド／別段」で推定する
onset / offset / velocity を分けてデコードする設計が研究側で有効報告（Zang et al.）。

### BP-2. 粗い転写 → score-informed refine → 記号化
C4DM / arXiv の流れ：  
**AMT → note-level velocity refinement（楽譜条件付き）→ symbolics**。

### BP-3. 固定閾値マッピングを信じない
`64=mf` 等の規格表は出発点に過ぎない。音源・ジャンル・楽器ごとに **相対正規化（曲内パーセンタイル、フレーズ内対比）** が必要（聴感報告から逆算）。

### BP-4. hairpin と段階記号を分離
まず p/mp/mf/f の **ステップ記号**、次に **局所勾配→hairpin**。実務者も hairpin を後回しにしている。

### BP-5. パイプラインの I/O を検証する
MuseScore 等で **全ノート velocity=1** のような intermediate 破壊を疑う。MIDI/MusicXML 往復テスト必須。

### BP-6. 人間編集を前提に UX を設計する
VGM 譜面化、Finale 要望、中国語の力度調整愚痴——いずれも **最終的に人が直す** 前提。自動結果は「下書き」。

### BP-7. 後段 refinement ツールを許容する
Narashi のような **タイミング固定・dynamics 平滑** は現実的な分割統治。

### BP-8. 目的別に成功定義を変える
- 耳コピのネタ取り → 固定 velocity でも可（yokohamiami）  
- 出版譜 → 記号の意味的正しさ  
- 再演奏 MIDI → 絶対 velocity の聴感  

---

## 6. 最新トレンド（2024–2026）

1. **大規模実データ AMT**  
   MuScriptor: 合成 1.5M MIDI 事前学習 → 実データ fine-tune → 人手検証 300 曲 RL  
   https://x.com/kyutai_labs/status/2075540047613276197  

2. **それでも velocity は未解決のまま「次のフロンティア」**  
   高精度多楽器転写でも固定 velocity／推定なしが実務で指摘。

3. **Score-informed velocity refinement の論文化**  
   arXiv:2508.07757、QMUL セミナー「…Transcription into Symbolics」。

4. **楽器特化 velocity（ギター等）**  
   arXiv:2606.24912（2026）。

5. **生成系での time-varying dynamics 制御**  
   Music ControlNet など、dynamics を「グローバル属性」ではなく **時系列制御信号** として扱う。

6. **双方向の dynamics データパス**  
   - 音→MIDI（AMT）  
   - 譜→MusicXML/MIDI（OCR）  
   出版品質の記号は後者の方が保持しやすい一方、前者は表現情報が落ちやすい。

7. **MIDI を「コード」に落とす後処理**  
   Decomposer（MIDI→Strudel）など、MuScriptor 後段で構造化する試み  
   https://x.com/haiyewon/status/2079240520942154062  
   ※強弱そのものよりパターン抽出寄りだが、**転写後パイプライン拡張**の潮流。

---

## 7. 失敗パターン分類（実装観点）

| 失敗型 | 症状 | 典型ソース |
|---|---|---|
| **F1 未推定** | 全ノート同一 velocity | MuScriptor 固定 velocity |
| **F2 絶対値崩壊** | 端が 0/127 に張り付く | コンピュータ dynamics 写像 |
| **F3 聴感ミスマッチ** | 規格 mf が p に聞こえる | サンプル音色依存 |
| **F4 記号過剰/不足** | 毎音 f/p、または無記号 | 閾値量子化の粗さ |
| **F5 hairpin 欠落** | クレッシェンドが階段状 | 勾配検出未実装 |
| **F6 I/O 破壊** | export で velocity=1 | 記譜ソフトバグ |
| **F7 混線** | ミックス音量を演奏強弱と誤認 | マスタリング済み音源 |
| **F8 手動前提の放棄失敗** | 「自動で譜面完成」期待 | 現場は dynamics 手付け |

---

## 8. 実装・プロダクト示唆（投稿総合）

採譜ソフトに「強弱推定＋記号化」を載せるなら、投稿群は次の設計を支持する。

1. **AMT 本体** … pitch/onset/instrument を優先（現状の勝ち筋）  
2. **Velocity head（分離）** … フレーム特徴＋ノート条件  
3. **Score-informed refine** … 拍節・声部・反復構造で滑らかに  
4. **相対正規化** … 曲内/フレーズ内パーセンタイル  
5. **記号量子化ポリシー**  
   - デフォルト: 少なめの段階記号（読みやすさ）  
   - 詳細モード: ノート velocity 保持＋選択的記号  
6. **Hairpin はオプション**（勾配が閾値超＆持続）  
7. **必ず手動編集 UI**（velocity レーン + 記号ドラッグ）  
8. **往復テスト**（MIDI↔MusicXML↔再生）で F6 を潰す  

---

## 9. 調査上の制約・バイアス

- X 検索は同音異義（RNA velocity、ビジネス「力度」、スポーツ PP 等）ノイズが多い。  
- **英語の研究・開発投稿は比較的拾える**が、**中国語の「自动扒谱→强弱记号」専門スレは希少**。力度調整の実務愚痴が中心。  
- 日本語実務投稿（MuseScore バグ、MusicXML 逆算、MuScriptor 試用）は英語圏の欠落を補う高信号だったため補助的に採用。  
- 論文本体の数値評価は X 投稿には載らないことが多く、**ここは「現場・開発者の語り」中心**。

---

## 10. 主要出典リスト（クリック用）

### 失敗・限界
| 投稿者 | 内容 | URL |
|---|---|---|
| @ntamotsu_ | MuScriptor は良いが velocity 推定不可 | https://x.com/ntamotsu_/status/2075767005538562077 |
| @yokohamiami | 固定 velocity・テンポ非復元 | https://x.com/yokohamiami/status/2076181368980271378 |
| @sha_w_ | mf=64 が聴感 p | https://x.com/sha_w_/status/1652579701419024384 |
| @SchumakerA | dynamics→velocity の潰れ | https://x.com/SchumakerA/status/1623862296937213953 |
| @knoike | MuseScore velocity=1 | https://x.com/knoike/status/1817896544294896074 |
| @marudebot | dynamics↔velocity 逆算地獄 | https://x.com/marudebot/status/1828795809200304211 |
| @ViolinSpeedruns | dynamics は手動追加 | https://x.com/ViolinSpeedruns/status/1981251527533629729 |
| @edamame_6240 | 力度調整 > 扒谱 | https://x.com/edamame_6240/status/2062075681341890989 |
| @Dollynx5 | 音量平衡の難しさ | https://x.com/Dollynx5/status/1948800681437266049 |
| @incipitsify | 記譜と現実音の乖離 | https://x.com/incipitsify/status/1490346471773949958 |

### 成功・研究・トレンド
| 投稿者 | 内容 | URL |
|---|---|---|
| @yongyi_zang | velocity 分離デコード | https://x.com/yongyi_zang/status/1870479053100400988 |
| @ArxivSound | Score-informed velocity refine | https://x.com/ArxivSound/status/2028701785666506831 |
| @ArxivSound | Guitar velocity prediction | https://x.com/ArxivSound/status/2070681391252357149 |
| @c4dm | Velocity→Symbolics セミナー | https://x.com/c4dm/status/1818186996021670225 |
| @kyutai_labs | MuScriptor 大規模データ | https://x.com/kyutai_labs/status/2075540047613276197 |
| @otaseishi | velocity refinement ツール | https://x.com/otaseishi/status/2051161631296790864 |
| @LEGAL_VST | velocity 付き audio2midi 訴求 | https://x.com/LEGAL_VST/status/1964982116401496452 |
| @notwaldorf | Magenta ピアノ転写 | https://x.com/notwaldorf/status/1042847899585900544 |
| @_akhaliq | dynamics 時系列制御 | https://x.com/_akhaliq/status/1724277147177541920 |

### 関連 arXiv（投稿から辿れる一次文献）
- https://arxiv.org/abs/2508.07757 — Score-Informed Transformer for Refining MIDI Velocity  
- https://arxiv.org/abs/2606.24912 — Velocity Prediction in Automatic Guitar Transcription  
- https://arxiv.org/abs/2607.08168 — MuScriptor（Kyutai 告知）

---

## 11. 一言で言うと

> **ピッチ採譜は「使える下書き」まで来たが、強弱はまだ「推定できない／固定／手動」がデフォルト。**  
> 記号化は単なる閾値処理ではなく、**聴感・音源・記譜慣習・I/O バグ**が絡む多段の翻訳問題であり、X上の実務者は失敗と手作業を繰り返し語っている。

---

### 補足
- 本調査は **X投稿ベース**。論文のベンチマーク数値や製品UIの網羅レビューは範囲外。  
- 中国語は「力度/扒谱」キーワード中心。専門開発者クラスタは英語・日英混在の MIR/記譜界隈に偏った。  
- Slack `#倉田_ログ` への作業ログ投稿は、本セッションに Slack MCP / API が接続されていないため未実施。接続可能になれば同内容の要約を投稿可能。
