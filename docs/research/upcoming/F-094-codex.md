# F-094 譜面差分ハイライト（2つのMusicXML/MIDIのピッチ・リズム差分可視化） — 調査（codex担当: 論文＋WEB / 失敗例重視）

- 機能: 2つの MusicXML/MIDI（例: 正解譜 vs 自動採譜結果、または版違い）のピッチ・リズム差分を可視化・ハイライト
- 調査分担: codex担当 = 論文＋WEB調査、**失敗例を最大限**
- 手法: `mcp__codex__codex`（cwd=採譜, read-only, model=gpt系）で論文/WEB横断調査 → 主要URL・数値を WebFetch で照合
- 作成日: 2026-07-21
- 言語方針: 英語中心（一部中国語論文含む）、**実在ソースのみ・URL併記・捏造禁止**

> 照合済み: MV2H README（DTW追加=v2.0/2019、`-p` penalty、MusicXML→4/4扱い、chord symbols非parse、music21 anacrusis問題）、nASAP/TISMIR.149（Peter et al. 2023、Parangonada の enharmonic 表示問題）、TISMIR.57（Ycart et al. 2020、知覚とmetricの乖離）は WebFetch で原典確認済み。

---

## エグゼクティブサマリー

**Score Diff Highlight の最大リスクは「差分検出」そのものではなく、その前段に必須の note correspondence（音符対応付け）が不安定なこと。** DTW・note matching・MV2H/F-measure・XML/MIDI diff はいずれも、失敗時に「本当の音楽的差分」ではなく「**対応付けの失敗**」を赤く塗ってしまう。単一の赤/緑 diff UI は、DTWの誤対応をそのまま「譜面差分」と誤表示する構造的欠陥を抱える。

---

## (1) DTW / Score Alignment の失敗モード

### 反復・ジャンプで構造的に破綻
DTW は単調増加の経路を仮定するため、反復・D.S./D.C./Coda・任意ジャンプでは構造的に壊れる。Shan & Tsai (ISMIR 2020) は、未知のジャンプ位置では Jump DTW が頑健でなく、反復・ジャンプ処理が主要ボトルネックだと報告。
- https://program.ismir2020.net/poster_1-07.html

Bukey, Feffer, Donahue (2024) も、反復記号を自動処理する既存DTW系は低品質になりがちで、専門家が repeat signs を数秒ラベルするだけで精度が大幅改善すると報告。「完全自動diff」が反復で破綻しやすい強い証拠。
- https://chrisdonahue.com/publication/24-11-jltr/

### 境界条件（端点吸着・off-diagonal drift）
通常DTW/subsequence DTW は「どこから始まりどこで終わるか」の仮定を置くため、前奏カット・後奏追加・途中抜粋・録音開始遅れで off-diagonal drift や誤った端点吸着が起きる。FlexDTW はこの問題を明示的に扱うために提案（ISMIR 2023）。
- https://zenodo.org/doi/10.5281/zenodo.10265393

### ポリフォニーで一次元列化が失敗
同時発音を一次元列に落とす時点で失敗する。nASAP/TISMIR は、DTW的 sequence alignment と note alignment は別物で、note alignment は未対応要素を含み、対応ペアは時間順序に厳密でない場合があると説明。「score chords をどう逐次表現するか」が中心的困難で、arpeggio・rolled chord・左右手ずれ・声部非同期で DTW path が one-to-many / many-to-one に引きずられる。
- https://transactions.ismir.net/articles/10.5334/tismir.149

### 装飾音（ornaments）
Nakamura et al. は ornaments の実現が不定で、chordal notes / ornaments / inter-chord events の IOI 分布が重なると報告。trill 後続音・short appoggiatura・arpeggio が対応付けを誤らせる。
- https://www.tandfonline.com/doi/abs/10.1080/09298215.2015.1078819

### 実録音での onset/offset 境界ズレ
Devaney は、初期DTW alignment の個別 onset 中央誤差が **118ms**、HMM refinement 後も **77ms** 程度残る例を報告。50ms前後の許容幅で diff 色付けすると、**境界誤差だけで rhythm difference に見える**。
- https://www.tandfonline.com/doi/full/10.1080/09298215.2014.890630

### 中国語文献の実装例と限界
張苾荍・韓聖龍は MIDI/MusicXML と WAV/MP3 の score alignment に chroma + DTW を使い、実録音＋手動小節ラベルで評価。ただし chroma は octave・voice 情報を潰すため、octave error・voice crossing・同音異声部の区別に弱い。
- https://manu44.magtech.com.cn/Jwk_infotech_wk3/article/2012/1003-3513/1003-3513-28-1-40.html

---

## (2) Note-to-Note Correspondence の失敗モード

「note A == note B」は単純な pitch+onset 近接では決まらない。

- **split/merge が insertion/deletion に落ちる**: nASAP は note alignment を match / deletion / insertion として表現するが、「片方の1音が他方の2音に分割」「trill が譜面上1記号で演奏上多数音」「grace note が拍外」で分類が曖昧化。mir_eval は bipartite matching で最適ペアリングするが、各 reference note は高々1つの estimated note にしか対応できず、split/merge は insertion/deletion に落ちる。
  - https://transactions.ismir.net/articles/10.5334/tismir.149
  - https://mir-eval.readthedocs.io/latest/api/transcription.html
- **同音連打の対応入れ替わり**: 同じ pitch の連続音は、onset が少しずれるだけで隣の同音に対応が入れ替わる。
- **voice crossing / chord splitting**: 見た目の差分と音響的差分が食い違う。musicdiff は `voicing` を通常無視でき、必要なら含められる設計 — 声部所属の違いが diff の目的次第で「重要差分」にも「ノイズ」にもなることを示す。
  - https://github.com/gregchapman-dev/musicdiff
- **enharmonic equivalence**: MIDI pitch や mir_eval の Hz/cent 比較では G♯ と A♭ は同一に見えるが、notation diff では spelling が意味を持つ。Cogliati & Duan は note spelling を評価項目に含める。
  - https://zenodo.org/records/1415830
- **octave error が評価設定で隠れる**: mir_eval multipitch は raw pitch と chroma-wrapped metrics を提供するが、chroma は octave を潰すため、chroma 類似度を使うと octave 間違いを「近い」と誤判定。
  - https://mir-eval.readthedocs.io/latest/api/multipitch.html
- **可視化側の落とし穴（照合済み）**: nASAP の Parangonada では pitch spelling を認識せず、A♭ major の黒鍵も♯表示になる（Fig.6 caption 明記）。diff UI が enharmonic spelling を保持しないと譜面差分として誤誘導。
  - https://transactions.ismir.net/articles/10.5334/tismir.149

---

## (3) MV2H / AMT 評価指標の限界

### MV2H の alignment 依存
MV2H は Multi-pitch, Voice, Meter, Value, Harmony を統合する有用指標だが、2018版は入力との time alignment を前提。非整列 score-to-score 評価には 2019版（v2.0）で DTW alignment を追加。**alignment が壊れると MV2H も壊れる**。
- https://arxiv.org/abs/1906.00566
- https://github.com/apmcleod/MV2H

### penalty 設定が差分量を変える（照合済み）
MV2H の README は、DTW insertion/deletion penalty `-p`（default 1.0）を上げると「一致が悪くても多くの音を強制的に align」、下げると完全一致以外を align しにくい、と説明。**score diff で penalty 設定が差分量を左右する具体的失敗源**。
- https://github.com/apmcleod/MV2H

### typesetting errors を意図的に評価しない
MV2H 2018論文は、beaming・stem direction・pitch spelling などは underlying analysis に従うとし、**適切な組版そのものは metric に含めない**と明言。「見た目の譜面差分ハイライト」用途では不足。
- http://ismir2018.ircam.fr/doc/pdfs/148_Paper.pdf

### MV2H の実装上の制限（照合済み）
README より: MusicXML は MuseScore3 経由変換が推奨、music21 変換では **anacrusis を手動設定（`-a INT`）が必要**（testで music21 が誤処理）、**time signature がない MusicXML は 4/4 扱い**、**chord symbols は parse されない**。
- https://github.com/apmcleod/MV2H

### mir_eval transcription の盲点
基本は pitch/onset/offset tolerance 内の note counting。**onset-only metric は pitch と offset を完全に無視**し、offset-only metric は pitch と onset を無視。「音高が違うが onset は合った」ケースを良く見せられる。
- https://mir-eval.readthedocs.io/latest/api/transcription.html

### F-measure 単独は誤差の性質を隠す
AMT サーベイは、Precision/Recall/F-measure は素早い比較に便利だが、誤りの性質をほとんど示さず timing tolerance の影響も測られないため誤解を生むと指摘。
- https://link.springer.com/article/10.1007/s13173-013-0118-6

### 知覚評価との乖離（照合済み）
Ycart, Liu, Benetos, Pearce (TISMIR 2020) は、F-measure 差が 10% 未満の場合、評価者が metric と確信を持って不一致になるのが約 **40%**。rhythm/tempo/meter が listener 判断に重要。note F1 が高くても「譜面として読みにくい/リズムが変」を見逃す。
- https://transactions.ismir.net/articles/10.5334/tismir.57

### MUSTER と edit-distance 系の過剰罰
MUSTER は MusicXML score transcription 向け edit-distance metrics で6側面を評価。ただし edit distance 系は、**1つの metrical alignment mistake が time signature・rest duration・note duration・tie 分割へ連鎖し過剰罰**になり得る（MV2H 論文が Cogliati & Duan 型 metric の限界として明示）。
- https://amtevaluation.github.io/
- http://ismir2018.ircam.fr/doc/pdfs/148_Paper.pdf

### 音楽的側面の欠落
2024 の musically informed piano transcription metrics も、従来の frame/note-wise IR metrics は articulation・dynamics・rhythmic precision を説明しにくいとする。Score Diff Highlight では「どの音が違うか」だけでなく「どう音楽的に違うか」が必要。
- https://www.catalyzex.com/paper/towards-musically-informed-evaluation-of

---

## (4) MusicXML / MIDI を diff substrate にする限界

### raw text diff は不適
MusicXML は partwise/timewise・defaults・layout・IDs・software固有 export の差で、同じ音楽でもXML構造や順序が大きく変わる。複数表現を持つ交換形式である点が diff を難しくする。
- https://www.musicxml.com/for-developers/musicxml-dtd/
- https://www.w3.org/2021/06/musicxml40/

### 「見た目差分」≠「意味差分」
Library of Congress は MusicXML を相互運用に強い形式としつつ、出版社固有の engraving や細部の見た目を完全には伝えない制限を挙げる。
- https://guides.loc.gov/music-notation-preferred-preservation-formats-for-digital-scores/musicxml

### MIDI は notation diff にさらに弱い
Standard MIDI Files は time-stamped MIDI data の交換形式で、音符・音量・音色・制御イベント中心。**beam・tie spelling・voice notation・enharmonic spelling は基本的に失われる**。
- https://midi.org/standard-midi-files

### MIDI timing は tick/tempo/拍子依存
delta time in ticks・PPQN・tempo で実時間が決まるため、**PPQ違い・tempo map違い・quantization違いが rhythm diff に化ける**。
- https://mido.github.io/mido/files/midi.html

### 正規化（canonical representation）が前提
partitura docs は、MEI/MusicXML/Humdrum/MIDI は情報豊富だがそのまま MIR tasks の入力に理想的ではない、と明記。まず canonical symbolic representation への正規化が必要。
- https://partitura.readthedocs.io/en/stable/introduction.html

### 可視化基盤 Verovio の import 制限
MusicXML 変換は開発中、web interface のサイズ制限、tuplets・user-defined symbols・multi-voice music の既知制限あり。
- https://www.verovio.org/musicxml.html
- https://book.verovio.org/toolkit-reference/input-formats.html

### 先行ツール musicdiff の設計と副作用
visible notation differences に焦点。2つの tied eighth notes と single quarter note、beamed 16ths と unbeamed 16ths を「違い」として扱う。採譜・OMR評価には良いが、**演奏上同じ差分も赤くなる**設計。
- https://github.com/gregchapman-dev/musicdiff

### semantic/notation-level diff の学術根拠
Foscarin et al. "A diff procedure for music score files"（DLfM 2019）は、XML譜面を直接diffせず、中間の notation tree 表現と sequence/tree edit distance を使う提案。raw text diff ではなく semantic/notation-level diff が必要という根拠。
- https://dlfm.web.ox.ac.uk/2019-proceedings
- https://doi.org/10.1145/3358664.3358671

---

## 実装上の結論（失敗回避のための設計指針）

Score Diff Highlight は、以下を**分離して表示**すべき。単一の赤/緑 diff は DTW の誤対応を「譜面差分」と誤表示する:

1. `alignment confidence`（対応付けの信頼度を明示し、低信頼領域を差分と区別）
2. `match type`: match / insertion / deletion / substitution / **split / merge / ornament**
3. `pitch equivalence mode`: MIDI pitch / enharmonic / diatonic staff position（用途で切替）
4. `rhythm mode`: performed time / quantized beat / notated value（境界誤差を rhythm diff にしない）

**明示的な QA 失敗ケース**として扱う: 反復・D.S./Coda、前奏/後奏の増減、装飾音、同音連打、voice crossing、arpeggio/rolled chord、enharmonic spelling、octave error、実録音の onset ズレ（77–118ms級）、MIDI の PPQ/tempo/quantization 差。

---

## 参照URL一覧
- Shan & Tsai (ISMIR 2020, Jump DTW): https://program.ismir2020.net/poster_1-07.html
- Bukey/Feffer/Donahue 2024 (repeat signs): https://chrisdonahue.com/publication/24-11-jltr/
- FlexDTW (ISMIR 2023): https://zenodo.org/doi/10.5281/zenodo.10265393
- Peter et al. 2023 nASAP/TISMIR.149: https://transactions.ismir.net/articles/10.5334/tismir.149
- Nakamura et al. (ornaments/alignment): https://www.tandfonline.com/doi/abs/10.1080/09298215.2015.1078819
- Devaney (onset error 77–118ms): https://www.tandfonline.com/doi/full/10.1080/09298215.2014.890630
- 張苾荍・韓聖龍 (中国語 chroma+DTW alignment): https://manu44.magtech.com.cn/Jwk_infotech_wk3/article/2012/1003-3513/1003-3513-28-1-40.html
- mir_eval transcription: https://mir-eval.readthedocs.io/latest/api/transcription.html
- mir_eval multipitch: https://mir-eval.readthedocs.io/latest/api/multipitch.html
- musicdiff (Chapman): https://github.com/gregchapman-dev/musicdiff
- Cogliati & Duan (spelling を含む eval): https://zenodo.org/records/1415830
- MV2H arXiv (2019 DTW版): https://arxiv.org/abs/1906.00566
- MV2H GitHub (README制限): https://github.com/apmcleod/MV2H
- MV2H 2018 論文 (typesetting除外): http://ismir2018.ircam.fr/doc/pdfs/148_Paper.pdf
- AMT survey (F-measure限界): https://link.springer.com/article/10.1007/s13173-013-0118-6
- Ycart et al. TISMIR.57 (知覚評価乖離): https://transactions.ismir.net/articles/10.5334/tismir.57
- MUSTER (amtevaluation): https://amtevaluation.github.io/
- Musically informed metrics 2024: https://www.catalyzex.com/paper/towards-musically-informed-evaluation-of
- MusicXML DTD (for-developers): https://www.musicxml.com/for-developers/musicxml-dtd/
- MusicXML 4.0 spec (W3C): https://www.w3.org/2021/06/musicxml40/
- LoC MusicXML preservation: https://guides.loc.gov/music-notation-preferred-preservation-formats-for-digital-scores/musicxml
- Standard MIDI Files: https://midi.org/standard-midi-files
- Mido (MIDI files/timing): https://mido.github.io/mido/files/midi.html
- partitura introduction: https://partitura.readthedocs.io/en/stable/introduction.html
- Verovio MusicXML: https://www.verovio.org/musicxml.html
- Verovio input formats: https://book.verovio.org/toolkit-reference/input-formats.html
- Foscarin et al. DLfM 2019 (diff procedure): https://dlfm.web.ox.ac.uk/2019-proceedings / https://doi.org/10.1145/3358664.3358671
