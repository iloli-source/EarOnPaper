# F-086 調査レポート（codex担当: 論文＋WEB・失敗例重視）

- **対象機能**: 採譜MIDIの調内制約クレンジング（推定スケールへのスナップ・外れ音の一括補正候補提示）
- **分担**: codex担当（論文＋WEB調査、失敗例を最大限収集）
- **調査方法**: OpenAI Codex（read-onlyセッション）による論文・実装記事調査。主要URLは WebFetch/WebSearch で実在性・記述内容をスポット検証済み。
- **言語方針**: 英語・中国語中心、実在ソースのみ・URL併記
- **作成日**: 2026-07-21

> 検証メモ: Ableton Live 12マニュアル（Fit to Scale=近接スケール音へ吸着・等距離なら低音）、music21のKrumhansl-Schmuckler「dominant keyをtonicと誤認しやすい」記述、Musicae Scientiae 2024「A regularization algorithm for local key detection」、Antares AutoTune 2026のFlex Tune/Humanize（表情ピッチ保持）を実地確認済み。Antares FAQは403で機械取得不可だがページは実在し機能記述も一致。

---

## 要旨

「推定スケールへ外れ音をスナップする」機能は、採譜MIDIの明白な誤検出を直す用途では有効だが、自動一括補正にすると音楽的に正しい外れ音を壊しやすい。特に危険なのは、転調、局所調、セカンダリードミナント、借用和音、クロマチック経過音、ブルーノート、装飾音、ピッチベンド由来の表情音である。実装方針は「自動適用」ではなく、「根拠付き候補提示 + 低信頼箇所のレビュー + 例外保護」を基本にすべき。

---

## (1) Scale-snapping methods

### 代表的な処理モデル

1. **調・スケール推定**
   - MIDIの各音をピッチクラスに集計し、24調のkey profileと照合する。
   - 古典的な基盤は Krumhansl-Schmuckler/Kessler 型。Krumhansl の章 “A key-finding algorithm based on tonal hierarchies” は、音列のピッチクラス分布を調性階層テンプレートと照合する方法を説明している。
     URL: https://academic.oup.com/book/40395/chapter-abstract/347203084
   - Temperley はK-S法を再検討し、短いセグメント、presence/absence入力、転調ペナルティを導入した。
     URL: https://online.ucpress.edu/mp/article-abstract/17/1/65/62051/What-s-Key-for-Key-The-Krumhansl-Schmuckler-Key

2. **許容ピッチ集合の生成**
   - 例: C majorなら `{C,D,E,F,G,A,B}`、A natural minorなら `{A,B,C,D,E,F,G}`。
   - 実務では natural/harmonic/melodic minor、mode、pentatonic、blues scale、ユーザー定義スケールを分ける必要がある。

3. **外れ音の候補化**
   - 単純法: 最も近いスケール音へ移動。
   - Ableton Live 12 の “Fit to Scale” は、選択音をクリップのスケール内の最も近い音へ調整し、等距離なら低い音へ寄せる。
     URL: https://www.ableton.com/en/live-manual/12/editing-midi/
   - Ableton FAQ も、スケール外の音は最も近いスケール音に動き、等距離なら低い音が使われると説明している。
     URL: https://help.ableton.com/hc/en-us/articles/11425083250972-Keys-and-Scales-in-Live-12-FAQ
   - Cubase もScale Assistantで、スケールに合わないMIDIピッチを選択スケール内の最も近い音へquantizeする。
     URL: https://www.steinberg.help/r/cubase-pro/15.0/en/cubase_nuendo/topics/midi_editors/midi_editors_note_pitches_to_scales_quantizing_t.html?contentId=UaQ8Br8gYUDwuHtzQF79Wg
   - Logic ProはPiano Roll Editorで、MIDIノートを特定のscale/keyへpitch quantizeできる。
     URL: https://support.apple.com/guide/logicpro/quantize-the-pitch-of-notes-lgcpf4f544d2/mac

4. **音声系ピッチ補正からの示唆**
   - Melodyne はNo Snap、Chromatic Snap、Key Snap、Chord Snapを選べる。
     URL: https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_PitchGridScale_2?env=dawsWithAra
   - MelodyneのCorrect Pitch Macroは、近い半音、現在スケール、または現在コードの構成音へ寄せられるが、選択範囲と強度をユーザーが決める設計である。
     URL: https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_MacroPitch?env=dawsWithAra
   - AutoTune 2026 はFlex Tuneで表情的なピッチ変動を残し、Humanizeで持続音の不自然な固定を避ける設計を採っている。
     URL: https://help.antarestech.com/hc/en-us/articles/42855736822932-AutoTune-2026-FAQ

### 実装上の基本形

- 各ノートに `in_scale`, `distance_to_scale`, `local_key_confidence`, `harmonic_context`, `duration`, `metrical_strength`, `neighbor_motion` を持たせる。
- 補正候補は最低でも `down`, `up`, `nearest`, `keep` を出す。
- 破壊的な「全音符を即スナップ」ではなく、「外れ音リスト」「小節単位プレビュー」「一括適用前の差分」を出す。

---

## (2) Modulation / borrowed chords / chromatic passing tones が誤補正される失敗ケース

### クロマチック経過音

- 例: C majorで `C-C#-D`。C#はDへの半音上行アプローチとして正しいが、C majorスケール外なので `C` または `D` に吸着される。
- Ableton型の「等距離なら低い音」規則では、C#がCへ落ちる可能性があり、上行の推進力が消える。
- 採譜MIDIでは短い経過音ほど誤検出にも見えるため、durationだけで削ると装飾・経過音を壊す。

### セカンダリードミナント

- 例: C major中の `D7 -> G`。F#はV/Vの第3音で、Gへの導音として重要。
- 単純スケールスナップはF#をFまたはGへ寄せ、D7の機能をDm7やDsus的な曖昧な響きに変える。
- 局所的に「次の強拍・次の和音へ半音解決するか」を見る必要がある。

### 借用和音・モーダルインターチェンジ

- 例: C major中の `Fm`, `Ab`, `Bb`, `Eb`。これらはC minorやMixolydian等からの借用として普通に現れる。
- `Ab -> G`、`Bb -> A/B` のような補正は、ポップスや映画音楽でよく使われる色彩を消す。
- Hookpadは非ダイアトニック音を明示入力でき、キー変更も小節単位で扱える。これは「スケール外 = 間違い」とみなさないUI例として重要。
  URL: https://www.hooktheory.com/support/hookpad

### ブルーノート、ベンド、歌唱表現

- Sweetwaterのピッチ補正解説は、ジャズのブルーノート、弦楽器の可変ピッチ、ギターのベンド、歌のスライドを「スケール周波数から外れているが音楽的に意味のあるピッチ」として扱っている。
  URL: https://www.sweetwater.com/insync/the-right-way-to-do-pitch-correction/
- MIDI化後にピッチベンドが失われ、音符だけを見ると「外れ音」に見える場合がある。
- 採譜MIDIでは、装飾的な短音、低velocity、隣接音への半音接近、同一声部の滑走は自動補正から除外するのが安全。

---

## (3) Key estimation が間違った場合のcascade breakdown

### 典型的な崩壊

- 実際はC major、推定がD majorの場合:
  - C natural と F natural が外れ音扱いされる。
  - CはBまたはC#、FはEまたはF#へ補正候補化される。
  - 旋律の主音、IV、導音関係がまとめて壊れる。
- 実際はA minor、推定がC majorの場合:
  - 自然短音階だけなら音集合は同じなので検出上は気づきにくい。
  - しかしG#などharmonic minorの導音、E7のG#、旋律短音階のF#が「外れ音」扱いされる。
  - 結果として短調のカデンツが弱くなる。

### key estimation自体の既知の弱点

- music21 の KrumhanslSchmuckler 実装説明は、Krumhansl-Schmuckler/Kessler重みにはdominant keyをtonicとして識別しやすい傾向があると記している。
  URL: https://music21.org/music21docs/moduleReference/moduleAnalysisDiscrete.html
- 2024年のlocal key detection研究（"A regularization algorithm for local key detection", Musicae Scientiae）は、global key detectionが転調部分を誤表現しやすいこと、短い局所セグメントでは逆に不要な転調を過検出しやすいことを指摘している。
  URL: https://journals.sagepub.com/doi/10.1177/10298649241245075
- 同研究は、K-S法で反復音が過重視される例として、C major triad後にEが反復されるとE minor寄りに誤判定され得ると述べている。これは採譜MIDIでも、トリル、連打、オスティナートに弱い。
- MIREXの評価では、誤推定を「完全五度」「関係長短調」「同主長短調」「その他」に分けている。2026年タスク定義でも、relative major/minorは部分点扱いで、そもそも頻出する誤りとしてモデル化されている。
  URL: https://music-ir.org/mirex/wiki/2026%3AAudio_Key_Detection
  mir_eval実装: https://mir-eval.readthedocs.io/latest/api/key.html
- MIREX 2018結果では、GiantStepsKeyでトップ級のFK1でもCorrectは67.88%、他システムではOtherが20-50%台に達する。調推定を下流の自動補正の唯一根拠にするには危険。
  URL: https://music-ir.org/mirex/wiki/2018%3AAudio_Key_Detection_Results
- 自動ピアノ採譜評価研究では、out-of-key false positiveは知覚的に目立つと仮定している一方、この定義は転調があると限界があると述べている。これは「外れ音検出」は有用だが、転調・局所調を無視すると誤警告になることを示す。
  URL: https://transactions.ismir.net/articles/10.5334/tismir.57

### HMM・深層学習の位置づけ

- Noland & SandlerのHMM key estimationは24調を状態、コード遷移を観測として扱い、Beatles 110曲で91%のglobal key分類を報告している。ただし初期モデルは手作業コード記号ベースで、複雑和音を制限している。
  URL: https://www.researchgate.net/publication/220723459_Key_Estimation_Using_a_Hidden_Markov_Model
- QM Vamp Key Detectorはブロックごとのchromagramとkey profileの相関から継続的にkeyを推定し、window lengthが短いほど短い調変化を拾いやすい。
  URL: https://vamp-plugins.org/plugin-doc/qm-vamp-plugins.html
- madmomはCNNKeyRecognitionProcessorを提供し、Korzeniowski & Widmer 2018のCNNベースglobal key分類を参照している。
  URL: https://madmom.readthedocs.io/en/v0.16/modules/features/key.html
  論文URL: https://ir.webis.de/anthology/2018.ismir_conference-2018.35/
- EssentiaのKey/KeyExtractorはHPCPと複数のprofileTypeを使える。Krumhansl、Temperley、Gomez、Noland等を切り替えられる点は実装比較に有用。
  URL: https://essentia.upf.edu/reference/streaming_Key.html
  URL: https://essentia.upf.edu/reference/std_KeyExtractor.html
- GómezのHPCP系研究は、polyphonic audioのtonal descriptionとkey estimationを扱う基礎資料。
  URL: https://pubsonline.informs.org/doi/10.1287/ijoc.1040.0126
  HPCP実装説明: https://www.upf.edu/web/mtg/hpcp

---

## (4) Human-in-the-loop review flow のベストプラクティス

### 原則

- **自動補正ではなく候補提示**: 「この音は外れています」ではなく、「現在の推定では外れ音。ただし借用/経過/転調の可能性あり」と表示する。
- **信頼度を分ける**:
  - 高信頼: 長い孤立音、前後に音楽的解決がない、推定調の信頼度が高い。
  - 中信頼: 短い装飾音、弱拍、隣接半音進行。
  - 低信頼: 転調候補区間、コード外だが半音解決する音、ブルーノート、借用和音候補。
- **差分プレビュー必須**: 補正前後のMIDIノート、半音移動量、対象小節、推定根拠を表で見せる。
- **Keepを第一級操作にする**: `適用 / 保持 / 代替候補 / この小節は別キー` を同列に置く。
- **局所調を編集可能にする**: Hookpadのように小節単位のkey changeを持てるUIが望ましい。
  URL: https://www.hooktheory.com/support/hookpad
- **スナップ強度を持つ**: AutoTuneのFlex TuneやHumanize、Melodyneの補正強度のように、100%吸着だけでなく部分補正・表情保持を提供する。
- **元データを破壊しない**: FL Studioは安全のため、Piano Rollのノートを編集しない限り自動でスケールへスナップしない設計を説明している。
  URL: https://cluster.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll.htm

### UI案

- 小節ごとの上部レーン: `推定キー`, `信頼度`, `代替キー`, `転調境界候補`
- ノート上の色:
  - 青: 調内
  - 黄: 外れ音だが経過/装飾/借用候補
  - 赤: 誤採譜らしい外れ音
  - 紫: 転調候補区間のため保留
- 候補テーブル:
  - `bar:beat`
  - `note`
  - `current key`
  - `reason`
  - `candidate pitches`
  - `risk label`
  - `apply/keep`
- 一括操作:
  - `高信頼のみ適用`
  - `短音は除外`
  - `半音解決する音は除外`
  - `転調候補区間は除外`
  - `選択小節だけ適用`
- 監査ログ:
  - 「C#4 -> D4、理由: C major外・Dへ解決、ただし経過音リスク」
  - 「F#4 keep、理由: D7->GのV/V候補」

---

## 採譜/Pitchsieve向け推奨仕様

- **MVP**: global key推定 + out-of-scale候補リスト + 手動適用。自動全適用は出さない。
- **次段階**: 小節単位local key推定、転調境界候補、セカンダリードミナント/借用和音/半音経過音の例外検出。
- **補正ルール**:
  - `duration < threshold` かつ隣接音へ半音進行する音はデフォルト保持。
  - 強拍・長音・孤立した外れ音のみ高信頼候補。
  - 推定キー信頼度が低い小節は候補提示のみ。
  - relative/parallel/fifth関係の代替キーを必ず表示。
- **失敗時の安全策**:
  - 1クリックUndo。
  - 適用前後A/B再生。
  - 元MIDIトラックを保持し、補正済みを別レイヤー化。
  - ユーザーが「この外れ音は正しい」とマークしたピッチ/小節/文脈を以後の候補から除外。

---

## 追加参考: 中国語Web実装・利用文脈

- Soundcharts中国語版はKey/BPM/Camelot等を返し、DJ・編成・編集用途で調性情報を使う流れを説明している。
  URL: https://soundcharts.com/zh/audio-finder
- freebeat.ai中国語版は音声アップロード後に調性・BPMを返し、複雑な曲は人工判断と併用することを示唆している。
  URL: https://freebeat.ai/zh/tools/key-finder
- aisong.io中国語版は調式検出を音楽転写前の補助として位置づけ、複雑または無調性音楽では精度が下がると明記している。
  URL: https://aisong.io/zh/key-detector

---

## 結論

この機能の中核は「スケールスナップ」ではなく「調性仮説に基づく外れ音レビュー」である。スナップ先の計算自体は単純だが、危険なのは誤推定キーと音楽的外れ音を区別できない点にある。Pitchsieveでは、最初から人間確認を前提にし、転調・借用・経過音・ブルーノートを保護する例外検出を入れるべきである。最も安全な出し方は、高信頼の誤採譜だけを一括候補化し、曖昧なものは「補正しない候補」として可視化する設計である。
