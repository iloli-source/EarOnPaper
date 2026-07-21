# F-092 生成AI楽曲向け採譜プリセット（合成音色・クリーンミックス向け前処理/量子化） — 調査（codex担当: 論文＋WEB / 失敗例重視）

- 機能: Suno / Udio / MusicGen / Stable Audio 等の生成AI音源を対象とした採譜プリセット。合成音色・過度にクリーンなミックスへの前処理と、時間/音程の量子化を含む。
- 調査分担: codex担当 = 論文＋WEB調査、**失敗例を最大限**（クリーンミックスの罠 / 過量子化 / ニューラルコーデック由来アーティファクト）
- 手法: `mcp__codex__codex`（cwd=採譜, read-only, gpt系）で論文/WEB横断調査 → 主要URL・数値を WebFetch/WebSearch で照合
- 作成日: 2026-07-21
- 言語方針: 英語中心 + 中国語（博客園/Bilibili）。**実在ソースのみ・URL併記**。未照合は「要照合」と明示。

> 照合済み: arXiv:2506.19108「A Fourier Explanation of AI-music Artifacts」(ISMIR 2025, Afchar et al., Suno/Udio でFourier領域アーティファクト検出、99%超) / arXiv:2405.04181「Detecting music deepfakes is easy but actually hard」(Afchar et al., 99.8%だが実運用は困難) / arXiv:2306.06546「High-Fidelity Audio Compression with Improved RVQGAN」(= DAC, NeurIPS 2023) / arXiv:2306.05284「Simple and Controllable Music Generation」(= MusicGen) / CPJKU/beat_this (ISMIR 2024「Beat This! Accurate Beat Tracking Without DBN Postprocessing」) / 博客園 MusicGen・EnCodec 解説2件。**Bilibili「精度95%」宣伝値は要照合**。

---

## (1) 手法と精度

生成AI楽曲向けAMTプリセットで最初に押さえるべきは、**「Suno / Udio音源を高精度に採譜できる」と検証された標準ベンチマークは現時点でほぼ存在しない**こと。既存AMTの精度は主に MAESTRO、MusicNet、Slakh、GuitarSet、NSynth、OpenMIC、MIREX で測られており、商用生成AI音源の混合済みマスターに対する実測値は要照合。

代表手法:
- **Basic Pitch**: 軽量な多音高・ノート転写。単一楽器や明瞭な旋律に強いが、混合音源・ドラム・GMプログラム推定・拍節解釈は主目的でない。**ピッチベンド出力を持つ点は、AI音源のグライド/ビブラートを潰さないために重要**。
- **Onsets and Frames**: ピアノ向け。onsetでframeを制約するため明瞭な打鍵に強い。一方、合成音の擬似アタック・ノイズ成分・パッドの遅い立ち上がりには弱い。
- **MT3**: 複数データセット統合、ノート/プログラム/ドラムをイベント列出力するマルチタスク型。生成AI楽曲のように「音色がGM分類に収まらない」場合、出力プログラムがもっともらしく見えても誤る。
- **MIREX系評価**: フレームF0・ノートonset/offset・ポリフォニック転写・ビート/テンポはあるが、「ニューラル生成音源」「Suno/Udioマスター」「コーデック劣化」を直接評価する標準タスクはまだ限定的。

**失敗ケース重視の要点**: ノートF1が高くても、以下が壊れると製品価値は落ちる — ピッチベンドが半音列に分割 / スウィングがストレート8分に丸められる / ドラムがGMマップで別楽器に割当 / パッド・ボーカルシンセの持続音が幻の分散和音になる / AI特有の高域アーティファクトがハイハット/倍音として採譜される。

---

## (2) クリーンミックスの罠（最重要）

生成AI楽曲は一聴「分離が良い・ノイズが少ない・音圧が安定」でAMTしやすく見えるが、AMTには逆に危険:

1. **過剰に同期したレイヤー**: 全パートが完全グリッド上で同時発音すると、onset検出器は1つの強いスペクトル変化しか観測しない。コード全体のonsetは取れても、個別楽器の立ち上がり順・ストラム・フラム・ゴーストノートが潰れる。
2. **物理楽器らしくないエンベロープ**: AIギター/ピアノ/パッドは実楽器風倍音を持ちつつ ADSR が非物理的。onset検出は「急なスペクトル変化」をノート開始とみなすため、フィルター開閉・サイドチェイン・ボコーダー変化をonsetと誤認する。
3. **ノイズが少ないほど倍音が強く見える**: 実録音では部屋鳴り・息・弦ノイズが音源識別の手掛かりになるが、クリーンなAI音源では倍音列だけが過度に整い、F0推定がオクターブ誤り・5度誤り・和音内 phantom F0 を出しやすい。
4. **過剰なマスタリング**: リミッター/コンプで音量差が平坦化し、velocity推定が不安定に。ビート推定がサイドチェインのポンピングを拍として拾う。
5. **ステレオの罠**: 派手なステレオ拡張を単純モノラル化すると位相キャンセルで中央のボーカル/ベースが弱まり、側成分のシンセ/ハイハットが過大評価される。

---

## (3) 量子化の失敗例

生成AI楽曲では量子化は「補正」でなく**破壊的編集**になりやすい:

- **false straight-eighths**: スウィング/シャッフル/後ノリがストレート8分・16分へ吸着。AI音源は元からグリッド感が強く「完全なストレート」と過信されやすい。
- **tuplet loss**: 3連・5連・速いラン・ロールが最短グリッドに丸められ、音符数が減るか等間隔32分連打に化ける。
- **grid-lock**: 全パートを同一グリッドへ吸着すると、ドラムの前ノリ・ベースの後ノリ・ボーカルのレイドバックが消え、再生MIDIが「死んだ演奏」になる。
- **scale-lock error**: 自動キー推定後のスケール補正で、ブルーノート・ピッチベンド・民族音階の揺れ・AIボーカルのグライドが隣接スケール音へ誤吸着。
- **bent/glide note splitting**: ギターベンド・シンセポルタメント・ボーカルのしゃくりが、半音階の短いノート列として出る。楽譜では汚く、DAW用途では不要MIDIが増える。
- **drum-map misassignment**: 808 kick とベース、clap と snare、noise riser と cymbal、sibilance と hi-hat が混同。生成AIのドラムは実録サンプルでなく複数音色の中間体になりやすい。
- **barline hallucination**: ループ境界/セクション切替を小節頭と誤認し、弱起・変拍子・途中テンポ変化を壊す。
- **duration quantization**: onsetだけ量子化しても offset を強く丸めると、レガート・ペダル・シンセリリース・ボーカル母音が短い矩形ノートになる。

**推奨**: 初期出力を「performance MIDI」（マイクロタイミング/ピッチベンド保持）と「score MIDI」（段階的量子化）に分離する。

---

## (4) ニューラルコーデック由来アーティファクト

MusicGen系は EnCodec の離散オーディオトークンを使い、DAC も RVQ系ニューラル圧縮、Stable Audio Open はオートエンコーダ潜在表現を使う。MP3/AACとは違う失敗をAMTに持ち込む:

- **token frame境界の周期性**: 短い時間単位で離散コードが更新され、復元波形に微小周期性/ざらつきが乗ると、スペクトルフラックス型onsetが細かい擬似onsetを出す。
- **高域の人工パターン**: AI音楽検出研究（arXiv:2506.19108）は生成音楽にFourier領域で識別可能なアーティファクト（微小スペクトルピーク＝checkerboard由来）が出ることを数学的に示す。AMTではこれがハイハット/シェイカー/シンバル/弦ノイズ/息成分として誤採譜されうる。
- **attack smearing**: コーデック復元や拡散系デコーダでトランジェントが丸まるとonset時刻が遅れ、ドラムだけ後ろにずれる/打鍵がコード単位で太る/速いパッセージがレガート化。
- **pitch smearing**: ボーカルシンセ/リードの連続ピッチがF0推定上「安定音程とノイズの中間」に見え、短い半音列・装飾音・無音区間として分断される。
- **phantom instruments**: 高域ざらつき・位相揺れ・倍音のにじみが実在しない楽器（薄いストリングス/遠いコーラス/小さいハイハット）として分類される。
- **再エンコード劣化**: Suno/Udio出力をユーザーがMP3・動画・SNS経由で再圧縮すると、ニューラルコーデックの癖＋従来コーデックのpre-echo/高域欠落が重なる。**生成元より流通後ファイルの方がAMTに難しい**。

---

## (5) 楽器分類・ビート推定の破綻

**楽器分類**: 既存データセット（実録音/サンプル/MIDIレンダリング/弱ラベル）に対し生成AI音源は外れ値 — GMプログラムに対応しないハイブリッド音色が多い / 「ギターっぽいシンセ」等の中間カテゴリが多い / 1ノート中に楽器カテゴリが変わる / ミックス前から音色が滲み classifier が主旋律の倍音を別楽器と見る。**ドラムはとくに危険で、kick/snare/hat でなく sub transient / noise burst / metallic tail として検出した方が実用的な場合がある**。

**ビート・テンポ推定**: 破綻点 — 完全グリッド伴奏なのにボーカル/シンセのフレーズが拍より目立つ / sidechain pump が四分拍として拾われる / 8分アルペジオが強くテンポ倍取り / ハーフタイムのドラムとダブルタイムのハイハットでテンポ仮説が分裂 / セクション遷移で小節頭がずれDBN平滑化が誤った拍を維持 / 曖昧なイントロ・アウトロで downbeat が消える。**単一BPMに確定せず、half/double・swing・triplet・局所テンポマップの複数仮説を保持すべき**。Beat This!（ISMIR 2024）のようにDBN後処理に依存しない手法も出ているが、生成AI音源の拍節曖昧性・倍テンポ問題を解決したわけではない。

---

## (6) ベストプラクティス（プリセット設計）

1. **入力診断を先に行う**: 生成AI由来らしさ / ステレオ位相 / ラウドネス / クリッピング / 再圧縮 / 高域アーティファクト / 無音でないイントロ・アウトロ を検出。
2. **単純モノラル化しない**: mid/side・左右別・モノラルの3系統で特徴抽出し位相キャンセルに強くする。
3. **onsetを複数方式で見る**: spectral flux だけでなく HFC・SuperFlux系・低域ドラム用・持続音用・ボーカル/シンセ用を分ける。単一onset confidenceを信用しない。
4. **ピッチベンドを標準保持**: AIボーカル/リード/ギター風では、12平均律ノートだけでなく cents 単位の連続F0を別レーンに残す。
5. **量子化は非破壊・段階式**: 初期は弱い吸着。小節グリッド・スウィング・3連・局所テンポ・パート別遅延を候補提示し確定前に比較。
6. **performance MIDI と score MIDI を分ける**: DAW編集用はタイミング/ベロシティ/ピッチ揺れ保持、譜面表示用は読みやすさ優先で簡約。
7. **ドラムはGM固定にしない**: 低域トランジェント・ノイズバースト・金属尾部・クラップ様など中間ラベルを持つ。
8. **プログラム分類に unknown を許す**: MT3系の GM program をそのまま信じず `unknown_synth_pluck` / `vocal_pad_like` / `guitar_like_synth` の保留カテゴリを持つ。
9. **ニューラルコーデック拡張で評価**: Slakh / MAESTRO / GuitarSet / NSynth を EnCodec・DAC・MP3/AAC・リミッター・ステレオワイド・拡散系劣化で再レンダリングし失敗パターンを回収。
10. **評価指標を増やす**: note F1 だけでなく program F1 / drum map accuracy / beat・downbeat F-measure / pitch-bend RMSE / groove deviation / quantization edit distance / false onset density。

---

## (7) 最新トレンド（2024-2026）

- 2024以降、音楽生成は EnCodec/RVQトークン系・潜在拡散/flow matching系・制御条件付き生成へ分岐。採譜側は「通常音楽」でなく「生成モデルのデコーダ癖」を前提にする必要が出ている。
- **MusicGen / AudioCraft**（arXiv:2306.05284）はテキスト/メロディ条件を EnCodecトークン生成へ接続する代表例。中国語技術ブログ（博客園）でも EnCodec / RVQ / codebook 解説が増加。
- **Stable Audio Open**（arXiv:2407.14358）はオープンなText-to-Music、44.1kHz音声＋潜在オートエンコーダ。EnCodec型と違うアーティファクトを持つため、プリセットは「MusicGen専用」にしない方がよい。
- **AI音楽検出**が活発化: 「Detecting music deepfakes...」(arXiv:2405.04181, 99.8%だが実運用困難) と「A Fourier Explanation...」(arXiv:2506.19108, ISMIR 2025, Suno/Udioで99%超) は、AMT前処理の「AI由来判定」「アーティファクト除去」に直結。
- 中国語圏資料は MusicGen/EnCodec解説・Basic Pitch利用チュートリアル・AI扒谱動画が中心。**「Suno/Udio音源のAMT失敗」に直接フォーカスした検証記事は少なく、製品開発では自社評価セットが必須**。

---

## 参照URL一覧

**AMT手法/データセット**
- Basic Pitch デモ: https://basicpitch.spotify.com/
- Basic Pitch GitHub: https://github.com/spotify/basic-pitch
- Basic Pitch paper (arXiv:2203.09893): https://arxiv.org/abs/2203.09893
- MT3 paper (arXiv:2111.03017): https://arxiv.org/abs/2111.03017
- MT3 GitHub: https://github.com/magenta/mt3
- Onsets and Frames paper (arXiv:1710.11153): https://arxiv.org/abs/1710.11153
- Magenta Onsets and Frames: https://magenta.tensorflow.org/onsets-frames
- Slakh2100: https://zenodo.org/records/4599666
- NSynth: https://magenta.tensorflow.org/datasets/nsynth
- NSynth paper (arXiv:1704.01279): https://arxiv.org/abs/1704.01279
- GuitarSet: https://guitarset.weebly.com/
- GuitarSet GitHub: https://github.com/marl/GuitarSet
- OpenMIC-2018 GitHub: https://github.com/marl/openmic-2018
- OpenMIC-2018 paper (arXiv:1807.03871): https://arxiv.org/abs/1807.03871

**MIREX / ビート**
- MIREX HOME: https://www.music-ir.org/mirex/wiki/MIREX_HOME
- MIREX 2024 Polyphonic Transcription: https://www.music-ir.org/mirex/wiki/2024:Polyphonic_Transcription
- MIREX 2025 Audio Beat Tracking: https://www.music-ir.org/mirex/wiki/2025:Audio_Beat_Tracking
- librosa onset_strength: https://librosa.org/doc/latest/generated/librosa.onset.onset_strength.html
- madmom GitHub: https://github.com/CPJKU/madmom
- Beat This! GitHub (ISMIR 2024): https://github.com/CPJKU/beat_this

**ニューラルコーデック / 生成モデル**
- EnCodec paper (arXiv:2210.13438): https://arxiv.org/abs/2210.13438
- EnCodec GitHub: https://github.com/facebookresearch/encodec
- DAC / Improved RVQGAN paper (arXiv:2306.06546, NeurIPS 2023): https://arxiv.org/abs/2306.06546
- DAC GitHub: https://github.com/descriptinc/descript-audio-codec
- MusicGen paper (arXiv:2306.05284): https://arxiv.org/abs/2306.05284
- AudioCraft GitHub: https://github.com/facebookresearch/audiocraft
- Stable Audio Open paper (arXiv:2407.14358): https://arxiv.org/abs/2407.14358
- Stable Audio Tools GitHub: https://github.com/Stability-AI/stable-audio-tools

**AI音楽検出 / アーティファクト（前処理に直結）**
- Detecting music deepfakes is easy but actually hard (arXiv:2405.04181): https://arxiv.org/abs/2405.04181
- A Fourier Explanation of AI-music Artifacts (arXiv:2506.19108, ISMIR 2025): https://arxiv.org/abs/2506.19108

**製品ドキュメント**
- Suno Help Center: https://help.suno.com/
- Udio Help Center: https://help.udio.com/

**中国語ソース**
- MusicGen理解（博客園 susuna596）: https://www.cnblogs.com/susuna596/p/19309199
- Transformers中文文档 MusicGen章（博客園 apachecn）: https://www.cnblogs.com/apachecn/p/18262272
- AI扒谱 / Basic Pitch 利用動画（Bilibili、**精度95%等の宣伝値は要照合**）: https://www.bilibili.com/video/BV1rK4y137Vt/
