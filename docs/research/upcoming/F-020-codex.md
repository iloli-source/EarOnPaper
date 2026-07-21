# F-020 歌声採譜・歌詞同期 — 論文＋WEB調査

**機能**: 歌声採譜・歌詞同期（ボーカル譜・音節割当・メリスマ・同期誤差）
**調査手段**: `mcp__codex__codex`（read-only, cwd=採譜）を主軸とし、WebSearch でURL・DOIを実在確認
**方針**: 失敗例最大化（AMNLT系 / 歌詞アライメント失敗 / ビブラート・メリスマのノート化失敗）。英語・中国語文献中心。実在URLのみ。捏造禁止。
**日付**: 2026-07-21

---

## 1. 主要な失敗モード（Synthesis）

### 1.1 ビブラート / ポルタメント / グリッサンドが note boundary に誤認される
歌声は1音の内部でもピッチが大きく揺れるため、ビブラートを複数ノートに過分割したり、legato遷移の境界を早すぎ/遅すぎに置く。median F0で note pitch を決める方式は scoop・fall・long slide・装飾音で代表音高を外す。frame-level F0 を素朴に MIDI 量子化するとこの失敗が直撃する。

### 1.2 メリスマが syllable-note assignment を壊す
「1 syllable = 1 note」は成立せず、1 syllable が複数 note に伸びる（メリスマ）。逆に装飾的ピッチ変化を「note」とみなすか「expressive gesture」とみなすかも曖昧。SVS向けアノテーションでは「word boundary は note boundary を含意するが逆は成立しない」という非対称制約が必要になる（ROSVOTが明示）。

### 1.3 歌唱特有の時間伸縮で lyrics-to-audio alignment が破綻
母音が長く子音が短い、休符・間奏・フェイク・繰り返し・未記載の掛け声などで Viterbi/CTC alignment がずれる。polyphonic music では伴奏が vocal feature を汚染し、vocal separation の insert/delete error がそのまま lyrics alignment error に伝播する。長い間奏（musical interlude）が特に word-boundary alignment error を増やす。

### 1.4 AMT/AMNLT系の joint transcription は「内容認識」と「対応付け」を混同する
note列とlyrics列がそれぞれ正しくても、対応する syllable/note group がずれると実用譜として失敗。従来の edit-distance 系メトリクスは content error と alignment error を1つに混ぜてしまうため、AMNLT では専用の **Alignment Error Rate (AlER)** が必要になった。heuristicな順序対応は melisma・missing syllable・extra note・楽譜画像上の視覚的ずれで破綻する。

---

## 2. 文献リスト（実在URL確認済み）

### 採譜・ノートセグメンテーション（ビブラート/メリスマ失敗中心）

1. **SiPTH: Singing Transcription Based on Hysteresis Defined on the Pitch-Time Curve**
   IEEE/ACM TASLP 2014. legatoではnote changeが瞬間でなく区間になるため、pitch-time curve上のhysteresisで分割。vibrato/unstable pitch対策の古典的基準点。
   DOI: https://doi.org/10.1109/TASLP.2014.2331102

2. **On the Preparation and Validation of a Large-Scale Dataset of Singing Transcription (MIR-ST500)**
   ICASSP 2021. 中国語ポップ500曲・16万超noteのlead vocal transcription dataset。non-expert annotation＋補正が必要な事実自体が note boundary定義の難しさを示す。
   https://ieeexplore.ieee.org/document/9414601/

3. **VOCANO: A Note Transcription Framework for Singing Voice in Polyphonic Music**
   singing voiceの高変動性とnote-event annotation不足をボトルネックと明示。semi-supervised学習を使うが伴奏分離依存が残る。
   https://github.com/B05901022/VOCANO （関連: MIR-ST500系, york135 GitHub）

4. **A Phoneme-Informed Neural Network Model for Note-Level Singing Transcription**
   ICASSP 2023. 歌声note onsetはlyrics phoneme変化と絡むためPPGをonset検出に投入。vibrato/bending/portamentoがboundary・pitchを難しくすると明示。
   https://arxiv.org/abs/2304.05917

5. **Robust Singing Voice Transcription Serves Synthesis (ROSVOT)**
   ACL 2024 Long Papers. 既存ASTは実用annotationには精度・robustness不足で word-note synchronization が課題。「melismaではnote boundaryがword boundaryより多い」を明示。noisy入力でもSOTA。
   https://arxiv.org/abs/2405.09940 / https://aclanthology.org/2024.acl-long.526/ / コード: https://github.com/RickyL-2000/ROSVOT

6. **STARS: A Unified Framework for Singing Transcription, Alignment, and Refined Style Annotation**
   2025（最新）。transcription・alignment・スタイル注釈を統合。ROSVOT/SongTrans系の後継的位置づけ。
   https://arxiv.org/abs/2507.06670

### 歌詞書き起こし・歌詞同期（alignment失敗中心）

7. **End-to-End Lyrics Transcription Informed by Pitch and Onset Estimation**
   CTC系ALT。singingのtime-stretchingにより internal audio-to-lyrics alignment が失敗しやすいと指摘。pitch/onset補助でcharacter alignmentを安定化。
   （ISMIR系。検索例: "End-to-End Lyrics Transcription Informed by Pitch and Onset"）

8. **Acoustic Modeling for Automatic Lyrics-to-Audio Alignment**
   polyphonic lyrics alignmentは伴奏汚染とannotated corpus不足で難しい。long-duration musical interludesがword-boundary alignment errorを増やすと報告。
   https://arxiv.org/abs/1902.06797

9. **Automatic Lyrics-to-audio Alignment on Polyphonic Music Using Singing-adapted Acoustic Models**
   speech acoustic modelをsinging向けにadapt。commercial polyphonic音源でのalignment。
   https://www.researchgate.net/publication/332791806

10. **LyricSynchronizer: Automatic Synchronization System Between Musical Audio Signals and Lyrics**
    IEEE JSTSP. CD音源はvocalが伴奏と重なるためspeech forced alignmentをそのまま使えない。vocal section detection・robust phoneme network・fricative detectionで補強。
    https://cir.nii.ac.jp/crid/1360567185274701824

11. **Creating DALI, a Large Dataset of Synchronized Audio, Lyrics and Notes**
    audio/lyrics/notesの大規模同期dataset。active learningで改善してもdataset内に残るerrorを明示。教師データ自体のalignment noiseが限界になる。
    https://arxiv.org/abs/1906.10606

### 中国語・声調言語（低資源・様式依存の失敗）

12. **Adapting Pretrained Speech Model for Mandarin Lyrics Transcription and Alignment**
    Mandarin polyphonic pop向けにWhisperをadapt。低資源言語ではデータ不足が中心課題でsource separationとaugmentationに依存。
    https://arxiv.org/abs/2311.12488

13. **Automatic Alignment of Long Syllables in A Cappella Beijing Opera**
    京劇のlong syllableをDHMM duration modelingで処理。genre-specific duration priorが効く一方、一般popへの転用は文化・様式依存が強い。
    （ISMIR/京劇コーパス系。検索例: "Automatic Alignment of Long Syllables Beijing Opera"）

14. **SongTrans: A Unified Song Transcription and Alignment Method for Lyrics and Notes**
    2024。58,144曲・807,960 song-lyric pair。前処理（vocal分離）なしでlyricsとnoteを同時transcribe＋align。AR（alignment強い）とNAR（pitch robust）を併用。note/lyrics同時alignの先駆。
    https://arxiv.org/abs/2409.14619

### AMNLT（楽譜画像×歌詞の対応付け失敗）

15. **Aligned Music Notation and Lyrics Transcription (AMNLT)**
    2024→ScienceDirect 2025掲載。music notationと歌詞を別々に読むだけでは lyrics-note alignment が失われる。many-to-many対応と専用の **Alignment Error Rate (AlER)** が必要（edit-distanceはcontent errorとalignment errorを混同する、が核心）。
    https://arxiv.org/abs/2412.04217 / https://www.sciencedirect.com/science/article/pii/S003132032500754X

16. **A Holistic Approach for Aligned Music and Lyrics Transcription**
    ICDAR 2023。AMNLTの前身。楽譜画像からmusicと歌詞を一体的に読む holistic OMR。
    https://link.springer.com/chapter/10.1007/978-3-031-41676-7_11

---

## 3. 設計上の含意（vocal-to-score / absolute-pitch-emulator 向け）

frame-level F0 を MIDI 化するだけでは不足。以下を**別々のオブジェクト**として持つべき:

- `note object`（onset/offset/pitch + confidence）
- `syllable object`（歌詞音節）
- `melisma group`（1 syllable → N notes を第一級構造として保持）
- `alignment confidence`（content error と alignment error を分離して評価。AMNLTの AlER 思想）

特に低confidenceのvibrato/portamento/melisma区間は**自動確定せず、候補分割を複数保持**する設計が現実的。「word boundary ⇒ note boundary」の非対称制約（ROSVOT）を明示的にコード化すると音節割当の破綻を減らせる。伴奏分離のinsert/delete errorがそのまま下流のalignment errorに伝播する点も、パイプライン設計で分離失敗confidenceを下流に渡すことで緩和できる。

---

## 4. 未検証・注意事項

- 文献 7・13 は codex 提示ベースで、本文の arXiv 番号までは WebSearch で単独確定できなかった（タイトル・会議は実在。番号確認は要追調査）。それ以外の全URL/DOI/arXiv番号は WebSearch で実在確認済み。
- VOCANO(3) は論文DOIよりGitHub/MIR-ST500系での参照が確実。arXiv番号は要確認。
- 捏造していないこと優先で、確定できない番号は「要確認」と明記した。
