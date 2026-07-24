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


def _spread_events(n: int, dur_sec: float) -> list[PitchEvent]:
    """n個のイベントを dur_sec に均等配置(密度 = n/dur_sec を制御)。"""
    step = dur_sec / max(1, n)
    return [
        PitchEvent(onset=i * step, offset=i * step + step * 0.8,
                   midi=60 + (i % 12), confidence=0.7)
        for i in range(n)
    ]


class TestDensityGuard:
    """#137: high採用が密度爆発(幽霊の嵐)したときだけnormalへ退避するガード。

    実曲10本コーパスの実測(2026-07-24): highが16.1/15.2音/秒に爆発した2曲は
    normalの方がクロマ一致・テンポ格子とも良好。一方PD15のrescue曲は
    waltz 12.9音/秒までhigh維持が正解 → 閾値14.0音/秒で両コーパスを分離。
    """

    def _patch(self, monkeypatch, n_normal, n_high, dur_sec):
        def fake(path, sensitivity="normal", **kw):
            n = n_high if sensitivity == "high" else n_normal
            return _spread_events(n, dur_sec)

        monkeypatch.setattr(adaptive, "detect_events_poly", fake)

    def test_storm_high_falls_back_to_normal(self, monkeypatch):
        # acoustic_fingerstyle実測相当: 比2.64・high密度16.1/s → normalへ退避
        self._patch(monkeypatch, 543, 1433, 89.0)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "normal"
        assert sel.density_guard is True
        assert len(sel.events) == 543

    def test_dense_but_sane_high_is_kept(self, monkeypatch):
        # metal実測相当: 比3.0・high密度10.2/s(14未満) → high維持(ガード非発動)
        self._patch(monkeypatch, 301, 915, 90.0)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "high"
        assert sel.density_guard is False
        assert len(sel.events) == 915

    def test_pd15_waltz_like_high_is_kept(self, monkeypatch):
        # PD15 waltz実測相当: 比3.01・high密度12.9/s → high維持(誤退避の回帰固定)
        self._patch(monkeypatch, 256, 771, 60.0)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "high"
        assert sel.density_guard is False

    def test_normal_selection_never_sets_guard(self, monkeypatch):
        self._patch(monkeypatch, 280, 420, 60.0)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "normal"
        assert sel.density_guard is False

    def test_guard_threshold_constant(self):
        assert adaptive.GHOST_STORM_DENSITY == 14.0


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
