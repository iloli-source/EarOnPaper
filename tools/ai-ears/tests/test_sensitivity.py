"""感度検証(synth_test.pyの7項目のpytest化)。

正解が既知の合成音源に対し、崩し方に応じてスコアが正しい序列で下がることを検証する。
ハーネス自体の信頼性の根拠なので、この7項目は synth_test.py と同一条件を維持する。
"""

import pytest


@pytest.mark.unit
class TestSensitivityOrdering:
    def test_identical_is_best(self, sensitivity_scores):
        s = sensitivity_scores
        best = max(v["overall"] for v in s.values())
        assert s["same"]["overall"] == best, "同一MIDIが最高スコアであるべき"

    def test_identical_beats_pitch_mutation(self, sensitivity_scores):
        assert sensitivity_scores["same"]["overall"] > sensitivity_scores["pitch_mut"]["overall"]

    def test_identical_beats_rhythm_mutation(self, sensitivity_scores):
        assert sensitivity_scores["same"]["overall"] > sensitivity_scores["rhythm_mut"]["overall"]

    def test_pitch_mutation_beats_unrelated(self, sensitivity_scores):
        assert sensitivity_scores["pitch_mut"]["overall"] > sensitivity_scores["unrelated"]["overall"]

    def test_rhythm_mutation_beats_unrelated(self, sensitivity_scores):
        assert sensitivity_scores["rhythm_mut"]["overall"] > sensitivity_scores["unrelated"]["overall"]

    def test_identical_above_08(self, sensitivity_scores):
        assert sensitivity_scores["same"]["overall"] >= 0.8

    def test_unrelated_below_06(self, sensitivity_scores):
        assert sensitivity_scores["unrelated"]["overall"] < 0.6


@pytest.mark.unit
class TestSensitivityMetricLevel:
    """総合だけでなく指標単位でも崩しに反応していること。"""

    def test_pitch_mutation_lowers_chroma(self, sensitivity_scores):
        assert sensitivity_scores["pitch_mut"]["chroma"] < sensitivity_scores["same"]["chroma"]

    def test_rhythm_mutation_lowers_onset(self, sensitivity_scores):
        assert sensitivity_scores["rhythm_mut"]["onset"] < sensitivity_scores["same"]["onset"]

    def test_all_scores_in_valid_range(self, sensitivity_scores):
        for case, metrics in sensitivity_scores.items():
            for name, score in metrics.items():
                if score is None:  # tempoは評価不能を許容する仕様
                    continue
                assert 0.0 <= score <= 1.0, f"{case}.{name}={score} が[0,1]の外"
