# F-102 サステインペダル(CC64)検出と記譜(MusicXML pedal要素) — 調査（codex担当: 論文＋WEB / 失敗例重視）

- 機能: ピアノ音源からのサステインペダル(CC64)検出と、その MusicXML `<pedal>` 要素への記譜
- 調査分担: codex担当 = 論文＋WEB調査、**失敗例を最大限**
- 手法: `mcp__codex__codex`（cwd=採譜, read-only）で論文/WEB横断調査 → 主要URL・数値を WebFetch/WebSearch で照合
- 作成日: 2026-07-21
- 言語方針: 英語中心（一部中国語系著者の論文含む）、**実在ソースのみ・URL併記**

> 注: 数値（MAESTRO pedal onset F1 = 91.86%、MusicXML `line`/`sign` の相互依存デフォルト、half/soft pedal 非対応など）は WebSearch/WebFetch で原典を照合済み。

---

## (1) ペダル検出の手法と精度

### MIREX 2024 の扱い
- MIREX 2024 に**独立したペダル評価タスクは無い**。ただし Polyphonic Transcription タスクが sustain pedal `CC64` を明示的に要求。慣例として `CC64 >= 64` を「on」、`< 64` を「off」とし、sostenuto / soft pedal は評価対象外。
- 結果はペダル推定がドメイン横断で弱いことを示す。Transkun V2 の pedal onset+offset F1 は MAESTRO で `0.8377` だが、MAPS では `0.5088` まで低下。データ拡張版 Transkun で MAPS を `0.5532` に改善。強力なノート推定系でも**ペダルを一切出力しない提出**があった（＝ノート精度とペダル精度は別物）。
  - https://music-ir.org/mirex/wiki/2024%3APolyphonic_Transcription
  - https://music-ir.org/mirex/wiki/2024%3APolyphonic_Transcription_Results

### データセット: MAESTRO
- 約200時間の音声/MIDI整列データ。sustain・sostenuto・una corda のペダル位置を含む。v1 は sustain `CC64`、v2 は `CC66/67` も保持。ペダル検出研究の事実上の標準。
  - https://magenta.withgoogle.com/datasets/maestro

### 主要論文
- **Kong et al. "High-resolution Piano Transcription with Pedals by Regressing Onset and Offset Times" (arXiv:2010.01815, 2020)** — オンセット/オフセット時刻を回帰。MAESTRO で note onset F1 = `96.72%`（Onsets and Frames の 94.80% を上回る）、**pedal onset F1 = `91.86%`（MAESTRO 初のベンチマーク）**。ByteDance 実装は広く再利用される。失敗要因: フレーム/ホップ長の制約、ラベル整列（アライメント）への敏感さ。
  - https://arxiv.org/abs/2010.01815
  - 実装: https://github.com/bytedance/piano_transcription
- **Liang / Fazekas / Sandler — CNN によるペダル検出** — ペダル onset と「ペダル区間」を2分類器で推定。テスト平均 F1 `0.74`、ロマン派レパートリーで良好。転移学習の後続研究では合成データ検証精度 `0.98` だが、実音響 Chopin では平均 F値 `0.89`・micro F `0.84`。失敗要因: 音高・ダイナミクス・ポリフォニーがペダルの音響痕跡を隠す、演奏スタイル・録音条件依存。
  - https://www.researchgate.net/publication/350371641_Transfer_Learning_for_Piano_Sustain-Pedal_Detection
- **Transkun V2 (arXiv:2404.09466)** — ノート/ペダルを区間として semi-CRF + Transformer でモデル化。ペダル延長を含まないデータ生成にも対応。
  - https://arxiv.org/abs/2404.09466
  - https://pypi.org/project/transkun/

**要点**: SOTA でもペダル F1 はノート F1 より一段低く、学習ドメイン外（MAPS等・実音響）で急落する。ペダルは「取れて当然」ではなく脆弱な特徴量。

---

## (2) ペダルによる音価過大の誤記譜（最重要の失敗例）

- MIREX の慣例: 打鍵離鍵（key-up）がサステイン中に起きた場合、note offset を**ペダル解放時刻または次の同音オンセットまで延長**する。これは MIDI 再生・評価では妥当だが、**記譜では危険** — 共鳴（resonance）を「書かれた音符の長さ」に変換してしまう。
  - https://music-ir.org/mirex/wiki/2024%3APolyphonic_Transcription
- ライブラリ Partitura はこの区別を `note_off`（物理的離鍵）と `sound_off`（サステインで調整された発音終了）として明示的に分離。ドキュメントは「score-MIDI ローダは deadpan なスコアMIDI用であり、表現的な演奏MIDI用ではない」と警告。
  - https://partitura.readthedocs.io/en/latest/

**失敗パターン**: ペダル延長された offset をそのまま音価にすると、全ての音符が過剰に長い記譜になる（共鳴 → 全音符/タイの海）。

---

## (3) 量子化との干渉・失敗例

- 量子化がペダル延長後の offset を消費すると、以下を生む:
  - **偽の長音符**、小節線をまたぐ不要なタイ
  - 誤ったボイス割当、演奏不能なレガート、和声変化まで保持される和音構成音
- **同音連打がペダル下にあると特に脆い**: 「次の同音まで延長」ルールが、真の打ち直し（re-articulation）を隠したり、1つの共鳴音を反復タイ記譜に分裂させたりする。
- ペダル解放タイミングは記譜上の拍の**間**に落ちることが多く、それを「音符終端」として量子化するとリズムが乱雑化する（本来は「ペダルリフト」の記号であるべき）。
- MAPS/MIREX の結果はドメイン横断の offset/ペダル問題を裏付け、MIREX は MAPS の offset 偏差アノテーション問題も指摘。

**推奨対処**: 量子化対象は「物理的/音楽的な音価」であって「ペダル延長された共鳴」ではない。offset を音価に流し込む前にペダル層を分離する。

---

## (4) MusicXML `<pedal>` 表現の落とし穴

- `<pedal>` は**視覚的ディレクション要素**。`type` は `start | stop | change | continue | discontinue | resume | sostenuto` を取る。`change` は「リフト＋踏み直し」を意味し `line="yes"` 前提。
  - https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pedal/
  - https://www.w3.org/2021/06/musicxml40/musicxml-reference/data-types/pedal-type/
- **line と sign の相互依存デフォルトに注意**（照合済み）: `line="no"` なら `sign` は既定 yes、`line="yes"` なら `sign` は既定 no。互換性のための条件付きデフォルトなので、**常に明示指定**すべき。
- **half-pedal は `<pedal>` グラフィックでは表現不可**。再生用途では `<sound>` の数値属性 `damper-pedal` / `sostenuto-pedal` / `soft-pedal`（`0–100` または yes/no）で表現。
  - https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/sound/
- **soft pedal（una corda）専用の `<pedal>` 視覚要素は無い**。MusicXML 仕様は `<words>` / `<bracket>` で特殊グラフィックを表現するよう案内。
- sostenuto は `type="sostenuto"` で区別されるが、多くの記譜ソフトでの描画/往復が不完全になりがち。

**失敗パターン**: (a) `line`/`sign` を省略して表示が意図と食い違う、(b) half-pedal を無理に on/off 化して情報欠落、(c) soft/sostenuto を damper と混同。

---

## (5) ベストプラクティス

1. **3層を分離して保持**: 物理的 `note_off` / 音響的 `sound_off` / 記譜上の音価。
2. **記譜の量子化はペダル延長前の音価に対して行う**（共鳴を音符長にしない）。
3. ペダルは MusicXML の **direction（`<pedal>`）として出力**し、再生忠実度が要る場合のみ `<sound damper-pedal="...">` を併記。
4. **CC64 は二値出力にしきい値処理**しつつ、half-pedal 研究/将来の記譜に備え内部では連続値を保持。
5. **明示的な QA 失敗ケース**として扱う: 強いリバーブ、密なポリフォニー、同音連打、ロマン派のペダリング、MAESTRO 外の実音響、MAPS 系のアライメント偏差。
6. MusicXML の `line`/`sign` は**常に明示指定**。half-pedal/soft/sostenuto は無理に `<pedal>` に押し込まず適切な手段を選ぶ。

---

## 参照URL一覧
- MIREX 2024 Polyphonic Transcription: https://music-ir.org/mirex/wiki/2024%3APolyphonic_Transcription
- MIREX 2024 Results: https://music-ir.org/mirex/wiki/2024%3APolyphonic_Transcription_Results
- MAESTRO: https://magenta.withgoogle.com/datasets/maestro
- Kong et al. 2020 (arXiv:2010.01815): https://arxiv.org/abs/2010.01815
- ByteDance piano_transcription 実装: https://github.com/bytedance/piano_transcription
- Transfer Learning for Piano Sustain-Pedal Detection (Liang et al.): https://www.researchgate.net/publication/350371641_Transfer_Learning_for_Piano_Sustain-Pedal_Detection
- Transkun V2 (arXiv:2404.09466): https://arxiv.org/abs/2404.09466
- Transkun (PyPI): https://pypi.org/project/transkun/
- Partitura docs: https://partitura.readthedocs.io/en/latest/
- MusicXML `<pedal>`: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pedal/
- MusicXML pedal-type: https://www.w3.org/2021/06/musicxml40/musicxml-reference/data-types/pedal-type/
- MusicXML `<sound>`: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/sound/
