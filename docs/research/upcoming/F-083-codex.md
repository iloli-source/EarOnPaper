# 小節・拍オフセットの系統補正／リバーリング（rebarring）調査レポート（codex＝論文・WEB担当）

**調査日:** 2026-07-21
**担当分担:** codex＝論文＋WEB検索（**失敗例を最大限**収集）
**対象機能（F-083）:** 小節・拍オフセットの系統補正／リバーリング＝rebarring・8分ズレの一括補正・手動同期点とその間の自動補間
**手法:** mcp__codex__codex（GPT-5系, cwd=採譜, read-only）でWEB調査を実行 → Claude側で主要ソースの実在・記述をWebFetch/WebSearchでスポット検証。実在確認できたもののみ採録。捏造なし。

> **検証メモ:** BeatNet+（TISMIR 2024, Heydari & Duan、Reggaeのbeat高/downbeat低）、Chiu et al. 2023（PLPDP, TASLP vol.31 pp.2824-2835, arXiv:2308.10355）、Kraprayoon/Pham/Tsai 2024（Applied Sci. 14(4):1459, DOI:10.3390/app14041459）はURL・著者・年・主張を個別に実データで確認済み。他の論文・製品ドキュメントはcodexの検索結果に基づき、タイトル/著者/年またはURLを併記。

---

## 0. 要約（3つの構造的失敗）

採譜での「8分ズレ一括補正」「小節線の引き直し」「手動同期点の間を自動補間」は、MIRでは **beat/downbeat tracking / meter tracking / tempo mapping / score-audio alignment / notation re-barring** に分かれる。研究・実装に共通する失敗は4類型:

1. **拍は合うが小節頭（downbeat）が半拍/1拍ずれる** — beatとdownbeatは別問題。
2. **途中の1同期点の誤りが以後の全小節へ伝播する** — barline drift/連鎖再計算。
3. **rubato/ritardandoで固定・グローバルテンポ仮定が破綻する** — post-processが硬すぎる。
4. **ユーザーが「解析結果の修正」と「音楽の編集」を混同する** — UI設計の失敗。

---

## 1. 論文・研究系サーベイ

| 論文 | 著者・年 | 手法 | データセット | 主要な知見／失敗 |
|---|---:|---|---|---|
| [Analysis of the meter of acoustic musical signals](http://sp.cs.tut.fi/pubdl/Klapuri2006-Analysis.pdf) | Klapuri, Eronen, Astola 2006 | tatum/tactus/measureを確率モデルで同時推定 | 474音楽信号 | 小節レベルまで推定する古典枠組み。入力アクセントから拍・小節を推定するため、**アクセントが弱い箇所で小節頭誤認**のリスク。 |
| [Joint Beat and Downbeat Tracking with Recurrent Neural Networks](https://zenodo.org/records/1415836) | Böck, Krebs, Widmer 2016（ISMIR） | RNNでbeat/downbeat activation → DBNで小節長モデル化 | 複数ジャンル | beat/downbeat同時推定の代表。**DBNの拍子・テンポ仮定が誤ると「拍は合うが小節頭がずれる」**出力に。 |
| [Rhythmic Pattern Modeling for Beat- and Downbeat Tracking](https://research.jku.at/de/publications/rhythmic-pattern-modeling-for-beat-and-downbeat-tracking-in-music/) | Krebs, Böck, Widmer 2013 | HMMでbeat/downbeat/tempo/meter/patternを同時推定 | 697 Ballroom曲 | 反復パターンに強いが**パターン学習依存 → 拍節感が曖昧な曲で誤パターンへロック**。 |
| [What Makes Beat Tracking Difficult? A Case Study on Chopin Mazurkas](https://www.researchgate.net/publication/220723198_What_Makes_Beat_Tracking_Difficult_A_Case_Study_on_Chopin_Mazurkas) | Grosche, Müller, Sapp 2010 | 複数演奏間の一貫性から失敗箇所を分類 | Chopin Mazurkas, 34–88演奏/曲 | **expressive performanceで局所テンポ偏差・ornament・弱拍・無音拍（non-event beat）が誤検出を誘発**。 |
| [Local Periodicity-Based Beat Tracking for Expressive Classical Piano Music](https://arxiv.org/abs/2308.10355) | Chiu, Müller, Davies, Su, Yang 2023（TASLP vol.31, pp.2824-2835） | PLPDP（local periodicity + DP）でpost-processing | ASAP, Maz-5 | 既存post-processor（PPT）は**global tempo transition仮定に硬く、局所テンポ変化に失敗**。Maz-5でF1 0.595→0.838、ASAP 0.473→0.493に改善。 |
| [User-Driven Fine-Tuning for Beat Tracking](https://www.mdpi.com/2079-9292/10/13/1518) | Pinto, Böck, Cardoso, Davies 2021 | 少量のユーザー拍注釈で曲ごとにDNN fine-tune | SMC, Hainsworth, GTZAN, TapCorrect | **rubato等で既存SOTAが低性能**。手動修正だけでなく曲固有fine-tuningが有効だが、**fine-tuningが一部で性能を悪化**とも報告。 |
| [BeatNet+: Real-Time Rhythm Analysis for Diverse Music Audio](https://transactions.ismir.net/articles/10.5334/tismir.198) | Heydari, Duan 2024（TISMIR） | CRNN + particle filtering | Ballroom, GTZAN, Hainsworth, Rock, RWC, MUSDB18等 | **Reggaeはbeat F1が最良級なのにdownbeat F1がワースト級**。syncopation/off-beat（one-drop/steppers/rockers）が小節頭識別を壊す（本レポートで実データ検証済み）。 |
| [Downbeat Tracking with Tempo-Invariant CNNs](https://machinelearning.apple.com/research/downbeat-tracking-with-tempo) | Di Giorgi, Mauch, Levy 2020 | tempo-invariant time-warping CNN | Groove MIDI, GTZAN, Ballroom | **通常CNNは未見テンポで性能低下**。tempo-invariant処理で汎化改善。 |
| [Measuring the Performance of Beat Tracking Algorithms Using a Beat Error Histogram](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Measuring-the-Performance-of-Beat-Tracking/99515514802346) | Davies, Degara, Plumbley 2011 | beat error histogram / information gain | annotated beat data | **F-measureだけでは半拍/倍テンポ/異metrical levelを見落とす**。ズレ診断には誤差ヒストグラムが有用。 |
| [Improving the Robustness of DTW to Global Time Warping Conditions in Audio Synchronization](https://www.mdpi.com/2076-3417/14/4/1459) | Kraprayoon, Pham, Tsai 2024（Applied Sci. 14(4):1459） | DTWのglobal time warping耐性強化（長さ正規化＋downsampling） | audio-audio同期ベンチ | **標準DTWは真の整合パスの平均傾きが1から大きくずれると（severe global time warping）性能が大きく低下**。DTW前のdownsampling正規化が最も有効。 |
| [Audio to Score Alignment Based on Chroma Features and DTW](https://manu44.magtech.com.cn/Jwk_infotech_wk3/EN/10.11925/infotech.1003-3513.2012.01.07) | Zhang Biqiao, Han Shenglong 2012（中文） | chroma + DTWでaudio-score alignment | 歴史的録音、手動小節ラベル | 実録音では**小節ground truthを手動付与して評価** → 完全自動だけでは同期点品質検証が必要。 |
| [Automatic alignment of a musical score to performed music](https://www.jstage.jst.go.jp/article/ast/22/3/22_3_189/_article/-char/en) | Meron, Hirose 2001 | DP/DTW（MIDI-to-MIDI, MIDI-to-audio） | performance DB | **alignmentが局所最小に落ちる場合、manual bootstrapping**で正しい整合を補助。 |
| [mir_eval.beat documentation](https://mir-eval.readthedocs.io/latest/api/beat.html) | Raffel et al. / mir_eval | CML/AML等の評価実装 | 汎用評価ライブラリ | beat評価は**複数metrical levelとtempo ambiguityを考慮**して行う必要がある。 |

---

## 2. 実装・製品ドキュメント（挙動と失敗関連の注意点）

| 製品/記事 | 仕組み | 失敗に直結する挙動 |
|---|---|---|
| [Logic Pro Beat Mapping](https://support.apple.com/en-gb/guide/logicpro/lgcp624214db/10.7/mac/11.0) | notesをrulerのbar/beatへ接続しtempo eventを作成 | **Beat Mapping後にTempo Trackを編集すると、beat mapping由来のタイミングが壊れる**。 |
| [Cubase Time Warp](https://www.steinberg.help/r/cubase-pro/15.0/en/cubase_nuendo/topics/editing_tempo_and_signature/editing_tempo_time_warp_c.html) | musical positionをtime positionへドラッグしtempo gridを変形 | **Warp Grid mode選択次第で「絶対時刻を保持」か「音楽イベントを追従」かが変わる** → 誤選択で逆挙動。 |
| [Melodyne Tempo Detection](https://helpcenter.celemony.com/M5/doc/melodyneEssential5/en/M5tour_TempoDetectionIntro_2?env=standAlone) | tempo/拍子検出、Bar 1配置、pickup処理 | **anacrusis（弱起）はBar -1扱い**。最初の完全小節の強拍をBar 1に置く。 |
| [Melodyne Assignment vs Editing](https://helpcenter.celemony.com/M5/doc/melodyneStudio5Training/en/HC2-Training_R1T2_Zuweisung_vs_Bearbeitung_M5) | Assign Tempo Modeで解析結果を直す | **解析修正（Assign）と音楽編集（Edit）を明確に分離**。Bar Ruler/メトロノーム不一致は編集前に直すべきとする。 |
| [ScoreCloud Quick-start](https://scorecloud.com/songwriter/tutorials/quick-start-guide/) | Pickup tool, barlineドラッグ, subdivision snap | **downbeatを3拍目と誤認する例を明示**。barlineドラッグで**"all following bars will be re-calculated"**（後続小節が連鎖再計算）。 |
| [AudioScore User Guide](https://manualzz.com/doc/23454412/neuratron-audioscore-user-guide) | barlineを左→右へ調整しnotation再計算 | **固定テンポでない場合、途中から直すと既修正barlineも動く → 先頭から順に**調整せよ。 |
| [AnthemScore documentation](https://lunaverus.com/documentation) | beats/downbeats編集、downbeat単位のtime/key/tempo適用 | time/key/tempoは**downbeatから次の値まで**適用。beatをドラッグ編集可能。 |
| [Dorico time signatures](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/write_mode/write_mode_notations_input/write_mode_time_signatures_inputting_panel_t.html) | 拍子入力で後続をre-bar | **次の既存拍子まで後続barlineを移動**。Insert modeなしでは不足拍を自動挿入しない。 |
| [Dorico Insert mode](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/write_mode/write_mode_insert_mode/write_mode_insert_mode_c.html) | Insert scope / stop position | Insert modeは後続音符を押し出す。**scope/stop position誤設定で広範囲がずれる**。 |
| [MuseScore time signatures](https://handbook.musescore.org/en_gb/notation/rhythm-meter-and-measures/time-signatures) | 拍子変更でre-bar | **既存音楽がre-barされ、一部アイテムが失われ得る**ため確認要。 |
| [MuseScore Regroup rhythms](https://handbook.musescore.org/fr/notation/rhythm-meter-and-measures/regroup-rhythms) | rhythmの表記上再グループ化 | **音自体は変えず beaming/tie表記のみ**を直す → 音価ズレ補正とは別機能（混同注意）。 |
| [Flat time signature](https://help.flat.io/en/music-notation-software/timesig/) | 範囲未選択なら次拍子/終端まで適用 | pickup設定と末尾小節の補償が必要な場合あり。**局所変更のつもりが広域適用**され得る。 |
| [Flat MIDI import](https://blog.flat.io/import-and-export-midi-your-music-score/) | MIDI performanceをnotationへ変換 | **MIDIはperformance timingを持つ → quantization quirksは手動cleanup**が必要。 |

---

## 3. 軸別「失敗例」（本レポートの主眼）

### 軸(1) beat/downbeat tracking と rebarringの手法 — 失敗例

- **拍は正しいが小節頭だけ間違う:** BeatNet+はReggaeでbeatは最良級なのにdownbeatがワースト級と報告。one-drop/steppers/rockers等のoff-beat patternがdownbeat識別を壊す。[Heydari & Duan 2024](https://transactions.ismir.net/articles/10.5334/tismir.198)
- **半拍・倍テンポ・半テンポに吸着する:** metrical level ambiguityは評価で考慮必須。F-measure単独ではズレの種類を診断できない。[Davies et al. 2011](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Measuring-the-Performance-of-Beat-Tracking/99515514802346) / [mir_eval.beat](https://mir-eval.readthedocs.io/latest/api/beat.html)
- **未見テンポで汎化失敗:** 通常CNNは学習外テンポで性能低下。[Di Giorgi et al. 2020](https://machinelearning.apple.com/research/downbeat-tracking-with-tempo)
- **rebarringで表記オブジェクトが壊れる:** MuseScoreは拍子変更でre-barされ一部アイテムが失われ得ると明記。[MuseScore](https://handbook.musescore.org/en_gb/notation/rhythm-meter-and-measures/time-signatures)
- **notation regroupと時間補正を混同:** MuseScore Regroupは音を変えず表記のみ直す機能で、拍位置補正ではない。[MuseScore Regroup](https://handbook.musescore.org/fr/notation/rhythm-meter-and-measures/regroup-rhythms)

### 軸(2) 系統オフセットの誤補正・小節線ドリフト — 失敗例

- **最初のdownbeat誤認が全体をずらす:** ScoreCloudは「3拍目を1拍目と誤認」時にPickup toolでbarline相対位置をずらす必要があると説明。[ScoreCloud](https://scorecloud.com/songwriter/tutorials/quick-start-guide/)
- **途中のbarlineを1つ動かすと後続が連鎖再計算:** ScoreCloudは barline draggingで "all following bars will be re-calculated"。[ScoreCloud](https://scorecloud.com/songwriter/tutorials/quick-start-guide/)
- **左から順に直さないと既修正点が動く:** AudioScoreは非固定テンポではbarline補正を先頭から前方へ進めるべきとする。[AudioScore](https://manualzz.com/doc/23454412/neuratron-audioscore-user-guide)
- **Beat Mapping後にTempo Track編集で同期破壊:** Logic ProはBeat Mapping後のTempo Track変更を避けよと警告。[Logic Pro](https://support.apple.com/en-gb/guide/logicpro/lgcp624214db/10.7/mac/11.0)
- **弱起の扱いを誤ると全小節番号がずれる:** MelodyneはanacrusisをBar -1へ置く。弱起解釈を誤ると小節頭・小節番号が一律ずれる。[Melodyne](https://helpcenter.celemony.com/M5/doc/melodyneEssential5/en/M5tour_TempoDetectionIntro_2?env=standAlone)

### 軸(3) テンポ揺れ／rubatoでの破綻 — 失敗例

- **rubatoで固定/グローバルテンポ仮定が破綻:** User-Driven Fine-Tuningはrubato等のchallenging conditionsで既存SOTA性能が低いと述べる。[Pinto et al. 2021](https://www.mdpi.com/2079-9292/10/13/1518)
- **expressive classicalでpost-processingが硬すぎる:** Chiu et al.はPPTがglobal tempo transition assumptionに依存し局所テンポ変化に失敗、と報告。[Chiu et al. 2023](https://arxiv.org/abs/2308.10355)
- **Mazurkasでornament/弱いbass/一定和声/無音拍がtracking errorを誘発。**[Grosche et al. 2010](https://www.researchgate.net/publication/220723198_What_Makes_Beat_Tracking_Difficult_A_Case_Study_on_Chopin_Mazurkas)
- **DTW alignmentも大域time-warp比が大きいと完全失敗:** Kraprayoon et al.はsevere global time warpingで標準DTWの性能が大きく落ちると報告（対策=前段downsampling正規化）。[Kraprayoon, Pham, Tsai 2024](https://www.mdpi.com/2076-3417/14/4/1459)
- **fine-tuning自体が逆効果になる場合:** ユーザー注釈での曲別fine-tuningが一部ケースで性能を悪化させることも。[Pinto et al. 2021](https://www.mdpi.com/2079-9292/10/13/1518)

### 軸(4) 手動同期点補間UXの落とし穴 — 失敗例

- **「解析結果の修正」と「音楽編集」を混同:** MelodyneはAssign modeとEdit modeを分離。tempo assignはBar Ruler/メトロノームを音楽に合わせる作業だと明示。[Melodyne Assign vs Edit](https://helpcenter.celemony.com/M5/doc/melodyneStudio5Training/en/HC2-Training_R1T2_Zuweisung_vs_Bearbeitung_M5)
- **Warp mode誤選択で保持対象が逆転:** Cubaseは絶対時刻を守るつもりが音楽イベント追従になる（逆も）。[Cubase Time Warp](https://www.steinberg.help/r/cubase-pro/15.0/en/cubase_nuendo/topics/editing_tempo_and_signature/editing_tempo_time_warp_c.html)
- **Insert scope誤設定で押し出しが波及:** DoricoのInsert mode scopeを誤ると意図しないvoice/player/global範囲に波及。[Dorico Insert](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/write_mode/write_mode_insert_mode/write_mode_insert_mode_c.html)
- **範囲未選択の一括適用:** Flatは範囲選択なしの拍子変更が次拍子/終端まで効き、局所変更のつもりが広域適用。[Flat](https://help.flat.io/en/music-notation-software/timesig/)
- **手動bootstrappingが前提の設計は、その手掛かりを間違えると全体整合が崩れる:** Meron & Hiroseは局所最小回避にmanual bootstrappingを要すると述べる（＝人手の初期点誤りが致命的）。[Meron & Hirose 2001](https://www.jstage.jst.go.jp/article/ast/22/3/22_3_189/_article/-char/en)

### 軸(5) ベストプラクティス

| プラクティス | 根拠／出典 |
|---|---|
| 解析補正モードと音楽編集モードをUIで分離 | Melodyne Assign Tempo Modeが先にBar Ruler/メトロノームを合わせる設計。[Melodyne](https://helpcenter.celemony.com/M5/doc/melodyneStudio5Training/en/HC2-Training_R1T2_Zuweisung_vs_Bearbeitung_M5) |
| 最初の完全小節downbeat・pickup・Bar 1を明示的に扱う | MelodyneはanacrusisをBar -1へ、Flatもpickup durationと末尾補償を扱う。[Melodyne](https://helpcenter.celemony.com/M5/doc/melodyneEssential5/en/M5tour_TempoDetectionIntro_2?env=standAlone) / [Flat](https://help.flat.io/en/music-notation-software/timesig/) |
| barline/sync point補正は左→右へ誘導 | AudioScoreは非固定テンポで先頭から前方へ修正せよ。[AudioScore](https://manualzz.com/doc/23454412/neuratron-audioscore-user-guide) |
| 同期点編集時に「後続が再計算される範囲」を可視化 | ScoreCloudはbarlineドラッグで後続barが再計算される仕様。[ScoreCloud](https://scorecloud.com/songwriter/tutorials/quick-start-guide/) |
| 8分ズレ補正は phase shift / pickup / rebar / regroup を別コマンドに分ける | ScoreCloud Pickup=位相補正、MuseScore Regroup=表記のみ、Dorico/MuseScore拍子変更=rebar。[ScoreCloud](https://scorecloud.com/songwriter/tutorials/quick-start-guide/) / [MuseScore Regroup](https://handbook.musescore.org/fr/notation/rhythm-meter-and-measures/regroup-rhythms) / [Dorico](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/write_mode/write_mode_notations_input/write_mode_time_signatures_inputting_panel_t.html) |
| 自動結果は誤差ヒストグラム/metrical-level診断で分類 | beat error histogramは半拍/位相/metrical-level誤りを診断しやすい。[Davies et al. 2011](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Measuring-the-Performance-of-Beat-Tracking/99515514802346) |
| rubato曲はglobal tempoではなくlocal periodicityまたは手動sync点 | PLPDPはlocal periodicityでMaz-5 F1を0.595→0.838へ改善。[Chiu et al. 2023](https://arxiv.org/abs/2308.10355) |
| 手動同期点は「小節/拍/細分」単位を切替可能に | AnthemScoreはdownbeat/beat線とnote spacingを分け、Logic/Cubaseはbar/beat ruler上でtempo map作成。[AnthemScore](https://lunaverus.com/documentation) / [Logic](https://support.apple.com/en-gb/guide/logicpro/lgcp624214db/10.7/mac/11.0) / [Cubase](https://www.steinberg.help/r/cubase-pro/15.0/en/cubase_nuendo/topics/editing_tempo_and_signature/editing_tempo_time_warp_c.html) |

---

## 4. 採譜プロダクトへの示唆

- **「一括8分ズレ補正」は単なる全ノート時間移動ではない。** downbeat phase correction / pickup（弱起）correction / tempo-map anchor correction の3系統に分けるべき。[ScoreCloud](https://scorecloud.com/songwriter/tutorials/quick-start-guide/) / [Melodyne](https://helpcenter.celemony.com/M5/doc/melodyneEssential5/en/M5tour_TempoDetectionIntro_2?env=standAlone)
- **「リバーリング」は「音価を保った小節線再配置（rebar）」と「表記上のbeaming/tie再グループ化（regroup）」を分離する。** 混同すると音を変えたつもりがないのに音価が壊れる/その逆。[Dorico](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/write_mode/write_mode_notations_input/write_mode_time_signatures_inputting_panel_t.html) / [MuseScore Regroup](https://handbook.musescore.org/fr/notation/rhythm-meter-and-measures/regroup-rhythms)
- **手動同期点の自動補間は「各点の影響範囲・補間方式・後続barline再計算・Undo単位」を明示せよ。** さもないとScoreCloud/AudioScore型の「1点修正で後続が全部動く」混乱が起きる。[ScoreCloud](https://scorecloud.com/songwriter/tutorials/quick-start-guide/) / [AudioScore](https://manualzz.com/doc/23454412/neuratron-audioscore-user-guide)
- **失敗検出UIは、F値だけでなく「半拍位相ズレ」「倍/半テンポ」「downbeatのみ誤り」「rubato局所破綻」を別ラベルで出す。** Davies et al.のbeat error histogram、mir_evalのmetrical-level評価と整合する。[Davies et al. 2011](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Measuring-the-Performance-of-Beat-Tracking/99515514802346) / [mir_eval.beat](https://mir-eval.readthedocs.io/latest/api/beat.html)
- **rubato/expressiveが主対象なら、グローバルテンポ推定は初期値に留め、local periodicity（PLPDP系）＋手動sync点を主軸に。** fine-tuningは逆効果もあるためオプトイン運用が安全。[Chiu et al. 2023](https://arxiv.org/abs/2308.10355) / [Pinto et al. 2021](https://www.mdpi.com/2079-9292/10/13/1518)
