# F-079 楽器プロファイル（弦数・音域制約・チューニング）の TAB 生成反映 — 調査

- 機能: 楽器プロファイル（ギター6/7弦・ベース4/5弦・バリトン・音域制約・弦数）を TAB 生成へ反映する
- 調査方式: mcp__codex__codex（Web 検索可、read-only）を主、WebSearch/WebFetch で補強
- 対象: 英語圏（arXiv/ISMIR/IEEE/ACM/仕様）中心、中国語圏（学位論文・特許・論文紹介）を併記
- 作成日: 2026-07-21
- 注記: 失敗例を最大化して収集。実在 URL のみ併記。

---

## 結論（要旨）

「instrument profile」は表示設定ではなく **TAB 生成の探索空間そのものを定義する制約（hard constraints）**。AMT（自動採譜）後段は、必ず `pitch == openPitch[string] + fret` で候補 `(string, fret)` を列挙し、その上で最適化する。最低限、プロファイルは以下を持つべき:

```
strings[]        # 各弦の開放弦ピッチ（低→高 or 高→低、stringOrder で明示）
openPitch[]      # 開放弦の実音（MIDI number）
maxFret          # 最大フレット
capo             # カポ位置（実音と表記音を分離）
tuningName       # standard / drop-D / drop-C / ...
range {min,max}  # 演奏可能音域（AMT の min_freq/max_freq に反映）
instrumentFamily # guitar / bass / baritone
stringCount      # 6/7/4/5 ...
```

---

## (1) プロファイル表現と (音高)→(弦,フレット) 割当問題

### 表現フォーマット
- **MusicXML**: TAB は各音符を `<technical><string/><fret/></technical>` で弦・フレット指定。弦数/調弦/カポは `<staff-details>` 内の `<staff-lines>`, `<staff-tuning>`, `<capo>` で表現。
  - https://w3c.github.io/musicxml/tutorial/tablature/
  - https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/string/
- **MuseScore**: 「弦リスト」「開放弦ピッチ」「フレット数」を明示保持。調弦変更時は可能なら既存フレットを自動調整するが、無理な場合は破綻する（後述の失敗例）。
  - https://musescore.org/en/handbook/4/customizing-tablature-staff
  - https://musescore.github.io/MuseScore_PluginAPI_Docs/plugins/html/class_ms_1_1_plugin_a_p_i_1_1_string_data.html
- **Humdrum `**fret`**: 絶対調弦/相対調弦/フレット調律を分離表現。6弦・12弦ギター、4弦ベース、リュート等へ拡張可能。可変弦数を扱う設計参考。
  - https://www.humdrum.org/rep/fret/index.html

### 割当問題（many-to-one / underdetermined）
同一ピッチ（例: E4）が複数の `(string, fret)` で演奏可能 → 組合せ空間が巨大で全探索不可。各時刻の候補運指をグラフの層にし、静的コスト（フレット位置・開放弦選好）＋遷移コスト（ポジション移動・弦移動・指span）を最小化する。

- **DP / Viterbi**: Itoh & Hayashida はマンハッタン距離＋弦・フレット・指制約＋DP。 https://cir.nii.ac.jp/crid/1390001204604232320
- **HMM**: Hori/Kameoka/Sagayama は左手フォームを隠れ状態、音列を観測列として運指決定・編曲を HMM 復号として扱う。Hori らは **minimax Viterbi**（運指難度の最大値を最小化）も提案。 https://www.jstage.jst.go.jp/article/imt/8/2/8_477/_article/-char/en
- **A\* pathfinding（A-star-Guitar）**: 弦・フレット組合せをノード、移動難度・指span・7フレット超ペナルティ等を重み付きエッジとしてポリフォニックに最適経路探索。
- **遺伝的アルゴリズム**: 演奏可能 TAB の自動生成。 https://www.researchgate.net/publication/251423049_A_genetic_algorithm_for_the_automatic_generation_of_playable_guitar_tablature
- **TabCNN**: 音声から直接6弦 TAB を推定し「多重音高推定→運指配置」を CNN で結合。ただし **出力設計が6弦前提になりやすい**。 http://archives.ismir.net/ismir2019/paper/000033.pdf / https://zenodo.org/records/3527800
- **Fretting-Transformer（2025）**: MIDI→TAB を Encoder-Decoder（T5系）で。近年の SOTA 系。 https://arxiv.org/html/2506.14223
- **MIDI-to-Tab（Masked LM, 2024）**: マスク言語モデリングで弦割当を推論。 https://arxiv.org/html/2408.05024

### 7弦/5弦/バリトン/Drop の影響
候補生成の **低域境界と重複候補数** が変わる。7弦=低B1、5弦ベース=低B0、バリトン=B1/A1 系、Drop D=D2。標準6弦 E2 前提のモデルや `fmin=E2` の処理では **これらが丸ごと欠落**する。プロファイル別に候補生成境界と AMT 帯域を切り替える必要がある。

---

## (2) 失敗ケース（重点）

- **低音域オクターブ誤り**: 基音が弱く倍音が強い低音（E2 以下、特に B1/B0 周辺）で1オクターブ上に吸われやすい。Basic Pitch は `minimum-frequency`/`maximum-frequency` で範囲外を除外できるが、**誤推定を修復する機能ではない**（フィルタであって補正ではない）。
  - https://github.com/spotify/basic-pitch
  - https://github.com/spotify/basic-pitch/blob/main/basic_pitch/note_creation.py
- **範囲外音（impossible notes）**: GuitarSet は初期版に「negative frets / impossible notes」があり、後続版で除去と明記。**プロファイル制約を通さない TAB 生成で起きる典型例**。 https://zenodo.org/records/3371780
- **弾けない同時音**: Yazawa et al. は多重音高推定が人間に弾けない組合せを出す問題を、プレイアビリティ制約＋DP で抑制。 https://waseda.elsevierpure.com/en/publications/audio-based-guitar-tablature-transcription-using-multipitch-analy/ / https://doi.org/10.1109/ICASSP.2013.6637636
- **「最大限多くの音を載せる」失敗**: MIDI-to-TAB 研究で、6音載せられるからと低確率・不自然な運指を選ぶケース。**音を減らした方が良い場合がある**。 https://arxiv.org/pdf/2510.10619 （初出 ResearchGate: https://www.researchgate.net/publication/361330737 ）
- **データセット過適合（cross-dataset で崩壊）**: SynthTab は GuitarSet/IDMT/EGDB 間の交差評価で大幅な性能低下を示し、音色・録音条件・分布の弱さを問題化。 https://synthtab.dev/ / https://arxiv.org/abs/2309.09085
- **カポ/チューニング誤認**: 同一実音列から「カポあり標準調弦」と「カポなし別ポジション」は区別不能なことが多い。MuseScore フォーラムでも標準譜→ベース TAB 変換で「wrong string」相談あり。 https://musescore.org/en/node/346610
- **ML 出力の不正 TAB**: NTU 修士論文は DadaGP から Transformer で楽譜→吉他譜を学習。出力指法が入力音高に存在しない場合は「不彈奏」に戻す後処理を実装（=ML はそのままだと不正 TAB を出す証左）。 https://tdr.lib.ntu.edu.tw/handle/123456789/94662?locale=en
- **中国特許 CN112634841B**: 各弦・各フレット・和弦音を訓練データ化して音声→吉他譜を生成する設計。ただし **訓練済みクラス外の調弦・弦数・低域拡張には弱い構造**。 https://patents.google.com/patent/CN112634841B/zh
- **少数サンプル×倍音（inharmonicity）依存**: 弦の inharmonicity を使うと弦推定精度は上がるが、録音・弦の状態依存で脆い。 https://www.researchgate.net/publication/360793239_A_Few-Sample_Strategy_for_Guitar_Tablature_Transcription_Based_on_Inharmonicity_Analysis_and_Playability_Constraints

---

## (3) ベストプラクティス / 実装推奨

- **プロファイル先行**: `InstrumentProfile` を先に確定し、AMT 後段は必ず `candidate(string, fret)` を列挙してから探索。候補ゼロは「範囲外 / 誤推定疑い / 別チューニング疑い」に分類する。
- **6弦固定にしない**: neural model は `S x (F+2)` の可変出力にするか、**音高推定と TAB 割当を分離**する（分離した方が弦数変更に強い）。
- **hard constraints**: 弦数、同一弦の同時発音不可、`0 <= fret <= maxFret`、最低開放弦未満不可、最大フレット超過不可。
- **soft costs**: 低フレット優先 / ポジション移動 / 弦移動 / 開放弦選好 / 前後文脈 / **音を落とすペナルティ** / 奏法ペナルティ。
- **低音の AMT 帯域をプロファイル別に下げる**: 標準 E2 だけでなく 7弦 B1、5弦ベース B0、Drop A 等の周波数を **テストに入れる**。
- **カポは実音と表記音を分離保持**。推定値は確定扱いせず、候補ランキング＋UI 修正前提。
- **不可能音を黙って丸めない**: `unassigned` / `octave-shift-suggested` / `dropped-note` / `requires-retune` のように **理由付きで出す**。
- **回帰テスト必須ケース**: 標準6弦 / 7弦 / 4・5弦ベース / バリトン / Drop D・Drop C / カポあり / 最低弦未満 / 最大フレット超過 / 7音和音 / 低域オクターブ誤り。

---

## 主要ソース一覧

| 種別 | URL |
|---|---|
| MusicXML TAB tutorial | https://w3c.github.io/musicxml/tutorial/tablature/ |
| MusicXML `string` element | https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/string/ |
| MuseScore TAB customization | https://musescore.org/en/handbook/4/customizing-tablature-staff |
| MuseScore StringData API | https://musescore.github.io/MuseScore_PluginAPI_Docs/plugins/html/class_ms_1_1_plugin_a_p_i_1_1_string_data.html |
| Humdrum `**fret` | https://www.humdrum.org/rep/fret/index.html |
| Itoh & Hayashida (DP運指) | https://cir.nii.ac.jp/crid/1390001204604232320 |
| Hori/Kameoka/Sagayama (HMM/minimax) | https://www.jstage.jst.go.jp/article/imt/8/2/8_477/_article/-char/en |
| TabCNN (ISMIR2019) | http://archives.ismir.net/ismir2019/paper/000033.pdf |
| TabCNN (Zenodo) | https://zenodo.org/records/3527800 |
| Fretting-Transformer (2025) | https://arxiv.org/html/2506.14223 |
| MIDI-to-Tab Masked LM (2024) | https://arxiv.org/html/2408.05024 |
| GA for playable tab | https://www.researchgate.net/publication/251423049_A_genetic_algorithm_for_the_automatic_generation_of_playable_guitar_tablature |
| ML MIDI→Tab (arXiv) | https://arxiv.org/pdf/2510.10619 |
| Basic Pitch | https://github.com/spotify/basic-pitch |
| Basic Pitch note_creation | https://github.com/spotify/basic-pitch/blob/main/basic_pitch/note_creation.py |
| GuitarSet (impossible notes除去) | https://zenodo.org/records/3371780 |
| Yazawa et al. (playability制約) | https://doi.org/10.1109/ICASSP.2013.6637636 |
| SynthTab (cross-dataset崩壊) | https://arxiv.org/abs/2309.09085 / https://synthtab.dev/ |
| MuseScore forum (wrong string) | https://musescore.org/en/node/346610 |
| NTU 修論 (楽譜→吉他譜) | https://tdr.lib.ntu.edu.tw/handle/123456789/94662?locale=en |
| 中国特許 CN112634841B | https://patents.google.com/patent/CN112634841B/zh |
| Few-Sample inharmonicity | https://www.researchgate.net/publication/360793239_A_Few-Sample_Strategy_for_Guitar_Tablature_Transcription_Based_on_Inharmonicity_Analysis_and_Playability_Constraints |
