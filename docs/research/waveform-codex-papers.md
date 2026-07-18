2026-07-19時点の調査要約です。Slack送信は試みましたが、現在のツール面に `send_message` が露出しておらず、Slack connector のインストール確認も未完了だったため未投稿です。

# AI採譜アプリ向け 波形処理技術調査

## 0. 結論

**第一候補の特徴表現**は、採譜本体では **CQT/HCQT系 + onset/frame/multipitchの多頭推定**、または既存SOTAの利用を前提に **MT3系のlog-mel seq2seq**。日常録音・楽器非依存を重視するなら、NF-050の「耳」層は **音質診断・前処理・F0/多重F0補助・信頼度推定**、その上の「記譜」層は **音符イベント生成と楽譜整形**に分けるのが妥当です。

**前処理で精度の8割**という強い学術的裏づけは見つかりません。根拠があるのは、SNR低下・録音環境差・残響・学習データの音響偏りがAMT精度を大きく落とし、ノイズ/残響/ピッチ/EQ augmentationが頑健性を改善する、という範囲です。

## 1. 波形→音符パイプライン

**確定知見**

AMTの典型構成は、音声波形 → 時間周波数表現 → フレーム別 pitch/onset/offset/velocity 推定 → 音符イベント化 → MIDI/譜面化です。近年も多くのSOTAは生波形直入力ではなく、STFT派生・mel・CQT/HCQTなどの時間周波数表現を使います。

入力表現の選択は性能に効きます。Cheuk et al. は、同じ単純NNでも入力表現だけで transcription accuracy が 8.33%上がり error が 9.39%下がると報告しています。log-frequency STFTが強く、melは少ないbin数でも比較的高性能という結果です。DOI: https://doi.org/10.1109/IJCNN48605.2020.9207605

主要モデルの入力整理:

| モデル | 対象 | 入力表現/前段 | 示唆 |
|---|---:|---|---|
| Onsets and Frames | ピアノ | spectrogram系、onsetとframeを分離推定 | onsetを明示的に持つのが有効。論文はonset情報で大幅改善を示す。https://arxiv.org/abs/1710.11153 |
| MT3 | 多楽器 | log Mel spectrogram → Transformer seq2seq MIDI-like token | 楽器横断には強いが、segment処理・token出力の後処理が必要。https://research.google/pubs/mt3-multi-task-multitrack-music-transcription/ / https://storage.googleapis.com/mt3/index.html |
| Basic Pitch | 楽器非依存・軽量 | harmonic stacking/CQT系の多出力モデル | 「1楽器に近い」入力で実用的。onset, note, contour/multipitchを同時推定。https://arxiv.org/abs/2203.09893 |
| Transkun V2 | ピアノ | 低時間解像度feature map + non-hierarchical Transformer + semi-CRF | ピアノでは強いが楽器非依存ではない。https://arxiv.org/abs/2404.09466 |

**設計示唆**

MVPでは「CQT/HCQT + Basic Pitch系」を第一候補にし、MT3系を多楽器・伴奏混在の比較モデルに置く。独自モデルを作るなら、生波形直入力を主戦場にするより、CQT/HCQT/log-melを安定実装し、onset/offset/multipitch/voicing/confidenceを別headにする方が堅いです。

## 2. F0推定・マルチピッチ推定

**確定知見**

単音F0はかなり成熟しています。CREPEは16kHzの1024サンプル波形を直接CNNに入れ、MDB-stem-synthでRPA 0.967、10 cent閾値でも0.909を報告しています。加法ノイズ実験では、pub/white noiseで概ねCREPEが強く、SNR 10dB未満では全体にCREPE優位とされています。https://arxiv.org/abs/1802.06182

pYINはYINの確率モデル化で、古典DSP + HMMの強いベースラインです。DOI: https://doi.org/10.1109/ICASSP.2014.6853678

SPICEはCQT上の自己教師ありpitch推定で、教師ラベルなしでもclean/noisy audioで教師ありモデルに近い精度を報告しています。DOI: https://doi.org/10.1109/TASLP.2020.2982285

PESTOはVQT/CQT系の自己教師ありpitch推定で、論文では130k parameters、5ms未満レイテンシ、サンプルレート/バッファ差への対応を主張しています。DOI: https://doi.org/10.5334/tismir.251

**未解決**

単音F0は「日常録音でも補助特徴として使える」水準ですが、多重音ではF0列だけから正確な音符イベント、offset、楽器分離、和音内の欠落基音を安定復元するのは未解決です。

**設計示唆**

F0推定は採譜本体ではなく、信頼度・候補音高・歌/単旋律モードの補助に使う。多重音ではBasic Pitch/MT3/Transkun系の多出力AMTを主にし、CREPE/PESTOは「単旋律らしさ判定」「主旋律抽出」「音程成分選択」の補助に回すべきです。

## 3. オンセット検出・ビートトラッキング

**確定知見**

Onsets and Framesは、piano onsetが振幅ピークと広帯域スペクトルを持つため検出しやすく、frame推定をonset情報に条件づけるのが有効と説明しています。https://arxiv.org/abs/1710.11153

一方、ソフトアタック楽器、歌、弦、管、残響の強い部屋では「音が始まった時刻」が物理的にも曖昧です。madmom系のRNN onset/beat実装は実用上の標準的ベースラインで、関連論文群を含みます。madmom論文 DOI: https://doi.org/10.1145/2964284.2973795

**設計示唆**

波形から直接「正しいonset」を1点で決めるUIにしない。候補onsetにconfidenceと許容幅を持たせ、譜面化層で拍・拍子・量子化と統合する。日常録音ではビート推定を先に固定しすぎると、rubatoや弾き語りで壊れます。

## 4. 前処理: ノイズ抑制・残響・正規化

**確定知見**

RNNoiseはRNNベースのリアルタイムnoise suppressionで、音声向けです。https://arxiv.org/abs/1709.08243 / https://github.com/xiph/rnnoise

DeepFilterNet/DeepFilterNet2は48kHz full-bandの低計算量speech enhancementで、DeepFilterNet DOI: https://doi.org/10.1109/ICASSP43922.2022.9747055、DeepFilterNet2 DOI: https://doi.org/10.1109/IWAENC53105.2022.9914782

AMT固有では、Kim & Lerch 2024が白色ノイズをMAESTROに注入し、clean baseline F1 96.7/94.5から、12dB SNRで約5% relative drop、9dBで約10% relative dropを報告。ノイズ混合学習は低SNRで改善するが、cleanを完全に捨てるとclean環境で悪化します。https://arxiv.org/abs/2410.14122

Edwards et al. 2024は、APTモデルが学習データの音響特性に過適合しうること、EQ・環境ノイズ・pitch shift・reverb augmentationを使った頑健化を報告。特にpitch shiftとreverbがMAPS外部評価でF1をそれぞれ3.1%, 2.8%改善、背景ノイズは条件により無効または悪化としています。DOI: https://doi.org/10.1109/LSP.2024.3363646 / https://arxiv.org/abs/2402.01424

**設計示唆**

推奨前処理は、`decode -> peak/true-peak診断 -> DC除去 -> loudness/RMS正規化 -> 任意の軽いdenoise -> CQT/log-mel抽出`。ただしRNNoise/DeepFilterNetは音声向けなので、音楽の倍音・減衰・弱音onsetを消す可能性があります。採譜では「常時denoise」ではなく、原音経路とdenoise経路を両方推論し、confidenceが上がる場合だけ採用する構成がよいです。

## 5. 音質診断の自動化

**実装可能**

F-002受入条件として実装しやすい項目:

| 診断 | 実装 | 出力 |
|---|---|---|
| クリッピング | sample peakが0dBFS近傍に連続、同値plateau、true peak | `clip_likely`, 区間 |
| SNR推定 | 無音/低エネルギー区間のnoise floor推定、または分位点ベース | `estimated_snr_db` |
| 帯域不足 | 長時間平均スペクトルで高域ロールオフ、codec lowpass検出 | `bandwidth_hz` |
| ラウドネス | ITU-R BS.1770/EBU R128 integrated loudness, LRA, true peak | `lufs`, `lra`, `dbtp` |

EBU R128/ITU-R BS.1770はラウドネス・true peakの実装標準として使えます。https://tech.ebu.ch/loudness/ / https://tech.ebu.ch/publications/r128

PEAQ/ITU-R BS.1387は客観的音質評価の標準ですが、参照音源が必要な用途が中心で、ユーザー録音の受入診断には重いです。https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1387-2-202305-I!!TOC-HTM-E.htm

## 6. 波形可視化

**確定知見**

大規模波形は全サンプル描画ではなく、min/max peakを事前計算してズームごとに読む方式が標準です。BBC `audiowaveform` は、Nサンプルごとに最小/最大ペアを作り、`.dat`/JSONとして保存し、ズームや時間範囲指定で描画できます。https://github.com/bbc/audiowaveform

ブラウザでは `wavesurfer.js` が実用標準の一つで、長尺音声では事前計算peaksを読む設計が推奨されています。https://wavesurfer.xyz/docs / https://wavesurfer.xyz/faq/

**設計示唆**

60fpsを狙うなら、波形はpeak pyramid、spectrogramはタイル化、譜面は同じ `time -> x` 変換を共有する。Canvas 2Dで十分な範囲から始め、長尺・多レイヤー・ズーム連続操作だけWebGL/WebGPUへ逃がすのが現実的です。

## 7. サンプリング・コーデック

**設計判断**

内部保存は原音保持。解析用にはモデル別に高品質resampleします。

推奨受入:

- WAV/FLAC: 16/24-bit PCM, 32-bit float, 44.1k/48kHzを標準
- m4a/aac/mp3/opus/ogg: 受けるが「lossy」警告とconfidence減点
- 16kHz: 音声/歌F0やMT3系には可。ただし高域倍音・onset診断には不利
- 96kHz以上: 保存は可、解析は44.1/48kHzへdownsampleで十分

Web Audio APIの `decodeAudioData()` はAudioContextのsample rateへresampleされるため、解析で厳密なサンプルレート管理が必要ならブラウザ任せにしない方がよいです。https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData

## 推奨アーキテクチャ

1. **受入診断層**: format/sample rate/bit depth/clip/SNR/bandwidth/loudnessを算出し、低品質なら理由付きで警告。
2. **前処理層**: 原音、正規化のみ、denoiseありの複数経路を作る。
3. **耳層 NF-050**: CQT/HCQT/log-mel、F0補助、multipitch/onset/offset confidenceを生成。
4. **記譜層**: beat/grid推定、音符イベント統合、楽器非依存のpitch-first MIDI、必要に応じて声部/楽器推定。
5. **可視化層**: peak pyramid + spectrogram tiles + MIDI/譜面を単一時間軸で同期。

**未解決として扱うべきこと**: 雑音混じり日常録音から、任意楽器・任意環境・複数音源を人間並みに完全採譜する汎用モデルはまだ確立していません。現実的には、音質診断とconfidenceを前面に出し、「絶対音感エミュレータ」はまず pitch/onset evidence extractor として設計するのが堅いです。


