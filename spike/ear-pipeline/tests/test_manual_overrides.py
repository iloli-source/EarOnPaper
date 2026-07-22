"""BPM・拍子・キーの任意上書き(「分かる人は指定してね」)のテスト。

自動検出はデフォルトのまま、指定した項目だけを上書きする。カエルの歌が
3拍子に誤検出される問題は、--beat 4/4 指定で確実に矯正できる(拍子上書き)。
"""

import music21

from earpipe.contracts import QuantizedNote
from earpipe.pipeline import _apply_bpm_override, _parse_beat, _parse_bpm_range
from earpipe.services.notate import to_score


def _notes():
    return [
        QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60 + (i % 5), confidence=0.9)
        for i in range(8)
    ]


class TestBpmOverride:
    def test_exact_override_replaces_estimate(self):
        assert _apply_bpm_override(97.0, 120.0, None) == 120.0

    def test_range_folds_double_into_range(self):
        # 推定140(倍取り)を 60-80 へ → 半分の70
        assert _apply_bpm_override(140.0, None, (60.0, 80.0)) == 70.0

    def test_range_folds_half_into_range(self):
        # 推定35(半取り)を 60-80 へ → 倍の70
        assert _apply_bpm_override(35.0, None, (60.0, 80.0)) == 70.0

    def test_no_override_keeps_estimate(self):
        assert _apply_bpm_override(72.0, None, None) == 72.0


class TestParsers:
    def test_parse_beat(self):
        assert _parse_beat("4/4") == "4/4"
        assert _parse_beat("3/4") == "3/4"
        assert _parse_beat(None) is None

    def test_parse_beat_rejects_unsupported(self):
        # 6/8等は非対応(シンプルさ優先)。不正拍子はエラーにする
        import pytest
        with pytest.raises(ValueError):
            _parse_beat("6/8")

    def test_parse_bpm_range_ascii_and_zenkaku(self):
        assert _parse_bpm_range("60-80") == (60.0, 80.0)
        assert _parse_bpm_range("60〜80") == (60.0, 80.0)
        assert _parse_bpm_range(None) is None


class TestToScoreOverrides:
    def _time_sig(self, score):
        return next(
            iter(score.recurse().getElementsByClass(music21.meter.TimeSignature)), None
        )

    def _key_sig(self, score):
        return next(
            iter(score.recurse().getElementsByClass(music21.key.KeySignature)), None
        )

    def test_beats_per_measure_forces_4_4(self):
        # カエルの歌の3拍子誤検出を 4/4 に矯正するのと同じ経路
        score = to_score(_notes(), bpm=120.0, beats_per_measure=4)
        assert self._time_sig(score).numerator == 4

    def test_beats_per_measure_forces_3_4(self):
        score = to_score(_notes(), bpm=120.0, beats_per_measure=3)
        assert self._time_sig(score).numerator == 3

    def test_time_signature_string_honored(self):
        # CLIは拍子を文字列で渡す(2/4·3/4·4/4)。to_scoreが文字列指定を尊重すること
        score = to_score(_notes(), bpm=120.0, time_signature="2/4")
        ts = self._time_sig(score)
        assert ts.numerator == 2 and ts.denominator == 4

    def test_key_tonic_override_g_major_one_sharp(self):
        score = to_score(_notes(), bpm=120.0, key_tonic="G", key_mode="major")
        assert self._key_sig(score).sharps == 1

    def test_key_tonic_override_a_minor_zero_accidentals(self):
        score = to_score(_notes(), bpm=120.0, key_tonic="A", key_mode="minor")
        assert self._key_sig(score).sharps == 0
