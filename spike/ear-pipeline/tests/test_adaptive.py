"""密度適応の感度自動選択(Issue #54)のテスト。

bp_worker(実検出)には依存せず、detect_events_poly をモックして選択ロジックを固定する。
実測の受入判定は bench_pd.py --adaptive(PD15曲)が担う。
"""

import pytest

from earpipe.contracts import PitchEvent
from earpipe.services.ear import adaptive
from earpipe.services.ear.adaptive import (
    DENSITY_RATIO_THRESHOLD,
    detect_events_adaptive,
)


def _events(n: int) -> list[PitchEvent]:
    return [
        PitchEvent(onset=i * 0.1, offset=i * 0.1 + 0.09, midi=60 + (i % 12), confidence=0.9)
        for i in range(n)
    ]


def _patch_counts(monkeypatch, n_normal: int, n_high: int):
    def fake(path, sensitivity="normal", **kw):
        return _events(n_high if sensitivity == "high" else n_normal)

    monkeypatch.setattr(adaptive, "detect_events_poly", fake)


class TestAdaptiveSelection:
    def test_dense_song_selects_high(self, monkeypatch):
        # 比4.0(トルコ行進曲相当) → high採用
        _patch_counts(monkeypatch, 100, 400)
        sel = detect_events_adaptive("dummy.wav")
        assert sel.profile == "high"
        assert len(sel.events) == 400
        assert sel.ratio == pytest.approx(4.0)

    def test_sparse_song_selects_normal(self, monkeypatch):
        # 比1.5(民謡相当) → normal維持(疎曲劣化ゼロの構造保証)
        _patch_counts(monkeypatch, 280, 420)
        sel = detect_events_adaptive("dummy.wav")
        assert sel.profile == "normal"
        assert len(sel.events) == 280

    def test_threshold_boundary(self, monkeypatch):
        # 閾値ちょうど(23/10==2.3)はhigh側(≥判定)。直下はnormal
        assert DENSITY_RATIO_THRESHOLD == 23 / 10
        _patch_counts(monkeypatch, 10, 23)
        assert detect_events_adaptive("d.wav").profile == "high"
        _patch_counts(monkeypatch, 10, 22)
        assert detect_events_adaptive("d.wav").profile == "normal"

    def test_normal_zero_high_nonzero_uses_high(self, monkeypatch):
        _patch_counts(monkeypatch, 0, 30)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "high"
        assert sel.ratio == float("inf")

    def test_both_zero_returns_empty(self, monkeypatch):
        # 無音・ノイズのみ入力で音符ゼロ(C1-3)を密度適応でも維持
        _patch_counts(monkeypatch, 0, 0)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "normal"
        assert sel.events == []


class TestOnsetMatchingProcedure:
    """C1-2: オンセット±50ms窓のマッチ手順の固定(bench_pd.note_f1)。"""

    @pytest.fixture()
    def note_f1(self):
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
        from bench_pd import note_f1 as fn

        return fn

    def test_match_within_50ms_window(self, note_f1):
        gt = [(1.00, 1.5, 60)]
        f1, _, _ = note_f1(gt, [(1.04, 1.5, 60)], tol=0.05)
        assert f1 == 1.0

    def test_no_match_outside_50ms_window(self, note_f1):
        gt = [(1.00, 1.5, 60)]
        f1, _, _ = note_f1(gt, [(1.06, 1.5, 60)], tol=0.05)
        assert f1 == 0.0

    def test_pitch_must_match(self, note_f1):
        gt = [(1.00, 1.5, 60)]
        f1, _, _ = note_f1(gt, [(1.00, 1.5, 61)], tol=0.05)
        assert f1 == 0.0

    def test_one_to_one_greedy(self, note_f1):
        # 1つの正解ノートは1つの予測にしかマッチしない(貪欲1対1)
        gt = [(1.00, 1.5, 60)]
        f1, prec, rec = note_f1(gt, [(1.00, 1.5, 60), (1.02, 1.5, 60)], tol=0.05)
        assert rec == 1.0
        assert prec == 0.5
