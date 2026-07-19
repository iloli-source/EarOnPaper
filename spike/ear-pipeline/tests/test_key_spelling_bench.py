"""C4受入計測(Issue #58)のテスト: 合成ケース + コーパス在時のスモーク。

- 合成ケース: 平行調タイブレーク(_resolve_relative_tonic)が主音強調で
  相対長短調を正しく決めることを、コーパス非依存で検証する。
- スモーク: PDコーパスと spike 採譜キャッシュが揃っている場合のみ、
  bench_key_spelling を実走して受入閾値(主調≥80%/綴り≥90%)を満たすか確認する。
  キャッシュ不在の環境(CI等)では skip する(basic-pitch再走はしない)。
"""

from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.spelling import estimate_key

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tools" / "ai-ears" / "testdata" / "pd-corpus"
OUT = CORPUS / "bench_out"


def _mel(midis, dur=1.0, last_dur=2.0):
    notes = []
    t = 0.0
    for i, m in enumerate(midis):
        d = last_dur if i == len(midis) - 1 else dur
        notes.append(QuantizedNote(start_beats=t, dur_beats=d, midi=m, confidence=0.9))
        t += d
    return notes


class TestRelativeTonicTiebreak:
    """平行調(相対長短調)の主音/旋法を主音強調で決め直せること。"""

    def test_a_minor_not_confused_with_c_major(self):
        # a-moll: 主音A(69)で開始・終止し、Aに音価が集まる。調号は0でC-durと同一。
        key = estimate_key(_mel([69, 71, 72, 74, 76, 74, 72, 71, 69]))
        assert key.tonic.pitchClass == 9  # A
        assert key.mode == "minor"

    def test_c_major_not_confused_with_a_minor(self):
        # C-dur: 主音C(60)で開始・終止。調号0だが主調はハ長調であるべき。
        key = estimate_key(_mel([60, 62, 64, 65, 67, 65, 64, 62, 60]))
        assert key.tonic.pitchClass == 0  # C
        assert key.mode == "major"

    def test_e_minor_not_confused_with_g_major(self):
        # e-moll: 主音E(64)強調。調号1#はG-durと共有。
        key = estimate_key(_mel([64, 66, 67, 69, 71, 69, 67, 66, 64]))
        assert key.tonic.pitchClass == 4  # E
        assert key.mode == "minor"

    def test_g_major_still_major_when_g_emphasized(self):
        key = estimate_key(_mel([67, 69, 71, 72, 74, 72, 71, 69, 67]))
        assert key.tonic.pitchClass == 7  # G
        assert key.mode == "major"

    def test_empty_defaults_to_c_major(self):
        key = estimate_key([])
        assert key.tonic.pitchClass == 0
        assert key.mode == "major"

    def test_tiebreak_preserves_key_signature(self):
        # タイブレークで長短調が入れ替わっても、平行調なので調号(sharps)は不変。
        notes = _mel([69, 71, 72, 74, 76, 74, 72, 71, 69])  # a-moll(0#)
        assert estimate_key(notes).sharps == 0


_HAS_CORPUS = CORPUS.exists() and any(OUT.glob("*_spike.mid"))


@pytest.mark.skipif(not _HAS_CORPUS, reason="PDコーパス/spike採譜キャッシュが無い環境")
class TestBenchSmoke:
    """コーパス在時のみ: ベンチ本体を実走し受入閾値を満たすか確認する。"""

    def test_bench_meets_c4_thresholds(self):
        from bench.bench_key_spelling import (
            KEY_ACCURACY_TARGET,
            SPELLING_MATCH_TARGET,
            main,
        )

        exit_code = main()
        result = OUT / "results_key_spelling.json"
        assert result.exists()
        import json

        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["n_ok"] >= 1
        assert data["key_accuracy"] >= KEY_ACCURACY_TARGET, (
            f"主調正解率 {data['key_accuracy']:.1%} が目標{KEY_ACCURACY_TARGET:.0%}未満"
        )
        assert data["spelling_rate"] >= SPELLING_MATCH_TARGET, (
            f"綴り一致率 {data['spelling_rate']:.1%} が目標{SPELLING_MATCH_TARGET:.0%}未満"
        )
        # 両閾値を満たすとき main は 0 を返す
        assert exit_code == 0

    def test_truth_cross_validated_for_most_songs(self):
        # 相互検証(music21)が大半で✓であること(prom等の既知外れは許容)。
        import json

        from bench.bench_key_spelling import main

        main()
        data = json.loads((OUT / "results_key_spelling.json").read_text(encoding="utf-8"))
        ok = [r for r in data["rows"] if r["status"] == "ok"]
        confirmed = sum(1 for r in ok if r["truth_confirmed_by_music21"])
        assert confirmed >= len(ok) * 0.8
