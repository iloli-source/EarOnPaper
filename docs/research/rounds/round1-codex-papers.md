> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

# AI採譜プロジェクト学術調査

## 結論サマリ

2024-2026時点の研究潮流は、単なる `audio -> MIDI` ではなく、`audio/performance MIDI -> 拍節構造・声部・譜割り・譜面記法` までを評価対象にする方向へ移っています。特に重要なのは以下です。

- 拍・小節推定は、`Beat This!` や `BeatNet+` により、DBN/particle filtering依存を減らす方向と、リアルタイム堅牢化の方向が並走。
- リズム量子化・整譜は、`MIDI2ScoreTransformer` と `piano_svsep` が、演奏MIDI後段の「読める譜面化」に近いSOTA。
- A2S直接変換は、2024年に `Transformer A2S`、`Hierarchical Decoding A2S` が出て、2026年MIREXで独立タスク化。まだ制約付きクラシック/ピアノ/弦楽四重奏中心。
- 評価は `Note F1` だけでは不十分で、`MUSTER`、`MV2H`、`CER/WER/LER on **kern`、人間評価相関指標が必要。
- 難易度別アレンジは、2022-2025に `playing-level conversion`、`notation-to-notation rearrangement`、`piano reduction` が進展。ただし商用利用できるコード・データは少ない。
- インド音楽は、Sargam/Bhatkhande風の離散譜ではなく、ガマカを含むピッチ曲線の記述的転写が中心。拍節は tala 適応が課題。
- 中国語圏は、CNKI相当では簡譜・節拍認識・教育応用が多く、国際会議では CUHK/中国系研究者が AMT/A2S Transformer、MusicXML、五声音階・古箏などを扱う流れがある。

---

## 1. リズム量子化・拍子推定・整譜の最新研究

### Beat / Downbeat Tracking

**Beat This! Accurate Beat Tracking Without DBN Postprocessing**  
Francesco Foscarin, Jan Schlüter, Gerhard Widmer, ISMIR 2024. arXiv:2407.21658, DOI: 10.48550/arXiv.2407.21658。  
DBN後処理を使わず、畳み込みとTransformerを組み合わせた beat/downbeat tracker。多ジャンル、拍子変化、クラシックのテンポ揺れに対応するため複数データセットで学習し、F1でSOTAを主張。ただし連続性指標では弱さが残るため、譜面化の前段では単独採用より後段の小節整合チェックが必要です。コード・重みはMITで公開され、商用利用しやすい部類です。([arxiv.org](https://arxiv.org/abs/2407.21658)) ([github.com](https://github.com/CPJKU/beat_this))

**BeatNet+: Real-Time Rhythm Analysis for Diverse Music Audio**  
Mojtaba Heydari, Zhiyao Duan, TISMIR 2024. DOI: 10.5334/tismir.198。  
BeatNetを拡張し、リアルタイム beat/downbeat/meter tracking を、歌声単独・非打楽器的音源にも適応する研究。補助ブランチ学習、guided fine-tuning、auxiliary-freezingで、打楽器成分の少ない音源にも頑健化しています。採譜プロジェクトでは「歌・弦・ソロ楽器の拍推定」に重要です。([transactions.ismir.net](https://transactions.ismir.net/articles/10.5334/tismir.198))

**Revisiting Meter Tracking in Carnatic Music using Deep Learning Approaches**  
Satyajeet Prabhu, 2025. arXiv:2509.11241, DOI: 10.48550/arXiv.2509.11241。  
Carnatic musicのtalaに対して、TCNとBeat This!を評価。既製SOTAはそのままではDBN baselineを常に超えないが、Carnaticデータでfine-tuningすると同等または上回る、という結果。西洋拍節モデルをそのまま使う危険性を示す重要研究です。([arxiv.org](https://arxiv.org/abs/2509.11241))

### Rhythm Quantization / Performance MIDI-to-Score

**End-to-end Piano Performance-MIDI to Score Conversion with Transformers**  
Tim Beyer, Angela Dai, ISMIR 2024. arXiv:2410.00210, DOI: 10.48550/arXiv.2410.00210。  
演奏MIDIからMusicXML/楽譜相当への変換をSeq2Seqで解く研究。連続時刻をcompound tokenで量子化し、音価・拍節構造・譜表割当・trill・stem directionまで直接予測します。MUSTERで既存HMM/深層手法を上回ると報告。A2S本体より、現実的には `audio -> MIDI -> MIDI2ScoreTransformer` の後段として有望です。ただしGitHubにはライセンスファイルが見当たらず、商用利用は要確認です。([arxiv.org](https://arxiv.org/abs/2410.00210)) ([github.com](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer))

**Cluster and Separate: a GNN Approach to Voice and Staff Prediction for Score Engraving**  
Foscarin et al., ISMIR 2024. arXiv:2407.21030, DOI: 10.48550/arXiv.2407.21030。  
量子化済みの記号列から、声部・譜表をGNNで割り当てるscore engraving後段の研究。ホモフォニック声部、cross-staff voiceを扱う点が重要。コード・事前学習モデルはMIT公開。ただし一部評価データは非公開で完全再現性に制約があります。([arxiv.org](https://arxiv.org/abs/2407.21030)) ([github.com](https://github.com/CPJKU/piano_svsep))

---

## 2. Audio-to-Score直接変換

**A Transformer Approach for Polyphonic Audio-to-Score Transcription**  
María Alfaro-Contreras et al., ICASSP 2024. DOI: 10.1109/ICASSP48485.2024.10447162。  
音声から `**kern` 風のスコアトークン列を直接生成するA2S研究。クラシック多声・弦楽四重奏系で、MIDIではなくスコア表現を直接狙う点が重要です。MIREX 2026 A2Sの参考文献にも採用されています。 ([transactions.ismir.net](https://transactions.ismir.net/articles/10.5334/tismir.57))

**End-to-End Real-World Polyphonic Piano Audio-to-Score Transcription with Hierarchical Decoding**  
Wei Zeng, Xian He, Ye Wang, IJCAI 2024. arXiv:2405.13527, DOI: 10.24963/ijcai.2024/862 / 10.48550/arXiv.2405.13527。  
ピアノA2Sで、bar-level decoderとnote-level decoderを分け、拍子・調・小節情報と音符列を階層的に出す。合成音だけでなく人間演奏録音でfine-tuningする点が実用寄りです。([amtevaluation.github.io](https://amtevaluation.github.io/)) ([arxiv.org](https://arxiv.org/abs/2405.13527))

**AMT-CMT: A Novel Automatic Music Transcription Model Based on Cross-Modal Transformer**  
Shuhao You et al., Expert Systems with Applications, online 2026. DOI: 10.1016/j.eswa.2026.133435。  
MusicXMLを構造トークン化し、beat-depth note weightingとMoE Transformerで、直接編集可能なMusicXML生成を狙う中国語圏/中国系著者の研究。MusicNet/URMPでFrame F1、Onset F1、Onset+Offset F1の改善を報告。ただし「入力にscore priorを使う」設計は、完全blind A2Sとは分けて評価すべきです。([sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0957417426023444?utm_source=openai))

**MIREX 2026 Audio-to-Score Transcription**  
2026年にA2Sが独立タスク化。入力は音声、出力は `**kern`。評価はCER/WER/LERとMV2Hを使い、ピッチ・音価・拍節・声部・譜表情報を含む「譜面として成立する出力」を求めています。これは研究コミュニティが `audio -> MIDI` では不十分と公式に認めた動きです。([transactions.ismir.net](https://transactions.ismir.net/articles/10.5334/tismir.57))

現状の精度感としては、A2S直接変換はまだ「制約付きドメインで研究可能」段階です。商用採譜で広いジャンルを扱うなら、当面は `audio -> note events -> beat/downbeat -> quantization -> voice/staff -> MusicXML engraving` の多段構成が堅実です。

---

## 3. 評価指標: 読めて弾ける楽譜をどう測るか

**MUSTER: Music Score Transcription Error Rate**  
MusicXML同士を比較する編集距離ベースの評価群。6種類のサブ指標で譜面要素を測るため、Note F1より「楽譜品質」に近いです。Nakamuraらのcomplete transcription系研究と、Hiramatsuらのvoice/note value評価を背景にしています。([amtevaluation.github.io](https://amtevaluation.github.io/))

**MV2H**  
McLeod & Steedman, ISMIR 2018。コードMIT。  
Multi-pitch、Voice、Meter、Value、Harmonyの平均で完全採譜を評価します。MIREX 2026 A2Sでも主要指標として採用予定。MusicXML/MIDI変換にも対応しますが、MusicXMLをMIDIへ落とす過程で記譜情報が失われる点には注意。([github.com](https://github.com/apmcleod/MV2H)) ([github.com](https://github.com/apmcleod/MV2H))

**CER/WER/LER on `**kern`**  
MIREX 2026では、`**kern` の文字・語・行単位編集距離をscore qualityとして採用。WERは音価とピッチが同時に合うか、LERは複数声部・複数楽器の整列が合うかに効きます。([transactions.ismir.net](https://transactions.ismir.net/articles/10.5334/tismir.57))

**Perceptual Validity Metrics**  
Ycart et al., TISMIR 2020. DOI: 10.5334/tismir.57。  
人間の聴取評価と従来Note F1の相関を調べ、リズム・テンポ・拍子が人間評価に強く効くことを示しました。実務では「音高F1は高いが、読めない譜面」を弾く前に弾けるか評価するため、Note F1だけでは足りません。([transactions.ismir.net](https://transactions.ismir.net/articles/10.5334/tismir.57))

推奨評価セットは、`Note F1 + Onset/Offset F1 + beat/downbeat F1 + MUSTER + MV2H + MusicXML validity + 人間評価` です。商用採譜ではさらに「小節ごとの拍数整合」「タイ/休符過剰」「譜表跨ぎ」「最短音価の過密度」「演奏難易度」を独自指標化する必要があります。

---

## 4. 難易度別アレンジ生成・簡易化

**Music Translation: Generating Piano Arrangements in Different Playing Levels**  
Matan Gover, Oded Zewi, ISMIR 2022. DOI: 10.5281/zenodo.7316588。  
難易度変換を「同じ曲の別レベル譜への翻訳」として定式化。phrase単位の並列データを作り、専門家評価に近い自動指標MuTEも提案。難易度別採譜の基礎研究として重要です。([zenodo.org](https://zenodo.org/records/7316588))

**Piano score rearrangement into multiple difficulty levels via notation-to-notation approach**  
Masahiro Suzuki, EURASIP JASMP 2023. DOI: 10.1186/s13636-023-00321-7。  
MIDI相当ではなく、記譜トークンを直接扱うnotation-to-notation変換。4段階の商用品質ポップピアノ譜を使い、MEGAモデルで任意難易度へ変換。アーティキュレーション等も扱えるため、採譜後の簡易化にはこちらの方向が近いです。([link.springer.com](https://link.springer.com/article/10.1186/s13636-023-00321-7))

**Towards Practical Automatic Piano Reduction using BERT with Semi-supervised Learning**  
Wong et al., 2025 preprint. arXiv:2512.21324, DOI: 10.48550/arXiv.2512.21324。  
オーケストラ/アンサンブルからピアノ譜へのreductionを半教師ありで扱う流れ。公開実装・データの商用可否は不透明です。([research.cuhk.edu.hk](https://research.cuhk.edu.hk/en/publications/piano-transcription-by-hierarchical-language-modeling-with-pretra/?utm_source=openai))

実装方針としては、採譜モデルの後段に「難易度制約付き整譜」を置くのが現実的です。削除・統合・リズム単純化・左手伴奏パターン置換を、演奏可能性制約で制御する構成がよいです。

---

## 5. インド音楽情報処理: Indian classical / sargam / tala

インド音楽では、西洋五線譜への変換より、raga/tala/sargam/ガマカをどこまで保つかが中心課題です。特にCarnaticでは連続的な装飾音が本質なので、単純な12平均律ノート列への量子化は情報を落とします。

**State-Based Transcription of Components of Carnatic Music**  
Venkata Viraraghavan, Hema Murthy, Arpan Pal, R. Aravind, ICASSP 2020. DOI: 10.17023/nbxg-3b37。  
Carnatic pitch curveをconstant-pitch notesとstationary pointsに分解し、Viterbiで状態列と量子化ピッチを推定。IIT Madras系の研究として、ガマカを含む記述的転写の代表例です。([resourcecenter.ieee.org](https://resourcecenter.ieee.org/conferences/icassp-2020/spsicassp20vid1462?utm_source=openai))

**SBT / State Based Transcription for Carnatic Music**  
ISMIR 2022 Indian Art Music tutorialでは、SBTツールがCarnaticのピッチ曲線をraga/gamakaに沿ってCSVの記述的転写へ変換する、と整理されています。入力にはtonicとragaが必要で、タンプーラ伴奏程度の清潔な録音で有効です。([mtg.github.io](https://mtg.github.io/IAM-tutorial-ismir22/melodic_analysis/melodic-transcription.html))

**Saraga: Open Datasets for Research on Indian Art Music**  
Ajay Srinivasamurthy et al., Empirical Musicology Review 2021. DOI: 10.18061/emr.v16i1.7641 / Zenodo DOI: 10.5281/zenodo.4301737。  
Carnatic/Hindustaniの音源、メタデータ、旋律・リズム・構造アノテーションを含む重要データセット。ただしCC BY-NC系が含まれ、商用学習データとしては要注意です。([researchgate.net](https://www.researchgate.net/publication/356947674_Saraga_Open_Datasets_for_Research_on_Indian_Art_Music?utm_source=openai))

**Automatic music transcription for sitar music analysis**  
Li Su, Alec Cooper, Yu-Fen Huang, Journal of New Music Research 2023. DOI: 10.1080/09298215.2023.2251450。  
Sitar向けAMTと音楽分析の研究。非西洋音楽では「完全な譜面」より「分析可能な転写」を目標にする傾向が強いです。

**Melodic and Metrical Elements of Expressiveness in Hindustani Vocal Music**  
Yash Bhake, Ankit Anand, Preeti Rao, ISMIR 2025. arXiv:2508.04430。  
Hindustani vocalの旋律・拍節表現に関する研究。Bhatkhande記譜やbandishのような伝統的記譜は、演奏解釈のための「schematic notation」であり、A2Sでは連続F0・歌詞・tala位置を併用する必要があります。([researchgate.net](https://www.researchgate.net/publication/394363029_Melodic_and_Metrical_Elements_of_Expressiveness_in_Hindustani_Vocal_Music?utm_source=openai))

採譜プロジェクトでインド音楽を扱うなら、MusicXML一本化より、`continuous pitch contour + tonic-normalized svara + tala cycle + optional sargam text` を内部表現に持つべきです。MusicXML出力は派生形式と考えるのが安全です。

---

## 6. 中国語圏・CNKI相当の動向

中国語圏では、国際論文としては以下が重要です。

- **AMT-CMT**, DOI: 10.1016/j.eswa.2026.133435。MusicXML構造、beat-depth、MoE Transformerを使うA2S寄り研究。([sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0957417426023444?utm_source=openai))
- **Piano Transcription by Hierarchical Language Modeling with Pretrained Roll-based Encoders**, CUHK, ICASSP 2025. arXiv:2501.03038, DOI: 10.1109/ICASSP49660.2025.10890508 / 10.48550/arXiv.2501.03038。ピアノロールencoderとLM decoderを組み合わせ、onset/pitch、velocity、offsetを階層的に予測。音符イベント精度改善が主で、譜面整形そのものは対象外です。([arxiv.org](https://arxiv.org/abs/2501.03038)) ([research.cuhk.edu.hk](https://research.cuhk.edu.hk/en/publications/piano-transcription-by-hierarchical-language-modeling-with-pretra/?utm_source=openai))

CNKI相当の中文文献では、節拍識別、音高抽出、簡譜生成、教育向け歌唱評価、商用AI扒谱に近い話題が目立ちます。ただし、国際ベンチマークでMusicXML/`**kern`まで評価する研究はまだ限定的です。中国国内サービスでは「簡譜・五線譜・MIDI/PDF出力」を掲げるものが増えていますが、論文としての再現性・ライセンス・評価セット公開は弱い傾向があります。

---

## 7. コード公開・ライセンス・商用利用

| 研究/実装 | 公開状況 | ライセンス | 商用利用観点 |
|---|---:|---|---|
| Beat This! | GitHub + PyPI +重み公開 | MIT | 商用利用しやすい。ただし訓練データの権利は別確認。([github.com](https://github.com/CPJKU/beat_this)) |
| BeatNet / BeatNet+ | GitHub + PyPI +重み公開 | CC BY 4.0 | 表示上は商用可。ただしコードにCC BYは珍しいので法務確認推奨。([github.com](https://github.com/mjhydri/BeatNet)) |
| Piano_SVSep | GitHub +事前学習モデル | MIT | 商用利用しやすい。J-pop評価データは非公開で再現制約あり。([github.com](https://github.com/CPJKU/piano_svsep)) |
| MIDI2ScoreTransformer | GitHub +モデル重み | ライセンスファイルなし | 権利不明。商用製品への組込不可扱いが安全。([github.com](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer)) |
| YourMT3+ / YourMT3 | GitHub + HF checkpoints | GitHubはGPL-3.0、HF checkpointはApache-2.0表示 | GPL義務に注意。独自商用プロダクトへの静的組込は避けたい。([github.com](https://github.com/mimbres/YourMT3)) |
| MV2H | GitHub | MIT | 評価用途に使いやすい。([github.com](https://github.com/apmcleod/MV2H)) |
| MUSTER | 評価スクリプト公開 | ライセンス要確認 | 研究評価には有用。商用CI利用前に確認。([amtevaluation.github.io](https://amtevaluation.github.io/)) |
| Suzuki difficulty rearrangement | 論文OA | 実装未確認 | 手法参考。商用品質データは非公開寄り。 |
| Gover/Zewi playing-level conversion | 論文OA | 論文CC BY 4.0 | データはピアノ学習アプリ由来で商用再利用は困難。([zenodo.org](https://zenodo.org/records/7316588)) |
| Saraga | データ公開 | CC BY-NC系 | 商用学習には不向き。研究評価向け。([researchgate.net](https://www.researchgate.net/publication/356947674_Saraga_Open_Datasets_for_Research_on_Indian_Art_Music?utm_source=openai)) |

---

## 8. 採譜プロジェクトへの実装示唆

最短で実用精度を狙うなら、A2S直接変換一本ではなく、以下の多段パイプラインが現実的です。

1. 音符イベント抽出: YourMT3+、Basic Pitch、Kong系HR piano transcriptionなどを比較。
2. 拍・小節推定: Beat This!を第一候補、リアルタイムや非打楽器音源ではBeatNet+も検証。
3. リズム量子化: performance MIDI-to-score Transformer系を参考に、拍グリッド上で音価・休符・タイを決める。
4. 声部・譜表分離: Piano_SVSep系GNNを後段に置く。
5. MusicXML生成: music21/MuseScore/Verovioで妥当性検証。
6. 評価: Note F1に加えて、MUSTER、MV2H、MusicXML validity、小節拍数整合、人間評価を入れる。
7. 難易度別譜面: まずルールベース簡易化、その後notation-to-notationモデルで置換。

2026年時点のSOTAから見ると、商用可能な中核部品としては `Beat This! MIT`、`Piano_SVSep MIT`、`MV2H MIT` が使いやすく、A2S直接生成モデルは研究参考または再実装対象です。MIDI2ScoreTransformerは技術的に最も近いが、ライセンス未整備のため、そのまま商用利用せず、論文ベースで独自実装するのが安全です。

補足: Slack作業ログは、現在の実行環境に `slack_send_message` / `send_message` 相当のSlack投稿ツールが提供されていないため未投稿です。
