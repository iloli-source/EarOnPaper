"""CLIサブコマンド(chunk / diff / compare)の結線テスト(#109 残オーファン)。

emitter の「単一副次出力」に収まらない3機能を、実採譜フロー(pipeline.main)から
到達可能にしたことを end-to-end で固定する。
- chunk: 長尺分割(F-004) split_into_chunks / Chunk
- diff:  譜面差分 diff_notes
- compare: AIの耳比較 run_compare / build_compare_command(外部ツールはmock)
"""

import json
import types

from earpipe import pipeline


def test_chunk_writes_nonempty_wavs(simple_wav, tmp_path):
    # Arrange
    wav_path, _melody, _bpm = simple_wav
    out_dir = tmp_path / "chunks"

    # Act
    rc = pipeline.main(["chunk", str(wav_path), "--out-dir", str(out_dir), "--max-sec", "600"])

    # Assert: 少なくとも1チャンクの非空wavが出る(短尺は1チャンク)
    assert rc == 0
    wavs = sorted(out_dir.glob("chunk_*.wav"))
    assert len(wavs) >= 1
    for w in wavs:
        assert w.stat().st_size > 0


def test_diff_of_identical_source_has_no_changes(simple_wav, tmp_path):
    """同一音源を A/B に渡すと採譜は決定的なので全音符が match(差分なし)。

    diff_notes は match も含めて分類を返す(音符の対応が付いた=match)。同一入力では
    add/remove/pitch_change/onset_shift 等の「実差分」が1件も無いことを確認する。
    """
    # Arrange
    wav_path, _melody, _bpm = simple_wav
    out = tmp_path / "diff.json"

    # Act
    rc = pipeline.main(
        ["diff", str(wav_path), str(wav_path), "-o", str(out), "--engine", "mono"]
    )

    # Assert: 全エントリが match、非matchの実差分は0
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["diff_count"] >= 1  # 音符があれば match エントリが並ぶ
    non_match = [d for d in payload["diffs"] if d.get("type") != "match"]
    assert non_match == [], f"同一音源なのに実差分が出た: {non_match}"


def test_compare_relays_returncode(monkeypatch, tmp_path):
    """compare は外部 ai-ears を起動する。ここでは run_compare をmockし中継を検証。"""
    # Arrange: run_compare を偽の CompletedProcess を返す関数に差し替え
    calls = {}

    def _fake_run_compare(original, transcription, report=None):
        calls["args"] = (str(original), str(transcription), report)
        return types.SimpleNamespace(stdout="F1=0.9\n", stderr="", returncode=0)

    monkeypatch.setattr(pipeline, "run_compare", _fake_run_compare)
    orig = tmp_path / "orig.wav"
    orig.write_bytes(b"x")
    trans = tmp_path / "t.musicxml"
    trans.write_text("<score/>", encoding="utf-8")

    # Act
    rc = pipeline.main(["compare", str(orig), str(trans)])

    # Assert: 終了コードを中継し、正しい引数で呼ばれた
    assert rc == 0
    assert calls["args"][0] == str(orig)
    assert calls["args"][1] == str(trans)
