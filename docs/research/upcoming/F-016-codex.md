# 強弱(ベロシティ)推定と譜面の強弱記号化 調査レポート（codex=論文・WEB担当、失敗例重視）

調査日: 2026-07-21
対象: 音声/MIDIからの velocity・dynamics 推定と、楽譜の強弱記号（pp/p/mp/mf/f/ff・crescendo/decrescendo hairpin）への離散化
分担: codex担当（論文＋WEB、失敗例を最大限）
方針: 実在ソースのみ・URL併記・憶測なし。英語・中国語中心。arXiv/IEEE(DOI)/GitHub/MAESTRO/MuseScore 等の一次情報を優先。

> 注: 本文中の arXiv:2508.07757（Score-Informed Transformer for Refining MIDI Velocity）と arXiv:2203.16294（Acoustics-specific Piano Velocity Estimation）は WebFetch で実在・タイトル・主題を確認済み。MAESTRO / Onsets and Frames / Kong et al. HPT / ByteDance実装 / EBU R128 / MuseScore Hairpins も既知の一次ソース。

---

## 結論

採譜パイプラインで `MIDI velocity → pp/p/mp/mf/f/ff` や `velocity slope → crescendo/decrescendo` を自動変換する機能は、**絶対閾値方式にすると高確率で破綻する**。理由は、MIDI velocity 自体が「録音上の音量」でも「楽譜上の強弱」でもなく、演奏装置・音源・楽器・部屋・マイク・録音ゲイン・正規化・音域・奏法に依存する**相対的な演奏制御値**だからである。

特に重要なのは、Onsets and Frames 論文自身が「velocity には絶対的意味がない」として、評価時に推定 velocity を線形回帰でスケール・オフセット補正してから比較している点。研究評価の段階ですでに「生の絶対 velocity」は信頼されていない。([arXiv:1710.11153](https://arxiv.org/abs/1710.11153))

---

## 1. 推定手法と精度（MAESTRO 等）

| 系統 | 方法 | データ/評価 | velocity関連の代表値 | 実務上の読み方 |
|---|---|---|---|---|
| MAESTRO | Yamaha Disklavier録音のaudio/MIDIペア | v3: 約198.7h, 1276演奏, 約3ms整列, key velocity/pedalあり | データセット自体は高品質な教師信号 | 基本はクラシック独奏ピアノ/特定収録条件寄り。汎化保証ではない。([MAESTRO](https://magenta.withgoogle.com/datasets/maestro)) |
| Onsets and Frames | log-mel + CNN/LSTMでonset/frame/offset/velocityを推定 | MAPS/MAESTRO系 | MAPSで Note w/ offset & velocity F1 ≈ 35.39。velocityは曲内最大値で正規化、推論時は `80*v+10` という任意マッピング | velocity出力は「自然な再生」目的に近く、絶対強弱記号へ直接使う設計ではない。([arXiv:1710.11153](https://arxiv.org/abs/1710.11153)) |
| MAESTRO版 Onsets and Frames | MAESTROで学習 | MAESTRO test | Note w/ offset & velocity F1 ≈ 77.54 | velocity込みにすると評価は大きく厳しくなる。([arXiv:1810.12247](https://arxiv.org/abs/1810.12247)) |
| Kong et al. High-res Piano Transcription (HPT) | onset/offset時刻回帰 + velocity submodule | MAESTRO | Note F1 ≈ 96.72; Note w/ offset & velocity F1 ≈ 80.92 | pitch/onsetは高精度でも、velocity込み評価ではまだ落ちる。([arXiv:2010.01815](https://arxiv.org/abs/2010.01815)) |
| ByteDance実装 | HPT PyTorch実装 | MAESTRO v2 test | velocity_mae ≈ 0.027（normalized、概算で約 3.4/127） | 同一データ分布内では小さいが、正規化尺度でのMAE。楽譜強弱の正解率ではない。([GitHub bytedance/piano_transcription](https://github.com/bytedance/piano_transcription)) |
| Score-informed velocity refinement | 既存AMTのvelocityをスコア情報で補正 | MAESTRO/SMD/MAPS | MAESTRO test: HPT MAE ≈ 4.6, Score-HPT ≈ 3.9-4.0; SMDでは HPT ≈ 10.0, Score-HPT ≈ 8.0 | 外部データ（SMD等）ではMAEが大きく悪化。スコア情報で補正しても完全ではない。([arXiv:2508.07757](https://arxiv.org/abs/2508.07757)) |
| Acoustics-specific velocity | 楽器・音響環境ごとの適応をモデル化（audio+aligned score→velocity） | 複数環境 | 環境非依存AMTより改善 | 楽器・部屋・マイクごとに velocity マッピングが違うことを明示的に扱う必要がある。([arXiv:2203.16294](https://arxiv.org/abs/2203.16294)) |

要点: pitch/onset の F1 が 96 を超えても、**velocity 込みの評価は 77〜81 程度に落ちる**。さらに学習分布外（SMD等）に出すと velocity MAE は 2 倍以上に悪化する。つまり velocity は「AMTの中でも最も汎化が弱い成分」。

---

## 2. 失敗モード一覧（録音レベル/音色でベロシティが不正確）

| 失敗モード | なぜ起きるか | 典型的な誤出力 |
|---|---|---|
| 録音ゲイン依存 | 同じ演奏でも録音レベルを上げれば波形振幅/LUFSは上がるが、MIDI velocityは変わらない | 全体が `f/ff` に寄る、または正規化後に局所差が潰れる |
| 正規化依存 | ピーク正規化/LUFS正規化/コンプレッションで音量分布が変わる。EBU R128/LUFSは番組全体の知覚ラウドネス指標でありnote velocityではない | ppのはずの箇所がmp、クライマックスがmf止まり ([EBU R128](https://tech.ebu.ch/publications/r128), [ITU-R BS.1770](https://www.itu.int/rec/R-REC-BS.1770/en)) |
| 楽器・音源依存 | MIDI仕様はNote On velocityを 0-127 とするが、velocityが実際の音量へどう変換されるかは機器依存。「velocity effect on volume is not defined」 | 同じvelocity 80がピアノAではmf、音源Bではf ([MIDI.org](https://midi.org/community/midi-specifications/how-do-controllers-calculate-velocity)) |
| 音域依存 | 低音は倍音・残響・持続が強く、高音は減衰が早い。同じvelocityでも知覚ラウドネスが違う | 左手伴奏が過大評価、右手旋律が過小評価 |
| 和音/音数依存 | 単音velocityは小さくても、同時発音数が多いと全体ラウドネスは大きい | 和音だけ `f`、旋律単音が `p` になり音楽的意図と逆転 |
| マイク距離/部屋鳴り | 直接音と残響音の比率が変わる。楽器・環境ごとにMIDIパラメータマッピングが違い、演奏者も環境に適応する | 残響の長い部屋でdecrescendoを過検出 ([arXiv:2203.16294](https://arxiv.org/abs/2203.16294)) |
| コンプレッサ/リミッタ | 強音のピークが抑えられ、弱音が持ち上がる | ダイナミックレンジが狭くなり、全部 `mp/mf` |
| AMTのnote誤り伝播 | velocity推定はonset位置に強く依存。onsetがズレるとアタック情報を取り逃がす | velocityが低く出る、hairpin開始位置がズレる |
| ペダル/残響混入 | sustain中の減衰音を新しい強音と誤解する | 実際は保持音なのにcrescendo扱い |
| 絶対閾値の破綻 | `0-30=pp`, `31-50=p` のような固定表は録音/楽器/曲ごとの基準を無視 | 弱い演奏だと全部 `p/pp`、強い演奏だと全部 `f/ff` |
| hairpin過検出 | velocity列は演奏表情・音型・アクセント・旋律交代で局所的に上下。単純な傾き検出はノイズに弱い | 1小節ごとに無意味な `< >` が乱発 |
| notation過密 | velocityの微細変化を全部記譜すると読めない譜面になる | `p < mf > mp < f` のような過剰表記 |

---

## 3. なぜ絶対velocityは pp/p/mp/mf/f/ff に対応しないか

楽譜の強弱記号は物理音量の絶対値ではなく「文脈内での演奏指示」である。中国語の音楽用語資料でも、pp/p/mp/mf/f/ff は「相対变化」であり特定音量レベルではないと説明されている。([autopiano.cn 力度记号](https://www.autopiano.cn/toolbox/musical_term))

Onsets and Frames は velocity label を曲内最大 velocity で割って正規化し、推論時の MIDI velocity 変換を "arbitrary" と明記している。さらに評価でも推定 velocity をスケール・オフセット補正してから、正規化後 0.1 以内かを見る方式。これは研究側も「velocity 64 = mf」のような固定対応を前提にしていないことを示す。([arXiv:1710.11153](https://arxiv.org/abs/1710.11153))

---

## 4. crescendo/hairpin 検出の追加リスク

MuseScore のドキュメントでは hairpin は crescendo/decrescendo を示すが、再生上も前後の dynamic mark や velocity change に依存すると説明されている。つまり notation 上の hairpin は「連続的な音量傾斜」だけでなく、開始/終了の強弱目標・フレーズ・声部・奏法に依存する。([MuseScore Hairpins](https://musescore.org/en/handbook/2/hairpins))

| 入力現象 | 誤判定 |
|---|---|
| 旋律が低音から高音へ移る | 音色差をcrescendoと誤認 |
| 和音数が増える | note density増加をvelocity増加と誤認 |
| アクセント列 | 短いhairpinを乱発 |
| ペダルで残響が増える | decrescendoが検出不能 |
| 途中で伴奏が入る | 本来の旋律dynamicではなく全体ラウドネスに引っ張られる |

---

## 5. ベストプラクティス

| 推奨 | 内容 |
|---|---|
| 絶対閾値を使わない | `velocity >= 96 => f` のような表は避ける。少なくとも曲内・楽器内・声部内の分位点で扱う |
| piece-level normalization | 曲ごとに中央値・IQR・分位点で正規化し、外れ値と録音ゲインの影響を減らす |
| voice/context別に推定 | 右手旋律/左手伴奏/ベース/内声を分ける。全ノート一括の平均velocityは危険 |
| loudness + note density併用 | MIDI velocityだけでなく短時間LUFS/RMS・同時発音数・音域・ペダル状態を見る（ただしLUFSもvelocityの代替ではない） |
| smoothingを入れる | note単位の生velocityではなく拍/小節/フレーズ単位のロバスト平滑化を使う |
| hairpinは高閾値・低頻度 | 長さ・単調性・前後dynamic差・フレーズ境界を満たす場合だけ出す |
| human-in-the-loop | 自動出力は「候補」とし、楽譜UIで pp-p-mp-mf-f-ff と hairpin を編集可能にする |
| calibration UI | ユーザーに「この曲の基準dynamic」を数箇所指定させ全体を再マップ |
| confidenceを出す | velocity推定MAE・録音品質・クリッピング・圧縮・AMT confidenceから「dynamic信頼度」を付与 |
| score-informed補正 | スコアが利用可能なら score-informed refinement で velocity MAE を改善（完全ではない） ([arXiv:2508.07757](https://arxiv.org/abs/2508.07757)) |

---

## 実装方針の現実解

1. AMTでnote/onset/offset/velocity/pedalを推定する。
2. 曲・パート・音域ごとにvelocityをロバスト正規化する。
3. 短時間loudness・note density・音域・声部重要度を加えて「relative dynamic curve」を作る。
4. dynamic記号は分位点ベースで少数だけ配置する。
5. hairpinは十分長い単調傾向かつ前後dynamic目標が明確な場合だけ出す。
6. 出力は確信度付き候補にし、人間が最終決定する。

最も避けるべき設計は、`MIDI velocity 0-127` を6区間に固定分割して `pp/p/mp/mf/f/ff` を直接出す方式。これは研究評価・MIDI仕様・楽譜記法のどの観点からも根拠が弱い。

---

## 参考URL（実在確認済み）

- MAESTRO Dataset: https://magenta.withgoogle.com/datasets/maestro
- Onsets and Frames arXiv: https://arxiv.org/abs/1710.11153
- Onsets and Frames + MAESTRO (Wave2Midi2Wave) arXiv: https://arxiv.org/abs/1810.12247
- High-resolution Piano Transcription (Kong et al.) arXiv: https://arxiv.org/abs/2010.01815
- ByteDance piano_transcription GitHub: https://github.com/bytedance/piano_transcription
- Acoustics-specific Piano Velocity Estimation arXiv: https://arxiv.org/abs/2203.16294 （WebFetch確認済み）
- Score-Informed Transformer for Refining MIDI Velocity arXiv: https://arxiv.org/abs/2508.07757 （WebFetch確認済み）
- EBU R128 (Loudness): https://tech.ebu.ch/publications/r128
- ITU-R BS.1770 (Loudness measurement): https://www.itu.int/rec/R-REC-BS.1770/en
- MuseScore Hairpins: https://musescore.org/en/handbook/2/hairpins
- MIDI.org velocity discussion: https://midi.org/community/midi-specifications/how-do-controllers-calculate-velocity
- 中文力度记号参考: https://www.autopiano.cn/toolbox/musical_term
