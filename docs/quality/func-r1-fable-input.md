# 機能別ダメ出し R1 (Fable / 入力側3機能: stem / ear / rhythm)

**監査人:** Fable(実行ベース攻撃担当) / **日付:** 2026-07-19
**方法:** spike/ear-pipeline/.venv で合成音源を自作(numpy/soundfile)し未テスト入力を実際に通した実測。
**基準:** 3つの錨(受入条件 / 封緘実測 / 外部水準)。引用のない指摘は不採用。
**ベースライン:** `pytest -q` → **172 passed**(85s)。既存テストは緑のまま以下の欠陥を素通ししている。

攻撃スクリプト: `/tmp/attack_stem*.py`, `/tmp/attack_ear*.py`, `/tmp/attack_rhythm*.py`, `/tmp/attack_poly.py`
実行: `PYTHONPATH=$PWD .venv/bin/python <script>`

---

## 【stem】 field.py / preprocess.py

対象: `analyze_field`(field.py:52)・`_estimate_snr_db`(field.py:31)・`denoise`(field.py:96)

| # | 攻撃入力 | 実測結果 | 判定 | 分類 |
|---|---------|---------|------|------|
| S1 | 2秒 連続 440Hz正弦 amp0.3 | `snr=0.000 → very_noisy` | 誤動作(クリーン純音を最悪判定) | **P0** |
| S2 | 同エネルギーだが無音ギャップ付き | `snr=182.272 → clean` | 物理不能値(docstringは≈9飽和を主張) | **P0** |
| S3 | NaN混入(1サンプル) | `ParameterError` クラッシュ | 契約ガード欠如 | **P1** |
| S4 | Inf混入(1サンプル) | `ParameterError` クラッシュ | 同上 | **P1** |
| S5 | sr=0 / sr=-44100 | `OK`(黙って処理・値は無意味) | 不正srを黙認 | P2 |
| S6 | int16 audio(値~数百) | `snr=1.94`(float64化されるが未正規化) | 黙って変な値 | P2 |
| S7 | 強クリッピング/DCオフセット/8k/48k/無音/極短 | 全てクラッシュせず | 正常(頑健) | — |

### P0-S1/S2: `_estimate_snr_db` はSNR推定器ではなく「無音率検出器」

`_estimate_snr_db`(field.py:31-39)は フレームRMSの p10/p90 比を dB化する。
docstring(field.py:32-36)は「静かなフレームを雑音床とみなす」と書くが、**雑音の有無ではなく"音が途切れるか"を測っている**。実測(`/tmp/attack_stem2.py`):

```
continuous-2s-tone: snr=0.000  prof=very_noisy   # p10=p90=0.1299 → log10(1)=0
sparse-notes(gaps):  snr=182.272 prof=clean       # p10=0.0(無音) → log10(∞)
melody-7notes:       snr=33.681  prof=clean
```

- クリーンな**持続音**(オルガン・持続する弓弦・ロングトーン)は p10≈p90 で `snr→0 → very_noisy` に落ちる。
- FieldReport.snr_db docstring(contracts.py)と FieldAnalysis(field.py:24-28)は「クリーン疎音源で≈9に飽和」と主張するが、**実測は182dBまで出る**。主張と実態が乖離。
- この値は下流 `field_select.select_events`(field_select.py:24-29)の閾値分岐を直接駆動する。持続音のクリーン録音が `very_noisy` 扱いになれば `min_conf=0.58 + min_dur=0.10` の過絞りが発動し、良品イベントを殺す(field_select自身のdocstring L20が pink SNR10 で F1 0.968→0.316 の劣化を記録済み=まさにこの過絞りの害)。
- **主張(SNR≈9飽和)と実態(0〜182)が一致していない**ため錨1・錨2に抵触。

再現: `PYTHONPATH=$PWD .venv/bin/python /tmp/attack_stem2.py`

### P1-S3/S4: NaN/Inf 入力の契約ガード欠如

`analyze_field`(field.py:58-59)は `len(y)==0` と `max(abs)<1e-9` はガードするが **非有限値を検査しない**。librosa.stft が `ParameterError: Audio buffer is not finite everywhere` を送出。実ファイル読込でNaNが混ざる経路(破損WAV・欠損補間)で入力側が即死する。境界検証(coding-style「システム境界で検証」)違反。

---

## 【ear】 mono.py / poly.py / bp_worker.py

対象: `detect_events`(mono.py:22)・`detect_events_poly`(poly.py:55)・`_validate_worker_json`(poly.py:43)

| # | 攻撃入力 | 実測結果 | 判定 | 分類 |
|---|---------|---------|------|------|
| E1 | ビブラート ±0.25〜2.0半音 6Hz/4Hz | **全て 0 events** | 音符を丸ごと消失 | **P0** |
| E2 | 100Hz純音(FMIN=65超の帯域内) | `0 events`(median f0=100.8は取れている) | 低音を確信度で殺す | **P1** |
| E3 | fmin>=fmax / fmin=0 | `ParameterError` クラッシュ | 契約ガード欠如 | **P1** |
| E4 | `_validate_worker_json` に `onset:"x"`(文字列) | **PASS**(型検査なし) | 契約が値型を検証しない | **P1** |
| E5 | midi=999999 | **PASS**(範囲検査なし) | 異常音高を素通し | P2 |
| E6 | A0=27.5Hz / C8=4186Hz(帯域外) | `0 events` | 仕様通り(帯域外) | — |
| E7 | グリッサンド 220→880 | `0 events`(断片化) | E1と同根 | P2 |

### P0-E1: ビブラートで音符が消失する(断片化バグ)

`detect_events`(mono.py:56-72)はフレーム毎のMIDI整数値が**変わるたびにセグメントを切る**(mono.py:62 `if cur != midi[start]`)。ビブラートは f0 が連続的に上下するため MIDI 整数が毎フレーム変動し、**どのセグメントも min_dur=0.08 に届かず全て破棄**される。実測(`/tmp/attack_ear3.py`):

```
vibrato-0.5semi 既定:       0 events
vibrato-0.5semi 緩和(dur0.02,conf0.1): 6 events midis=[69,68,67,74,76,79]  # 断片
  track内の distinct midi: [-1,64..80]   # ±8半音に飛び散る
```

弦・管・声楽のビブラートは**演奏の常態**(±0.25半音でも消える)。「音程が確かに検出できた区間だけをイベント化」(mono.py:32)という設計原則が、揺れる音=普通の音を"検出不能"に落とす。中央値/最頻値への丸めやヒステリシスが無い。錨1(楽器非依存NF-050)に抵触。

### P1-E2: 帯域内の低音を確信度閾値で殺す

100Hz(FMIN=65 と 中央のFMAX の間)は pYIN が median f0=100.8 を正しく取るのに、既定 `min_conf=0.5`(mono.py:18)で全滅。低音は pYIN の有声確率が構造的に低く、**帯域として受け入れると宣言した音域(FMIN=65=C2)が実質使えない**。65Hz境界音・70Hz も 0 events。

### P1-E3/E4: 契約ガードの穴

- `detect_events` は `fmin>=fmax`・`fmin=0` を検査せず librosa の生 `ParameterError` を露出(mono.py:41、境界検証なし)。
- `_validate_worker_json`(poly.py:43-52)は**キー存在のみ**検査し値型を見ない。`onset:"x"` が通過 → 下流の `r["offset"]-r["onset"]`(poly.py:98)で `TypeError` に化ける遅延爆発。プロセス間契約(docstring「JSONだけが契約」)としては型・範囲検査まで必要。

---

## 【rhythm】 quantize.py

対象: `estimate_tempo`(quantize.py:58)・`estimate_grid`(quantize.py:132)・`quantize_events`(quantize.py:178)

| # | 攻撃入力(合成イベント列) | 実測結果 | 判定 | 分類 |
|---|--------------------------|---------|------|------|
| R1 | quantize_events(bpm=0) | `ZeroDivisionError` クラッシュ | ガード欠如 | **P1** |
| R2 | quantize_events(bpm=-120) | 負のstart_beats=[-1.5..0.0] を黙って返す | 不正値を黙認 | **P1** |
| R3 | 55BPM 8分音符列(BPM_MIN=60未満) | `est=110.0`(2倍) → dur誤り0.75拍 | 範囲外で倍化 | **P1** |
| R4 | 200BPM 4分音符列(BPM_MAX=180超) | `est=100.0`(半分) | 範囲外でオクターブ誤り | **P1** |
| R5 | 三連符 72/90BPM | grid=(_,4) **binary誤判定** | 三連系検出が事前分布外で崩れる | **P1** |
| R6 | 曲中テンポ変化 100→140 | `est=150.0`(どちらでもない中間) | 一定テンポ仮定の限界(記録済) | P2 |
| R7 | スウィング(2:1)120BPM | `est=90.0` | スウィングIOIで誤推定 | P2 |
| R8 | 弱起(1拍目休符・0.25拍ずれ開始) | `est=120.0` 正解 | 正常(頑健) | — |
| R9 | 三連符 96/108/120BPM | grid=(_,3) 正解 | 事前分布中心付近は正常 | — |

### P1-R1/R2: quantize_events のBPMガード欠如

`quantize_events`(quantize.py:193 `grid = 60.0/bpm/grid_per_beat`)は bpm=0 で `ZeroDivisionError`、負bpm で**負の start_beats を黙って生成**(R2実測 `[-1.5,-1.0,-0.5,0.0]`)。estimate_tempo は BPM_DEFAULT に退避する安全網があるが、**quantize_events は外部から直接呼べる公開関数**でガードが無い。境界検証違反。

### P1-R3/R4: 範囲外テンポの倍/半誤りが下流の音価を破壊

BPM探索は `bpm_min..bpm_max`(quantize.py:81)= 60..180 に固定。範囲外の真テンポは必ず範囲内の倍音に化ける。実測(`/tmp/attack_rhythm2.py`):

```
55bpm-truth(8分音符 0.545s): est=110.0 → dur_beats全て0.75拍  # 正解0.5拍。1.5倍に膨張
200bpm-truth(4分音符):       est=100.0                         # 半分
```

R3は単にテンポが違うだけでなく、**誤ったグリッドで量子化した結果 音価そのもの(0.5拍→0.75拍)が壊れる**。譜面の音符長が誤る=採譜品質の直撃。「一定テンポ仮定」の限界記録(quantize.py:75)は**範囲外テンポの倍化には触れていない**ため、限界台帳が不完全。

### P1-R5: 三連符検出が事前分布(108BPM中心)から外れると崩壊

`estimate_grid`(quantize.py:132)の三連系判定は `PRIOR_CENTER_BPM=108` の log2ガウス事前分布に依存。実測で **96/108/120BPMの三連符は grid=3 で正解**だが **72/90BPMは grid=4(binary)に誤判定**:

```
triplet@72:  grid=(108.0,4) MISSED   # 72の三連 → 108の16分にエイリアス
triplet@90:  grid=(135.0,4) MISSED
triplet@96/108/120: grid=(_,3) OK
```

docstring(quantize.py:144-146)は「一様音符列では両系同点→事前分布中心から遠い三連曲は2分系に倒れうる」と限界を**正直に記録済み**。実測はこの記録を裏付ける(誠実)。ただし遅い三連曲(72/90)の失敗率は台帳に数字が無い → ダッシュボードに実測を追記すべき。

---

## P0/P1 集計

- **stem:** P0×2(S1/S2 SNR推定器の破綻)・P1×2(S3/S4 NaN/Infガード)
- **ear:** P0×1(E1 ビブラート消失)・P1×3(E2低音・E3契約ガード・E4型検査欠如)
- **rhythm:** P0×0・P1×5(R1/R2ガード・R3/R4範囲外倍化・R5遅い三連)

**合計 P0×3 / P1×10。** ベースライン172テストは全て緑=これら欠陥は**現行テストの盲点**。

---

## ダッシュボード行案(docs/quality/function-dashboard.md 追記用)

| 機能 | 現在スコア(実測根拠) | 既知の限界(正直リスト) | 次の改善候補 |
|------|----------------------|------------------------|-------------|
| **stem** | ★★☆☆☆ SNR推定が持続音で破綻(0〜182dbの非物理値)。頑健性は高(クリップ/DC/8k/48k/無音/極短は全て非クラッシュ) | (1)`_estimate_snr_db`は無音率検出器で持続音=very_noisy誤判定 (2)NaN/Inf非ガード (3)非有限srを黙認 | 真のスペクトルSNR(雑音床の周波数推定)へ置換 or 名称を`silence_ratio`に正直化しdocstringの≈9飽和主張を撤回。非有限値の境界ガード追加 |
| **ear** | ★★☆☆☆ 静止純音A4は正確(midi69 conf0.94)だがビブラート/低音/揺れる音=常態が消失 | (1)ビブラート±0.25半音でも0 events(整数丸めでセグメント断片化) (2)FMIN帯の低音がmin_conf=0.5で全滅 (3)fmin/fmax・worker JSONの契約ガードが型/範囲を検査せず | pitch trackに中央値平滑化/ヒステリシスを入れ揺れを1音に束ねる。低音域はmin_conf適応。`_validate_worker_json`に型・範囲検査追加 |
| **rhythm** | ★★★☆☆ 事前分布中心(96-120BPM)の2分/3分系は正確・弱起も頑健。範囲外と遅い三連で破綻 | (1)quantize_eventsがbpm=0で例外/負bpmで負start (2)60-180範囲外テンポは倍/半に化け音価まで破壊 (3)72/90の三連符は2分系に誤倒れ(台帳に失敗率数字なし) | quantize_eventsにbpm>0ガード。BPM探索範囲を拡張 or 範囲外を検出して警告。遅い三連の実測失敗率をダッシュボードに追記 |

---

## 最重要発見(1つに絞るなら)

**stem の `_estimate_snr_db`(field.py:31)がSNR推定器を騙るが実体は「音の途切れ率」**。クリーンな持続音を `very_noisy` と誤判定し(snr=0.0)、下流 field_select の過絞りを誤発動させて良品を殺す。しかも FieldAnalysis/FieldReport のdocstringが主張する「≈9飽和」は実測(0〜182)と完全に食い違い、**錨2(主張と実態の一致)に真正面から抵触**する。172テストはこれを一切検出していない。
