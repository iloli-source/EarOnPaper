"""#57 C3拍子整合 + #59 C5譜面自動検査の回帰テスト。

2層構成:
  1. 合成ケース(常時実行): 既知の音符列で check_* 関数の判定を固定する。
     連桁違反の陽性検出(わざと拍を跨ぐ連桁を作って検出できること)も確認し、
     検出器が「常に0を返すだけ」でないことを保証する。
  2. PDコーパス(不在時skip): PD15曲で異常拍子ゼロ・連桁違反ゼロ・ヘッダ妥当を検査。
     小節数は「4拍基準±1(記譜側の小節割りの妥当性)」を緑の不変条件とし、
     「正解拍子基準±1(#59文面)」は4/4固定に阻まれるため xfail で正直に記録する。

検査対象は自社spikeの譜面出力(to_score が生む music21 Score)。BP venvは使わない。
"""

import music21
import pytest

from bench.bench_score_checks import (
    CORPUS,
    SANE_TIME_SIGNATURES,
    build_score_for_song,
    check_score,
    check_time_signature,
    count_beam_boundary_violations,
    expected_measures_from_gt,
    gt_to_quantized,
    _gt_tempo_and_ts,
)
from bench.bench_pd import SONGS
from earpipe.contracts import QuantizedNote
from earpipe.services.notate import to_score

CORPUS_MISSING = not CORPUS.exists()
skip_no_corpus = pytest.mark.skipif(
    CORPUS_MISSING, reason=f"PDコーパス不在: {CORPUS}"
)


def _existing_songs() -> list[tuple[str, str, str]]:
    return [s for s in SONGS if (CORPUS / f"{s[0]}.mid").exists()]


# ---- 合成ケース(常時実行) ----


class TestTimeSignatureSanity:
    """#57: 出力拍子が常識集合に入り、異常拍子を出さない。"""

    def test_scale_gives_sane_common_time(self):
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60 + i, confidence=0.9)
            for i in range(8)
        ]
        score = to_score(notes, bpm=120.0)
        res = check_time_signature(score, gt_num=4, gt_den=4)
        assert res.is_sane
        assert res.output_ts in SANE_TIME_SIGNATURES

    def test_output_ts_is_always_44_documented_limitation(self):
        """to_score は現状4/4固定。異常拍子が構造上出ないことの根拠を固定する。

        この不変条件が崩れた(=拍子推定が導入され4/4以外を出す)場合、
        本テストが落ちて「拍子整合検証の前提が変わった」ことを知らせる。
        """
        notes = [QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9)]
        score = to_score(notes, bpm=120.0)
        ts = score.recurse().getElementsByClass(music21.meter.TimeSignature).first()
        assert ts is not None and ts.ratioString == "4/4"

    def test_sane_set_excludes_pathological_meters(self):
        assert "11/8" not in SANE_TIME_SIGNATURES
        assert "13/16" not in SANE_TIME_SIGNATURES


class TestBeamBoundaryDetector:
    """#59(c): 連桁が拍境界を跨がないことの検出器を両側から固定する。"""

    def test_no_violation_on_clean_eighths(self):
        # 各拍頭から8分2つずつ = 拍内で連桁が閉じる、跨がない
        notes = [
            QuantizedNote(start_beats=i * 0.5, dur_beats=0.5, midi=60, confidence=0.9)
            for i in range(8)
        ]
        score = to_score(notes, bpm=120.0)
        groups, violations = count_beam_boundary_violations(score)
        assert groups >= 1
        assert violations == 0

    def test_detector_catches_cross_beat_beam(self):
        """わざと拍境界を跨ぐ連桁を組み、検出器が違反を数えることを確認する。

        makeBeams は通常は拍で連桁を切るので、拍0.5→1.5 に渡る2音を1グループに
        手動で connect し、検出器が offset の整数拍差を違反として拾えるか見る。
        """
        m = music21.stream.Measure()
        m.insert(0, music21.meter.TimeSignature("4/4"))
        n1 = music21.note.Note("C4", quarterLength=0.5)
        n2 = music21.note.Note("D4", quarterLength=0.5)
        # 0.75拍目と1.25拍目に置く → 整数拍 0 と 1 を跨ぐ
        m.insert(0.75, n1)
        m.insert(1.25, n2)
        n1.beams.append("start")
        n2.beams.append("stop")
        part = music21.stream.Part()
        part.append(m)
        score = music21.stream.Score()
        score.insert(0, part)
        groups, violations = count_beam_boundary_violations(score)
        assert groups == 1
        assert violations == 1


class TestScoreCheckSynthetic:
    """#59: ヘッダ妥当性と小節数判定の合成ケース。"""

    def test_header_valid_for_simple_melody(self):
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60, confidence=0.9)
            for i in range(8)
        ]
        score = to_score(notes, bpm=120.0)
        res = check_score(score, expected_measures=2)
        assert res.header_valid
        assert res.ts_string in SANE_TIME_SIGNATURES
        assert res.key_sharps is not None and -7 <= res.key_sharps <= 7

    def test_measures_within_tol_true_when_matching(self):
        # 8拍 = 4/4で2小節。期待2なら±1以内。
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60, confidence=0.9)
            for i in range(8)
        ]
        score = to_score(notes, bpm=120.0)
        res = check_score(score, expected_measures=2)
        assert res.measures_within_tol

    def test_measures_within_tol_false_when_far_off(self):
        notes = [
            QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60, confidence=0.9)
            for i in range(8)
        ]
        score = to_score(notes, bpm=120.0)
        # 出力2に対し+5。オクターブ等価(×2=4)でも±1に入らない明確な不一致
        res = check_score(score, expected_measures=7)
        assert not res.measures_within_tol


# ---- PDコーパス(不在時skip) ----


@skip_no_corpus
class TestPDCorpusTimeSignature:
    """#57: PD全曲で異常拍子を1件も出さない。"""

    def test_no_anomalous_time_signature_across_corpus(self):
        anomalous = []
        for rel, slug, _cat in _existing_songs():
            score, _bpm, num, den = build_score_for_song(rel)
            res = check_time_signature(score, num, den)
            if not res.is_sane:
                anomalous.append((slug, res.output_ts))
        assert anomalous == [], f"異常拍子を出した曲: {anomalous}"


@skip_no_corpus
class TestPDCorpusScoreChecks:
    """#59: PD全曲でヘッダ妥当・連桁違反ゼロ・小節割り妥当(4拍基準)。"""

    def test_headers_valid_across_corpus(self):
        bad = []
        for rel, slug, _cat in _existing_songs():
            score, bpm, num, den = build_score_for_song(rel)
            exp = expected_measures_from_gt(CORPUS / f"{rel}.mid", bpm, num, den)
            res = check_score(score, exp)
            if not res.header_valid:
                bad.append((slug, res.ts_string, res.key_sharps))
        assert bad == [], f"ヘッダ不正の曲: {bad}"

    def test_no_beam_boundary_violations_across_corpus(self):
        violators = []
        for rel, slug, _cat in _existing_songs():
            score, _bpm, _num, _den = build_score_for_song(rel)
            _groups, violations = count_beam_boundary_violations(score)
            if violations:
                violators.append((slug, violations))
        assert violators == [], f"連桁が拍境界を跨いだ曲: {violators}"

    def test_measure_division_sound_under_engine_meter(self):
        """記譜側の小節割り自体は妥当(エンジン自身が選んだ拍子の基準で±1以内)。

        拍子推定(estimate_meter)導入後は出力拍子がL/4になるため、
        音符スパン(拍)をLで割った期待小節数と出力小節数を突合する。
        正解拍子基準の±1(オクターブ等価込み)は
        test_measure_count_vs_gt_meter が判定する。
        """
        import math

        bad = []
        for rel, slug, _cat in _existing_songs():
            gt_path = CORPUS / f"{rel}.mid"
            bpm, _num, _den = _gt_tempo_and_ts(gt_path)
            score, _bpm, _n, _d = build_score_for_song(rel)
            res = check_score(score, expected_measures=1)
            num_s, den_s = res.ts_string.split("/")
            beats_per_measure = int(num_s) / (int(den_s) / 4.0)
            notes = gt_to_quantized(gt_path, bpm)
            span = max(n.start_beats + n.dur_beats for n in notes)
            exp_own = max(1, math.ceil(span / beats_per_measure))
            out = res.output_measures
            if abs(out - exp_own) > 1:
                bad.append((slug, out, exp_own, res.ts_string))
        assert bad == [], f"自拍子基準で小節割りが±1を超えた曲: {bad}"


@skip_no_corpus
class TestPDCorpusMeasureCount:
    """#59「正解拍子基準±1」: 拍子推定導入(estimate_meter)で達成。

    判定は小節長オクターブ等価(×2)込み(_measures_match・根拠は同関数docstring:
    2/4vs4/4等は音響から決定不能な記譜慣習でテンポ倍半曖昧性と同型)。
    """

    def test_measure_count_vs_gt_meter(self):
        bad = []
        for rel, slug, _cat in _existing_songs():
            gt_path = CORPUS / f"{rel}.mid"
            bpm, num, den = _gt_tempo_and_ts(gt_path)
            score, _bpm, _n, _d = build_score_for_song(rel)
            exp = expected_measures_from_gt(gt_path, bpm, num, den)
            res = check_score(score, exp)
            if not res.measures_within_tol:
                bad.append((slug, res.output_measures, exp))
        assert bad == [], f"正解拍子基準で±1を超えた曲: {bad}"
