"""F-008 複数ファイル一括採譜キュー(Issue #108)。

先行研究(docs/research/upcoming/F-008-{grok,codex}.md)の失敗例を反映した最小実装。

反映した pitfalls:
- 並列実行はOOMを招く(grok 3.9 @omriariav / codex 2.1)。既定は直列(concurrency=1)。
- 1つの不正ファイルがbatch全体を殺す(codex basic-pitch #31: 4→1 Aborted)。
  → 各itemを独立ジョブとして扱い、1件失敗しても継続して部分失敗を記録する。
- サイレント品質崩壊・decode例外の握り潰し(codex 2.2)。
  → 例外は握り潰さず error 文字列として記録し、成功/失敗を明示フラグで返す。
- 親batchが子の実状態とズレる(codex Sidekiq batches)。
  → 集計はitemごとのBatchJob状態を唯一の真実として組み立てる。
- transcribe_fn を注入することでモデル依存を切り離しテスト可能にする(codex 3.2)。

原理的限界(notesにも明記): 本モジュールはキューの制御(直列実行・失敗隔離・
進捗通知)のみを担う。GPU VRAM監視・chunk一貫性検査・crash recovery/DLQ・
idempotency commit といった重い運用機構は、本spikeの純Python軽量依存の範囲外で
あり未実装。採譜精度そのもの(50%/10%帯・chunk継ぎ目不一致)は transcribe_fn 側の
責務であり、キュー層では改善できない。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Literal, Optional

# ジョブ状態(codex 1: per-item state)。QUEUED→RUNNING→(SUCCEEDED|FAILED)。
JobStatus = Literal["queued", "running", "succeeded", "failed"]

# 採譜関数の型: 入力パスを受け取り任意の成果物を返す(戻り値は使わず成否のみ判定)。
TranscribeFn = Callable[[str], object]
# 進捗コールバックの型: 各ジョブ完了時に確定済みBatchJobを受け取る。
ProgressFn = Callable[["BatchJob"], None]


@dataclass(frozen=True)
class BatchJob:
    """一括採譜キュー内の1入力ファイルに対応する不変ジョブ(C3・ADR-001準拠)。

    - input_path: 採譜対象の入力パス(同一性キー)。
    - status: 現在の状態(queued/running/succeeded/failed)。
    - error: 失敗時の例外メッセージ。成功・未実行時は None。

    不変性(coding-style CRITICAL): 状態遷移は replace で新インスタンスを生成し、
    既存インスタンスは決して破壊的に更新しない。
    """

    input_path: str
    status: JobStatus = "queued"
    error: Optional[str] = None


def _run_one(job: BatchJob, transcribe_fn: TranscribeFn) -> BatchJob:
    """単一ジョブを実行し、成否を反映した新しいBatchJobを返す(失敗を隔離)。

    transcribe_fn がどのような例外(decode不正・OOM・非対応format等)を投げても
    ここで捕捉し、error に文字列化して FAILED 状態の新インスタンスを返す。
    こうすることで1件の失敗がキュー全体を止めないことを保証する
    (codex basic-pitch #31 の "1つが全滅させる" 失敗への対策)。
    """
    running = replace(job, status="running", error=None)
    try:
        transcribe_fn(running.input_path)
    except BaseException as exc:  # noqa: BLE001 - 部分失敗の隔離が目的。全例外を記録して継続。
        # KeyboardInterrupt 等の BaseException もキューを黙って壊さないよう記録する。
        # ただし詳細traceback抑制のため型名+メッセージのみ保持(ログ肥大を防ぐ)。
        message = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        return replace(running, status="failed", error=message)
    return replace(running, status="succeeded", error=None)


def run_batch(
    input_paths: list[str],
    transcribe_fn: TranscribeFn,
    on_progress: Optional[ProgressFn] = None,
) -> list[dict]:
    """入力パス群を直列に採譜し、item単位の結果リストを返す。

    Args:
        input_paths: 採譜対象パスのリスト。空リストは空結果を返す(no-op)。
        transcribe_fn: 単一パスを採譜する注入関数。例外送出で失敗扱いになる。
        on_progress: 各ジョブ確定時に呼ばれる任意コールバック。確定済みBatchJobを
            受け取る。コールバック内の例外はキュー継続のため捕捉・無視する
            (通知失敗が採譜バッチを止めてはならない)。

    Returns:
        入力と同順の結果辞書リスト。各要素は
        ``{"input": str, "ok": bool, "error": str | None}``。
        ok=True は SUCCEEDED、ok=False は FAILED を表し、
        1件失敗しても残りは処理を継続する(部分失敗の記録)。

    Raises:
        TypeError: input_paths が list でない、または transcribe_fn が
            呼び出し可能でない場合(境界での入力検証・fail fast)。

    設計根拠(先行研究): 並列化はOOMを招くため既定で直列(grok 6.1 / codex 3-4)。
    親batchは集計のみを持ち、各itemを独立ジョブ化する(codex 3-2)。
    """
    # 入力検証(coding-style: 境界で検証・fail fast)。
    if not isinstance(input_paths, list):
        raise TypeError("input_paths は list[str] である必要があります。")
    if not callable(transcribe_fn):
        raise TypeError("transcribe_fn は呼び出し可能である必要があります。")

    results: list[dict] = []
    for input_path in input_paths:
        job = BatchJob(input_path=input_path, status="queued")
        done = _run_one(job, transcribe_fn)

        if on_progress is not None:
            # 進捗通知の失敗でキューを止めない(観測層の障害を採譜から隔離)。
            try:
                on_progress(done)
            except Exception:  # noqa: BLE001 - 通知失敗はバッチ本流に伝播させない。
                pass

        results.append(
            {
                "input": done.input_path,
                "ok": done.status == "succeeded",
                "error": done.error,
            }
        )

    return results
