"""回帰テスト: 「クロマは密なゴミに寛容」問題(台帳§7.1で実測発見)。

壊れたONNX経路のBasic Pitchが密集ノートを出力した際、クロマ類似(音高一致)は
0.84-0.91と高く出てしまい、総合スコアだけ見ると壊れた出力を見逃しかけた。

このテストはその症状を合成で再現し、ハーネスの仕様として固定する:
- クロマ単体は密なゴミを見逃しうる(既知の限界)
- ただし onset(precision) と health(密度) が検出する
- 従って総合は「高一致」判定にならない
この3点が崩れたら、ハーネスの防御が壊れたことを意味する。
"""

import numpy as np
import pretty_midi
import pytest

import ears


def dense_garbage_pm(duration: float = 20.0, notes_per_sec: float = 40.0):
    """全音域に密集したゴミノート(壊れた採譜出力の再現)。"""
    rng = np.random.default_rng(42)
    pm = pretty_midi.PrettyMIDI(initial_tempo=120)
    inst = pretty_midi.Instrument(program=0)
    n = int(duration * notes_per_sec)
    for _ in range(n):
        start = float(rng.uniform(0, duration))
        inst.notes.append(
            pretty_midi.Note(
                velocity=70,
                pitch=int(rng.integers(30, 100)),
                start=start,
                end=start + float(rng.uniform(0.03, 0.25)),
            )
        )
    pm.instruments.append(inst)
    return pm


@pytest.fixture(scope="module")
def garbage_result(reference_audio):
    y, _ = ears.load_audio(str(reference_audio))
    pm = dense_garbage_pm()
    notes = pm.instruments[0].notes
    y_synth = ears.synthesize_midi(pm)
    result = {
        "chroma": ears.chroma_similarity(y, y_synth),
        "onset": ears.onset_match(y, notes),
        "tempo": ears.tempo_consistency(y, pm),
        "health": ears.score_health(pm, notes),
    }
    result["overall"] = ears.overall(result)
    return result


@pytest.mark.unit
class TestDenseGarbageRegression:

    def test_onset_precision_detects_garbage(self, garbage_result):
        """幽霊だらけの出力はonset precisionが低い(検出の第一防御)。"""
        assert garbage_result["onset"]["precision"] < 0.5

    def test_health_flags_density(self, garbage_result):
        """異常密度をhealthが指摘する(検出の第二防御)。"""
        assert any("密度" in i for i in garbage_result["health"]["issues"])
        assert garbage_result["health"]["score"] < 0.8

    def test_overall_not_high_match(self, garbage_result):
        """クロマが寛容でも、総合は「高一致」にならないこと(最終防御)。"""
        assert garbage_result["overall"]["score"] < 0.80
        assert "高一致" not in garbage_result["overall"]["verdict"]

    def test_chroma_leniency_documented(self, garbage_result):
        """クロマ単体は密なゴミに寛容(既知の限界の記録)。

        この値が将来大きく下がったら、クロマ指標が改善されて限界が解消された
        ことを意味する — その場合はREADMEの限界記述も更新すること。
        """
        assert garbage_result["chroma"]["score"] > 0.3
