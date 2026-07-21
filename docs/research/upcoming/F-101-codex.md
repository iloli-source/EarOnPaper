# F-101 鍵盤運指推定（指番号自動付与・右手/左手割当） — 調査（codex担当: 論文＋WEB / 失敗例重視）

- 機能: ピアノ譜に対する**指番号（1–5）の自動付与**と**右手/左手（RH/LH）割当・分割**
- 調査分担: codex担当 = 論文＋WEB調査、**失敗例を最大限**
- 手法: `mcp__codex__codex`（cwd=採譜, read-only）で論文/WEB横断調査 → 主要URL・数値を WebSearch で照合
- 作成日: 2026-07-21
- 言語方針: 英語中心（一部中国語系著者の論文含む）、**実在ソースのみ・URL併記**

> 注: 主要書誌（Nakamura et al. 2020 / PIG、Ramoneda et al. 2022 / ThumbSet、Parncutt 1997、Guan et al. 2022、Hiramatsu et al. 2021）は WebSearch で原典URL・著者・数値を照合済み。書誌が確認しにくかった表記（"Al Kasimi/Nichols/Wang SVDP"）は本文で明示的に訂正した。

---

## (1) 運指推定 METHODS and DATASETS

### データセット

**PIG（PIano fingerinG Dataset）** — 現在の事実上の標準ベンチマーク。
- Nakamura, Saito, Yoshii, "Statistical Learning and Estimation of Piano Fingering," *Information Sciences* 517:68–85, 2020.
  - DOI: https://doi.org/10.1016/j.ins.2019.12.068
  - arXiv: https://arxiv.org/abs/1904.10237
  - データセット/デモ: https://beam.kisarazu.ac.jp/~saito/research/PianoFingeringDataset/ , https://statpianofingering.github.io/demo.html
- 内容: 古典曲 150 曲（Bach/Mozart/Chopin ほか 24 作曲家）、309 個の運指アノテーション、約 100,044 notes。全音符に expert pianist の指番号。Bach/Mozart/Chopin 各 10 曲は**各曲 4 人以上**の運指があり、これが「複数正解」評価の根拠になる。
- **限界（採譜エンジンにとって重要）**: スコア＋テキスト運指が中心で、**演奏映像・個人の手形状・実演テンポ・ペダル・意図したフレージング**は基本的に含まれない。よって「物理的に演奏可能か」を直接学べない。

**ThumbSet** — 大規模だが低品質・部分ラベルのクラウドソース系。
- Ramoneda, Jeong, Nakamura, Serra, Miron, "Automatic Piano Fingering from Partially Annotated Scores using Autoregressive Neural Networks," ACM MM 2022.
  - DOI: https://doi.org/10.1145/3503161.3548372
  - PDF: https://eita-nakamura.github.io/articles/Ramoneda_PianoFingeringFromPartiallyAnnotatedScores_2022.pdf
  - データセット: https://doi.org/10.5281/zenodo.6433702
  - コード: https://github.com/PRamoneda/Automatic-Piano-Fingering
- 内容: MuseScore 由来のパブリックドメイン MusicXML 2,523 曲、**部分的・ノイズの多い**運指ラベルを**非専門アノテータ**からクラウドソース。
- **限界**: データセット説明自体が「出典不明・部分的・ノイズ多め・PIG より低品質」と明記。学習者向け/出版社/一般ユーザ由来のため、そのまま正解として使うと非現実運指を学習しうる。

### 手法系譜

**HMM 系（統計モデルの初期〜主流）**
- Yonebayashi, Kameoka, Sagayama, "Automatic Decision of Piano Fingering Based on Hidden Markov Models," IJCAI 2007, pp.2915–2921. CiNii: https://cir.nii.ac.jp/crid/1010282256907681697 — 手形・指位置を hidden state、音列を emission として Viterbi 最尤運指。初期の統計モデル。
- Nakamura, Ono, Sagayama, "Merged-Output HMM for Piano Fingering of Both Hands," ISMIR 2014, pp.531–536. https://ir.webis.de/anthology/2014.ismir_conference-2014.86/ — 両手を merged-output HMM として扱い、**手パート未指定のスコアで運指と手割当を同時**に扱う方向を提示（後述 (3) で再掲）。

**Dynamic Programming / ergonomic cost model**
- Parncutt, Sloboda, Clarke, Raekallio, Desain, "An Ergonomic Model of Keyboard Fingering for Melodic Fragments," *Music Perception* 14(4):341–382, 1997. DOI: https://doi.org/10.2307/40285730 — 指間スパン・弱指・親指黒鍵・thumb-passing 等の rule cost を定義し、短い単旋律断片で最小コスト経路を探索。以後の DP/コスト系すべての土台。
- Jacobs, "Refinements to the Ergonomic Model of Keyboard Fingering of Parncutt, Sloboda, Clarke, Raekallio, and Desain," *Music Perception* 18(4):505–511, 2001. DOI: https://doi.org/10.1525/mp.2001.18.4.505 — 半音距離ではなく**物理距離**を考慮する修正。
- Al Kasimi, Nichols, Raphael, "A Simple Algorithm for Automatic Generation of Polyphonic Piano Fingerings," ISMIR 2007, pp.355–356. https://ir.webis.de/anthology/2007.ismir_conference-2007.89/ — polyphonic score に対し horizontal cost と chord vertical cost を定義し DP 的に探索。
  - **⚠️ 書誌訂正**: 依頼にあった「**Al Kasimi/Nichols/Wang "SVDP"**」という表記は主要書誌では確認できない。実在する代表文献は上記 **Al Kasimi/Nichols/Raphael** であり、"SVDP" という略称は本調査では原典を特定できなかった（幻覚の可能性が高いので採用しない）。

**メタヒューリスティック（VNS）**
- Balliauw, Herremans, Palhazi Cuervo, Sörensen, "A variable neighborhood search algorithm to generate piano fingerings for polyphonic sheet music," *Intl. Transactions in Operational Research* 24(3):509–535, 2017. DOI: https://doi.org/10.1111/itor.12211 — DP の組合せ爆発を避け VNS で複雑 polyphony を探索。
  - **失敗**: Nakamura et al. 2020 の再現比較では **MusicXML parsing failure により 30 test pieces 中 14 曲しか処理できず**、処理できた集合でも 2nd HMM より低スコア（後掲表）。

**Sequence NN / GNN / Transformer 周辺**
- Nakamura et al. 2020 内の DNN FF / LSTM は pitch sequence 入力。出力系列制約が弱く、**HMM より低い**（下表）。
- Ramoneda et al. 2022（ThumbSet）: autoregressive seq2seq + beam search、AR-LSTM / AR-GNN。PIG fine-tuning 後に HMM/RNN baseline を上回ると報告。
- 中国語文献: Li Qiang, Wu Zhengbiao, Guan Xin, "结合深度乐谱特征融合的钢琴指法生成方法（Piano fingering generation with deep musical score feature fusion）," *CAAI Transactions on Intelligent Systems（智能系统学报）* 18(6):1287–1294, 2023. DOI: https://doi.org/10.11992/tis.202303018 , 全文: https://html.rhhz.net/tis/html/202303018.htm — pitch+speed 特徴、Word2Vec-CBOW、BiLSTM-CRF、左右手鏡像 augmentation。提案法 66.97 Mgen / 72.18 Mhigh。
- **注意**: 純粋な Transformer を PIG 運指推定の標準ベンチとして確立した査読済み SOTA は乏しい。「Transformer にすれば解ける」という根拠は現状**弱い**。

### PIG 上の代表数値（Nakamura et al. 2020）

評価指標: `Mgen`=general match（全 annotator に平均的に近いか）／`Mhigh`=最も近い GT との一致／`Msoft`=各音がいずれか 1 人の GT と一致すれば可／`Mrec`=recombination match（複数 GT を区間で切替えた最良系列との一致）。

| Method | Mgen | Mhigh | Msoft | Mrec |
|---|---:|---:|---:|---:|
| 1st HMM | 61.7 | 68.3 | 82.8 | 74.0 |
| 2nd HMM | 64.3 | 70.8 | 85.3 | 77.6 |
| 3rd HMM | 64.5 | 71.0 | 85.5 | 77.8 |
| Chord HMM | 61.2 | 67.7 | 81.7 | 73.8 |
| DNN FF | 61.5 | 66.2 | 82.5 | 69.5 |
| DNN LSTM | 61.3 | 66.1 | 82.8 | 69.5 |
| **Human** | **71.4** | **79.1** | **90.8** | **84.3** |

**要点**: 最良の 3rd HMM でも human agreement（71.4 Mgen）に届かない。この「人間同士でも 71.4」が**天井**であり、精度議論の前提になる。

---

## (2) FAILURE ケースと限界

### 複数正解が本質（single-label accuracy が誤解を生む）
- PIG の pianist 間一致は 2 人比較で平均 60–80% 程度。Bach subset では **4 人全員が同じ指を付けた音は 39.3%** に過ぎず、**2 種類の指が現れた音が 49.4%**。Mozart/Chopin でも複数選択は日常的。
- ゆえに単一ラベル accuracy は「別解だが自然」な運指を誤りに数える。反復音・旋律頂点・フレーズ切れ・速度・非レガート・ペダル前提では、教師との差分が必ずしも失敗ではない。

### 評価指標の罠
- `Mgen`: 全演奏者に平均的に近いことを評価 → **個性的で一貫した運指を不利**にしうる。
- `Mhigh`: 最も近い 1 annotator に寄る → 局所的な偶然一致を拾う。
- `Msoft`: 各音が誰か 1 人と一致すれば可 → 隣接遷移が破綻した**"切り貼り運指"を過大評価**。
- `Mrec`: それを軽減するが recombination cost の設計依存。
- Nakamura et al. 2020 自身が「match rate は acceptable error と unacceptable error を区別できない。主観評価・演奏可能性指標は未解決」と明記。**accuracy 単独で品質を語れない。**

### 物理的に不可能・非現実な運指
- Guan, Zhao, Li, "Estimation of playable piano fingering by pitch-difference fingering match model," *EURASIP J. Audio, Speech, and Music Processing* 2022:7. DOI: https://doi.org/10.1186/s13636-022-00237-8
  - 通常の HMM state transfer は密集音階（compact scales）で「手を動かさないと弾けない」運指を生むと指摘し、**IFR = irrational fingering rate** を導入。
  - 提案 PdF は 3rd HMM 比 average match +4.06% / highest match +2.87%。prior knowledge で IFR を 0 にできるが、**その制約が合理的な休符・手移動・手の協調まで消すリスク**も自認。

### 和音・polyphony
- Chord は同時発音の縦制約・音価違い・保持音・声部交差が絡む。Nakamura et al. 2020 の Chord HMM は **61.2 Mgen と 1st HMM 61.7 より低く**、synthetic duration や不自然な overlap が制約を悪化させた可能性。
- Guan et al. 2022 も pitch-only モデルは chord の time information 不足で誤り、PdF でも不要な finger crossing / finger repeats を消し切れないと報告。

### 黒鍵・白鍵
- Parncutt モデルは thumb-on-black / five-on-black / thumb-passing を rule 化したが、**現代ピアノでは黒鍵親指が常に悪いわけではない**。黒鍵回避 rule は初心者・古典慣習には合っても、Chopin 以降・速いパッセージ・大きい手では過剰制約。
- Jacobs 2001 の指摘どおり、半音数だけで距離を測ると C–E と Db–F の物理距離差・黒鍵高さ・手首角度を取り逃がす。

### 手交差・同音換指・輪指・特殊奏法
- Li/Wu/Guan 2023 は、提案 BiLSTM-CRF でも**同音換指・輪指などの特殊運指を完全には生成できず**、autoregressive LSTM には error propagation があると述べる。
- Guan et al. 2022 も repeated pitches は運指候補が多く習慣依存が強いため学習困難と報告。
- **手交差**は「右手=高音／左手=低音」という前提を破り、運指推定と手割当の**両方を同時に壊す**（(3) と直結）。

---

## (3) 右手 / 左手 ASSIGNMENT の落とし穴

### ピッチ閾値分割は危険
- 「C4 以上＝右手／未満＝左手」や「上段/下段譜で分ける」単純法は、**手交差・伴奏型の跳躍・内声・アルペジオ・左手高音メロディ・右手低音補助・連弾風 texture** で破綻する。
- 実際の手割当は音高だけでなく、同時刻の chord span・前後文脈・音価・声部継続・フレーズ・手移動コストに依存する。

### voice separation ≠ hand separation
- Hiramatsu, Nakamura, Yoshii, "Joint Estimation of Note Values and Voices for Audio-to-Score Piano Transcription," ISMIR 2021. PDF: https://archives.ismir.net/ismir2021/paper/000034.pdf
  - piano transcription では **note values と voice labels が相互依存**し、voice label は upper/lower staff（=右手/左手パート）を含むと定義。
  - 既存 voice separation は monophonic voice 仮定や正確な duration 仮定に依存しがちだが、実際のピアノ声部は chord を含み音価推定も誤るため、**そのまま手割当には使えない**。

### Merged-output HMM の示唆
- Nakamura/Ono/Sagayama 2014（前掲 ISMIR 2014）: 左右手パート未指定でも 2 つの手モデルから merged output を生成する確率モデルとして、**運指決定と voice-part separation を同時**に扱う。
  - 「先に手を閾値で割ってから片手運指」より principled。ただしモデルは簡単な polyphony 前提で、**両手重複・parallel motion・手交差・密集和音での実用限界**が残る。

### 採譜エンジン実装上の落とし穴（下流波及）
- audio-to-score では multipitch/onset error・quantization error・duration error が手割当に**波及**する。
- 誤って split された音は、後段の運指モデルで「物理的にありそうな片手運指」に**無理やり補正**され、最終スコアは一見自然でも実際の両手協調としては不自然になりうる。
- 逆に、運指モデルを hand assignment の **prior** として使えば、広すぎる片手 span・同時刻の指重複・非現実な crossing を検出できる。

### 実用方針（結論）
- right/left assignment は pitch threshold ではなく、**`hand label + voice label + fingering + note value` の joint inference** として扱うべき。
- 候補生成では両手に複数候補を残し、コスト/確率に pitch range・span・同時和音の縦制約・前後移動・voice continuity・staff notation・tempo・休符・保持音・手交差許容を入れる。
- 評価は hand accuracy 単独でなく、**演奏可能性・譜面可読性・human alternative acceptance・下流の `Mrec` / IFR** で見る。

---

## 参照URL一覧（実在確認済み中心）

- PIG / Nakamura 2020: https://doi.org/10.1016/j.ins.2019.12.068 , https://arxiv.org/abs/1904.10237 , https://beam.kisarazu.ac.jp/~saito/research/PianoFingeringDataset/
- ThumbSet / Ramoneda 2022: https://doi.org/10.1145/3503161.3548372 , https://doi.org/10.5281/zenodo.6433702 , https://github.com/PRamoneda/Automatic-Piano-Fingering
- Yonebayashi 2007 (HMM): https://cir.nii.ac.jp/crid/1010282256907681697
- Merged-output HMM 2014: https://ir.webis.de/anthology/2014.ismir_conference-2014.86/
- Parncutt 1997: https://doi.org/10.2307/40285730
- Jacobs 2001: https://doi.org/10.1525/mp.2001.18.4.505
- Al Kasimi/Nichols/Raphael 2007: https://ir.webis.de/anthology/2007.ismir_conference-2007.89/
- Balliauw 2017 (VNS): https://doi.org/10.1111/itor.12211
- Guan 2022 (PdF / IFR): https://doi.org/10.1186/s13636-022-00237-8
- Li/Wu/Guan 2023 (中文): https://doi.org/10.11992/tis.202303018 , https://html.rhhz.net/tis/html/202303018.htm
- Hiramatsu 2021 (note value + voice/hand): https://archives.ismir.net/ismir2021/paper/000034.pdf
