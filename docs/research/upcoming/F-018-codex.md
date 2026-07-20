# F-018 ドラム採譜 — 論文＋WEB調査（失敗モード中心）

> 対象機能: キット別自動採譜・同時打音・GM Drum Map / MusicXML percussion マッピング
> 調査手段: mcp__codex__codex（read-only, cwd=採譜）。英語・中国語ソース中心、実在URL併記。
> 調査観点: 失敗例の最大化 — (1)ADT手法と精度・データセット (2)同時打音/ゴーストノート/シンバルの検出失敗とドメインギャップ (3)記譜の落とし穴
> 更新日: 2026-07-21

---

## 1. ADT(Automatic Drum Transcription) 手法・精度・データセット

### データセット
- **IDMT-SMT-Drums**: 608 WAV / 約2h10m / 104ループ。対象は **BD/SD/HH の3点セットのみ**（フルキット非対応）。
  https://www.idmt.fraunhofer.de/en/publications/datasets/drums.html
- **ENST-Drums**: プロ3名、各約75分、8ch録音。sticks/rods/brushes/mallets を網羅、off-beatのゴーストノートも注釈対象。ADT評価の定番。
  https://perso.telecom-paristech.fr/grichard/ENST-drums/
- **MDB Drums**: MedleyDB由来23曲、7994 onset、6クラス/21サブクラス。
  https://github.com/CarlSouthall/MDBDrums
- **ADTOF**: リズムゲーム譜面由来の大規模弱ラベル群（計359h級）。2023論文で ADTOF-YT(245h/2924曲/5 vocab), ADTOF-RGW(114h/1739曲), TMIDT(259h)。
  https://github.com/MZehren/ADTOF ／ https://www.mdpi.com/2624-6120/4/4/42

### 精度目安（F-measure / F1）
- **Frame-RNN (Zehren 2023)**: ADTOF-RGW `0.83`, ADTOF-YT `0.85`, RBMA `0.65`, ENST `0.78`, MDB `0.81`。
  → ジャンル/録音条件でばらつく点に注意。RBMA(実曲)で0.65まで落ちる。
- **Omnizart / Wei 2021系（note-level F1）**: ENST `74%`, MDB `71%`。
  https://github.com/Music-and-Culture-Technology-Lab/omnizart/blob/master/paper.md
- **Conformer系フルキット（2026）**: ENST内 Micro-F1 3-class `0.920±0.001`, 8-class `0.872±0.002`。
  ただし **外部データへのゼロショットは 0.70–0.72 まで低下**（＝ドメイン内で高くても本番で落ちる）。
  https://www.mdpi.com/2076-3417/16/13/6746
- **MT3 vs Onsets-and-Frames系（2026比較）**: Slakh Drums onset F1 が MT3 `74.16%`, OaFS `71.23%`。
  https://www.mdpi.com/2624-6120/7/1/12 ／ https://storage.googleapis.com/mt3/index.html

### 手法別の特性と落とし穴
- **NMF/テンプレート分離**: BD/SD/HHの3点には強いが、フルキット・音色差・同時打音で崩れる。
- **RNN/CNN(onset系)**: 実データで安定するが、クラス不均衡（tom/cymbalが少数）で弱クラスが落ちる。
- **Transformer / tatum同期**: 反復構造に効くが、**グリッド誤差で「同一楽器の複数onsetが1 tatumに潰れる」「50ms外へ量子化される」** 失敗が典型。
  https://www.mdpi.com/2624-6120/2/3/31

---

## 2. 同時打音 / ゴーストノート / シンバルの検出失敗・ドメインギャップ

- **同時打音が最大リスク**: 2025 ISMIR論文 — DTD(ドラム単体)は「同時onsetを除くとほぼ完全」に近づく＝同時打音が主たる誤り源。DTM(混合曲)では伴奏・歌の干渉が主因で、同一キット・強onsetのみ・非同時化の各条件で約5%ずつ改善。
  https://publica.fraunhofer.de/entities/publication/825f8da1-a712-4825-bc33-8d869801a8e4
- **ゴーストノート**: 低SNRで false negative 化。ENSTはoff-beatのゴーストを注釈する一方、無音に近いタイムキープ打音は除外 → **「何をノートとするか」の定義がデータセット間で揺れる**（評価が不安定）。
- **シンバル系が難物**: crash/ride/splash/china/ride bell/bow は広帯域ノイズ・長い減衰・overhead bleed で混ざる。SOTAでも toms/cymbals は弱クラスとして残存。
- **hi-hat の連続性**: closed/open/pedal は実質連続量。GMは `42 closed / 44 pedal / 46 open` の3値だが、半開き・チック・フットスプラッシュを3分類へ潰すと記譜が不自然になる。
- **ドメインギャップ**: brushes/rods/mallets、live録音のPA/観客音、close-mic対overhead、他楽器低域によるBDマスキング。**合成→実録の転移ギャップ**が繰り返し強調される（中国語要約含む）。
  https://hub.baai.ac.cn/paper/5ecd04db-4e81-41e1-9a87-82ef86ccdb6d

---

## 3. 記譜(percussion clef / GM Drum Map / MusicXML percussion) の落とし穴

### GM Drum Map
- 事実上の既定だが **「音色」までは保証しない**。基本割当:
  `35/36` kick, `37` side stick, `38/40` snare, `42/44/46` hi-hat, `49/57` crash, `51/59` ride, `53` ride bell。
  https://midi.org/midi-ci-profile-for-default-drum-note-map ／ https://www.cs.cmu.edu/~music/cmp/archives/cmsip/readings/GMSpecs_PercMap.htm

### MusicXML percussion
- 打楽器は `<pitch>` で出さず、**`<unpitched><display-step>` で譜面位置 / `<instrument id>` で音源ID / `<midi-unpitched>` で再生音** を分離する。
  https://w3c-cg.github.io/musicxml/tutorial/percussion/
- **【最重要バグ源】`midi-unpitched` は 1-based（1–128）**。通常のMIDI note number(0–127)と **+1 ずれる**。
  例: GM kick `36` → MusicXML では `37`。オフバイワン混入の定番。
  https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/midi-unpitched/
- **notehead が意味を担う**: hi-hat=`x`、cymbal=`diamond` 等、snare/kick=normal。同一line上でも notehead で区別が必要。
- **multi-voice 必須**: hi-hat/ride=上向き stem、kick=下向き、snare/tom=文脈依存。全部を単一voice/chordにすると beam/stem/可読性が壊れる。MuseScoreもdrumsetごとにline/head/voice/stemを保持。
  https://musescore.org/en/handbook/developers-handbook/references/instrumentsxml-documentation
- **rimshot / cross-stick**: GMでは `37 side stick` やsnare系に分岐。モデルがSD一括だと復元不能。
  → **設計指針: 「検出クラス」と「記譜/再生マップ」を分離し、未知/低信頼は編集可能な候補として提示する。**

---

## 設計への含意（F-018向け要点）

1. **同時打音・ゴースト・シンバルを一次リスクとして設計**。単体ベンチのF値（0.9台）を信じず、外部データゼロショット0.70前後を前提にレビュー段を置く。
2. **検出クラスと記譜/再生マップを疎結合化**。hi-hat 3値・rimshot等は低信頼候補として編集可能に。
3. **MusicXML `midi-unpitched` の 1-based（+1）ずれ**を実装時の必須チェック項目にする。notehead/voice/stem のドラム譜規約もテスト対象。
