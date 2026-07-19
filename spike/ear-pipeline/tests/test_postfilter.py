"""postfilter(#31 幽霊除去)と感度可変(#32 取りこぼし救済)のテスト。

解剖(rhythm-autopsy.md)の実測に基づく合成ケース:
- 幽霊 = 倍音位置の低confidence音・同一音高の分裂・密集ゴミ
- 救済 = 低閾値検出で音符が増える方向(高感度 ⊇ 通常のはず)
"""

import pytest

from earpipe.ear import PitchEvent
from earpipe.postfilter import (
    apply_postfilter,
    filter_harmonic_ghosts,
    merge_splits,
)


def ev(onset: float, offset: float, midi: int, conf: float) -> PitchEvent:
    return PitchEvent(onset=onset, offset=offset, midi=midi, confidence=conf)


# ---- 分裂マージ(#31b) ----


class TestMergeSplits:
    def test_merges_same_pitch_tiny_gap(self):
        """同一音高・極短ギャップ(<80ms)の連続は1音に統合される(ペダル再トリガー対策)。"""
        events = [ev(0.0, 0.5, 60, 0.8), ev(0.55, 1.0, 60, 0.7)]  # gap 50ms
        out = merge_splits(events)
        assert len(out) == 1
        assert out[0].onset == 0.0
        assert out[0].offset == 1.0
        assert out[0].midi == 60
        assert out[0].confidence == pytest.approx(0.8)  # 高い方を保持

    def test_does_not_merge_large_gap(self):
        events = [ev(0.0, 0.5, 60, 0.8), ev(0.8, 1.2, 60, 0.7)]  # gap 300ms = 別の音
        assert len(merge_splits(events)) == 2

    def test_does_not_merge_different_pitch(self):
        events = [ev(0.0, 0.5, 60, 0.8), ev(0.52, 1.0, 62, 0.7)]
        assert len(merge_splits(events)) == 2

    def test_merges_chain_of_fragments(self):
        """3分裂以上の連鎖も1音になる。"""
        events = [ev(0.0, 0.3, 64, 0.6), ev(0.33, 0.6, 64, 0.5), ev(0.62, 0.9, 64, 0.7)]
        out = merge_splits(events)
        assert len(out) == 1
        assert out[0].offset == 0.9

    def test_empty(self):
        assert merge_splits([]) == []


# ---- 倍音幽霊フィルタ(#31a) ----


class TestHarmonicGhosts:
    def test_removes_octave_ghost_over_fundamental(self):
        """基音(高conf)の+12半音に重なる低conf音は倍音幽霊として除去。"""
        fund = ev(0.0, 1.0, 60, 0.8)
        ghost = ev(0.05, 0.95, 72, 0.2)  # +12, 基音にほぼ全被覆
        out = filter_harmonic_ghosts([fund, ghost])
        assert fund in out
        assert ghost not in out

    def test_removes_twelfth_ghost(self):
        """第3倍音(+19半音)の低conf音も除去。"""
        fund = ev(0.0, 1.0, 48, 0.9)
        ghost = ev(0.1, 0.9, 67, 0.18)  # +19
        out = filter_harmonic_ghosts([fund, ghost])
        assert ghost not in out

    def test_keeps_confident_harmonic_note(self):
        """+12でも確信度が高ければ実音(オクターブ重ね)として残す。"""
        fund = ev(0.0, 1.0, 60, 0.8)
        real = ev(0.0, 1.0, 72, 0.75)
        out = filter_harmonic_ghosts([fund, real])
        assert real in out

    def test_keeps_non_harmonic_interval(self):
        """倍音関係にない音程(+13半音)は低confでも倍音幽霊としては消さない。"""
        fund = ev(0.0, 1.0, 60, 0.8)
        other = ev(0.1, 0.9, 73, 0.2)
        out = filter_harmonic_ghosts([fund, other])
        assert other in out

    def test_keeps_ghost_without_temporal_overlap(self):
        """時間が重ならなければ倍音候補でも消さない(独立した音)。"""
        fund = ev(0.0, 0.5, 60, 0.8)
        later = ev(0.7, 1.2, 72, 0.2)
        out = filter_harmonic_ghosts([fund, later])
        assert later in out

    def test_chord_fundamentals_survive(self):
        """三和音の構成音(全て高conf)は互いを消さない。"""
        chord = [ev(0.0, 1.0, 60, 0.7), ev(0.0, 1.0, 64, 0.7), ev(0.0, 1.0, 67, 0.7)]
        assert len(filter_harmonic_ghosts(chord)) == 3


# ---- 統合(apply_postfilter) ----


class TestApplyPostfilter:
    def test_pipeline_order_merge_then_ghost(self):
        """分裂した幽霊もマージ後にまとめて除去される。"""
        fund = ev(0.0, 1.0, 60, 0.85)
        g1 = ev(0.05, 0.4, 72, 0.2)
        g2 = ev(0.45, 0.9, 72, 0.22)  # 分裂した倍音幽霊
        out = apply_postfilter([fund, g1, g2])
        assert [e.midi for e in out] == [60]

    def test_empty(self):
        assert apply_postfilter([]) == []

    def test_pure_melody_untouched(self):
        """幽霊のないきれいな旋律は素通し(非破壊)。"""
        melody = [ev(0.0, 0.5, 60, 0.8), ev(0.5, 1.0, 62, 0.8), ev(1.0, 1.5, 64, 0.8)]
        assert apply_postfilter(melody) == melody


# ---- 感度可変(#32) ----


class TestSensitivity:
    def test_invalid_sensitivity_rejected(self):
        from earpipe.ear_poly import detect_events_poly

        with pytest.raises(ValueError):
            detect_events_poly("dummy.wav", sensitivity="turbo")

    @pytest.mark.e2e
    def test_high_sensitivity_detects_at_least_as_many(self, chords_wav):
        """低閾値(high)は通常(normal)の検出を包含する方向に働く(取りこぼし救済の前提)。"""
        from earpipe.ear_poly import bp_python_path, detect_events_poly

        if bp_python_path() is None:
            pytest.skip("basic-pitch 環境なし")
        path, _chords, _bpm = chords_wav
        n_normal = len(detect_events_poly(path))
        n_high = len(detect_events_poly(path, sensitivity="high"))
        assert n_high >= n_normal

    @pytest.mark.e2e
    def test_high_plus_postfilter_keeps_f1(self, chords_wav):
        """高感度+postfilterでも和音進行のF1が通常検出から劣化しない(両輪の成立)。"""
        from earpipe.ear_poly import bp_python_path, detect_events_poly

        if bp_python_path() is None:
            pytest.skip("basic-pitch 環境なし")
        from tests.conftest import chords_to_seconds, note_f1

        path, chords, bpm = chords_wav
        truth = chords_to_seconds(chords, bpm)

        def f1_of(events):
            pred = [(e.midi, e.onset, e.offset) for e in events]
            return note_f1(truth, pred, onset_tol=0.12)

        base = f1_of(detect_events_poly(path))
        both = f1_of(apply_postfilter(detect_events_poly(path, sensitivity="high")))
        assert both >= base - 0.05  # 救済+除去の複合で悪化しないこと


class TestReview40Regressions:
    """レビュー#40の修正回帰(M8: 包含イベントのマージ)。"""

    def test_merge_contained_retrigger_keeps_long_offset(self):
        # 長い音(0-2.0s)の中に短い再トリガー(0.5-0.7s)が包含されるケース。
        # 旧実装はrun末尾のoffset(0.7)を採用し音が縮んでいた。
        events = [
            PitchEvent(onset=0.0, offset=2.0, midi=60, confidence=0.9),
            PitchEvent(onset=0.5, offset=0.7, midi=60, confidence=0.5),
        ]
        merged = merge_splits(events)
        assert len(merged) == 1
        assert merged[0].offset == 2.0

    def test_merge_gap_tracks_run_end_not_last_offset(self):
        # 包含イベントの後、真のrun終端(2.0)からgap内(2.05)の音は同一runに入るべき
        events = [
            PitchEvent(onset=0.0, offset=2.0, midi=60, confidence=0.9),
            PitchEvent(onset=0.5, offset=0.7, midi=60, confidence=0.5),
            PitchEvent(onset=2.05, offset=2.3, midi=60, confidence=0.8),
        ]
        merged = merge_splits(events)
        assert len(merged) == 1
        assert merged[0].offset == 2.3
