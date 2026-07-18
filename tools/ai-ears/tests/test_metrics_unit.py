"""ears.py 各指標関数の境界ケースのユニットテスト。"""

import copy

import numpy as np
import pretty_midi
import pytest
import soundfile as sf

import ears
import synth_test


def make_pm(notes_spec, bpm=100, drum=False, program=0):
    """(pitch, start, end) のリストからPrettyMIDIを作る。"""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=program, is_drum=drum)
    for pitch, start, end in notes_spec:
        inst.notes.append(
            pretty_midi.Note(velocity=90, pitch=pitch, start=start, end=end)
        )
    pm.instruments.append(inst)
    return pm


# ---------------------------------------------------------------- 読み込み系

@pytest.mark.unit
class TestLoaders:
    def test_load_audio_missing_file_raises(self, tmp_path):
        with pytest.raises(Exception):
            ears.load_audio(str(tmp_path / "not-exist.wav"))

    def test_load_audio_empty_raises(self, tmp_path):
        path = tmp_path / "empty.wav"
        sf.write(path, np.zeros(0, dtype=np.float32), ears.SR)
        with pytest.raises(ValueError, match="音声が空"):
            ears.load_audio(str(path))

    def test_load_midi_no_notes_raises(self, tmp_path):
        path = tmp_path / "empty.mid"
        pretty_midi.PrettyMIDI(initial_tempo=100).write(str(path))
        with pytest.raises(ValueError, match="音符がありません"):
            ears.load_midi(str(path))

    def test_load_midi_drum_only_raises(self, tmp_path):
        """ドラムトラックのみのMIDIは音程ノートなし扱い(仕様)。"""
        path = tmp_path / "drums.mid"
        make_pm([(36, 0.0, 0.1), (38, 0.5, 0.6)], drum=True).write(str(path))
        with pytest.raises(ValueError, match="音符がありません"):
            ears.load_midi(str(path))

    def test_load_midi_broken_file_raises(self, tmp_path):
        path = tmp_path / "broken.mid"
        path.write_bytes(b"this is not a midi file")
        with pytest.raises(Exception):
            ears.load_midi(str(path))

    def test_synthesize_midi_normalized(self, reference_pm):
        audio = ears.synthesize_midi(reference_pm)
        assert len(audio) > 0
        assert np.max(np.abs(audio)) <= 1.0 + 1e-6


# ---------------------------------------------------------------- 指標1: クロマ

@pytest.mark.unit
class TestChromaSimilarity:
    def test_identical_audio_high(self, reference_pm):
        y = ears.synthesize_midi(reference_pm)
        result = ears.chroma_similarity(y, y)
        assert result["score"] >= 0.9

    def test_score_in_range_for_noise_pair(self):
        rng = np.random.default_rng(0)
        y1 = rng.standard_normal(ears.SR * 2).astype(np.float32)
        y2 = rng.standard_normal(ears.SR * 2).astype(np.float32)
        result = ears.chroma_similarity(y1, y2)
        assert 0.0 <= result["score"] <= 1.0


# ---------------------------------------------------------------- 指標2: 出だし一致

@pytest.mark.unit
class TestOnsetMatch:
    def test_silent_audio_returns_zero(self):
        y = np.zeros(ears.SR * 2, dtype=np.float32)
        pm = make_pm([(60, 0.0, 0.5)])
        result = ears.onset_match(y, pm.instruments[0].notes)
        assert result["score"] == 0.0
        assert "検出できません" in result["explanation"]

    def test_single_note_perfect_case(self, tmp_path):
        pm = make_pm([(69, 0.5, 1.0)])
        path = synth_test.render_sine(pm, tmp_path / "one.wav")
        y, _ = ears.load_audio(str(path))
        result = ears.onset_match(y, pm.instruments[0].notes)
        assert 0.0 <= result["score"] <= 1.0
        assert result["precision"] >= 0.0 and result["recall"] >= 0.0

    def test_ghost_notes_lower_precision(self, reference_audio, reference_pm):
        """幽霊音符(実音のない位置の音符)を足すとprecisionが下がる。"""
        y, _ = ears.load_audio(str(reference_audio))
        clean = ears.onset_match(y, reference_pm.instruments[0].notes)

        ghosted = copy.deepcopy(reference_pm)
        rng = np.random.default_rng(1)
        end_time = ghosted.get_end_time()
        for _ in range(120):
            t = float(rng.uniform(0, end_time)) + 0.033  # 格子から外す
            ghosted.instruments[0].notes.append(
                pretty_midi.Note(velocity=60, pitch=72, start=t, end=t + 0.05)
            )
        result = ears.onset_match(y, ghosted.instruments[0].notes)
        assert result["precision"] < clean["precision"]


# ---------------------------------------------------------------- 指標3: テンポ整合

@pytest.mark.unit
class TestTempoConsistency:
    def test_matching_tempo_high(self, reference_audio, reference_pm):
        y, _ = ears.load_audio(str(reference_audio))
        result = ears.tempo_consistency(y, reference_pm)
        if result["score"] is None:
            pytest.skip("この素材ではテンポ推定不能(仕様上は総合から除外)")
        assert result["score"] >= 0.7

    def test_double_tempo_tolerated(self, reference_audio):
        """倍テンポ表記のMIDIは許容される(仕様)。"""
        y, _ = ears.load_audio(str(reference_audio))
        pm_double = synth_test.build_midi(synth_test.MELODY, bpm=synth_test.BPM * 2)
        result = ears.tempo_consistency(y, pm_double)
        if result["score"] is None:
            pytest.skip("テンポ推定不能")
        assert result["score"] >= 0.7

    def test_wildly_wrong_tempo_low(self, reference_audio):
        y, _ = ears.load_audio(str(reference_audio))
        pm_wrong = synth_test.build_midi(synth_test.MELODY, bpm=333)
        result = ears.tempo_consistency(y, pm_wrong)
        if result["score"] is None:
            pytest.skip("テンポ推定不能")
        assert result["score"] < 0.9

    def test_midi_without_tempo_uses_default(self):
        """テンポイベントなしMIDIでも例外にならない。"""
        y = ears.synthesize_midi(synth_test.build_midi(synth_test.MELODY))
        pm = pretty_midi.PrettyMIDI()  # initial_tempoは内部で持つがget_tempo_changesは空になり得る
        pm.instruments.append(pretty_midi.Instrument(program=0))
        pm.instruments[0].notes.append(pretty_midi.Note(90, 60, 0.0, 1.0))
        result = ears.tempo_consistency(y, pm)
        assert result["score"] is None or 0.0 <= result["score"] <= 1.0


# ---------------------------------------------------------------- 指標4: 譜面健全性

@pytest.mark.unit
class TestScoreHealth:
    def test_healthy_score_no_issues(self, reference_pm):
        result = ears.score_health(reference_pm, reference_pm.instruments[0].notes)
        assert result["score"] >= 0.9
        assert result["issues"] == []

    def test_too_short_notes_flagged(self):
        notes = [(60 + (i % 12), i * 0.02, i * 0.02 + 0.005) for i in range(100)]
        pm = make_pm(notes)
        result = ears.score_health(pm, pm.instruments[0].notes)
        assert any("短い音符" in i for i in result["issues"])
        assert result["score"] < 0.9

    def test_out_of_range_pitch_flagged(self):
        pm = make_pm([(5, 0.0, 0.5), (110, 1.0, 1.5), (60, 2.0, 2.5)])
        result = ears.score_health(pm, pm.instruments[0].notes)
        assert any("音域外" in i for i in result["issues"])

    def test_dense_ghost_notes_flagged(self):
        rng = np.random.default_rng(2)
        notes = [
            (int(rng.integers(40, 90)), t, t + 0.15)
            for t in np.linspace(0, 2.0, 120)
        ]
        pm = make_pm(notes)
        result = ears.score_health(pm, pm.instruments[0].notes)
        assert any("密度" in i for i in result["issues"])


# ---------------------------------------------------------------- 総合・レポート

@pytest.mark.unit
class TestOverallAndReport:
    def _results(self, chroma, onset, tempo, health):
        return {
            "chroma": {"score": chroma, "explanation": ""},
            "onset": {"score": onset, "explanation": ""},
            "tempo": {"score": tempo, "explanation": ""},
            "health": {"score": health, "explanation": "", "issues": []},
        }

    def test_weighted_average(self):
        result = ears.overall(self._results(1.0, 1.0, 1.0, 1.0))
        assert result["score"] == 1.0
        assert result["excluded_metrics"] == []

    def test_tempo_none_excluded_not_punished(self):
        with_none = ears.overall(self._results(0.9, 0.9, None, 0.9))
        assert with_none["excluded_metrics"] == ["tempo"]
        assert with_none["score"] == pytest.approx(0.9, abs=1e-6)

    @pytest.mark.parametrize(
        "score,keyword",
        [(0.85, "高一致"), (0.7, "部分一致"), (0.3, "低一致")],
    )
    def test_verdict_boundaries(self, score, keyword):
        result = ears.overall(self._results(score, score, score, score))
        assert keyword in result["verdict"]

    def test_make_report_contains_scores_and_caveat(self):
        results = self._results(0.9, 0.8, 0.7, 0.6)
        results["health"]["issues"] = ["テスト用の指摘"]
        results["overall"] = ears.overall(results)
        report = ears.make_report(results, "orig.wav", "trans.mid")
        assert "総合スコア" in report
        assert "テスト用の指摘" in report
        assert "音楽家の耳の代替ではない" in report
