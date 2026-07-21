"""F-008 一括採譜キュー run_batch/BatchJob のテスト(AAA形式)。

先行研究の失敗例を検証観点に落とし込む:
- 部分失敗の隔離(basic-pitch #31: 1件失敗でも継続)。
- 直列処理・入力順序保持。
- 進捗通知が呼ばれ、通知失敗がキューを止めないこと。
- 例外種別を問わず error に記録し成否フラグで返すこと。
"""

import dataclasses

import pytest

from earpipe.services.batch_queue import BatchJob, run_batch


def test_all_succeed_returns_ok_results_in_order() -> None:
    # Arrange
    inputs = ["a.wav", "b.wav", "c.wav"]
    seen: list[str] = []

    def transcribe(path: str) -> str:
        seen.append(path)
        return f"score:{path}"

    # Act
    results = run_batch(inputs, transcribe)

    # Assert
    assert seen == inputs  # 直列・入力順で処理
    assert [r["input"] for r in results] == inputs
    assert all(r["ok"] for r in results)
    assert all(r["error"] is None for r in results)


def test_partial_failure_is_isolated_and_queue_continues() -> None:
    # Arrange: 2番目だけ失敗させ、後続が継続することを検証(basic-pitch #31 対策)
    inputs = ["ok1.wav", "bad.wav", "ok2.wav"]

    def transcribe(path: str) -> str:
        if path == "bad.wav":
            raise ValueError("decode failed")
        return "score"

    # Act
    results = run_batch(inputs, transcribe)

    # Assert
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
    assert results[1]["error"] == "ValueError: decode failed"
    assert results[2]["ok"] is True  # 失敗後も処理継続


def test_on_progress_called_per_job_with_confirmed_status() -> None:
    # Arrange
    inputs = ["x.wav", "y.wav"]
    progressed: list[BatchJob] = []

    def transcribe(path: str) -> None:
        if path == "y.wav":
            raise RuntimeError("boom")

    # Act
    run_batch(inputs, transcribe, on_progress=progressed.append)

    # Assert
    assert [j.input_path for j in progressed] == inputs
    assert progressed[0].status == "succeeded"
    assert progressed[1].status == "failed"
    assert progressed[1].error == "RuntimeError: boom"


def test_progress_callback_failure_does_not_stop_batch() -> None:
    # Arrange: 通知コールバックが毎回例外を投げても本流は完走する
    inputs = ["1.wav", "2.wav"]

    def transcribe(path: str) -> str:
        return "score"

    def bad_progress(_job: BatchJob) -> None:
        raise KeyError("progress sink down")

    # Act
    results = run_batch(inputs, transcribe, on_progress=bad_progress)

    # Assert
    assert len(results) == 2
    assert all(r["ok"] for r in results)


def test_empty_input_is_noop() -> None:
    # Arrange
    calls: list[str] = []

    # Act
    results = run_batch([], lambda p: calls.append(p))

    # Assert
    assert results == []
    assert calls == []


def test_base_exception_is_recorded_not_propagated() -> None:
    # Arrange: KeyboardInterrupt(BaseException) でもキューを黙って壊さない
    inputs = ["k.wav", "next.wav"]

    def transcribe(path: str) -> None:
        if path == "k.wav":
            raise KeyboardInterrupt()

    # Act
    results = run_batch(inputs, transcribe)

    # Assert
    assert results[0]["ok"] is False
    assert results[0]["error"] == "KeyboardInterrupt"
    assert results[1]["ok"] is True


def test_batchjob_is_frozen_and_defaults() -> None:
    # Arrange
    job = BatchJob(input_path="song.wav")

    # Act / Assert: 既定値と不変性(frozen)を確認
    assert job.status == "queued"
    assert job.error is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        job.status = "running"  # type: ignore[misc]


def test_input_validation_rejects_non_list_and_non_callable() -> None:
    # Arrange / Act / Assert
    with pytest.raises(TypeError):
        run_batch("not-a-list", lambda p: None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        run_batch(["a.wav"], object())  # type: ignore[arg-type]
