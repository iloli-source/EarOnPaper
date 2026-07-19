"""rhythm機能別監査(func-r1-fable-input)のP1群に対する攻撃再現テスト(Issue #47)。

R1/R2: quantize_events のBPMガード欠如(ZeroDivision・負start_beatsの黙認)
R3/R4: 探索範囲(60-180)外の真テンポが倍/半に化ける問題の正直な処理
R5:    事前分布から遠い三連符(72/90)の2分系エイリアス(既知限界の実測固定)

方針(規約=function-critique-protocol):
- クラッシュ/黙認 → 明示エラー(境界検証)
- 検出可能な曖昧性(遅い側) → TempoOctaveAmbiguityWarning
- 検出不能な曖昧性(速い側・一様三連) → 挙動をテストで文書化(限界台帳)
"""

import warnings

import pytest
from earpipe.contracts import PitchEvent
from earpipe.services.rhythm import (
    TempoOctaveAmbiguityWarning,
    estimate_grid,
    estimate_tempo,
    quantize_events,
)


def stream(bpm: float, subdiv: int, n: int = 32, pitch: int = 69) -> list[PitchEvent]:
    """一様音符列(subdiv=拍あたりの音数: 1=4分, 2=8分, 3=3連8分)。"""
    spb = 60.0 / bpm
    step = spb / subdiv
    return [
        PitchEvent(i * step, i * step + step * 0.9, pitch + (i % 3), 0.9)
        for i in range(n)
    ]


class TestQuantizeEventsGuards:
    """R1/R2: 公開関数 quantize_events の境界検証。"""

    def test_bpm_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="bpm"):
            quantize_events(stream(120, 2, 8), bpm=0)

    def test_bpm_negative_raises_value_error(self):
        # 旧実装は負の start_beats([-1.5..0.0])を黙って返していた
        with pytest.raises(ValueError, match="bpm"):
            quantize_events(stream(120, 2, 8), bpm=-120)

    def test_bpm_nan_raises_value_error(self):
        with pytest.raises(ValueError, match="bpm"):
            quantize_events(stream(120, 2, 8), bpm=float("nan"))

    def test_bpm_inf_raises_value_error(self):
        with pytest.raises(ValueError, match="bpm"):
            quantize_events(stream(120, 2, 8), bpm=float("inf"))

    def test_grid_per_beat_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="grid_per_beat"):
            quantize_events(stream(120, 2, 8), bpm=120, grid_per_beat=0)

    def test_valid_input_still_works(self):
        notes = quantize_events(stream(120, 2, 8), bpm=120)
        assert notes and all(n.start_beats >= 0 for n in notes)


class TestRangeArgValidation:
    """推定関数の探索範囲引数の境界検証。"""

    def test_estimate_tempo_rejects_nonpositive_min(self):
        with pytest.raises(ValueError, match="bpm_min"):
            estimate_tempo(stream(120, 2), bpm_min=0)

    def test_estimate_tempo_rejects_inverted_range(self):
        with pytest.raises(ValueError, match="bpm_min"):
            estimate_tempo(stream(120, 2), bpm_min=180, bpm_max=60)

    def test_estimate_grid_rejects_nonfinite_range(self):
        with pytest.raises(ValueError, match="bpm"):
            estimate_grid(stream(120, 2), bpm_max=float("inf"))


class TestOctaveAmbiguityWarning:
    """R3: 真テンポが範囲より遅い場合、倍解釈を黙って返さず警告する。"""

    def test_slow_eighths_emit_warning(self):
        # 真55BPMの8分音符列: 範囲内の110(4分解釈)に化けるが、55の8分解釈も
        # 同fit・音価妥当 → 曖昧性を警告
        with pytest.warns(TempoOctaveAmbiguityWarning):
            est = estimate_tempo(stream(55, 2))
        assert est == pytest.approx(110.0, rel=0.05)

    def test_slow_45bpm_eighths_emit_warning(self):
        # 真45BPMの8分音符列 → 90(4分解釈)に化けるが45の8分解釈も同fit
        with pytest.warns(TempoOctaveAmbiguityWarning):
            est = estimate_tempo(stream(45, 2))
        assert est == pytest.approx(90.0, rel=0.05)

    def test_slow_quarters_pick_odd_grid_without_false_warning(self):
        # 真50BPMの4分(IOI=1.2s)は62.5の「5×16分」解釈に化ける(半分62.5/2=31.25は
        # fit=0のため警告対象外)。範囲外の遅い4分は検出不能ケースとして挙動を固定
        with warnings.catch_warnings():
            warnings.simplefilter("error", TempoOctaveAmbiguityWarning)
            est = estimate_tempo(stream(50, 1))
        assert est == pytest.approx(62.5, rel=0.05)

    @pytest.mark.parametrize("bpm,subdiv", [(120, 2), (100, 2), (108, 2)])
    def test_normal_tempos_do_not_warn(self, bpm, subdiv):
        with warnings.catch_warnings():
            warnings.simplefilter("error", TempoOctaveAmbiguityWarning)
            est = estimate_tempo(stream(bpm, subdiv))
        assert est == pytest.approx(bpm, rel=0.05)

    def test_estimate_grid_propagates_warning(self):
        with pytest.warns(TempoOctaveAmbiguityWarning):
            estimate_grid(stream(55, 2))


class TestFastSideDocumentedLimit:
    """R4: 真テンポ>BPM_MAXは半分解釈と数学的に同一で検出不能(文書化された限界)。

    一様4分音符列@200は8分音符列@100と完全に同一のIOI列のため、
    警告なしで100を返すのが現在の仕様(docstring限界台帳に記録)。
    """

    def test_200bpm_quarters_alias_to_half(self):
        est = estimate_tempo(stream(200, 1))
        assert est == pytest.approx(100.0, rel=0.05)


class TestSlowTripletDocumentedLimit:
    """R5: 事前分布中心(108)から遠い三連は2分系にエイリアスする(実測固定)。

    triplet-8th@72 ≡ straight-8th@108(数学的同一)。オッカム減点(2分系優先)の
    設計上、一様・変化形とも72/90は2分系へ倒れる。有効域(96-120)は
    tests/test_triplet.py が保証。ここでは限界の実測値を回帰固定する。
    """

    @pytest.mark.parametrize("bpm,expect_alias", [(72, 108.0), (90, 135.0)])
    def test_slow_uniform_triplet_aliases_to_duple(self, bpm, expect_alias):
        est, gpb = estimate_grid(stream(bpm, 3, n=36))
        assert gpb == 4  # 既知限界: 2分系に倒れる
        assert est == pytest.approx(expect_alias, rel=0.05)
