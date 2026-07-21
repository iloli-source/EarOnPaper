# バッチ処理（複数ファイルの一括採譜キュー）調査レポート（codex=論文・WEB担当、失敗例重視）

調査日: 2026-07-21
対象: AMT（Automatic Music Transcription）/ audio-to-MIDI / 楽譜化パイプラインにおける **複数ファイルの一括処理・ジョブキュー・チャンク処理**
分担: codex担当（論文＋WEB、失敗例を最大限）
方針: 実在ソースのみ・URL併記・憶測なし。英語・中国語中心。arXiv/IEEE(DOI)/GitHub Issues/公式ドキュメントを優先。job-queueエンジニアリング文献（Celery/Sidekiq/BullMQ/Triton等）も含む。

> 検証済みURL（WebFetchで実在・内容確認）: basic-pitch [#31](https://github.com/spotify/basic-pitch/issues/31)（4ファイル中1つだけ出力・他はAborted）, faster-whisper [#1257](https://github.com/SYSTRAN/faster-whisper/issues/1257)（batch80で19GB vs 通常11GB）, basic-pitch [#169](https://github.com/spotify/basic-pitch/issues/169)（MIDI再生でmemory/CPU/disk spike）, Omnizart JOSS DOI [10.21105/joss.03391](https://joss.theoj.org/papers/10.21105/joss.03391)。その他は既知の公式ドキュメント/論文一次ソース。

---

## 結論

採譜のバッチは「audio ingest → decode/resample → feature extraction → model inference → MIDI/MusicXML/score render → storage/通知」という**長いpipeline**であり、通常のジョブキュー障害に加えて、**音声長・サンプルレート・GPU VRAM・一時ファイル・出力整合性**が壊れやすい。したがってバッチ機能の価値は「高速に一括正解を出すこと」ではなく、**リソース枯渇の予防・部分失敗の隔離・item単位の進捗と復旧**にある。「フォルダを投げれば朝には完成譜が並ぶ」という設計は、リソース枯渇とサイレントな品質崩壊で高確率に破綻する。

---

## 1. 失敗モード一覧（リソース枯渇・部分失敗・進捗管理を厚めに）

| 失敗モード | 具体例 / 根拠 | 主因 | 実務的な対策 |
|---|---|---|---|
| 長尺音声を全件メモリ展開してOOM | `librosa.load` は音声を `np.ndarray` にロードし既定でresampleする（[librosa docs](https://librosa.org/doc/main/generated/librosa.load.html)） | `N files × duration × sample_rate × channels × feature copies` が積み上がる | 事前にduration/size上限。`soundfile.blocks()` 等のblock-wise読込（[SoundFile docs](https://python-soundfile.readthedocs.io/en/0.10.3post1/)） |
| batch size拡大でGPU VRAM枯渇 | Faster-WhisperのBatched推論で batch size 80 が **19GB**、通常Whisperは **11GB** の報告（[Issue #1257](https://github.com/SYSTRAN/faster-whisper/issues/1257)） | 音声長のばらつき・padding・mel/spec tensor・decoder cacheが同時常駐 | duration bucket、adaptive/縮退batch、GPUごとconcurrency=1、OOM時は小batchで再実行 |
| Worker数爆発で各workerがモデル重複ロード | Celeryは既定でCPU数ベースconcurrency（[Celery workers](https://docs.celeryq.dev/en/stable/userguide/workers.html)） | GPUモデルをprocessごとにloadしVRAM/RAMを線形消費 | GPU workerは専用queue＋`--concurrency=1`/GPU semaphore。CPU前処理とGPU推論を別queue化 |
| Prefetchで未処理タスクを抱えすぎる | Celeryはprefetch count次第で「メモリに収まらないメッセージ」まで予約し得る（[Celery optimizing](https://docs.celeryq.dev/en/latest/userguide/optimizing.html?highlight=prefetch)） | 長時間AMTジョブに短時間ジョブ向けprefetch設定を流用 | 長尺AMT queueは `worker_prefetch_multiplier=1`。短尺/長尺を別workerへroute |
| C拡張リークで徐々に死ぬ | Celeryは `max_tasks_per_child`/`max_memory_per_child` をメモリリーク対策に用意（[Celery workers](https://docs.celeryq.dev/en/stable/userguide/workers.html)） | TF/PyTorch/librosa/ffmpeg/codecが解放してもOSへ返さない | worker recycle、RSS/VRAM監視、1 job 1 process隔離、長尺処理後にworker再起動 |
| 一時ファイル・中間WAV・TFRecordでdisk full | Magenta Onsets&Framesのdataset生成は出力約 **19GB** と明記（[Magenta O&F README](https://github.com/magenta/magenta/blob/main/magenta/models/onsets_frames_transcription/README.md)） | mp3→wav展開・mel cache・MIDI/MusicXML/PNG/PDF同時生成 | job専用temp dir、quota、TTL cleanup、atomic rename、失敗時のmanifest reconciliation |
| SIGKILL/OOMで一時ファイルが残る | Python tempfileは高水準APIに自動cleanupがあるが低水準APIは手動（[Python tempfile](https://docs.python.org/3/library/tempfile.html)） | OOM killer/hard timeoutでは `finally` が走らない場合がある | 起動時に古いjob tempを掃除。`job_id/tmp/` 構造にして安全にGC |
| ブラウザ側MIDI再生でリソースspike | Basic Pitchサイトで再生数秒後にmemory/CPU/disk spike（[Issue #169](https://github.com/spotify/basic-pitch/issues/169)） | 推論後のMIDI render/playbackもresource consumer | preview低解像度化、巨大MIDIのノート数上限、Web Worker解放、停止時dispose |
| **1つの不正ファイルがbatch全体を殺す** | Basic Pitchで4ファイル中1つだけ出力、他はAbortedの報告（[Issue #31](https://github.com/spotify/basic-pitch/issues/31)） | multi-file CLIを単一process/単一exit codeで扱う | **1 file = 1 durable job**。親batchは集計のみ。失敗itemをFAILEDにして続行 |
| 無音・壊れたcodec・非対応formatがsilent skip | Basic Pitch issueはformat/length制限が不明なままabort（[Issue #31](https://github.com/spotify/basic-pitch/issues/31)） | decode例外を握りつぶす、stderrだけに出す、出力存在確認なし | preflight decode、duration/channels/sr記録、stderr保存、**出力checksum必須** |
| "成功"でも音楽的に壊れた出力 | Magenta O&F drumがColabで16kHz扱いになりhi-hat等が消える再現問題（[Magenta #1876](https://github.com/magenta/magenta/issues/1876)） | preprocessing条件が学習/論文/CLIとずれる | canonical audio specをmanifestに保存。modelごとにrequired sample rateを検証 |
| **OOM jobを再配信してpoison loop** | CeleryはOOM taskの再実行が高頻度message loopを起こし得ると警告（[Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)） | `acks_late` と自動retryを雑に有効化 | OOMは `Reject(requeue=False)` でDLQへ。再試行は「batch size縮小/分割」後に限定 |
| Retryで重複出力・孤児出力 | Celeryはlate ack時に複数回実行され得るのでidempotent必須（[Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)） | 出力pathが固定で途中生成物をcommit済み扱い | idempotency key = input hash + model version + params。tmp出力→atomic commit |
| **親batchが永遠にcompleteしない** | Sidekiq Batchesはjob lost/process killで stuck batch が起きる（[Sidekiq Batches](https://sidekiq.org/wiki/Batches)） | 親batchが子jobの実在状態とズレる | batch manifestをDBに持ち、queue状態だけに依存しない。reconcile jobを定期実行 |
| process crashで実行中job喪失 | Sidekiq OSSはprocess crash/memory limit killで実行中jobがlostになり得る（[Sidekiq Error Handling](https://sidekiq.org/wiki/Error-Handling)） | ack/fetch信頼性の限界 | reliable queue/visibility timeout/heartbeat lease。crash後はmanifestから再投入 |
| **started/stuckが見えない** | Celery `track_started` は既定falseで通常はpending/finished/retry粒度（[Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)） | 長時間AMTに粗いtask stateを流用 | per-item state: `QUEUED, DECODING, FEATURES, INFERING, EXPORTING, SUCCEEDED, FAILED, CANCELED` |
| CPU集約でlock更新できずstalled/二重実行 | BullMQはCPU busyでlock更新不能→stalled→再処理（[BullMQ stalled jobs](https://docs.bullmq.io/guide/workers/stalled-jobs)） | event loop/heartbeatがAMT処理に塞がれる | heavy workをsandbox/processへ逃がす。stalled監視＋idempotent出力 |
| **キャンセル不能でGPUを占有し続ける** | BullMQはAbortSignalベースのcancellationを推奨（[BullMQ cancelling jobs](https://docs.bullmq.io/guide/workers/cancelling-jobs)） | 推論/ffmpeg/exportの各stageがcancel checkしない | stage境界でcancel token確認。ffmpeg subprocess kill、GPU tensor解放、partial output破棄 |
| 進捗%が実感とズレる | Onsets and Frames supplementは高frame scoreでも聴感上悪い例を示す（[O&F supplement](https://storage.googleapis.com/magentadata/papers/onsets-frames/index.html)） | AMTのMIDIノート数・onset/offset・聴感が単純progressに乗らない | progressは `decode/features/inference/postprocess/export` のstage別。品質警告は別指標 |

---

## 2. カテゴリ別の掘り下げ

### 2.1 リソース枯渇（resource exhaustion）
- **GPU VRAM が最大のボトルネック。** batch sizeと音声長のばらつきが乗算的にVRAMを食う。faster-whisper #1257 の「batch80=19GB」は、AMTでも同型の危険を示す。GPU workerはconcurrency=1＋length bucket＋OOM時の自動縮退が基本形。
- **CPU側はメモリリークと一時ファイル。** librosaの全展開ロード、mp3→wav中間ファイル、mel cache、MusicXML/PDFレンダの多重生成でRAMとdiskの両方が枯渇する。Magentaのdataset生成が**19GB**出力になる例が「中間物のサイズは想像より桁が大きい」ことの実証。
- **worker多重化がモデルを重複ロードしてメモリを線形消費。** Celeryの既定concurrency（CPU数）でGPUモデルをprocessごとにloadすると即死する。CPU前処理queueとGPU推論queueの分離が必須。

### 2.2 部分失敗（partial failure）
- **単一processのmulti-file CLIは「1つ壊れると全滅」する。** basic-pitch #31 が典型（4→1）。バッチは必ず **item単位の耐久ジョブ**に分解し、親は集計だけを持つ。
- **poison message / retry暴走。** OOMを自動requeueすると同じジョブが延々と落ち続けてキューを塞ぐ（Celery警告）。分類retryが必須: decode不正/非対応format→**DLQ**、network/storage→backoff retry、OOM→**batch縮小/分割してから**限定retry、同一OOM連続→poison扱いでDLQ。
- **idempotency欠如で重複・孤児出力。** late ackで複数実行され得る前提で、`input hash + model version + params` をidempotency keyにし、tmp出力→検証→atomic commitにする。commit前の成果物は成功扱いしない。
- **サイレント品質崩壊。** decode成功でもsample-rate mismatch（Magenta #1876）や空MIDI・異常ノート数で「成功したが壊れた譜面」が量産される。夜間バッチほど目視QC前に積み上がる。

### 2.3 進捗管理・可観測性（progress / observability）
- **粗いtask stateの流用が最大の落とし穴。** Celeryは既定で `track_started=false`、pending/finished粒度しか無い。数分〜数十分かかるAMTには不足で、「動いているのか止まっているのか」が見えない。**per-item stage state + heartbeat**が必要。
- **stuck / crash lost。** Sidekiq Batches/Error Handlingが示す通り、process killで子jobがlostしても親batchはcompleteにならず永遠に待つ。**queue状態に依存せずmanifest(DB)基準でreconcile**するのが唯一の復旧手段。`RUNNING`かつheartbeat expiredなら再投入かFAILEDへ遷移。
- **キャンセル不能。** cancel tokenを各stage境界で確認しないと、GPUを掴んだまま停止できない（BullMQ）。ffmpeg subprocess killとGPU tensor解放をcancel時に必ず行う。
- **進捗%の意味。** frame scoreが高くても聴感が悪い（O&F supplement）ため、progress barと品質指標は分離する。

---

## 3. AMTバッチ設計の最小ベストプラクティス

1. **入力ごとにmanifest rowを作る**: `item_id, input_hash, model_version, params, duration, state, attempt, error_class, output_uri`。
2. **親batchは集計に徹し、推論は必ずper-item job化**する。
3. **enqueue前にリソース推定**: duration/sample_rate/channels/予測mel frames/予測VRAM/予測disk。
4. **GPU queueはlength bucket + bounded concurrency**。OOM時だけ自動で `batch_size↓` またはchunk分割。
5. **出力は `tmp/job_id/*` に生成→検証→atomic rename**。manifest commit前の成果物は成功扱いしない。
6. **retryを分類**: decode不正/非対応format→DLQ、network/storage→backoff、OOM→縮退retry、連続OOM→poison。
7. **進捗はbatch全体%でなくper-item stage + heartbeat**。stuck判定は「状態更新なしN分」。
8. **crash recoveryはqueueでなくmanifest基準**で再構築。`RUNNING`+heartbeat expired→再投入/FAILED。
9. **AMT固有の品質失敗も記録**: sample-rate mismatch、異常ノート数、空MIDI、極端なtempo、MusicXML export失敗。

---

## 4. 主要参考文献・一次ソース

- Omnizart（AMT汎用ツールボックス）JOSS DOI [10.21105/joss.03391](https://joss.theoj.org/papers/10.21105/joss.03391)
- Kong et al., High-resolution Piano Transcription, IEEE/ACM TASLP DOI [10.1109/TASLP.2021.3121991](https://doi.org/10.1109/TASLP.2021.3121991)
- Basic Pitch paper, [arXiv:2203.09893](https://arxiv.org/abs/2203.09893)
- MT3 (multi-task multitrack transcription) [GitHub](https://github.com/magenta/mt3)
- Magenta Onsets & Frames [README](https://github.com/magenta/magenta/blob/main/magenta/models/onsets_frames_transcription/README.md) / [O&F supplement](https://storage.googleapis.com/magentadata/papers/onsets-frames/index.html)
- ジョブキュー: [Celery workers](https://docs.celeryq.dev/en/stable/userguide/workers.html) / [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html) / [Celery optimizing](https://docs.celeryq.dev/en/latest/userguide/optimizing.html?highlight=prefetch) / [Sidekiq Batches](https://sidekiq.org/wiki/Batches) / [Sidekiq Error Handling](https://sidekiq.org/wiki/Error-Handling) / [BullMQ stalled jobs](https://docs.bullmq.io/guide/workers/stalled-jobs) / [BullMQ cancelling jobs](https://docs.bullmq.io/guide/workers/cancelling-jobs)
- GitHub Issues（検証済）: basic-pitch [#31](https://github.com/spotify/basic-pitch/issues/31) / [#169](https://github.com/spotify/basic-pitch/issues/169) / faster-whisper [#1257](https://github.com/SYSTRAN/faster-whisper/issues/1257) / Magenta [#1876](https://github.com/magenta/magenta/issues/1876)
- I/O: [librosa.load](https://librosa.org/doc/main/generated/librosa.load.html) / [SoundFile](https://python-soundfile.readthedocs.io/en/0.10.3post1/) / [Python tempfile](https://docs.python.org/3/library/tempfile.html)
