# ギターTAB譜自動生成・運指最適化 調査レポート（codex=論文・規格担当）

調査日: 2026-07-20
対象: automatic guitar tablature transcription / MIDI-to-tab arrangement / fingering optimization

## 1. audio → guitar tablature の研究系譜

| 論文 | 著者・年 | 手法 | データセット | 主な評価 |
|---|---:|---|---|---|
| *Automatic Transcription of Guitar Chords and Fingering From Audio* | Ana M. Barbancho, Anssi Klapuri, Lorenzo J. Tardón, Isabel Barbancho, 2012 | 複数F0推定のsalienceを観測量、330種類のコード運指配置をHMM隠れ状態として推定 | 独自録音系。詳細ライセンス未確認 | コード/運指分類。DOI: [10.1109/TASL.2011.2174227](https://doi.org/10.1109/TASL.2011.2174227) |
| *Inharmonicity-Based Method for the Automatic Generation of Guitar Tablature* | Isabel Barbancho et al., 2012 | 弦ごとの非調和性から音高とstring/fretを推定。和音も対象 | RWC instruments + 独自録音 | string/fret推定。DOI: [10.1109/TASL.2012.2191281](https://doi.org/10.1109/TASL.2012.2191281) |
| *Audio-based guitar tablature transcription using multipitch analysis and playability constraints* | Yazawa, Sakaue, Nagira, Itoyama, Okuno, 2013 | LHAによるmultipitch推定 + 演奏可能な押弦構成の列挙 + DPで時間連続性最適化 | MIDI由来の合成ギター音 | MPE F-measureが平均5.9ポイント改善、playable tabを出力。DOI: [10.1109/ICASSP.2013.6637636](https://doi.org/10.1109/ICASSP.2013.6637636) |
| *Automatic transcription of guitar tablature from audio signals in accordance with player's proficiency* | Yazawa, Itoyama, Okuno, 2014 | multipitch推定 + DP。熟練度パラメータで音響再現性と運指容易性の重みを調整 | 合成ギター音 | multipitch精度と運指容易性。DOI: [10.1109/ICASSP.2014.6854175](https://doi.org/10.1109/ICASSP.2014.6854175) |
| *Automatic tablature transcription of electric guitar recordings by estimation of score- and instrument-related parameters* | Kehling, Abeßer, Dittmar, Schuller, 2014 | onset/offset、multipitch、string、奏法分類を組み合わせる電気ギター解析 | 独自/実験録音。未確認 | onset/offset/MPE 98%、string 82%、plucking 93%、expression 83% と報告 |
| *Guitar Tablature Estimation with a Convolutional Neural Network* / TabCNN | Andrew Wiggins, Youngmoo Kim, 2019 | CQT入力CNNでaudio→6弦ごとのfret分類を直接推定。MPEと運指割当を結合 | GuitarSet mic recordings | pitch/tab precision, recall, F1, TDR。DOI: [10.5281/zenodo.3527800](https://doi.org/10.5281/zenodo.3527800) |
| *A data-driven methodology for considering feasibility and pairwise likelihood...* | Cwitkowitz, Driedger, Duan, 2022 | TabCNN系の出力に、同時発生しにくいstring/fretペアを抑えるinhibition objectiveを追加 | DadaGP由来の共起統計 + GuitarSet系 | duplicate-pitch errors低減、feasibility/likelihood改善 |
| *FretNet: Continuous-Valued Pitch Contour Streaming for Polyphonic Guitar Tablature Transcription* | Cwitkowitz, Hirvonen, Klapuri, 2023 | TabCNN系を拡張。Harmonic CQT、discrete tab、pitch deviation、onset headを同時推定 | GuitarSet | frame/note MPE、tab推定、連続ピッチ解像度。DOI: [10.1109/ICASSP49357.2023.10094825](https://doi.org/10.1109/ICASSP49357.2023.10094825), arXiv: [2212.03023](https://arxiv.org/abs/2212.03023) |
| *SynthTab: Leveraging Synthesized Data for Guitar Tablature Transcription* | Zang, Zhong, Cwitkowitz, Duan, 2024 | DadaGP由来TABをstring-awareに合成し、TabCNN/TabCNN+の事前学習に利用 | SynthTab + GuitarSet/IDMT/EGDB | cross-dataset Tab F1改善。arXiv: [2309.09085](https://arxiv.org/abs/2309.09085) |
| *High Resolution Guitar Transcription via Domain Adaptation* | Riley, Edwards, Dixon, 2024 | ピアノ高解像度転写モデル/score-audio alignmentをギターへ適応 | GuitarSet + score-audio pairs | GuitarSetでSOTAと記載。arXiv: [2402.15258](https://arxiv.org/abs/2402.15258) |
| *GAPS: A Large and Diverse Classical Guitar Dataset and Benchmark Transcription Model* | Riley, Guo, Edwards, Dixon, 2024 | 14時間超の実演奏・スコア対応 classical guitar データセット + benchmark | GAPS, GuitarSet | supervised/zero-shot GuitarSetでSOTAと記載。arXiv: [2408.08653](https://arxiv.org/abs/2408.08653) |

## 2. MIDI/音高列 → 弦・フレット割当のアルゴリズム

代表的な定式化は「各時刻/音符の候補string-fret配置をノード、隣接時刻の配置間をエッジとする層状グラフの最短路」。

| 系統 | 代表研究 | 要点 |
|---|---|---|
| グラフ最短路 / Viterbi / DP | Sayegh, *Fingering for string instruments with the optimum path paradigm*, 1989 | string instrumentsの運指を候補状態列の最適経路として扱う古典的枠組み。CiNii: [link](https://cir.nii.ac.jp/crid/1574231876386494720) |
| DP | Itoh & Hayashida, *Optimization for Guitar Fingering on Single Notes*, 2004 | 単旋律を多段決定問題化。手移動をフレット・弦方向のマンハッタン距離で評価。DOI: [10.1541/ieejeiss.124.1396](https://doi.org/10.1541/ieejeiss.124.1396) |
| DP + 学習コスト | Radisavljevic & Driessen, *Path Difference Learning for Guitar Fingering Problem*, 2004 | published tablatureからコスト重みを学習。static cost + transition costをDPで最小化 |
| TAB生成システム | Miura et al., *Constructing a system for finger-position determination and tablature generation...*, 2004 | 初心者向けに演奏負担を最小化し、S2TでTAB出力。DOI: [10.1002/scj.10609](https://doi.org/10.1002/scj.10609) |
| Genetic Algorithm | Tuohy & Potter, *A Genetic Algorithm for the Automatic Generation of Playable Guitar Tablature*, 2005 | fitness functionでplayabilityを評価。商用ソフトより破綻しにくいと主張。ICMC full text: [link](https://hdl.handle.net/2027/spo.bbp2372.2005.013) |
| Input-output HMM | Hori, Kameoka, Sagayama, *Input-Output HMM Applied to Automatic Arrangement for Guitars*, 2013 | 左手フォームを隠れ状態、楽譜音列を観測列としてViterbi復号。初心者向けHMMパラメータを手設定。DOI: [10.11185/imt.8.477](https://doi.org/10.11185/imt.8.477) |
| CNN/ML | Kaliakatsos-Papakostas et al., *A Machine Learning Approach for MIDI to Guitar Tablature Conversion*, 2022 | MIDI pitch + 過去4フレームTABを入力し、6x25 fretboard確率を出力。DOI: [10.5281/zenodo.6573024](https://doi.org/10.5281/zenodo.6573024) |
| Masked LM | Edwards, Riley, Sarmento, Dixon, *MIDI-to-Tab*, 2024 | BART系Transformerでstring tokenをマスク予測。DadaGP事前学習 + curated professional guitar subsetで微調整。arXiv: [2408.05024](https://arxiv.org/abs/2408.05024) |
| Encoder-decoder Transformer | Hamberger et al., *Fretting-Transformer*, 2025 | T5でMIDI→TABをsymbolic translation化。tuning/capo条件も扱う。arXiv: [2506.14223](https://arxiv.org/abs/2506.14223) |

定石のコスト関数/制約:

- ハンドポジション移動: 連続音・連続和音間の平均フレット/代表フレット移動量
- フレットスパン: 同時に押さえる最低・最高フレット差、指の到達範囲
- 開放弦: 押弦不要なので報酬にする研究が多い一方、音色・持続・ポジション一貫性のため過剰優先は避ける
- 弦移動: 隣接音の弦変更コスト、同一弦/近接弦の継続性
- 演奏可能性制約: 6弦に同時1音、同一弦同時多音不可、手指数、バレー、フレット範囲、チューニング/カポ
- 音楽的自然さ: 低音は低い弦、高音は高い弦、和音フォームの慣用性、音色の一貫性
- 奏者レベル: Yazawa 2014やHori 2013では初心者向けに難度重みを調整

## 3. playability の定量化

- **Tab precision / recall / F1**: string-fret組み合わせが正しいか。TabCNN系の基本指標
- **Pitch precision / recall / F1**: string-fretを無視して音高が合っているか
- **TDR (Tablature Disambiguation Rate)**: 正しく検出されたpitchのうち、string-fretも正しく割り当てられた割合。TabCNN論文と派生研究で使用
- **duplicate-pitch errors / inhibition loss**: 同じpitchを複数弦に重複推定する不自然さ。Cwitkowitz 2022系
- **playable/unplayable制約違反率**: 同時押弦不能、過大スパン、弦衝突などの違反数
- **人間評価**: Tuohy & Potterはpublished tablatureや商用ソフトとの主観比較、MIDI-to-Tab系は熟練ギタリスト評価を実施と報告（詳細プロトコルは本文未確認箇所あり）
- **一致率だけでは不十分**: published tabと異なっても演奏しやすい代替運指が存在するため、ground truth一致率はplayabilityの代理指標に留まる

## 4. TAB譜のリズム/音価表記

- ASCII TAB単体は伝統的に弦線とフレット番号中心で、正確な音価表現が弱い
- MusicXML公式チュートリアルは、TAB表示ではリズム情報が隠される場合があっても、MusicXML内部ではdurationを指定する必要があると説明。参照: [MusicXML Tablature tutorial](https://w3c.github.io/musicxml/tutorial/tablature/)
- MEI stringtabでは、`tabGrp` のdurationを視覚的なリズム記号 `tabDurSym` で表せる。参照: [MEI String Tablature](https://music-encoding.org/guidelines/dev/mei-neumes/content/tablature.html)
- Guitar ProやMuseScoreでは、符幹つきTAB、標準譜併記、声部別休符/音価管理で対応。Guitar Pro内部形式の完全な公式公開仕様は未確認

## 5. MusicXML / MEI / Guitar Pro のTAB表現

| 形式 | TAB表現 |
|---|---|
| MusicXML 4.0 | `notations/technical/fret` と `string` で各noteのフレット・弦を表す。`staff-details` に `staff-lines`, `staff-tuning`, `capo`, `show-frets`。公式: [`string`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/string/), [`staff-details`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/staff-details/) |
| MEI | `staffDef notationtype="tab.guitar"`、`lines="6"`、`note tab.course="..." tab.fret="..."`。開放弦は `tab.fret="0"`。公式: [MEI tablature](https://music-encoding.org/guidelines/dev/mei-neumes/content/tablature.html) |
| Guitar Pro | DadaGPがGP3/GP4/GP5をtoken化し、PyGuitarPro等が読み書き可能。公式ファイル仕様・ライセンスは未確認。DadaGP repoのencoder/decoderはMITだが、データセット本体は研究目的で要申請。参照: [DadaGP GitHub](https://github.com/dada-bots/dadaGP) |

## 6. 評価用データセットとライセンス

| データセット | 内容 | ライセンス/利用条件 |
|---|---|---|
| GuitarSet | 360 excerpts、6 players、30 lead sheets、hexaphonic pickup + mic、JAMS注釈（pitch contour/string/fret/chord/beat/style） | CC BY 4.0。DOI: [10.5281/zenodo.3371780](https://doi.org/10.5281/zenodo.3371780) |
| DadaGP | 26,181 GuitarPro songs、739 genres、tokenized format + encoder/decoder | コードはMIT。データ本体は研究目的で要申請。著作権由来の制約に注意。論文: [ISMIR 2021 PDF](https://archives.ismir.net/ismir2021/paper/000076.pdf) |
| SynthTab | DadaGP一部から約6,700時間、15,211 tracks、23 timbresを合成 | 明示ライセンス未確認。arXiv: [2309.09085](https://arxiv.org/abs/2309.09085), site: [synthtab.dev](https://synthtab.dev/) |
| EGFxSet | 8,970 recordings、標準チューニング電気ギター全音 + 12 effects、string/fret/effect注釈 | HF mirrorはCC BY 4.0記載、一次Zenodoライセンスは要再確認。site: [egfxset.github.io](https://egfxset.github.io/) |
| GAPS | classical guitar、14時間、200人超、audio-score aligned | ライセンス未確認。arXiv: [2408.08653](https://arxiv.org/abs/2408.08653) |
| IDMT/EGDB/EGSet12 | 電気ギター/エフェクト/評価用としてTabCNN派生で使用 | 個別ライセンス未確認 |

## 7. 中国語文献について（正直な報告）

公開Web検索では、CNKI/万方に限定した「吉他 六线谱 自动生成 运指」系の一次情報は十分に確認できなかった。確認できた中国語圏関連は、MIDI-to-Tabの中国語抄録ページや、琵琶向けのPipaSet/TEASなど近接領域に留まる。ギターTAB自動生成そのものの中国語大学論文・CNKI文献は**未確認**。
