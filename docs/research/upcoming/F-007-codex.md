# F-007 区間選択採譜 — 論文＋WEB調査（失敗モード中心）

> 対象機能: 曲全体でなく指定区間だけを採譜/Audio→MIDI 化する（section / region / clip selection → transcription）
> 調査手段: mcp__codex__codex（read-only, cwd=採譜）＋ WebSearch 検証。英語・中国語ソース中心、実在URL併記。
> 調査観点: 失敗例の最大化 — (1)区間切り出し/チャンクの境界アーティファクト (2)オンセット切断（アタック欠落・末尾クリップ） (3)区間端の精度低下
> 更新日: 2026-07-21

---

## 0. 前提: 「区間採譜」は既存AMTの内部チャンク処理と同じ失敗を共有する

実SOTAは長尺を扱えず、**固定長セグメントに切って独立推論→連結**している。つまり「ユーザーが指定区間を切り出す」ことは、既存モデルが内部でやっている chunking をユーザー空間へ露出させる行為で、**チャンク境界の破綻がそのまま区間端の破綻**になる。したがって内部チャンクの既知バグ・対策がそのまま F-007 の設計根拠になる。

---

## 1. 実AMTシステムの chunking / windowing（固定窓が既定）

- **MT3**: Transformer長制約により音声を `2.048秒` の **non-overlapping segment** に分割、各 segment を独立推論して連結。segment をまたぐ音のため `tie` section を導入し、論文中で **「note-off を忘れる」問題**を明示。
  https://arxiv.org/pdf/2111.03017
- **MT3前身 Seq2Seq Piano Transcription (ISMIR2021)**: 長尺入力を約 `4秒` の non-overlapping segment に切って独立転写→連結。
  https://archives.ismir.net/ismir2021/paper/000030.pdf ／ https://magenta.tensorflow.org/transcription-with-transformers
- **YourMT3+**: MT3系拡張。入力を `2.048秒 audio segment` として扱う（YMT3=256 time steps log-mel、YPTF系 PerceiverTF encoder）。
  https://arxiv.org/pdf/2407.04822
- **Basic Pitch (Spotify)**: `AUDIO_WINDOW_LENGTH = 2秒`。推論時に **overlapping window（43,844 samples 窓 / overlap 7,680 samples）**、各窓の前後 `15 frames`（`DEFAULT_OVERLAPPING_FRAMES = 30` の半分）を捨てて中央 142 frames を連結。→ **overlap-and-crop でedge予測を捨てる実装パターン**。
  https://github.com/spotify/basic-pitch/blob/main/basic_pitch/constants.py ／ https://github.com/spotify/basic-pitch/blob/main/basic_pitch/inference.py
- **Onsets and Frames / Magenta.js**: default `chunkLength = 250 frames`。実装で前後に `RF_PAD = 3 frames`（receptive-field padding）を付け、**中央だけを unbatch** して連結。
  https://github.com/magenta/magenta-js/blob/master/music/src/transcription/transcription_utils.ts ／ https://magenta.withgoogle.com/onsets-frames
- **hFT-Transformer (Sony, ISMIR2023)**: chunk化しつつ、論文が **「estimated onset and offset accuracy fluctuates depending on the relative position in the processing chunk … tends to be worse at both ends」** と明記。対策は推論 stride を半分にして **chunk中央部だけ採用**。
  https://arxiv.org/abs/2307.04305 ／ https://archives.ismir.net/ismir2023/paper/000024.pdf
- **Kong et al. / ByteDance piano_transcription**: 高分解能 onset/offset regression と **pedal transcription**。区間切り出し時は pedal/sustain/offset 欠落リスクへ直結。
  https://arxiv.org/abs/2010.01815 ／ https://github.com/bytedance/piano_transcription

---

## 2. 区間切り出し固有の失敗モード（境界アーティファクト・オンセット切断）

### 2-1. 境界アーティファクト / spectral leakage
- 任意範囲で音声を切ると STFT 上で**有限長窓の端点不連続**が生まれ、spectral leakage・端点 zero-pad の影響が出る。
  https://www.ni.com/en/shop/data-acquisition/measurement-fundamentals/analog-fundamentals/understanding-ffts-and-windowing.html
- **STFT の端 padding 差**が本質的問題: `librosa.stft(center=True)` は端を pad、SciPy STFT も boundary/padded で端を拡張。→ **同じ時刻でも「whole-song 推論」と「section-only 推論」で最初/最後の frame 特徴が変わる**（同一入力でも切り方で結果が変わる非再現性）。
  https://librosa.org/doc/latest/generated/librosa.stft.html ／ https://scipy.github.io/devdocs/reference/generated/scipy.signal.stft.html

### 2-2. receptive-field truncation（区間端はモデル内部より不利）
- CNN系は端で畳み込み context が不足。Magenta.js O&F がわざわざ `RF_PAD` を入れているのはこのため。**section 冒頭をそのままモデル入力冒頭にすると、内部チャンクより端frameが不利**になる。
  https://github.com/magenta/magenta-js/blob/master/music/src/transcription/transcription_utils.ts

### 2-3. onset truncation（アタック切れ）
- Onsets and Frames は **「onset detector が確信した frame でだけ新規 note を開始」**する設計。選択開始が attack transient の**後**にあると、持続音は frame 活性があっても **note化されない or 短い誤noteとして除去**されやすい。→ 区間の頭を数十ms失うだけで冒頭ノートが消える。
  https://magenta.withgoogle.com/onsets-frames

### 2-4. note-off / sustain / decay loss（末尾クリップ）
- MT3 は segment をまたぐ note で **note-off を忘れる**問題を tie で緩和。section end で decay/pedal/offset が切れると **note duration が過短/過長**、pedal が飲み込まれる。
  https://arxiv.org/pdf/2111.03017 ／ https://arxiv.org/abs/2010.01815

---

## 3. 区間端の精度劣化と緩和策（overlap-add / context padding / streaming）

- **実測根拠が最強なのは hFT-Transformer**: chunk内位置ごとの誤差を観察し「端で悪化」を確認、stride半減で中央部のみ採用。**F-007 の edge 評価設計にそのまま流用可能**。
  https://arxiv.org/abs/2307.04305
- **overlap-and-crop 型**: Basic Pitch は overlap で推論し各窓の overlap 端を削って連結（＝edge予測を捨てる）。
  https://github.com/spotify/basic-pitch/blob/main/basic_pitch/inference.py
- **context padding 型**: Magenta.js O&F は chunk 前後に RF padding、中央を使う。→ **「推論範囲」と「返却範囲」を分ける**設計思想。
  https://github.com/magenta/magenta-js/blob/master/music/src/transcription/transcription_utils.ts
- **state/tie 型**: MT3 は segment 冒頭に既 active な notes を宣言させる tie section。**section start で既発音noteをどう表現するか**のデータ設計に重要。
  https://arxiv.org/pdf/2111.03017

### 【実在バグ例】Basic Pitch の frame-level temporal drift（Issue #190）
- `hop_size ≠ kept_frames × FFT_HOP` により、**frame-level出力の時刻と原音位置が累積ズレ**。約530秒ファイルで **末尾 −2.7秒 のドリフト**。note-level（秒stamp化されたonset/offset由来）は影響なしだが、**frame配列を評価/下流に使うと区間位置がずれる**。→ チャンク連結の seam 起因の実バグの好例。
  https://github.com/spotify/basic-pitch/issues/190

### 評価指標
- MT3/hFT は Frame / Onset / Onset+Offset / Velocity 付き F1。F-007 では**全体F1だけでなく `start/end ±0.5秒` の edge band と interior を分けて測る**べき。
  https://arxiv.org/pdf/2111.03017 ／ https://arxiv.org/abs/2307.04305

---

## 4. F-007 設計への含意

1. **区間音声を物理的に切ってからAMTしない**。`selection_start − context` 〜 `selection_end + context` で推論し、**返却時だけ選択範囲へcrop**する（推論範囲≠返却範囲）。
2. **context長はモデルchunk長以上**を確保: MT3/YourMT3系=`2.048秒`、Seq2Seq piano系=約`4秒`、O&F系=receptive field 以上。
   https://arxiv.org/pdf/2111.03017 ／ https://archives.ismir.net/ismir2021/paper/000030.pdf
3. **出力noteを3分類**: `inside` / `started_before_selection` / `ends_after_selection`。冒頭持続音を「新規onset」と誤表示しない（tie思想）。
4. **overlap推論では中央採用を標準**に（hFT・Basic Pitch が直接の根拠）。
   https://arxiv.org/abs/2307.04305 ／ https://github.com/spotify/basic-pitch/blob/main/basic_pitch/inference.py
5. **QAデータセット**: 同じ区間を `whole-song→crop` と `section-only` で比較し、`0–500ms` / `500ms–2s` / interior で F1・offset error を分離計測。切り方非再現性（§2-1）を回帰テスト化。

### 中文二次資料（技術根拠は上記一次情報を優先）
- hFT-Transformer を AMT系基礎モデルとして紹介する記事。
  https://cloud.tencent.com/developer/news/1808370

---

## 付記
- Codex（gpt系）で調査実行成功。主要主張（hFTの端劣化明記、Basic Pitchの窓/crop、Basic Pitch drift Issue #190）は WebSearch で一次ソース照合済み。
- 捏造URLなし。中国語一次論文は乏しく、根拠は arXiv/GitHub/ISMIR/公式docs を主とした。
