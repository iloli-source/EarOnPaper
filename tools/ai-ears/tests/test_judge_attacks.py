"""審判(AIの耳)を騙す攻撃の回帰テスト — Issue #48。

func-r1-fable-output で実証された審判の穴3件を仕様として固定する:
1. オクターブ誤り: 全音+12の採譜が「高一致」になってはならない(register指標)
2. health崖: 密度をハード閾値(旧25音/秒)未満に整えたゴミが素通りしてはならない
3. score_rhythm: 正解MIDIあり運用では総合スコアに組み込まれなければならない
"""

import copy
import random

import numpy as np
import pytest
from conftest import CompareArgs

import ears


def _shift_octave(pm, semitones: int):
    pm2 = copy.deepcopy(pm)
    for inst in pm2.instruments:
        for n in inst.notes:
            n.pitch = int(np.clip(n.pitch + semitones, 0, 127))
    return pm2


def _scramble_rhythm(pm, seed: int = 7):
    """音高は保ったまま開始時刻をシャッフルする(音楽的には完全な誤り)。"""
    pm2 = copy.deepcopy(pm)
    rng = random.Random(seed)
    notes = pm2.instruments[0].notes
    total = max(n.end for n in notes)
    for n in notes:
        dur = max(0.08, n.end - n.start)
        n.start = rng.uniform(0.0, max(0.1, total - dur))
        n.end = n.start + dur
    notes.sort(key=lambda n: n.start)
    return pm2


@pytest.fixture(scope="module")
def baseline_result(reference_audio, reference_midi):
    return ears.cmd_compare(CompareArgs(reference_audio, reference_midi))


class TestOctaveAttack:
    """攻撃(a): 全音を1オクターブ上げた採譜(実務では完全な誤り)。"""

    @pytest.fixture(scope="class")
    def octave_result(self, workdir, reference_pm, reference_audio):
        pm_up = _shift_octave(reference_pm, +12)
        path = workdir / "attack_octave_up.mid"
        pm_up.write(str(path))
        return ears.cmd_compare(CompareArgs(reference_audio, path))

    def test_register_metric_exists(self, baseline_result):
        assert "register" in baseline_result, "register(音域一致)指標が存在すべき"

    def test_baseline_register_high(self, baseline_result):
        assert baseline_result["register"]["score"] is not None
        assert baseline_result["register"]["score"] >= 0.8, "同一MIDIの音域一致は高いべき"

    def test_octave_up_register_low(self, octave_result):
        assert octave_result["register"]["score"] is not None
        assert octave_result["register"]["score"] <= 0.5, (
            "1オクターブ上げは音域不一致として検出されるべき"
        )

    def test_octave_up_not_high_match(self, octave_result, baseline_result):
        assert octave_result["overall"]["score"] < 0.80, (
            "オクターブ誤りが『高一致』(0.80以上)と判定されてはならない"
        )
        assert octave_result["overall"]["score"] <= baseline_result["overall"]["score"] - 0.10, (
            "オクターブ誤りはbaselineから明確に減点されるべき"
        )


class TestDensityCliffAttack:
    """攻撃(b): 旧ハード閾値(25音/秒)未満に整えた幽霊音符の大群。"""

    @pytest.fixture(scope="class")
    def ghost_pm(self, reference_pm):
        import pretty_midi

        total = max(n.end for n in reference_pm.instruments[0].notes)
        pm = pretty_midi.PrettyMIDI(initial_tempo=100)
        inst = pretty_midi.Instrument(program=0)
        rng = random.Random(11)
        # 20音/秒 = 旧崖(25)の手前に整えたゴミ
        n_notes = int(total * 20)
        for i in range(n_notes):
            start = (i / 20.0) % total
            pitch = rng.randint(40, 90)
            inst.notes.append(
                pretty_midi.Note(velocity=70, pitch=pitch, start=start, end=start + 0.06)
            )
        pm.instruments.append(inst)
        return pm

    def test_ghost_mass_health_penalized(self, ghost_pm):
        notes = [n for inst in ghost_pm.instruments for n in inst.notes]
        health = ears.score_health(ghost_pm, notes)
        assert health["score"] < 0.8, (
            f"20音/秒×{len(notes)}個の幽霊はhealthで減点されるべき(実測 {health['score']})"
        )
        assert any("密度" in i for i in health["issues"]), "密度異常がissuesに載るべき"

    def test_normal_density_not_penalized(self, reference_pm):
        notes = [n for inst in reference_pm.instruments for n in inst.notes]
        health = ears.score_health(reference_pm, notes)
        assert health["score"] >= 0.95, "通常密度のメロディは密度減点を受けないべき"


class TestScoreRhythmWeight:
    """攻撃(c)対応: 正解MIDIあり運用でscore_rhythmが総合に効くべき。"""

    def test_reference_mode_includes_score_rhythm(self, reference_audio, reference_midi):
        result = ears.cmd_compare(
            CompareArgs(reference_audio, reference_midi, reference=reference_midi)
        )
        assert "score_rhythm" in result, "正解あり運用ではscore_rhythmが算出されるべき"
        assert "score_rhythm" in result["overall"]["weights"], (
            "score_rhythmは総合の重みに組み込まれるべき"
        )

    def test_rhythm_scramble_detected_in_reference_mode(
        self, workdir, reference_pm, reference_audio, reference_midi
    ):
        pm_bad = _scramble_rhythm(reference_pm)
        path = workdir / "attack_rhythm_scramble.mid"
        pm_bad.write(str(path))
        good = ears.cmd_compare(
            CompareArgs(reference_audio, reference_midi, reference=reference_midi)
        )
        bad = ears.cmd_compare(CompareArgs(reference_audio, path, reference=reference_midi))
        assert bad["overall"]["score"] <= good["overall"]["score"] - 0.10, (
            "リズムでたらめは正解あり総合で明確に減点されるべき"
        )

    def test_backward_compat_without_reference(self, baseline_result):
        assert "score_rhythm" not in baseline_result, "正解なし運用は従来どおり(後方互換)"
        assert abs(sum(baseline_result["overall"]["weights"].values()) - 1.0) < 1e-6
