# ドラム採譜機能のX調査レポート  
**対象機能**: キット別自動採譜 / 同時打音 / GM Drum Map  
**収集期間感**: 主に 2024–2026（投稿日ベース）  
**言語**: 英語中心＋中国語・日本語実務者を補完  
**方針**: 実投稿ベース・出典リンクつき。失敗例を厚く。

---

## 0. 調査サマリー（実務者視点）

| 軸 | 現場で見えたこと |
|---|---|
| **成功** | フルミックス→マルチ楽器MIDI（MuScriptor/Mirelo）、ステム分離→Audio→MIDI、EZDrummerへの載せ替えで「感触」が戻る |
| **失敗（最多）** | 精度の曲依存、タイミングズレ、velocity/ghost欠落、キットMap不一致、同時打音表現の制約、合成データ↔実録音ギャップ |
| **限界** | ドラムは「音符」より「イベント分類問題」。GMは共通語だが製品Mapは分裂 |
| **BP** | 先にステム分離／GM出力＋製品別リマップ／人手補正前提／ドメイン適応用の現実的合成データ |
| **トレンド** | full-mix多楽器AMT、diffusion精密化、drum-stem特化、open-weight、キットMap製品要件化 |

**調査上の注意**: X上で「ドラム自動採譜」そのものを専門的に議論する中国語投稿は少なめ。中国語は「人力扒鼓」「譜面サービス品質」「MIDI打ち込み」寄りの言及が中心。英語は**研究bot／開発者／プロデューサー**の層が厚い。

---

## 1. 成功例（Success）

### 1.1 フルミックスから楽器別MIDI（含むドラム）

**@MireloAI（開発）** — 2026-07-10  
フル録音から voice / **drums** / bass / keys 等を別MIDIとして返すAudio-to-MIDIを発表。ステム不要を訴求。  
https://x.com/MireloAI/status/2075536492177354771

**@pagarciadom（@MireloAI）** — 2026-07-15  
既存Audio-to-MIDIの多くは「1音源ずつ」で、自分たちは**フルミックス一括**（ギター・ボーカル・ピアノ・**ドラム**含む）だと主張。  
https://x.com/pagarciadom/status/2077344364079042963

**@SpacklMarketing（実務・スタジオ）** — 同スレ返信  
故人の複雑フィンガーピッキング伴奏をデモで起こし、Ample Guitarで検証。「本物のギタリスト代替ではないが道は開いた」。ギター事例だが**AMTの実案件成功**として参照価値あり。  
https://x.com/SpacklMarketing/status/2075606950641840340

**@haiyewon（CMU Music AI研究者）** — 2026-07-20  
MuScriptor（audio→MIDI）→Decomposer（MIDI→Strudel）で *What a Fool Believes* を再構築。「**days of hand-writing** until it grooved」＝自動は入口、人間が仕上げ。  
https://x.com/haiyewon/status/2079240520942154062

### 1.2 ステム分離 + DAW変換パイプライン

**@hotgood（実務）** — 2026-02-28  
Acon Digital Remix:Drums + Logic で **2mixドラム → MIDI** の手順をまとめた（Remix:Drumsは安価なドラム分離）。  
https://x.com/hotgood/status/2027580458436071620

**@takoyakiguitar（ギタリスト／プロデューサー）** — 2026-06-09  
Suno曲のドラムを **RipX** と **Logic Drum Replacement** で比較:

- RipX: キック／スネア／**シンバル類まで含む全体**を取ろうとする  
- Logic: **キック＆スネア特化**の印象  

→ ツールが「キット全体」か「置換用K/S」かで役割が分かれる成功理解。  
https://x.com/takoyakiguitar/status/2064260192293077018

**@sanChri0720（DTM実務）** — 2026-07-19  
各楽器ステム→FSP8でAudio→MIDI修正。「**ドラムのMIDI変換は以前よりかなり精度が向上**」。ただし他パートはまだ修正が重い。  
https://x.com/sanChri0720/status/2078733794627256384

### 1.3 キット音源へ載せて初めて成功するパターン

**@nir_un（教育・制作）** — 2026-03-20  
生徒用にドラム再現。ライブのタイミングがピアノロールで再現できず、**drum stem → MIDI** してもまだ違う → **EZDrummerに投げて初めてスウィングとvelocityがハマった**。  
https://x.com/nir_un/status/2034904340398272771

→ 「採譜精度」と「キット再生の感じ」は別問題、という実務の成功条件。

### 1.4 研究側の前進（X上で流通する論文）

| 論文（X投稿） | 示唆 | 出典 |
|---|---|---|
| **Noise-to-Notes**（DiffusionでADT生成・精緻化） | 検出→拡散精緻化 | [@toyama_keisuke](https://x.com/toyama_keisuke/status/2046997033337401536) / arXiv:2509.21739 |
| **Enhanced ADT via Drum Stem Source Separation** | 先にドラムステム分離してから採譜 | [@ArxivSound](https://x.com/ArxivSound/status/1972886901217804516) / arXiv:2509.24853 |
| **Towards Realistic Synthetic Data for ADT** | 合成データの現実性 | [@ArxivSound](https://x.com/ArxivSound/status/2011667891968741473) / arXiv:2601.09520 |
| **synthetic-to-real transfer gap in ADT** | 合成→実録音の転移ギャップ | [@ArxivSound](https://x.com/ArxivSound/status/1818135514140033249) |
| **Keep the beat going: ADT with momentum** | オンセット追跡の安定化 | [@ArxivSound](https://x.com/ArxivSound/status/2012036504160518355) / arXiv:2507.12596 |

---

## 2. 失敗例（Failure）— 厚めに

### 2.1 精度が曲難易度で崩壊する

**@CabbageLettuce1** — 2026-07-18（Mirelo試用）

> - 自分でも人力でなんとかなる曲: 精度 **約50%**  
> - 自分だけでは絶望的な曲: 精度 **約10%**  
> → 専用モデルより Demucs + librosa を握らせた方が良さそう  

https://x.com/CabbageLettuce1/status/2078348054697246827

**失敗の型**: 「デモでは映えるが、難しい実曲で信頼できない」→ 自動採譜は**下書き**止まり。

### 2.2 タイミングが「同じなのにズレて聞こえる」

**@unigame619232（UKG/2-stepプロデューサー）** — 2026-06-25  

SunoステムのDrumをAudio→MIDI→909 Kick再割当:

> 同じタイミングなのに、ずれて聴こえる。  
> 何もしない方がよかったのかな。

https://x.com/unigame619232/status/2070153762745012523

**失敗の型**: 量子化／オンセット誤差／サンプルアタック差で**グルーヴ破壊**。キック置換の典型失敗。

### 2.3 モデル仕様上の「表現できない失敗」（同時打音・velocity）

**Sonic Field による MuScriptor 分析**（投稿 [@sonic_field](https://x.com/sonic_field/status/2078880397920731383)、記事 2026-07-18）:

- **velocity / dynamics を保持しない**  
- **同一 pitch × 同一 instrument の同時2音を表現できない**  
- **ドラムは onset-only イベント扱い**  
- 楽器は **36グループ**の分類体系に押し込まれる  
- pop / 西欧クラシック寄りバイアス。レア楽器・非主流ジャンルは劣化しやすい  
- 実録音ファインチューニングで指標が約20pt改善（合成pretrain単独より）＝**合成だけでは足りない**

記事: https://sonicfield.org/muscriptor-audio-to-midi  

**失敗の型**:

| 現場現象 | 仕様との対応 |
|---|---|
| ゴーストノートが消える／平坦 | velocity未出力 |
| キック+スネア同時は出るが「同音同楽器の重なり」が潰れる | 同時2音制約 |
| シンバル長音・ロールがイベント列に崩れる | onset-only |
| ジャンル偏りで誤分類 | 訓練分布バイアス |

### 2.4 GMは共通語だが「キットMapは地獄」（製品間失敗）

**@ismyhc（開発者）** — MuScriptorスレで連続質問:

1. EZDrummer / Addictive / Logic 等への**正しいMap出力**はあるか  
   https://x.com/ismyhc/status/2075597926064128316  
2. 標準はGMだが、**ezdrummer, Logic Pro, etc may use variations**  
   https://x.com/ismyhc/status/2075625746203045992  
3. 主要VST向けに**エクスポートMapがあれば killer feature**  
   https://x.com/ismyhc/status/2075626108385407345  
4. 以前から「drum stem → MIDI with mappings to ezdrummer, ggd」が欲しい  
   https://x.com/ismyhc/status/2013789955835806198

**@MireloAI の公式回答** — 2026-07-10  

> The drums come as a **consolidated midi stem**, so there is still **some manual mapping** to be done at this stage.  
> Is there a standard, universal mapping for drum plugins?

https://x.com/MireloAI/status/2075624374338465847

**失敗の型**: 採譜が正しくても **Kickがタムに鳴る／ハットがクラッシュになる** 等のMap事故。  
GM (Kick36, Snare38, CHH42…) は共通語だが、**製品Mapは分裂**しているのが現状の合意。

### 2.5 「1対1のドラム採譜」を意図的に避ける製品

**@tracktuneraudio** — 2026-07-14  

> No loops. No audio generation. **No one-to-one drum transcription.**  
> Just editable **GM drum MIDI** shaped around the flow of your track.

https://x.com/tracktuneraudio/status/2077007691587649992

**示唆**: 市場側も「正確な1:1採譜」の難易度・期待値ギャップを認識し、**編曲寄りGM生成**に退避する動きがある＝採譜製品の失敗リスクの裏返し。

### 2.6 ゴーストノート・マイクブリード・ロボット感（置換／検出系）

**@AnsataProAudio（Waves InTrigger紹介）** — 2025-11-20  

> Most tools struggle with **ghost notes**, **mic bleed**, or just sound **robotic**.

https://x.com/AnsataProAudio/status/1991484672170479769

**失敗の型**（ライブ多重マイク前提）:

- ゴーストが落ちる／逆にブリードをヒットと誤検出  
- velocityが階段状で人間味がない  
- スネア横マイクとハットの誤認

### 2.7 合成データ ↔ 実録音ギャップ（研究が「失敗の主因」と名指し）

X上で繰り返し流れる論文群:

- *Analyzing and reducing the **synthetic-to-real transfer gap*** in ADT  
  https://x.com/ArxivSound/status/1818135514140033249  
- *Towards **Realistic Synthetic Data** for Automatic Drum Transcription*  
  https://x.com/ArxivSound/status/2011667891968741473  

**失敗の型**: ベンチではFが高いのに、実曲（ルーム残響・チューニング差・電子キット・Lo-fi）で崩壊。

### 2.8 AIドラム／MIDIが「2004年のMIDI」に聞こえる

**@jonesmaestro（映画作曲家）** — 2026-07-20  

> Your AI drums sound like a MIDI file from 2004.  
> Frequency Intelligence… 60Hz kick, 400Hz snare body…

https://x.com/jonesmaestro/status/2079221214669640071

**@abe / @stubbornsticks** — 2026-07-19  

リズムはMIDIで正確に組めるのに、**ドラムの「音」選びが常にひどい**。  
https://x.com/stubbornsticks/status/2078747062548505030

→ 採譜後の**音色割当失敗**も「自動採譜パイプライン全体の失敗」として頻出。

### 2.9 人力・外注譜面の失敗（中国語／周辺言語）

**@LinningInMono** — 2025-06-20（中文）  

> 价值一千二百元人民币的乐队总谱制作：所有声部都用MIDI转写，**鼓谱打出升降号**，**铺面错误还很多**。

（約1200元の総譜＝全パートMIDI転記、**ドラム譜に臨時記号**、レイアウト誤り多数）  
https://x.com/LinningInMono/status/1936114696488468699

**失敗の型**: 自動でも外注でも、**ドラム譜記譜規約（五線での打楽器記譜 vs 音名記号）**を誤解すると即不合格。

**@NG____02** — 2025-12-17（中文・学習ログ）  

kz系のドラムを人力で解析中:

> 扒谱工程…并不完美，甚至可以说没法听……kick很明显是合成器做的而军鼓听着像在敲锅。

https://x.com/NG____02/status/2001328287000477886

**失敗の型**: 電子／加工系キットは「生ドラムMap」前提だと**音色識別が破綻**。

**@Dollynx5** — 2025-07-25  

既存譜がある曲でもバランス調整が難しく、「自分で扒谱なんて想像もしたくない」。  
https://x.com/Dollynx5/status/1948800681437266049

### 2.10 その他の失敗パターン（周辺だが実務で効く）

| 投稿 | 内容 | リンク |
|---|---|---|
| @Blarg08125613 | AI音楽は局所は正しいが**大構造が崩壊**（記譜・生成共通） | https://x.com/Blarg08125613/status/1896355878338748716 |
| @8co28 | SunoのMIDI出力は改善したが**まだ限界を感じる** | https://x.com/8co28/status/2058009089108758771 |
| @HighReso | Logic Drum Kit Designer → AD2 は**MIDIマップ変更だけ**で済む（＝逆にMapを誤ると全破壊） | https://x.com/HighReso/status/2037017495442452777 |
| @cqwww | Hydrogenクラッシュ→**pad notesをGM drum channelにリマップ**してFluidSynth直結へ逃げ | https://x.com/cqwww/status/2039210220673516007 |

---

## 3. 限界（Limitations）— 投稿から抽出した構造

### 3.1 同時打音（polyphony / multi-voice）

1. **キット内同時打**（kick+snare+hh）は「別ノート番号」なら扱えることが多い  
2. **同一ノートの重なり・ロール・フラム**はトークン設計で落ちやすい（MuScriptor: same pitch+instrument 同時不可）  
3. **オープン／クローズドHHの状態遷移**や**フットスプラッシュ**は分類粒度不足で崩れやすい  
4. フルミックスでは他楽器マスキングにより同時打の**一部のみ検出**

### 3.2 キット別自動採譜

- 生キット／電子キット／808系／パーカッション拡張で**音響クラスが非定常**  
- 学習データが「標準ロックキット＋GMラベル」寄りだと、**中国語ユーザーが触れる電子系・加工系で誤認**（@NG____02）  
- 「キット別」は**音響分類＋記譜Map＋再生Map**の3層問題。多くは第1層だけ自動化

### 3.3 GM Drum Map

```
実務で共有されているGM例（@ismyhc）:
Kick 36 / Snare 38 / Sidestick 37
CHH 42 / Pedal HH 44 / OHH 46
Toms 41–50 / Crash 49,57 / Ride 51 / Bell 53
```

**限界**:

- GMは**交換フォーマット**であって、**製品再生Mapではない**  
- 主要開発者製品ですら「universal mappingはあるか？」と逆質問（@MireloAI）  
- ユーザー要求は **EZDrummer / GGD / Addictive / Logic** への**直接出力**（@ismyhc）

### 3.4 評価指標と体感の乖離

研究は onset F-measure 等で議論されるが、実務失敗は:

- **感じのズレ**（@unigame619232）  
- **velocityの死**（Sonic Field）  
- **Map後の誤楽器鳴り**  
- **譜面として読めない**（臨時記号・レイアウト）

→ 「数値上OK／現場NG」が構造的限界。

---

## 4. ベストプラクティス（Best Practices）

投稿横断で収束した実務レシピ:

### 4.1 パイプラインを分割する

```
[2mix]
  → ① ドラムステム分離（Demucs / Remix:Drums / RipX 等）
  → ② ADT / Audio→MIDI（キット分類）
  → ③ GM正規化
  → ④ 製品Map（EZD / AD / Logic / GGD…）
  → ⑤ 人手で ghost / タイミング / 省略
  → ⑥ キット音源で試聴フィードバック
```

根拠:

- Enhanced ADT via **Drum Stem Source Separation**（研究）  
- Demucs_6s を drum separator として使う開発者（@entrepeneur4lyf）  
- EZDrummer載せ替えで初めて成功（@nir_un）  
- Gradioデモでも **Demucs Split option** を用意（@fffiloni）  
  https://x.com/fffiloni/status/2078128083995963779

### 4.2 「完全自動」を捨て、編集可能MIDIをゴールにする

- @haiyewon: 自動→**数日手書きで groove まで**  
- @sanChri0720: 変換後に**直す**前提  
- @tracktuneraudio: 1:1採譜を諦め**editable GM**へ

### 4.3 GMを中間言語にし、製品Mapはテーブル化する

- @ismyhc: 主要VSTの mapping tables はWebにある  
- @HighReso: Logic→AD2 はMap変更のみ  
- 製品側は **「GM + プリセットMapエクスポート」** が差別化点

### 4.4 ツール役割を分ける

| 目的 | 向きやすいツール感（投稿ベース） |
|---|---|
| 全体ドラムイベント | RipX 系（K/S/Cymbal含む） |
| キック／スネア置換 | Logic Drum Replacement 特化 |
| 2mixのK/S/HH/Cym/Tom調整 | Remix:Drums |
| フルミックス多楽器 | MuScriptor 系（ただしMap/velocity限界） |

### 4.5 データ／訓練側（研究BP）

- 合成pretrain → **実録音fine-tune**（MuScriptor: +約20pt）  
- **Realistic synthetic** で domain gap を詰める  
- Diffusion refinement（Noise-to-Notes）で曖昧オンセットを再生成

### 4.6 ゴースト・ブリード対策（置換ワークフロー）

- 単純threshold検出はゴースト／ブリードで破綻（InTrigger周りの問題認識）  
- マルチマイクなら**ブリードモデル or ステム化後に検出**  
- velocityは後段で人間化／キットのラウンドロビンに任せる

---

## 5. 最新トレンド（2025–2026, X上）

1. **Full-mix multi-instrument AMT**  
   MuScriptor / Mirelo × Kyutai。ドラムは「統合MIDIステム」として出力され、**手動Map前提**が明示された。

2. **Open-weight + ローカルWebDAW統合**  
   @acidsound が MuScriptor Medium をVibeSeqに統合（audio→editable MIDI tracks）。  
   https://x.com/acidsound/status/2077457830886662434

3. **Stem-first ADT**  
   論文・実務双方で「先にドラム分離」が定石化。Acon Remix:Drums のような**ドラム特化分離**も流通。

4. **Diffusion-based ADT refinement**  
   Noise-to-Notes（Sony系研究者 @toyama_keisuke が共有）。

5. **Domain gap が研究の主戦場**  
   synthetic-to-real / realistic synthetic data が連続投稿。

6. **キットMapがプロダクト要件として前面化**  
   採譜精度の次の争点が **EZDrummer/GGD向けMap出力**（開発者ユーザーのkiller feature要望）。

7. **「採譜しない」製品の出現**  
   arrangement-aware GM生成（1:1 transcription回避）。

8. **生成AI曲のMIDI化需要**  
   Suno等 → RipX / Logic でドラムMIDI化実験が日常化（@takoyakiguitar 等）。

---

## 6. 機能設計への示唆（キット別・同時打音・GM）

| 機能要件 | X上の根拠 | 設計ヒント |
|---|---|---|
| **キット別自動採譜** | 電子/加工キット誤認、訓練分布バイアス | キットプロファイル（Rock / EDM / 808 / Perc）をユーザー指定 or 自動推定。未対応キットは「未分類」で落とす |
| **同時打音** | onset-only、同音同時不可 | 多ラベル onset（K∧S∧HH）＋フラム/ロール専用イベント。同一ノート重なりは時間分解能で表現 |
| **GM Drum Map** | 製品Map分裂、手動Map必須の公式回答 | **出力モード: GM / EZD / AD2 / Logic / GGD**。内部はGM正規化、最後にLUT |
| **失敗を減らすUI** | 50%/10%精度、タイミングズレ体感 | 信頼度ヒートマップ、K/S/HH別F表示、難曲警告、「ステム分離して再実行」ボタン |
| **velocity/ghost** | 欠落が批判の中心 | 少なくとも相対velocity；ghost候補を薄表示して人手確認 |

---

## 7. 収集の偏り・限界（本調査）

- **英語**: 研究bot（@ArxivSound）と製品ローンチ（Mirelo）が厚い。失敗の一次情報は**試用ツイ・開発者Q**に偏る。  
- **中国語**: 「自动鼓谱转录」専門スレは希少。**扒谱・外注譜・MIDI制作**の失敗が中心。  
- **日本語**: 実務比較（RipX vs Logic）が具体的で有用。補完として採用。  
- Reddit/論文本体の深掘りは本調査範囲外（X投稿＋Sonic Field記事まで）。

---

## 8. 主要出典一覧（クリック用）

### 開発・製品
- https://x.com/MireloAI/status/2075536492177354771  
- https://x.com/MireloAI/status/2075624374338465847  
- https://x.com/pagarciadom/status/2077344364079042963  
- https://x.com/tracktuneraudio/status/2077007691587649992  
- https://x.com/fffiloni/status/2078128083995963779  

### 実務失敗・試用
- https://x.com/CabbageLettuce1/status/2078348054697246827  
- https://x.com/unigame619232/status/2070153762745012523  
- https://x.com/nir_un/status/2034904340398272771  
- https://x.com/takoyakiguitar/status/2064260192293077018  
- https://x.com/sanChri0720/status/2078733794627256384  
- https://x.com/LinningInMono/status/1936114696488468699  
- https://x.com/NG____02/status/2001328287000477886  
- https://x.com/AnsataProAudio/status/1991484672170479769  

### GM / キットMap
- https://x.com/ismyhc/status/2075597926064128316  
- https://x.com/ismyhc/status/2075625746203045992  
- https://x.com/ismyhc/status/2075626108385407345  
- https://x.com/HighReso/status/2037017495442452777  

### 研究（X流通）
- https://x.com/toyama_keisuke/status/2046997033337401536  
- https://x.com/ArxivSound/status/1972886901217804516  
- https://x.com/ArxivSound/status/2011667891968741473  
- https://x.com/ArxivSound/status/1818135514140033249  
- https://x.com/ArxivSound/status/2012036504160518355  

### 技術解説（Web）
- https://sonicfield.org/muscriptor-audio-to-midi  

---

## 9. 一言でいうと

> **ドラム自動採譜は「当たる時は下書きとして強い」が、失敗は (1) 難曲での分類崩壊 (2) タイミング／velocityの死 (3) GM≠製品Map (4) 同時打音・ゴーストの表現限界 (5) 合成↔実録音ギャップ に集中する。**  
> 勝っている現場は **ステム分離 → ADT → GM → キット別Map → 人手** の分業で、完全自動を期待していない。

---

必要なら次の深掘りもできます:

1. **失敗例だけ**を表形式で30件規模に再収集（製品名軸: Logic / RipX / MuScriptor / Suno）  
2. **GM↔EZDrummer/GGD/AD2** のMap差分を実装向けに整理  
3. 上記を採譜ソフトの**機能仕様書ドラフト**に落とす
