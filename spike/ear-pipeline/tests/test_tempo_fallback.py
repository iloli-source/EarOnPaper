"""#136: テンポ推定二段化(格子破綻→音響フォールバック)の回帰テスト。

実曲の歪みギターステムで poly 検出が高密度イベント(約18音/秒)を出すと
IOI格子フィットが破綻し、既定値120.0へ黙って退避していた(Mr. Big/
Dream Theater実測)。破綻時は音響ベース推定へフォールバックし、
出所(bpm_source)を正直に返すことを固定する。
"""

import numpy as np
import pytest

from earpipe.contracts import PitchEvent
from earpipe.services.rhythm.audio_tempo import estimate_audio_tempo
from earpipe.services.rhythm.quantize import (
    BPM_DEFAULT,
    GRID_PER_BEAT,
    estimate_grid_ex,
)


def ghost_storm_events(rate_per_sec: float = 18.0, dur_sec: float = 30.0,
                       seed: int = 136) -> list[PitchEvent]:
    """倍音の嵐(Mr. Bigギターステム型)の合成: 格子で説明できない稠密オンセット。"""
    rng = np.random.default_rng(seed)
    n = int(rate_per_sec * dur_sec)
    onsets = np.sort(rng.uniform(0.0, dur_sec, n))
    return [
        PitchEvent(float(t), float(t) + 0.08, int(rng.integers(40, 88)),
                   float(rng.uniform(0.2, 0.9)))
        for t in onsets
    ]


def steady_melody_events(bpm: float = 100.0, n: int = 32) -> list[PitchEvent]:
    """4分音符の規則的メロディ(格子フィットが成功する正常系)。"""
    spb = 60.0 / bpm
    return [
        PitchEvent(i * spb, i * spb + spb * 0.9, 60 + (i % 5), 0.9)
        for i in range(n)
    ]


class TestGridExFallback:
    def test_ghost_storm_without_fallback_returns_default(self):
        est = estimate_grid_ex(ghost_storm_events())
        assert est.source == "default"
        assert est.bpm == BPM_DEFAULT
        assert est.grid_per_beat == GRID_PER_BEAT

    def test_ghost_storm_with_fallback_uses_audio_bpm(self):
        est = estimate_grid_ex(ghost_storm_events(), fallback_bpm=lambda: 83.4)
        assert est.source == "audio"
        assert est.bpm == pytest.approx(83.4)

    def test_ghost_storm_fallback_none_falls_back_to_default(self):
        est = estimate_grid_ex(ghost_storm_events(), fallback_bpm=lambda: None)
        assert est.source == "default"
        assert est.bpm == BPM_DEFAULT

    def test_steady_melody_is_grid_and_fallback_not_called(self):
        called = []

        def spy():
            called.append(1)
            return 999.0

        est = estimate_grid_ex(steady_melody_events(100.0), fallback_bpm=spy)
        assert est.source == "grid"
        assert est.bpm == pytest.approx(100.0, abs=1.0)
        assert not called, "正常系でフォールバックが呼ばれてはいけない(遅延性)"

    def test_empty_events_use_fallback(self):
        est = estimate_grid_ex([], fallback_bpm=lambda: 90.0)
        assert est.source == "audio"
        assert est.bpm == pytest.approx(90.0)


def click_track(bpm: float, sr: int = 22050, dur_sec: float = 20.0) -> np.ndarray:
    """既知テンポの合成クリック(短い減衰バースト列)。"""
    y = np.zeros(int(sr * dur_sec), dtype=np.float32)
    step = 60.0 / bpm
    burst = (np.random.default_rng(0).standard_normal(256).astype(np.float32)
             * np.exp(-np.linspace(0, 8, 256)).astype(np.float32))
    t = 0.0
    while t < dur_sec - 0.1:
        i = int(t * sr)
        y[i:i + 256] += burst
        t += step
    return y


class TestPipelineBpmSource:
    def test_transcribe_reports_grid_source(self, simple_wav, tmp_path, capsys):
        """正常音源でJSONに bpm_source: grid が貫通する(#136統合)。"""
        import json

        from earpipe import pipeline

        wav_path, _melody, _bpm = simple_wav
        out_xml = tmp_path / "out.musicxml"
        rc = pipeline.main(
            ["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono"]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["bpm_source"] == "grid"

    def test_transcribe_override_reports_override_source(self, simple_wav, tmp_path, capsys):
        import json

        from earpipe import pipeline

        wav_path, _melody, _bpm = simple_wav
        out_xml = tmp_path / "out.musicxml"
        rc = pipeline.main(
            ["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono",
             "--bpm", "77"]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["bpm"] == 77.0
        assert payload["bpm_source"] == "override"


class TestAudioTempo:
    def test_click_track_100bpm(self):
        bpm = estimate_audio_tempo(click_track(100.0), 22050, 60.0, 180.0)
        assert bpm is not None
        assert bpm == pytest.approx(100.0, abs=3.0)

    def test_silence_returns_none(self):
        assert estimate_audio_tempo(np.zeros(22050 * 5, dtype=np.float32),
                                    22050, 60.0, 180.0) is None

    def test_octave_folds_into_range(self):
        # 60BPMのクリックを100-200の範囲で頼むと120(倍)へ折られる
        bpm = estimate_audio_tempo(click_track(60.0), 22050, 100.0, 200.0)
        assert bpm is not None
        assert bpm == pytest.approx(120.0, abs=5.0)
