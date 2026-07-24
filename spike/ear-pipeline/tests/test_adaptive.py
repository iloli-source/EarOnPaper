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
        # 閾値ちょうど(22/10==2.2)はhigh側(≥判定)。直下はnormal。
        # #144実測: 正解付き実曲(夢見る)が比2.26で、highにしか無い和音最高音
        # (C#4/A3/E4)を取りこぼしていた。PD15の実測ギャップ(rescue最小2.56/
        # 非rescue最大2.03)の中なので2.2への引き下げはPD15の選択を変えない。
        assert DENSITY_RATIO_THRESHOLD == 22 / 10
        _patch_counts(monkeypatch, 10, 22)
        assert detect_events_adaptive("d.wav").profile == "high"
        _patch_counts(monkeypatch, 10, 21)
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


class TestPowerContextOctaveRescue:
    """#144: normal採用時、highからパワーコード文脈(+7同時)の+12補完だけ救済。

    正解付き実曲(夢見る)の実測: 欠けた和音最高音は全て検出済みルートの+12で、
    無差別+12救済は倍音幽霊も拾いF1が下がる(0.674)が、+7(5度)が同時に居る
    文脈限定なら precision を保って recall が上がる(0.684→0.701)。
    """

    def test_rescues_octave_over_power_chord(self, monkeypatch):
        root = PitchEvent(onset=0.0, offset=1.0, midi=49, confidence=0.8)
        fifth = PitchEvent(onset=0.0, offset=1.0, midi=56, confidence=0.7)
        octave = PitchEvent(onset=0.0, offset=1.0, midi=61, confidence=0.3)

        def fake(path, sensitivity="normal", **kw):
            if sensitivity == "high":
                return [root, fifth, octave,
                        PitchEvent(onset=2.0, offset=2.4, midi=70, confidence=0.2)]  # 比2.0<2.2
            return [root, fifth]

        monkeypatch.setattr(adaptive, "detect_events_poly", fake)
        sel = detect_events_adaptive("d.wav")
        assert sel.profile == "normal"
        assert any(e.midi == 61 for e in sel.events), "パワーコード文脈の+12が救済される"
        assert not any(e.midi == 70 for e in sel.events), "文脈外のhigh音は入らない"

    def test_no_rescue_without_fifth_context(self, monkeypatch):
        root = PitchEvent(onset=0.0, offset=1.0, midi=49, confidence=0.8)
        octave = PitchEvent(onset=0.0, offset=1.0, midi=61, confidence=0.3)

        def fake(path, sensitivity="normal", **kw):
            return [root, octave] if sensitivity == "high" else [root]

        monkeypatch.setattr(adaptive, "detect_events_poly", fake)
        sel = detect_events_adaptive("d.wav")
        assert not any(e.midi == 61 for e in sel.events), "単音上の+12(倍音疑い)は救済しない"


class TestHarmonicCleanup:
    """#144: +19/+24/+28倍音の弱信頼度クリーンアップ(実測: 幽霊のconf比95%≤0.75)。"""

    def test_weak_upper_harmonic_removed(self):
        from earpipe.services.ear.postfilter import cleanup_upper_harmonics

        base = PitchEvent(onset=0.0, offset=1.0, midi=45, confidence=0.8)
        ghost = PitchEvent(onset=0.0, offset=0.9, midi=64, confidence=0.2)  # +19
        out = cleanup_upper_harmonics([base, ghost])
        assert ghost not in out and base in out

    def test_strong_real_note_kept(self):
        from earpipe.services.ear.postfilter import cleanup_upper_harmonics

        base = PitchEvent(onset=0.0, offset=1.0, midi=45, confidence=0.5)
        real = PitchEvent(onset=0.0, offset=1.0, midi=64, confidence=0.45)  # 比0.9>0.75
        out = cleanup_upper_harmonics([base, real])
        assert real in out

    def test_suboctave_ghost_cannot_kill_real_fifth(self):
        # #144実測バグの回帰固定: サブオクターブ幽霊(C#2)が基音扱いされ、
        # +19の本物の5度(G#3)を殺していた。+12上に同等信頼度の音を持つ音は
        # 基音として無効(サブオクターブ疑い)。
        from earpipe.services.ear.postfilter import cleanup_upper_harmonics

        ghost_sub = PitchEvent(0.0, 1.0, 37, 0.6)   # C#2(幽霊・強め)
        root = PitchEvent(0.0, 1.0, 49, 0.55)       # C#3(本物)
        fifth = PitchEvent(0.0, 1.0, 56, 0.2)       # G#3(本物・弱い)
        out = cleanup_upper_harmonics([ghost_sub, root, fifth])
        assert fifth in out, "本物の5度が幽霊基音に殺されてはいけない"

    def test_power_chord_members_untouched(self):
        from earpipe.services.ear.postfilter import cleanup_upper_harmonics

        evs = [PitchEvent(0.0, 1.0, 49, 0.8), PitchEvent(0.0, 1.0, 56, 0.4),
               PitchEvent(0.0, 1.0, 61, 0.3)]  # +7/+12は対象外
        assert cleanup_upper_harmonics(evs) == evs


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
