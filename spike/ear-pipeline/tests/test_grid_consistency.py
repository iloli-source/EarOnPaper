"""Issue #43: 格子選択の単一経路化の回帰テスト。

背景: 初デモの turkish_pd.musicxml がテンポ79.5・time-modification 82%
(3:2格子の誤選択)で生成された(codex解剖)。HEADでは再現しないが、
「2分系の曲がpipeline経路で三連格子に化けない」ことを回帰として固定する。
あわせて、テンポ・格子系の推定が estimate_grid の1箇所に統一されている
(pipeline結果のbpm/grid_per_beatが量子化・記譜まで貫通する)ことを検証する。
"""

import xml.etree.ElementTree as ET

import pytest
import soundfile as sf

from earpipe.pipeline import transcribe_file
from tests.conftest import SR, render_melody

# 16分・8分主体の2分系メロディ(120BPM)。三連要素は含まない。
# conftest.render_melody の形式: (MIDIノート, 開始拍, 長さ拍)
_DURS = [
    (76, 0.25), (74, 0.25), (75, 0.25), (74, 0.25),  # 16分の回音風
    (72, 0.5), (74, 0.5),
    (76, 0.25), (74, 0.25), (75, 0.25), (74, 0.25),
    (72, 0.5), (69, 0.5),
    (71, 0.5), (72, 0.5), (74, 1.0),
    (76, 0.25), (77, 0.25), (76, 0.25), (74, 0.25),
    (72, 0.5), (74, 0.5), (69, 1.0),
]
DUPLE_MELODY = []
_t = 0.0
for _m, _d in _DURS:
    DUPLE_MELODY.append((_m, _t, _d))
    _t += _d
DUPLE_BPM = 120.0


@pytest.fixture(scope="module")
def duple_wav(tmp_path_factory):
    y = render_melody(DUPLE_MELODY, DUPLE_BPM)
    path = tmp_path_factory.mktemp("grid43") / "duple120.wav"
    sf.write(path, y, SR)
    return path


def _time_modification_ratio(musicxml_path) -> float:
    """MusicXML中の note に対する time-modification(変則音価)の比率。"""
    root = ET.parse(musicxml_path).getroot()
    notes = root.iter("note")
    n_notes = 0
    n_tm = 0
    for n in notes:
        n_notes += 1
        if n.find("time-modification") is not None:
            n_tm += 1
    return (n_tm / n_notes) if n_notes else 0.0


class TestGridPathConsistency:
    """2分系入力がpipeline経路で三連格子に化けないこと(#43回帰)。"""

    def test_duple_melody_selects_duple_grid_and_sane_tempo(self, duple_wav, tmp_path):
        out_xml = tmp_path / "duple.musicxml"
        result = transcribe_file(duple_wav, out_musicxml=out_xml)

        # 格子系: 2分系(16分格子)が選ばれる
        assert result["grid_per_beat"] == 4, (
            f"2分系メロディで三連格子が選ばれた: {result['grid_per_beat']}"
        )
        # テンポ: 120±5%(倍半・3:2化けなし)
        assert DUPLE_BPM * 0.95 <= result["bpm"] <= DUPLE_BPM * 1.05, (
            f"テンポが化けた: {result['bpm']} (正解{DUPLE_BPM}。"
            f"79.5系なら3:2格子誤選択の再発)"
        )

    def test_musicxml_time_modification_is_rare_for_duple(self, duple_wav, tmp_path):
        """デモ回帰の本丸: 2分系の曲でtime-modificationが常識的水準(<10%)。"""
        out_xml = tmp_path / "duple.musicxml"
        transcribe_file(duple_wav, out_musicxml=out_xml)
        ratio = _time_modification_ratio(out_xml)
        assert ratio < 0.10, (
            f"三連記号(変則音価)が過剰: {ratio:.0%} (初デモは82%誤爆だった)"
        )

    def test_result_bpm_and_grid_propagate_to_notes(self, duple_wav):
        """estimate_gridの結果が量子化まで貫通している(単一経路)ことの検証。

        全音符のstart_beatsが選択された格子(1/grid_per_beat拍)に乗っていれば、
        別経路の推定が混入していない。
        """
        result = transcribe_file(duple_wav)
        gpb = result["grid_per_beat"]
        for n in result["notes"]:
            pos = n.start_beats * gpb
            assert abs(pos - round(pos)) < 1e-6, (
                f"音符が選択格子に乗っていない: start_beats={n.start_beats}, grid={gpb}"
            )
