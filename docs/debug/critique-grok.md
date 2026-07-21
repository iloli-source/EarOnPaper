チェックリストと本体コードを読み、根拠付きで厳しくレビューします。まず観点表とディレクトリ構成を把握します。既存のデバッグ報告と本体エントリポイントを並行で読み、配線・孤立コードを洗い出します。配線と孤立モジュールを静的に洗い出すため、pipeline 全体と import グラフを調べます。孤立機能と本番経路の境界不備を、ソース根拠付きで深掘りします。コード根拠を揃えて、重要度順のダメ出し報告書をまとめます。# EarOnPaper 厳格デバッグ／レビュー報告

**対象:** `spike/ear-pipeline/earpipe`（本体）+ `app/`（Electron）  
**観点:** `docs/debug/debug-checklist.md` A–H  
**方法:** ソース実読 + import グラフ静的解析（憶測での「未使用」判定は避ける）  
**前提:** EOP-DEBUG-20260721-001 の 21 項目はアプリ境界でかなり直っている。本報告はその**残存／構造的問題**に集中する。

---

## 総評

| 領域 | 評価 |
|------|------|
| Electron 境界（D/B/C/E） | 前回修正で改善。残は接続漏れ・CLI 機能未露出 |
| `pipeline.py` 本番経路 | **狭い**。耳→量子化→五線/MIDI/PDF/(TAB CLI) のみ |
| services 層 | **約 9,800 LOC が tests-only / ライブラリ止まり** |
| 偽成功リスク | 進捗 UI・要件台帳の「✅」が実配線より甘い |

`pipeline.py` が実際に import して使う記号は次だけである（`asdict`/`Path` 除く）:

`apply_postfilter`, `bp_python_path`, `choose_engine`, `detect_events`, `detect_events_adaptive`, `detect_events_poly`, `select_events`, `correct_tuning_file`, `to_score`, `write_midi`, `write_midi_raw`, `write_musicxml`, `write_pdf`, `write_tab_pdf`, `BPM_DEFAULT`, `GRID_PER_BEAT`, `anchor_to_zero`, `estimate_grid`, `estimate_tempo_map`, `quantize_events`, `MELODIC_STEMS`, `STEMS`, `analyze_field`, `denoise`, `load_audio`, `separate_stems`, `trim_leading_silence_file`

---

## CRITICAL

### 1. [H 機能接続 / C 偽成功] 進捗 UI は実質タイマーのみ（3.5 修正が未完成）

**根拠**

- `pipeline.py` の出力は終了時の **stdout JSON だけ**（行 343, 376）。ステージ用の stderr ログは無い。
- `app/main.js` は stderr を `transcribe-progress` に流す（行 170–175）。
- `app/renderer/app.js` は `detectStageFromLog` を接続済み（行 192–197）だが、キーワード（`librosa`/`quantize`/`engrave` 等）は **本番パイプラインが吐かない**。
- 同時に `STAGE_DELAYS` タイマー（行 14, 186–190）が残っており、実ログ無しでも 4s/14s/24s/34s でステージが進む。

**影響:** ユーザーに「音高検出中…」等と見せるが、実処理段階とは無関係。長尺 poly ではステージが先に 100% 近く行き、その後も待つ。

**修正案**

1. `transcribe_file` の各段階で `print(..., file=sys.stderr, flush=True)`（または構造化 JSON 行）を必ず出す。  
2. UI キーワードを実ログ文言に合わせる。  
3. タイマーはフォールバックに格下げし、実ログ受信後は無効化。  
4. 回帰: 「stderr に stage マーカーが出ること」の CLI テスト + renderer の unit。

---

### 2. [H / 要件嘘] F-108 field mode の分類ゲートが pipeline に未接続

**根拠**

| 実装 | 場所 | pipeline からの呼び出し |
|------|------|------------------------|
| `classify_segment` → `SoundEvent` | `stem/field.py:173–278` | **なし** |
| `gate_by_class` | `ear/field_select.py:40–52` | **なし** |
| `select_events(snr_db)` のみ | `pipeline.py:172–173` | あり |
| `denoise` | mono 経路のみ（`pipeline.py:136–137,168–169`） | poly はファイル直読み（doc 81–84 で自認） |

`docs/requirements/implementation-status.md` は F-108 を **✅** と記載（行 53）しているが、F-108 の中核である「6 タグ分類で音符化可否を決める」経路は **死んでいる**。  
動いているのは SNR 閾値の軽いフィルタだけ。

**修正案**

- A: セグメント単位で `classify_segment` → `gate_by_class` → 残った区間だけ検出、または検出後に時間ゲート。  
- B: 未接続なら台帳を 🟡 に直し、`gate_by_class` を public API から下げるか「実験的」と明示。  
- 最低限: `pipeline` から呼ばれる統合テスト（speech/noisy が譜面に載らないこと）。

---

### 3. [E ライフサイクル] `transcribe_file` の一時資源に try/finally がない

**根拠:** `pipeline.py:93–117, 205–210`

```python
stem_tmp_dir = Path(tempfile.mkdtemp(...))   # 途中で例外 → 削除されない
trimmed_path, ... = trim_leading_silence_file(...)
...
# 成功時のみ:
if tuned_tmp is not None: tuned_tmp.unlink(...)
if trim_tmp is not None: trim_tmp.unlink(...)
if stem_tmp_dir is not None: shutil.rmtree(...)
```

分離・トリム・チューニング補正・検出・記譜のどこで落ちても **一時 wav / stem ディレクトリが残留**する。

**修正案:** 本体を `try/finally` で囲み、`finally` で 3 種を必ず片付ける（`_run_separate_transcribe` 行 353–374 と同型）。

---

### 4. [E / バグ] `trim_tmp` 判定が `in_path_orig` 比較で壊れている

**根拠:** `pipeline.py:108–109`

```python
trimmed_path, trimmed_sec = trim_leading_silence_file(in_path)
trim_tmp = trimmed_path if trimmed_path != Path(in_path_orig) else None
```

`trim_leading_silence_file` の契約（`preprocess.py:48–49`）は **「カット不要なら入力 path を返す」**。  
`--stem` 時、カット不要だと `trimmed_path` は **stem の一時 wav** になり、`in_path_orig`（元音源）とは必ず異なる → `trim_tmp = stem パス` と誤認。

成功時は処理後に unlink するため致命傷になりにくいが、

- stem ファイルを「トリム一時」として消す誤った責務分担  
- 将来 `trim_tmp` を「処理中も残す」と扱うと即壊れる  
- `correct_tuning_file` は `corrected != trimmed` で正しく判定している（行 116）のに、trim だけ不整合

**修正案**

```python
src_for_trim = Path(in_path)
trimmed_path, trimmed_sec = trim_leading_silence_file(src_for_trim)
trim_tmp = trimmed_path if trimmed_path.resolve() != src_for_trim.resolve() else None
```

---

## HIGH

### 5. [H] ライブラリ実装だが pipeline / app から死んでいる機能群（約 9.8k LOC）

import グラフ上 **prod の呼び出し元が `__init__` / テストのみ** の代表。いずれも実装・単体テストはあるが **`transcribe_file` 経路に乗らない**。

| モジュール | 公開 API | 問題 |
|------------|----------|------|
| `ear/drums.py` + `notate/drum_notation.py` | `detect_drums` / `drums_to_musicxml` | `separate-transcribe --include-drums` は **音程検出を drums に適用**（`pipeline.py:365–367`）。ドラム譜経路なし |
| `rhythm/midi_cleanup.py` | `cleanup_notes` | 記譜前クリーンアップが未接続 |
| `ear/velocity.py` | `estimate_velocities` | 速度は `confidence` からの式（`score.py:411`）のまま |
| `ear/pedal.py` | `detect_sustain*` | サスティン未記譜 |
| `ear/instrument_classify.py` | `classify_instrument` | 楽器推定結果がプロファイル／記譜に未反映 |
| `ear/hints.py` | `apply_hints` | CLI/app にヒント入力なし |
| `stem/diagnose.py` | `diagnose_audio` | 音質警告が app に出ない |
| `stem/chunk.py` | `split_into_chunks` | 長尺分割が pipeline に未配線 |
| `stem/genai_preset.py` / `region_select.py` | preprocess / crop | 未使用 |
| `rhythm/rebar.py` | `correct_beat_offset` | 未使用 |
| `batch_queue.py` | `run_batch` | CLI/app 未接続 |
| `quality/client.py` | `run_compare` | 品質ループ未接続 |
| notate の大半 | jianpu/leadsheet/GP/UST/LLM/運指/装飾/handoff 等 | CLI フラグも app も無し（`write_tab_pdf` のみ CLI `--tab`） |

**修正案（方針を選べ）**

1. **Wire:** 最小でも `cleanup_notes` → `to_score` 前、drums は `detect_drums`→`drums_to_musicxml`、diagnose を JSON に載せる。  
2. **Quarantine:** `services/*/experimental/` へ移し、`__init__` の巨大 re-export を削減。  
3. **台帳:** `implementation-status.md` の ✅ を「ライブラリ実装・本番未配線」に書き換える（現状は **C 偽成功**）。

---

### 6. [H / ドキュメント偽成功] 要件台帳が「関数がある＝実装済」になっている

**根拠:** `implementation-status.md` 例

- F-002 音質診断 ✅（`diagnose.py`）→ pipeline 未呼び出し  
- F-004 chunk ✅ → 未呼び出し  
- F-015 楽器分類 ✅ → 未呼び出し  
- F-078 奏法検出 ✅（`technique.py`）→ 未呼び出し  
- F-052 MusicXML 検証 ✅ → `write_musicxml` 後に `validate_musicxml` を **呼ばない**（validate は handoff 内部と tests のみ）

**修正案:** 判定基準を「`pipeline.py` または `app` からの到達可能経路があるか」に変更。ライブラリのみは 🟡。

---

### 7. [B クロスプラットフォーム] Python 側の POSIX 固定パスが残存

| 箇所 | 内容 |
|------|------|
| `ear/poly.py:27–29` | `_BP_PYTHON_CANDIDATES` が全て `.../bin/python` |
| `quality/client.py:17` | `_AI_EARS / ".venv" / "bin" / "python"` 固定 |

Electron 側の `platform-utils.js` は Win/POSIX 対応済み（3.2/3.6）。**エンジン本体と quality クライアントは未追随**。  
`EARPIPE_BP_PYTHON` が無い Windows では poly が `bp_python_path() is None` → auto は mono 退避、明示 poly は RuntimeError。

**修正案:** `platform-utils` と同型の候補生成を Python に移植（`Scripts/python.exe` vs `bin/python`）。`quality/client` は `sys.executable` または env 優先。

---

### 8. [H] Electron app が CLI 機能の大半を固定／未露出

**根拠:** `main.js:141–150` と `renderer/app.js:200`

```javascript
const result = await window.earpipe.transcribe(filePath, 'auto', title)
// args: transcribe, -o, --pdf, --midi, --engine only
```

未接続の CLI 機能:

- `--field-mode` / `--stem` / `--sensitivity` / `--postfilter` / `--timing`  
- `--tab` / `--tab-plain` / `separate-transcribe`  
- engine 選択 UI なし（常に `'auto'`）

**preload** の `openExternal`（`preload.js:8`）は **renderer から未使用**（grep ヒットは定義のみ）。IPC と権限チェックだけが生きた死コード。

**修正案:** 必要機能だけ UI + IPC 引数を増やす。不要なら `openExternal` を削除。TAB/stem は少なくとも advanced メニューで CLI パリティを。

---

### 9. [A 境界値] 量子化・raw MIDI の非有限値ガードが不完全

**jianpu** は 3.12 で `math.isfinite` 対応済み（`jianpu.py:117`）。**本番必須経路は未対応**。

`quantize.py:266–267`:

```python
start_q = int(round(e.onset / grid))
dur_q = max(1, int(round((e.offset - e.onset) / grid)))
```

- `onset=NaN/Inf` → `ValueError` / `OverflowError`  
- `offset < onset` → 負 duration が `max(1, …)` で **1 格子の音符に化ける**（黙殺）

`score.py` `write_midi_raw:401–407`:

```python
if math.isnan(n.onset_sec) or math.isnan(n.offset_sec):
    # フォールバック
else:
    start = float(n.onset_sec)  # +Inf は isnan をすり抜け
```

`pitch=int(n.midi)` は 0–127 外・巨大値で pretty_midi 例外／不正 MIDI。

**修正案**

- `quantize_events` 入口で `isfinite(onset/offset)`・`offset>onset`・`0<=midi<=127` を検証／スキップ。  
- `write_midi_raw` は `math.isfinite`、pitch clamp。  
- RED テスト: NaN/Inf/inverted/midi=10**12。

---

### 10. [C] 空採譜でも「成功」しうる

**根拠**

- `pipeline` は `notes=[]` でも MusicXML/PDF/MIDI を書き得る（行 183–203）。  
- app の `ensureOutputs`（`main.js:66–78`）は **非空ファイル**のみ確認。`n_notes===0` でも成功 UI。  
- ユーザーは「採譜できた」と誤認。

**修正案:** `n_notes==0` を soft-fail（警告付き成功 or 明示エラー）にし、UI で「音符 0」を強調。オプションで empty を reject。

---

## MEDIUM

### 11. [H / 設計負債] `tempo_map` は計算されるが記譜に使われない

`pipeline.py:226–228` で `estimate_tempo_map` を JSON に載せる一方、`quantize_events` / `to_score` は単一 `bpm`。  
docstring に将来課題と明記（`tempo_map.py:13–15`）されているが、**「C2 実装済」と読むと偽成功**。台帳 F-017 は 🟡 で正しい。UI には `tempo_map` 非表示。

---

### 12. [G / 二重 API] ルートシムと services の二重公開

| ルート | 中身 |
|--------|------|
| `earpipe/ear.py` | → `services.ear.mono` |
| `earpipe/ear_poly.py` | → poly（**tests only**） |
| `earpipe/postfilter.py` | → postfilter（**tests only**） |
| `earpipe/quantize.py` / `notate.py` | シム |
| `earpipe/__init__.py` | 旧 API を re-export（import 時に mono/librosa を強制） |

`ear_poly` / ルート `postfilter` は本番 pipeline が `services.*` を直 import するため **消し忘れ候補**。  
`__init__.py` の eager import は、軽量ツールが `import earpipe.contracts` したつもりでも副作用が重い。

**修正案:** シムを非推奨警告付きに一本化、または削除計画。`__init__` は lazy / 薄い公開に。

---

### 13. [A] SNR 定数の二重定義（stale flag 予備軍）

- `stem/field.py:19–20` `_SNR_CLEAN_DB` / `_SNR_NOISY_DB`  
- `ear/field_select.py:11–12` 同値をコメント付き複製  

コメントは「変更時は両方」とあるが、コンパイラは強制しない。ズレると field 報告と選択フィルタが矛盾。

**修正案:** `contracts` または単一 `field_thresholds.py` に集約。

---

### 14. [D/E] `batch_queue` が `BaseException` を捕捉

`batch_queue.py:64–68` は `KeyboardInterrupt` / `SystemExit` も failed ジョブに変換。キュー用途では意図的だが、対話 CLI では Ctrl-C が効かない。配線時は `Exception` に戻し、interrupt は再送出。

---

### 15. [A/F] `estimate_tempo_map` の窓ループが長尺で重い

`tempo_map.py:58–68`: 各窓で全 events を線形スキャン → 概ね **O((T/window) × N)**。  
数時間音源 + 密イベントで結果 JSON 生成だけでも鈍化。chunk 未配線と組み合わさると悪化。

**修正案:** イベントをソート済み前提で two-pointer、または長尺は tempo_map をスキップ／間引き。

---

### 16. [D] ドラッグ＆ドロップ経路の UI 側検証欠落（main で再検証はあり）

renderer は drop 後すぐ `startTranscribe`（`app.js:144–151`）。main の `isAllowedAudioInput` で落ちるが、エラー表示まで行く。UX 上は drop 時に拡張子チェックしてよい（信頼境界の主検証は main のままで正しい）。

---

### 17. [C] `field_mode` の poly 降噪ギャップ（既知だが製品表示なし）

`pipeline.py:81–84` が正直に記録。app から field を出せない現状では実害は限定的だが、CLI ユーザーには「field を付けたのに poly では denoise されない」が分からない。結果 JSON に `field_mode_limitations: ["poly_no_denoise"]` を推奨。

---

## LOW / 静的品質 (G)

### 18. 未使用 import（実害小）

ルートシムで `from earpipe.contracts import PitchEvent` を読み、`__all__` 再 export のみでローカル未使用（`ear.py:3`, `quantize.py:3`）。Ruff F401。`# noqa: F401` を付けるか `__all__` 経由の明示 re-export に。

### 19. `openExternal` / 未使用 preload API

上述 HIGH-8。削除 or 「外部で開く」ボタン接続。

### 20. score の 4/4 固定前提の散在

`score.py:20–21` `TIME_SIGNATURE`、`tab.py:31` `_BEATS_PER_MEASURE = 4`。`estimate_meter` は score 内で使われるが TAB は 4/4 固定。拍子推定と TAB の不整合は部分実装として残る。

---

## 観点別サマリ（チェックリスト対応）

| 観点 | 判定 | 代表 issue |
|------|------|------------|
| A 境界値 | **残存** | quantize / write_midi_raw の NaN·Inf·inverted（#9） |
| B クロス PF | **残存** | poly/quality の `bin/python` 固定（#7） |
| C 偽成功 | **残存** | 進捗タイマー（#1）、空採譜成功（#10）、台帳 ✅（#6） |
| D 信頼境界 | 概ね OK | app IPC は allowlist+isFile。残は UX 層 |
| E ライフサイクル | **残存** | try/finally 欠如（#3）、trim_tmp 誤判定（#4） |
| F テスト性能 | 部分 | tempo_map O(T×N)（#15）。field convolve は修正済 |
| G 静的品質 | 中 | 巨大未配線 surface、シム二重化（#5,#12） |
| H 機能接続 | **最悪** | field 分類・drums・cleanup・velocity・app CLI パリティ |

---

## 推奨修正順序（影響 × コスト）

1. **即:** `transcribe_file` を try/finally + `trim_tmp` 判定修正（#3,#4）  
2. **即:** pipeline stderr ステージログ + タイマー格下げ（#1）  
3. **短:** quantize / MIDI 境界値ガード + テスト（#9）  
4. **短:** 台帳の ✅ を配線基準に修正（#6）— コードより先に嘘を止める  
5. **中:** `cleanup_notes` を quantize 後に配線；drums は pitch 経路を止めて専用経路 or 拒否（#5）  
6. **中:** field `classify_segment`+`gate_by_class` を wire か experimental 降格（#2）  
7. **中:** poly/quality の Win パス（#7）  
8. **長:** app に field/stem/tab/engine、または死機能の削除・隔離

---

## やらないこと（本レビューの範囲外）

- 実装パッチの適用（調査・ダメ出し依頼のため未着手）  
- 全テスト実行（当環境に `librosa` 無しで earpipe import 不可）  
- Slack 投稿（接続 MCP に Slack が無く送信不能）

必要なら次ステップとして、上記 1–3 だけ **Plan → RED テスト → 最小パッチ** まで進められます。
