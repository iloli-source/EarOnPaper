# F-084 記譜前のMIDIクリーンアップ工程 調査レポート（codex担当: 論文＋WEB / 失敗例重視）

> 対象機能: 記譜前のMIDIクリーンアップ工程 —— 量子化・音価・密度・不要音の削除を**記譜化する前に確定させる順序制御**。
> 調査分担: codex担当（論文＋WEB、失敗例を最大限）。
> 調査手段: `mcp__codex__codex`（GPT-5.2）を主軸に実行し、主要出典は WebSearch で実在性・正規URLを再検証済み。
> 収集言語: 英語中心、一部中国語Webソース。すべて実在ソース・URL併記。
> 作成日: 2026-07-21

---

## 0. 要旨（3行）

- 削除（pruning）を最初に強くかけるのは危険。**原MIDI非破壊保存 → 拍/テンポ/小節推定 → オンセット量子化 → 音価/オフセット決定 → 声部割当 → 密度簡略化 → スプリアス音の最終除去（可逆） → 記譜** が安全な順序。
- 最大の失敗類型は **false-positive pruning（本物の音を消す）** と **量子化↔音価決定の相互干渉**。「短いから」「弱いから」「グリッド外だから」の単独条件削除が主犯。
- Nakamura らの研究群が示すように、余分音除去はリズム量子化の「前処理」ではなく**量子化と統合して解く推定問題**として扱うのが有効。実装上は「早期に削除」ではなく「早期に低信頼フラグ、最後に確定」。

---

## 1. 記譜前クリーンアップの手法と順序（軸1）

### 1.1 前提: AMT出力の「MIDI」は事実ではなく推定結果

音声AMT（automatic music transcription）の出力は、ピッチ・オンセット・オフセット・ベロシティ・信頼度を持つ**候補列**であって確定事実ではない。Spotify の Basic Pitch も、モデル出力からMIDIイベント/CSV note events を生成する際に、オンセット閾値・フレーム閾値・最小音長（`min_note_len`）などの後処理パラメータが結果を大きく左右する。したがってクリーンアップ工程では常に「raw event / quantized event / notation event」を分離し、**削除・結合・量子化を非破壊で**行うのが原則。

### 1.2 拍・テンポ・小節線を最初に固める理由

量子化は「絶対時刻 → 相対的な記譜時間（拍・小節）」への写像なので、拍・テンポ・小節線の誤りが全後工程を汚染する。Takeda ら（HMMによるMIDI採譜）や Cemgil ら（ベイズ的テンポ追跡＋リズム量子化の結合）が示す通り、音価列・テンポ・拍子・小節位置は本質的に同時推定すべき問題。

Shibata/Nakamura/Yoshii (2021) は、**音符レベル精度が高くても、テンポスケール・拍子・小節線などのグローバル構造が誤りやすい**と報告している。これは「個々の音は合っているのに楽譜として読めない」典型的な失敗であり、記譜前にグローバル構造を優先確定すべき根拠になる。

### 1.3 オンセット量子化を先に、音価決定は後で

- **オンセット量子化**: 各音の開始位置を拍グリッドへ配置。
- **音価決定**: 量子化済みオンセット・実オフセット・次音オンセット・声部・ペダル・奏法を見て、四分/八分/タイ/スタッカート等を決定。

Nakamura/Yoshii/Dixon (2017, Note Value Recognition) は、**演奏上の実音長が記譜音価から大きくずれる**ため音価/オフセット推定が難しく、従来法では不完全な楽譜になりやすいと述べる。音価推定はオンセット譜時刻に依存するので、**オンセット量子化の誤りがそのまま音価誤りへ伝播**する。順序を守る必然性がここにある。

### 1.4 密度調整は音価決定「後」

密度調整（1拍内の最大音数・最小可読単位・連続同音統合・装飾音扱い）を音価決定前に走らせると、短い本物音・前打音・トリル・速いリフ・ゴーストノートを消しやすい。ギターTAB系の RiffToTab も、タブ変換の前に「Quantize → trim density → lock scale → keep melody intent」の順で**MIDI意図を整えてから楽器固有マッピングへ渡す**設計を掲げている。

### 1.5 スプリアス音除去は最後に確定（統合推定として）

Nakamura/Benetos/Yoshii/Dixon (2018, ICASSP) は、多音高検出が**余分音とタイミング誤差**を生み、それがリズム量子化を難しくすると指摘し、metrical HMM を拡張して**余分音除去をリズム量子化に組み込む**。重要なのは、余分音除去が量子化の「前処理」ではなく**量子化と相互作用する推定問題**として扱われている点。実装上の最終除去は単一根拠でなく複数根拠にすべき：

- 音響信頼度が低い
- 譜面上も実時間上も音長が短すぎる
- 近傍ピッチ/倍音由来の疑いが高い
- 拍グリッド上で説明できない
- 声部進行・和声・楽器制約で説明しにくい
- ユーザーが削除候補をレビューできる

---

## 2. 失敗例: 過剰削除が本物の音を消す（軸2, 最重要）

### 2.1 短音しきい値による本物音の削除

Basic Pitch の後処理には `min_note_len` があり、短すぎる音を `continue` でスキップする実装がある。ノイズ除去としては合理的だが、**前打音・装飾音・速い経過音・ハンマリング/プリングオフ・短いスタッカート**を消すリスクを伴う。MuseScore の MIDI import も「shortest note value」を設定でき、短すぎると譜面が過密化し、長すぎると**実在する細かい音符が表現不能**になる（どちらに振っても失敗する二律背反）。

**教訓**: `80ms未満は削除` のような固定ミリ秒の絶対ルールは危険。BPM相対・楽器別・奏法別・局所密度別にする。

### 2.2 密度トリムによる速いパッセージの破壊

「1拍にN音まで」式の密度制限はノイズに効くが、以下を誤削除しやすい：ピアノ反復音・トレモロ・アルペジオ・ドラムのゴーストノート・ギター/ベースの速いリフ・歌唱のこぶし/メリスマ。Nakamura (2018) が note-tracking で **repeated notes（反復音）の扱いを改善**しているのは、反復音が単純なオンセット統合で失われやすいという実装上の警告そのもの。

### 2.3 スコア情報に寄せすぎる削除（score-informed の副作用）

Ewert/Wang/Müller/Sandler (2016, ISMIR) の score-informed transcription は、既知スコアに対する「正しい音・欠落音・余分音」検出で強力。しかし**教育用途で "スコアにない音=extra" とみなせても、自由採譜では装飾・即興・編曲上の実音かもしれない**。参照スコアや想定キーに合わないだけで削除すると genuine notes を消す。

同論文の具体的失敗例: **piece 6 で余分音（extra note）クラスの F値が大きく低下**。原因は、実演でスコア上の pitch 54/66 が pitch 53/65 に置換されており、該当ピッチのテンプレート学習・外挿が破綻したこと。**しきい値やテンプレートが局所文脈に合わないと、実際に鳴った音でも検出・分類に失敗する**という好例。

### 2.4 倍音・隣接音の誤検出を消す副作用

AMTでは倍音由来のオクターブ誤検出・部分音・隣接半音誤りが頻出する。Ycart らは、**誤りの種類によって聴感上の目立ち方が違い、調外の false positive は特に目立つ**と報告。よって削除は必要だが、「調外」「弱い」「短い」だけで消すと、**ブルーノート・クロマチックアプローチ・非和声音**まで消える。評価指標も音符F値だけで見ると、この種の質的差異を見落とす。

---

## 3. 量子化と音価決定の相互干渉（軸3）

### 3.1 量子化が早すぎると起きること

- テンポ推定がわずかに遅れるだけで、八分音符が「付点八分＋十六分」に化ける。
- スイングをストレート八分へ丸め、実際の三連/シャッフルを失う。
- アルペジオを和音に畳み、分散和音の意図を失う。
- 反復音のオンセットが近すぎて1音に統合される。
- オフセットが拍に吸われ、スタッカートや休符が消える。

### 3.2 音価決定が早すぎると起きること

拍グリッドがまだ不確かなため、後で小節線や拍子を直したときに**タイ・休符・連桁・声部が総崩れ**になる。

### 3.3 単一「quantize」ボタンの誤り

MuseScore の MIDI import は、適応的量子化グリッド・tuplet search・human performance・time signature・simplify durations・swing detection を**別々の操作**として持つ。これは実務的にも、**拍・連符・音価簡略化・スイング認識が別問題**であり、単一の「量子化」処理に押し込めてはいけないことを示す。McLeod/Steedman の MV2H が multi-pitch / voice / meter / note value / harmony を**分離して評価**するのも同じ思想。

---

## 4. ベストプラクティス（軸4）

1. **raw MIDI を絶対に破壊しない** —— すべての削除は `suppressed` フラグで表現し元イベントへ戻せるようにする。
2. **削除より先に「疑い」を付ける** —— `low_confidence` / `possible_harmonic` / `too_short` / `off_grid` / `density_candidate` を付与し、最終レンダリング直前まで確定しない。
3. **テンポ/拍/小節は複数仮説で保持** —— 単一BPMへ早期固定しない。rubato・pickup・ritardando・swing・6/8と3/4の曖昧性で効く。
4. **オンセット量子化と音価決定を分離** —— 開始位置を決めてから、次音・実オフセット・ペダル・声部・楽器制約を見て音価を決める。
5. **最小音長を固定ミリ秒だけで決めない** —— BPM相対・楽器別・奏法別・局所密度別に。
6. **密度調整はジャンル/楽器別に** —— ピアノ・ギター・ドラム・歌唱で「細かい本物音」の意味が違う。ギターTABなら RiffToTab 型に「MIDI意図を残してから運指制約へ渡す」。
7. **グローバル閾値を避ける** —— Ewert らのように pitch-dependent thresholding を使う（音域・音色・録音条件でエネルギーが大きく変わる）。
8. **評価をノートF値だけで終わらせない** —— MV2H（multi-pitch / voice / meter / note value / harmony）で見る。A2Sでは WER/LER も、音高と音価が同一トークンとして正しいかを見るため有用。
9. **UIで削除候補を可視化** —— 「消した音」「統合した音」「量子化で移動した音」をレビュー可能にする。Klangio や Bots for Music の中国語ページも、生成後に音符・拍号・速度・調号・音価を編集できる設計が前提。

---

## 5. 推奨実装順序（順序制御の確定案）

```text
Audio
  -> AMT note candidates（ピッチ/オンセット/オフセット/信頼度）
  -> raw MIDI-like event store（非破壊保存）
  -> beat / tempo / downbeat hypotheses（複数仮説）
  -> onset quantization, soft（オンセットのみ、可逆）
  -> repeated-note & onset-merge analysis（反復音を保護）
  -> duration / note-value / tie / rest decision（音価確定）
  -> voice / staff / hand / instrument assignment
  -> density simplification with protected-note classes（保護クラス付き）
  -> spurious-note pruning, reversible（最終・可逆）
  -> MusicXML / **kern / notation rendering
```

**核心原則**: density と pruning を「音楽的意図の確定前」に走らせない。「短いから削除」「弱いから削除」「グリッド外だから削除」の単独条件は false-positive pruning の主要原因になる。

---

## Sources（すべて実在確認済み・URL併記）

論文（一次情報）:

- Nakamura, Benetos, Yoshii, Dixon (2018, ICASSP), “Towards Complete Polyphonic Music Transcription: Integrating Multi-Pitch Detection and Rhythm Quantization” — 余分音除去をmetrical HMMへ統合。 https://eita-nakamura.github.io/articles/AudioAndMIDITranscription_ICASSP2018.pdf （書誌: https://www.semanticscholar.org/paper/8b613c642dba723a4a3294e407b9ce1c7529965b ）
- Nakamura, Yoshii, Dixon (2017), “Note Value Recognition for Piano Transcription Using Markov Random Fields” — 音価/オフセット推定の困難。 https://arxiv.org/abs/1703.08144
- Nakamura, Yoshii ほか (2017), “Rhythm Transcription of Polyphonic Piano Music Based on Merged-Output HMM for Multiple Voices” — 声部併合とリズム量子化。 https://arxiv.org/pdf/1701.08343
- Shibata, Nakamura, Yoshii (2021, Information Sciences), “Non-Local Musical Statistics as Guides for Audio-to-Score Piano Transcription” — グローバル構造の誤りやすさ。 https://arxiv.org/pdf/2008.12710 （書誌: https://dblp.org/rec/journals/isci/ShibataNY21.html ）
- Cemgil, Desain, Kappen, “Rhythm Quantization for Transcription” — テンポ追跡とリズム量子化の結合。 https://cir.nii.ac.jp/crid/1363107369742995584
- Takeda ほか, “Hidden Markov Model for Automatic Transcription of MIDI Signals” — 音価・テンポの同時推定。 https://era.ed.ac.uk/items/d13a9449-85ba-4db7-be0d-e33a975c3344/full
- Ewert, Wang, Müller, Sandler (2016, ISMIR), “Score-Informed Identification of Missing and Extra Notes in Piano Recordings” — piece 6 の extra-note F値低下（過剰/誤削除の具体例）、pitch-dependent thresholding。 https://archives.ismir.net/ismir2016/paper/000123.pdf
- Ycart ほか, “Investigating the Perceptual Validity of Evaluation Metrics for Automatic Piano Music Transcription” — 誤り種別による聴感差、調外FPの目立ち。 https://transactions.ismir.net/articles/10.5334/tismir.57
- McLeod, Steedman (2018, ISMIR), “Evaluating Automatic Polyphonic Music Transcription” (MV2H) — multi-pitch/voice/meter/note value/harmony の分離評価。 https://ismir2018.ircam.fr/doc/pdfs/148_Paper.pdf （コード: https://github.com/apmcleod/MV2H ）
- McLeod (2019), “Evaluating Non-aligned Musical Score Transcriptions with MV2H” — 非アラインMusicXML評価。 https://arxiv.org/pdf/1906.00566
- Hawthorne ほか, “Onsets and Frames: Dual-Objective Piano Transcription” — オンセット/フレーム二目的、後処理閾値の影響。 https://research.google/pubs/onsets-and-frames-dual-objective-piano-transcription/

ツール・実装・ドキュメント:

- Basic Pitch（Spotify） モデルカード / note生成コード（`min_note_len` 等の後処理）。 https://huggingface.co/spotify/basic-pitch / https://github.com/spotify/basic-pitch/blob/main/basic_pitch/note_creation.py
- MuseScore MIDI import（量子化・tuplet search・simplify durations・swing detection）。 https://musescore.org/en/handbook/2/midi-import
- MIREX Audio-to-Score Transcription タスク定義。 https://music-ir.org/mirex/wiki/2026%3AAudio-to-Score_Transcription
- RiffToTab ワークフロー（Quantize→trim density→lock scale→keep melody intent）。 https://rifftotab.com/
- Audio-to-Score Piano Transcription プロジェクトページ（audio2score、日本語版あり）。 https://audio2score.github.io/ / https://audio2score.github.io/index-ja.html

中国語Webソース:

- Klangio Transcription Studio（生成後に音符・拍号・速度・調号・音価を編集）。 https://klang.io/zh-hans/transcription-studio/
- Bots for Music（中国語UI）。 https://botsformusic.com/zh

---

## 補足メモ（検証の状態）

- 主要論文（Nakamura 2018 ICASSP / Ewert 2016 ISMIR / Shibata 2021 / MV2H 2018）は WebSearch で実在・正規URLを再確認済み。Nakamura 2018 は著者本人サイトの canonical PDF（`eita-nakamura.github.io/.../AudioAndMIDITranscription_ICASSP2018.pdf`）へ差し替え。
- codex 初回出力にあった一部URL（NII CiNii ページ等）は書誌ページであり本文PDFではない場合があるため、可能な範囲で著者サイト/ISMIRアーカイブ/arXivの一次PDFへ寄せた。
- Basic Pitch の `min_note_len`、MuseScore の shortest note value / swing detection は公開ドキュメント・公開コードで確認できる範囲の記述。パラメータ挙動の詳細は実装時に該当バージョンで再確認推奨。
