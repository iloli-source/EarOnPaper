"""F-086 調内制約クレンジング(scale_cleanse)のユニットテスト。

合成メロディで「調外音の候補提示」と「非破壊/apply の挙動」を AAA 形式で検証する。
先行研究(F-086)の失敗例(経過音・装飾音の誤補正、キー誤りの連鎖)を踏まえ、
既定非破壊・経過音保護・元音保持を回帰固定する。
"""

import math

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.scale_cleanse import (
    RISK_LIKELY_ERROR,
    RISK_PASSING,
    RISK_WEAK,
    cleanse_to_scale,
)


def _note(midi: int, start: float, dur: float = 1.0, conf: float = 0.9) -> QuantizedNote:
    """テスト用の量子化音符を組み立てる小ヘルパ。"""
    return QuantizedNote(
        start_beats=float(start), dur_beats=float(dur), midi=int(midi), confidence=float(conf)
    )


class TestNonDestructiveDefault:
    def test_returns_input_unchanged_when_apply_false(self):
        # Arrange: C majorで C4(調内) と C#4(調外・強拍長音)
        notes = [_note(60, 0.0, 1.0), _note(61, 1.0, 1.0)]

        # Act
        out_notes, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert: 非破壊(出力は入力と同一内容)、候補は1件提示される
        assert out_notes == notes
        assert len(candidates) == 1
        assert candidates[0]["original_midi"] == 61

    def test_does_not_mutate_original_list(self):
        # Arrange
        notes = [_note(60, 0.0), _note(61, 1.0)]
        original_snapshot = list(notes)

        # Act
        cleanse_to_scale(notes, key_tonic_pc=0, mode="major", apply=True)

        # Assert: 入力 list は不変(immutability)
        assert notes == original_snapshot

    def test_diatonic_only_yields_no_candidates(self):
        # Arrange: C majorスケールのみ(全て調内)
        notes = [_note(m, i) for i, m in enumerate([60, 62, 64, 65, 67, 69, 71])]

        # Act
        out_notes, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert
        assert candidates == []
        assert out_notes == notes


class TestSnapDirectionAndCandidate:
    def test_out_of_key_note_snaps_to_nearest_and_prefers_lower_on_tie(self):
        # Arrange: C majorで C#4(pc=1)。Cへ-1、Dへ+1の等距離 → 低い側(C=60)
        notes = [_note(61, 0.0, 2.0)]

        # Act
        _, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert: 等距離タイは下(C=60)、代替に D=62 が含まれる
        c = candidates[0]
        assert c["snapped_midi"] == 60
        assert c["move_semitones"] == -1
        assert 62 in c["alt_midis"]

    def test_preserves_original_midi_and_confidence(self):
        # Arrange: 確信度をわざと下げた調外音
        notes = [_note(66, 0.0, 2.0, conf=0.42)]  # F#4 in C major

        # Act
        _, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert: 元音と確信度が候補に保持される(キー誤りの検証用)
        c = candidates[0]
        assert c["original_midi"] == 66
        assert c["confidence"] == pytest.approx(0.42)

    def test_minor_mode_uses_natural_minor_scale(self):
        # Arrange: A minor(tonic pc=9)。C natural(60,pc=0=相対度数3)は調内
        notes = [_note(60, 0.0, 1.0)]

        # Act
        _, candidates = cleanse_to_scale(notes, key_tonic_pc=9, mode="minor")

        # Assert: 自然短音階の第3音(C)は調内 → 候補なし
        assert candidates == []


class TestRiskClassificationReflectsResearch:
    def test_strong_beat_long_out_of_key_is_likely_error(self):
        # Arrange: 強拍(整数拍)かつ長音の孤立調外音 → 誤採譜らしい高信頼
        notes = [_note(60, 0.0, 1.0), _note(61, 2.0, 1.0), _note(64, 3.0, 1.0)]

        # Act
        _, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert
        assert candidates[0]["risk"] == RISK_LIKELY_ERROR

    def test_short_semitone_passing_tone_is_protected(self):
        # Arrange: C-C#-D の半音上行経過音(短い8分)。研究(codex(2))の保護対象
        notes = [_note(60, 0.0, 0.5), _note(61, 0.5, 0.5), _note(62, 1.0, 0.5)]

        # Act
        _, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert: C#(index1)は経過音候補として保持ラベル
        passing = [c for c in candidates if c["original_midi"] == 61]
        assert len(passing) == 1
        assert passing[0]["risk"] == RISK_PASSING

    def test_apply_snaps_only_likely_error_and_protects_passing(self):
        # Arrange: 強拍長音の調外(補正対象)と 短い経過音(保護対象)を混在
        notes = [
            _note(60, 0.0, 1.0),   # C (in-scale)
            _note(61, 1.0, 0.5),   # C# short passing between C and D -> protect
            _note(62, 1.5, 0.5),   # D (in-scale)
            _note(66, 2.0, 1.0),   # F# strong-beat long out-of-key -> snap
            _note(64, 3.0, 1.0),   # E (in-scale)
        ]

        # Act
        out_notes, candidates = cleanse_to_scale(
            notes, key_tonic_pc=0, mode="major", apply=True
        )

        # Assert: 経過音C#(61)は保持、強拍F#(66)はスナップ適用される
        assert out_notes[1].midi == 61  # passing tone untouched
        passing = next(c for c in candidates if c["index"] == 1)
        assert passing["applied"] is False
        snapped = next(c for c in candidates if c["index"] == 3)
        assert snapped["applied"] is True
        assert out_notes[3].midi == snapped["snapped_midi"]

    def test_weak_beat_out_of_key_is_not_auto_applied(self):
        # Arrange: 弱拍(0.5拍位置)の調外音は低確信 → apply でも保持
        notes = [_note(60, 0.0, 1.0), _note(61, 0.5, 1.0)]

        # Act
        out_notes, candidates = cleanse_to_scale(
            notes, key_tonic_pc=0, mode="major", apply=True
        )

        # Assert
        assert candidates[1 - 1]["risk"] in (RISK_WEAK, RISK_PASSING)
        assert out_notes[1].midi == 61  # 保持


class TestEdgeCasesAndValidation:
    def test_empty_input_returns_empty(self):
        # Arrange / Act
        out_notes, candidates = cleanse_to_scale([], key_tonic_pc=0, mode="major")

        # Assert: 無理に推定せず空を返す
        assert out_notes == []
        assert candidates == []

    def test_invalid_mode_raises_value_error(self):
        # Arrange
        notes = [_note(60, 0.0)]

        # Act / Assert: 静かに失敗しない
        with pytest.raises(ValueError):
            cleanse_to_scale(notes, key_tonic_pc=0, mode="dorian")

    def test_tonic_pc_is_normalized_mod_12(self):
        # Arrange: 主音pcに範囲外(12=C相当)を渡しても %12 で正規化される
        notes = [_note(61, 0.0, 2.0)]  # C# out of key in C major

        # Act
        _, cand_wrapped = cleanse_to_scale(notes, key_tonic_pc=12, mode="major")
        _, cand_plain = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert: 12 と 0 は同一挙動
        assert cand_wrapped[0]["snapped_midi"] == cand_plain[0]["snapped_midi"]

    def test_nan_confidence_becomes_zero(self):
        # Arrange: 確信度NaNの調外音(旧4引数構築等)
        notes = [
            QuantizedNote(
                start_beats=0.0, dur_beats=2.0, midi=61, confidence=float("nan")
            )
        ]

        # Act
        _, candidates = cleanse_to_scale(notes, key_tonic_pc=0, mode="major")

        # Assert: NaNは0.0へ丸める(下流のソート/表示の安全側)
        assert candidates[0]["confidence"] == 0.0
        assert not math.isnan(candidates[0]["confidence"])
