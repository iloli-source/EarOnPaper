"""記譜前MIDIクリーンアップ工程(F-084)のユニットテスト。

先行研究(F-084-{grok,codex}.md)の教訓を回帰テストとして固定する:
- 過剰削除(false-positive pruning)を起こさない(単独条件で本物を消さない)
- 削除は可逆(removed に元インスタンス+理由を保持)
- 完全重複のみ安全統合、微小音価は低信頼と併せてのみ除去
"""

from earpipe.contracts import QuantizedNote
from earpipe.services.rhythm.midi_cleanup import (
    CONF_FLOOR,
    MIN_DUR_BEATS,
    RemovedNote,
    cleanup_notes,
)
import pytest


def note(start, dur, midi, conf=0.9):
    """テスト用の QuantizedNote ファクトリ(実側は既定NaNのまま)。"""
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=conf)


class TestBasics:
    def test_empty_input_returns_empty_and_zero_report(self):
        # Arrange
        notes: list[QuantizedNote] = []

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert cleaned == []
        assert report["input_count"] == 0
        assert report["output_count"] == 0
        assert report["removed_count"] == 0
        assert report["reasons"] == {}
        assert report["removed"] == []

    def test_clean_input_passes_through_unchanged(self):
        # Arrange: 通常の四分/八分音符。削除対象なし
        notes = [note(0.0, 1.0, 60), note(1.0, 0.5, 62), note(1.5, 0.5, 64)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 3
        assert report["removed_count"] == 0
        assert report["output_count"] == 3

    def test_report_counts_are_consistent(self):
        # Arrange
        notes = [note(0.0, 1.0, 60), note(0.0, 1.0, 60, conf=0.5)]  # 完全重複

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert: input = output + removed が常に成り立つ
        assert report["input_count"] == report["output_count"] + report["removed_count"]


class TestExactDuplicate:
    def test_exact_duplicate_merged_keeping_longer(self):
        # Arrange: 同一格子(0.0, 60)で音価違い。長い方が残る
        notes = [note(0.0, 0.5, 60, conf=0.9), note(0.0, 1.0, 60, conf=0.6)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 1
        assert cleaned[0].dur_beats == 1.0
        assert report["reasons"]["exact_duplicate"] == 1

    def test_exact_duplicate_same_dur_keeps_higher_confidence(self):
        # Arrange: 同一格子・同音価。高信頼が残る
        notes = [note(0.0, 1.0, 60, conf=0.4), note(0.0, 1.0, 60, conf=0.95)]

        # Act
        cleaned, _ = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 1
        assert cleaned[0].confidence == 0.95

    def test_removed_note_preserves_original_for_reversibility(self):
        # Arrange
        loser = note(0.0, 0.25, 60, conf=0.5)
        notes = [note(0.0, 1.0, 60, conf=0.9), loser]

        # Act
        _, report = cleanup_notes(notes)

        # Assert: 削除記録に元インスタンスが可逆情報として保持される
        removed = report["removed"]
        assert len(removed) == 1
        assert isinstance(removed[0], RemovedNote)
        assert removed[0].note == loser
        assert removed[0].reason == "exact_duplicate"


class TestMicroLowConf:
    def test_micro_and_low_conf_removed(self):
        # Arrange: 微小音価かつ低信頼の幽霊。同拍に本物の持続音がある
        notes = [note(0.0, 1.0, 60, conf=0.9), note(0.0, 0.05, 84, conf=0.2)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 1
        assert cleaned[0].midi == 60
        assert report["reasons"]["micro_low_conf"] == 1

    def test_micro_but_high_conf_is_kept(self):
        # Arrange: 短いが高信頼(装飾音・16分走句)は残す(単独条件で消さない)
        notes = [note(0.0, 1.0, 60, conf=0.9), note(0.0, 0.05, 84, conf=0.9)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert: 高信頼の短音は保護される
        assert len(cleaned) == 2
        assert report["removed_count"] == 0

    def test_low_conf_but_normal_dur_is_kept(self):
        # Arrange: 低信頼だが十分な音価(弱音でも本物)は残す
        notes = [note(0.0, 1.0, 60, conf=0.9), note(1.0, 0.5, 62, conf=0.2)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 2
        assert report["removed_count"] == 0

    def test_lone_micro_low_conf_note_is_protected(self):
        # Arrange: その拍にそれしか音が無い微小・低信頼ノートは消さない(安全弁)
        notes = [note(0.0, 0.05, 60, conf=0.2)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert: 本物の単音かもしれないので残す
        assert len(cleaned) == 1
        assert report["removed_count"] == 0


class TestOctaveHarmonic:
    def test_low_conf_octave_over_strong_fundamental_removed(self):
        # Arrange: 強い基音(60・1拍・高信頼)の1オクターブ上に、
        # 十分な音価だが低信頼のノート(72)。倍音誤検出として除去したい。
        # 音価は通常なので micro_low_conf では消えず、step 3 が発火する。
        notes = [note(0.0, 1.0, 60, conf=0.9), note(0.0, 1.0, 72, conf=0.2)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert: 倍音誤検出として除去され、基音は残る
        midis = {n.midi for n in cleaned}
        assert midis == {60}
        assert report["reasons"]["octave_harmonic"] == 1
        # 可逆情報に元インスタンスが残る
        assert report["removed"][0].note.midi == 72

    def test_octave_pair_both_strong_are_kept(self):
        # Arrange: オクターブ関係でも両方が本物(長い・高信頼)なら残す
        notes = [note(0.0, 1.0, 60, conf=0.9), note(0.0, 1.0, 72, conf=0.9)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 2
        assert report["removed_count"] == 0

    def test_non_octave_low_conf_note_is_kept(self):
        # Arrange: 低信頼でもオクターブ関係でない(5度上=67)なら倍音扱いしない
        notes = [note(0.0, 1.0, 60, conf=0.9), note(0.0, 1.0, 67, conf=0.2)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert: 非和声音・ブルーノート等の可能性があるため残す
        assert len(cleaned) == 2
        assert report["removed_count"] == 0

    def test_lone_low_conf_octave_note_is_protected(self):
        # Arrange: 同拍に基音が無い(単独)低信頼オクターブ候補は消さない(安全弁)
        notes = [note(0.0, 1.0, 72, conf=0.2)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 1
        assert report["removed_count"] == 0


class TestNoOverPruning:
    def test_fast_passage_of_short_high_conf_notes_survives(self):
        # Arrange: 16分走句(短いが高信頼)。過剰削除で消してはならない
        notes = [note(i * 0.25, 0.25, 60 + i, conf=0.85) for i in range(8)]

        # Act
        cleaned, report = cleanup_notes(notes)

        # Assert: 全音符が生き残る
        assert len(cleaned) == 8
        assert report["removed_count"] == 0

    def test_dense_chord_not_collapsed(self):
        # Arrange: 同拍の三和音(全て本物)。倍音誤除去で潰さない
        notes = [note(0.0, 2.0, 48, 0.8), note(0.0, 2.0, 52, 0.8), note(0.0, 2.0, 55, 0.8)]

        # Act
        cleaned, _ = cleanup_notes(notes)

        # Assert
        assert len(cleaned) == 3


class TestValidation:
    def test_non_positive_min_dur_raises(self):
        with pytest.raises(ValueError):
            cleanup_notes([note(0.0, 1.0, 60)], min_dur_beats=0.0)

    def test_out_of_range_conf_floor_raises(self):
        with pytest.raises(ValueError):
            cleanup_notes([note(0.0, 1.0, 60)], conf_floor=1.5)

    def test_default_thresholds_are_conservative(self):
        # Arrange/Act/Assert: 既定値が保守的(32分・低い信頼下限)であることを固定
        assert MIN_DUR_BEATS == 0.125
        assert CONF_FLOOR == 0.35


class TestOrderingAndSort:
    def test_output_sorted_by_start_then_midi(self):
        # Arrange: 入力順は乱れているが出力は昇順に整う
        notes = [note(2.0, 1.0, 67), note(0.0, 1.0, 64), note(0.0, 1.0, 60)]

        # Act
        cleaned, _ = cleanup_notes(notes)

        # Assert
        keys = [(n.start_beats, n.midi) for n in cleaned]
        assert keys == sorted(keys)
