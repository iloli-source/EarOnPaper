"""マイク/ライン録音入力(F-005)のテスト。

実ハードウェアはCIに無いため、録音関数 `_record_audio` をmockして境界を検証する:
- sounddevice 未導入時は導入方法を示して失敗(黙って落ちない)
- 録音成功時は wav を書き出し、--transcribe で採譜まで通る
"""

import json

import numpy as np

from earpipe import pipeline


def test_record_missing_sounddevice_returns_hint(monkeypatch, tmp_path, capsys):
    # Arrange: sounddevice 未導入相当(RuntimeError)を模す
    def _raise(seconds, samplerate):
        raise RuntimeError("マイク録音には sounddevice が必要です: `pip install sounddevice`")

    monkeypatch.setattr(pipeline, "_record_audio", _raise)
    out = tmp_path / "rec.wav"

    # Act
    rc = pipeline.main(["record", "--out", str(out), "--seconds", "1"])

    # Assert: 導入方法を示して非ゼロ終了(黙って失敗しない)
    assert rc == 2
    assert "sounddevice" in capsys.readouterr().err


def test_record_writes_wav(monkeypatch, tmp_path):
    # Arrange: 1秒ぶんの無音を録音したことにする
    sr = 8000

    def _fake_record(seconds, samplerate):
        return np.zeros(int(seconds * samplerate), dtype="float32")

    monkeypatch.setattr(pipeline, "_record_audio", _fake_record)
    out = tmp_path / "rec.wav"

    # Act
    rc = pipeline.main(["record", "--out", str(out), "--seconds", "1", "--samplerate", str(sr)])

    # Assert: wav が非空で出力される
    assert rc == 0
    assert out.is_file() and out.stat().st_size > 0


def test_record_then_transcribe(monkeypatch, tmp_path, capsys):
    """--transcribe で録音→採譜まで通り、MusicXML が出る。"""
    # Arrange: 決定的な440Hz正弦波を「録音」したことにする
    sr = 16000

    def _fake_record(seconds, samplerate):
        t = np.linspace(0, seconds, int(seconds * samplerate), endpoint=False)
        return (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype("float32")

    monkeypatch.setattr(pipeline, "_record_audio", _fake_record)
    out = tmp_path / "rec.wav"

    # Act
    rc = pipeline.main(
        ["record", "--out", str(out), "--seconds", "1", "--samplerate", str(sr), "--transcribe"]
    )

    # Assert: 採譜結果の MusicXML が出力される
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "transcribed" in payload
    xml_path = tmp_path / "rec.musicxml"
    assert xml_path.is_file() and xml_path.stat().st_size > 0
