**前提**
`docs/quality/function-critique-protocol.md:5-15` の3錨で見ました。受入条件は C1/C2/C3/C8、封緘実測は `results-pd.md` と G0解剖、外部水準は Basic Pitch公式、BeatNet+/tempo評価系の近年論文を参照。Slack投稿は、このセッションに指定チャンネルへ直接送る `send_message` ツールが見つからず未実行です。

## stem（前処理・降噪）

**3錨照合:** C8は「ノック/雨+口ずさみ/エアコンhum」とSNR段階の選択抽出率/誤音符化率を要求していますが、実装は `load_audio` がロードのみ（`spike/ear-pipeline/earpipe/services/stem/preprocess.py:12-15`）、本体はRMS百分位SNR・HPSS・固定スペクトラルゲート（`field.py:31-39`, `63-83`, `96-111`）。実測も合成sine+白/ピンク/残響/打撃中心で、実録音は未測定と自白しています（`spike/ear-pipeline/bench/results-field.md:3-16`, `24`）。外部水準では、単純HPSS/ゲートではなく分離・学習ベース前処理と併用する方向が普通で、ここはC8を名乗るには弱いです。

- **P0: スペクトラルゲートが持続音そのものを雑音床扱いして削る。** `noise_mag=10 percentile` を全周波数で引く固定ゲート（`field.py:106-110`）なので、無音区間のない持続音では音楽成分が床に入る。今回攻撃で純440Hz sineは `sine441 snr=0.0/profile=very_noisy/harmonic_ratio=1.0/denoise_rms_ratio=0.054`、8kHzでも `0.072`。C8の「音程成分の選択抽出」（`core-requirements-v3.md:71-72`）に対し、前処理が音程成分を約93-95%落とす。
- **P1: SNR推定が絶対SNRではなく、DC/クリップ/短尺を全部 `very_noisy` に倒す。** コード上もRMSの10/90 percentile比だけ（`field.py:31-39`）で `sr` 未使用（`field.py:52-56`）。今回攻撃では DC offset が `snr=0.0/profile=very_noisy/harmonic_ratio=1.0`、クリップ音源も `snr=0.0/profile=very_noisy/harmonic_ratio=1.0`。これは「非音程の誤音符化率」を測る以前に、分類器がDCを調波扱いする。
- **P1: HPSS分類の誤分類率が測られていない。** 実装は `p_e > 2.0*h_e` と flatness `>0.15` の二値ヒューリスティック（`field.py:16-19`, `74-83`）。テストは「比率が増える」程度（`tests/test_field_mode.py:171-181`）で、C8が要求する6分類タグ/受入デモ3種（`core-requirements-v3.md:71-72`）の精度表がない。
- **P2: 短尺入力の扱いが一貫しない。** `denoise` は2048未満を素通し（`field.py:101-105`）だが `analyze_field` はSTFTへ進み、今回 `short512` は warning 付きで `snr=0.018/profile=very_noisy/harmonic_ratio=1.0`。攻撃入力としてはクラッシュしないが、品質報告としては信用できない。

**ダッシュボード行案:** `stem | 35/100 | 合成雑音では白10dB F1 0.118→1.000、ピンク5dB 0→0.815。ただし持続音ゲート削り、DC/clip誤分類、実フィールド未測定 | 次: denoise前後の音楽成分保持率、DC/clip/短尺/SR差、実録3種をC8受入に固定`

## ear（音高検出）

**3錨照合:** C1は PD15曲で BP素点 F1@100ms `0.709` 非劣化、bp_worker互換JSON、A=440±30cents補正を要求（`core-requirements-v3.md:42-45`）。現実は rescue構成で score_rhythm は `0.402 > 0.387` だが F1@100ms は `0.650 < 0.709`（`results-pd.md:60-66`, `70-73`）。Basic Pitch自体は多声・ピッチベンド検出を持つが「1楽器ずつが最善」と公式が言っています（[Spotify Basic Pitch GitHub](https://github.com/spotify/basic-pitch), [Spotify Engineering](https://engineering.atspotify.com/2022/6/meet-basic-pitch)）。この実装はそのbend出力を捨てています。

- **P0: C1の主指標でBP非劣化を満たしていない。** `results-pd.md:60-66` で rescueは F1@100ms `0.650`、BP素点 `0.709`。受入条件は「Note F1@100ms ≥ BP素点平均0.709」（`core-requirements-v3.md:42-44`）。score_rhythmだけ勝ったと言うなら、C1ではなくC3の局所勝利。
- **P1: bp_worker契約がキー存在だけで、値域/型/時刻単調性/NaNを通す。** `_validate_worker_json` は list と必須キーだけ確認（`poly.py:40-52`）。今回攻撃で `offset<onset, midi=200, confidence=2.0` も、`onset=NaN, midi="60", confidence=NaN` も通過。`PitchEvent` 側も値域制約なし（`contracts.py:10-18`）。C1のJSON契約として脆い。
- **P1: mono/poly切替が判断ではなく手動フラグ。** CLI既定は `engine="mono"`（`pipeline.py:24`, `121-124`）、polyは明示時だけ（`pipeline.py:51-55`）。今回Cメジャー三和音をmonoへ投げると `n=0`。多重音高検出C1を既定体験で満たしていない。
- **P1: confidence較正が実測分布ではなく固定閾値。** monoは `MIN_CONFIDENCE=0.5`（`mono.py:17-18`）、polyは normal/highで `0.15/0.08`（`poly.py:14-23`）、field選択は `0.50/0.55/0.58`（`field_select.py:10-34`）。PD実測では rescueの recall `0.861` と引き換えに precision `0.547`（`results-pd.md:60-66`）で、較正済みconfidenceとは呼べない。
- **P1: postfilterは既知の逆効果をまだオプションとして残すには危険。** 倍音差集合で低confidenceを消す（`postfilter.py:13-18`, `69-98`）。実測で「本物のオクターブ重ねを誤除去」「recall 0.583まで低下」（`results-pd.md:74-77`）。今回攻撃でも `48(conf=.9)+60(conf=.35)` の実オクターブが `2→1` に削られた。
- **P2: 音域/ベンドの契約が出力で落ちる。** monoの既定範囲は C2-C7（`mono.py:13-14`）だが今回 `30Hz/55Hz` はゼロ、`4000Hz` は `midi=95` として検出。Basic Pitch workerは `_bends` を捨てる（`bp_worker.py:83-91`）ので、ビブラート/ピッチベンドは最初から譜面反映不能。

**ダッシュボード行案:** `ear | 42/100 | rescue score_rhythm 0.402は利点。ただしC1 F1 0.650でBP 0.709未満、契約値域なし、既定monoで多声不可、bend破棄 | 次: worker schema厳格化、曲密度/多声自動選択、confidence校正曲線、bend保持`

## rhythm（テンポ・量子化）

**3錨照合:** C2はテンポマップ、C3は実タイミング+格子の二重表現を要求（`core-requirements-v3.md:47-55`）。実装は `BPM_MIN=60/BPM_MAX=180` の一定テンポ探索（`quantize.py:7-9`, `58-76`, `132-147`）。近年のbeat trackingはPLP/DBN/ニューラルでbeat/downbeatや非打楽器/歌声も扱う方向で、BeatNet+のように多様音源・非打楽器を対象にします（[TISMIR BeatNet+ 2024](https://transactions.ismir.net/articles/10.5334/tismir.198?_rsc=1tt34)）。tempo評価自体も未解決性が指摘されています（[TISMIR tempo estimation overview](https://transactions.ismir.net/articles/10.5334/tismir.43)）。

- **P0: C2の「テンポマップ」ではなく単一BPM。** `estimate_grid` は `tuple[float,int]` だけ返す（`quantize.py:132-175`）、pipeline結果も単一 `bpm` と `grid_per_beat`（`pipeline.py:68-76`, `89-96`）。受入条件の「区間別テンポ系列」「ルバートで区間分割が破綻しない」（`core-requirements-v3.md:47-50`）は未実装。
- **P1: 限界域が仕様外に落ちる。** 探索範囲は60-180固定（`quantize.py:7-8`, `81`, `157`）。今回攻撃で真50BPMは `62.5`、真200BPMは `100.0`。C2の合成マトリクスは60-150だけ（`core-requirements-v3.md:47-49`、`tests/test_quantize.py:86-98`）なので、ユーザー指定の60未満/180超は守れていない。
- **P1: 弱起を位相として保持しない。** 量子化は絶対0秒基準で丸めるだけ（`quantize.py:193-208`）。今回 `offset=0.17s/120BPM` は先頭が `0.25拍`、残差 `-0.36 grid` のまま全音符に固定オフセットが残る。弱起/小節先頭の概念がない。
- **P1: 二重表現は保持しているが、整合検査が浅い。** `QuantizedNote` は `onset_sec/offset_sec` を持つ（`contracts.py:20-41`）、clip時も実タイミング保持（`quantize.py:227-231`）。ただし dedup は同一 `(start_beats,midi)` で長い方を残し、捨てたイベントの実タイミングは消える（`quantize.py:210-215`）。PDでは raw F1 `0.678` が grid `0.650` を上回る（`results-pd.md:88-93`）ので構造の価値はあるが、同時衝突時の二重整合はまだ穴。
- **P1: ルバート/アッチェレランド/スウィングを単一格子へ潰す。** コードコメントもルバート・曲中系切替はスコープ外（`quantize.py:144-147`, `results-pd.md:103-108`）。今回攻撃で `accel80to160` は単一 `120.0`、`swing120_2:1` は `90.0/gpb=4` に誤解釈。スウィング記法やテンポ系列は出ない。
- **P2: G0解剖では量子化後に幽霊が増えるケースがある。** u1は BP TFLite `2377 notes / precision 0.263`（`rhythm_autopsy_tflite.json:13-22`）から spike `2779 notes / precision 0.189`（`同:53-62`）。u4も spike precision `0.195`（`同:237-245`）。C3の平均score_rhythm `0.402` は良いが、入力側rhythmとしては過剰発火をまだ増幅している。

**ダッシュボード行案:** `rhythm | 48/100 | C3 raw/grid二重表現は成果: raw F1 0.678 vs grid 0.650、score_rhythm 0.402。ただし単一BPM、60-180外、弱起、ルバート/accel/swing未対応 | 次: tempo_map型、位相/弱起推定、local tempo segmentation、swing/timing style併記`

**外部参照**
Basic Pitch公式GitHub、Spotify Engineering記事、TISMIR BeatNet+ 2024、TISMIR tempo estimation overview、IJCAI 2024 audio-to-score hierarchical decodingを確認しました。今回の結論は、外部SOTAに追いつけというより、現コードの主張をC1/C2/C3/C8の受入条件まで正直に下げるべき、という判定です。
