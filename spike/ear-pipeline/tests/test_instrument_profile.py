"""instrument_profile（F-079 / Issue #90）のテスト。

研究(F-079-grok / F-079-codex)が挙げた失敗例を回帰テスト化する:
- 弦数/音域プロファイル不一致（5弦→4弦の暗黙変換、high C 無しで不能）
- 低域境界の欠落（7弦B1・5弦ベースB0 が落ちる）
- 弦順反転（低→高の取り違え）
- 音域外を黙って丸める
- tab.py.assign_frets 互換（pitch == open_midi + fret）
"""

from __future__ import annotations

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.instrument_profile import (
    PROFILES,
    FitResult,
    InstrumentProfile,
    fit_to_profile,
    get_profile,
)
from earpipe.services.notate.tab import TUNING_GUITAR, _candidates


def _note(midi: int, start: float = 0.0, conf: float = 0.9) -> QuantizedNote:
    """テスト用 QuantizedNote 生成ヘルパ。"""
    return QuantizedNote(start_beats=start, dur_beats=1.0, midi=midi, confidence=conf)


# ---------------- プロファイル定義そのものの健全性 ----------------


def test_all_profiles_are_frozen_and_low_to_high() -> None:
    # Arrange
    names = ("guitar6", "guitar7", "guitar_dropd", "bass4", "bass5", "baritone")

    # Act / Assert: 全プロファイルが存在し、開放弦が低→高（昇順）で並ぶ
    for name in names:
        prof = PROFILES[name]
        assert prof.strings == tuple(sorted(prof.strings)), name
        assert prof.name_ja  # 和名が空でない
        assert prof.fret_max > 0


def test_string_counts_match_names() -> None:
    # Arrange / Act / Assert: 名前が示す弦数と実データが一致
    assert PROFILES["guitar6"].string_count == 6
    assert PROFILES["guitar7"].string_count == 7
    assert PROFILES["bass4"].string_count == 4
    assert PROFILES["bass5"].string_count == 5


def test_guitar6_matches_tab_module_tuning() -> None:
    # Arrange
    profile = PROFILES["guitar6"]

    # Act / Assert: tab.py の TUNING_GUITAR と同一定義（配線互換の要）
    assert profile.strings == TUNING_GUITAR


# ---------------- 弦順反転の失敗を構造的に防ぐ ----------------


def test_reversed_string_order_is_rejected() -> None:
    # Arrange: 高→低（降順）の不正な並び
    bad = (64, 59, 55, 50, 45, 40)

    # Act / Assert: 構築時に弾かれる（研究3.8 弦順反転の防止）
    with pytest.raises(ValueError):
        InstrumentProfile(name="bad", strings=bad, fret_max=19, name_ja="不正")


def test_empty_strings_and_negative_fret_rejected() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        InstrumentProfile(name="empty", strings=(), fret_max=19, name_ja="空")
    with pytest.raises(ValueError):
        InstrumentProfile(name="negfret", strings=(40,), fret_max=-1, name_ja="負")


# ---------------- 候補列挙が tab.py と一致（多重写像モデル） ----------------


def test_candidates_match_tab_candidates_for_guitar6() -> None:
    # Arrange: guitar6 と同条件（fret_max=19）で複数のMIDIを比較
    profile = PROFILES["guitar6"]

    # Act / Assert: 各音高で tab.py._candidates と完全一致
    for midi in (40, 52, 60, 64, 83):
        assert profile.candidates(midi) == _candidates(midi), midi


def test_candidate_satisfies_pitch_equals_open_plus_fret() -> None:
    # Arrange
    profile = PROFILES["guitar6"]
    midi = 60  # C4

    # Act
    cands = profile.candidates(midi)

    # Assert: 全候補が pitch == open_midi + fret を満たす（不変条件）
    assert cands
    for si, fret in cands:
        assert profile.strings[si] + fret == midi
        assert 0 <= fret <= profile.fret_max


# ---------------- 低域境界の欠落を防ぐ（7弦B1 / 5弦ベースB0） ----------------


def test_guitar7_low_b1_is_playable_but_guitar6_is_not() -> None:
    # Arrange: 7弦の最低開放弦 B1 = MIDI 35
    low_b1 = 35

    # Act / Assert: 7弦では演奏可、標準6弦では音域外（研究の低域欠落失敗）
    assert PROFILES["guitar7"].is_playable(low_b1)
    assert not PROFILES["guitar6"].is_playable(low_b1)


def test_bass5_low_b0_is_playable_but_bass4_is_not() -> None:
    # Arrange: 5弦ベースの最低開放弦 B0 = MIDI 23
    low_b0 = 23

    # Act / Assert: 5弦では演奏可、4弦では音域外（5弦→4弦の暗黙変換禁止の根拠）
    assert PROFILES["bass5"].is_playable(low_b0)
    assert not PROFILES["bass4"].is_playable(low_b0)


def test_lowest_and_highest_range_properties() -> None:
    # Arrange
    guitar6 = PROFILES["guitar6"]

    # Act / Assert
    assert guitar6.lowest_open_midi == 40
    assert guitar6.highest_midi == 64 + 19


# ---------------- fit_to_profile: 音域外を黙って丸めない ----------------


def test_fit_separates_in_and_out_of_range_without_dropping() -> None:
    # Arrange: 6弦で弾ける C4(60) と、音域下限未満の C1(24)
    notes = [_note(60), _note(24, start=1.0)]
    profile = PROFILES["guitar6"]

    # Act
    result = fit_to_profile(notes, profile)

    # Assert: どちらも失われず分類される（in + out = 全入力）
    assert isinstance(result, FitResult)
    assert result.n_in_range == 1
    assert result.n_out_of_range == 1
    assert result.in_range[0].midi == 60
    total = result.n_in_range + result.n_out_of_range
    assert total == len(notes)


def test_out_of_range_note_carries_nonzero_octave_shift_suggestion() -> None:
    # Arrange: 低すぎる C1(24) は上方向、高すぎる音は下方向のシフトになる
    low = _note(24)
    high = _note(120)
    profile = PROFILES["guitar6"]

    # Act
    result = fit_to_profile([low, high], profile)
    shifts = {note.midi: shift for note, shift in result.out_of_range}

    # Assert: 低音は +（上げ）、高音は -（下げ）、いずれも非ゼロ（丸め禁止＝提案として明示）
    assert shifts[24] > 0
    assert shifts[120] < 0


def test_octave_fold_brings_note_into_range() -> None:
    # Arrange
    profile = PROFILES["guitar6"]
    midi = 24  # C1, 音域外

    # Act
    shift = profile.octave_folds_to_range(midi)
    folded = midi + shift * 12

    # Assert: 提案シフト適用後は音域内に収まる
    assert profile.lowest_open_midi <= folded <= profile.highest_midi


def test_in_range_note_has_zero_octave_fold() -> None:
    # Arrange / Act / Assert
    profile = PROFILES["guitar6"]
    assert profile.octave_folds_to_range(60) == 0


def test_fit_with_empty_notes_returns_empty_result() -> None:
    # Arrange / Act
    result = fit_to_profile([], PROFILES["bass4"])

    # Assert
    assert result.n_in_range == 0
    assert result.n_out_of_range == 0


# ---------------- get_profile の入力検証 ----------------


def test_get_profile_returns_known_profile() -> None:
    # Arrange / Act / Assert
    assert get_profile("bass5").string_count == 5


def test_get_profile_rejects_unknown_name_with_helpful_message() -> None:
    # Arrange / Act / Assert: 未知名は利用可能名を添えて弾く
    with pytest.raises(KeyError) as exc:
        get_profile("mandolin")
    assert "利用可能" in str(exc.value)


# ---------------- Drop D / バリトンが独立プロファイルとして機能 ----------------


def test_drop_d_extends_low_range_below_standard() -> None:
    # Arrange: Drop D の6弦は D2(38)。標準の E2(40) より低い
    d2 = 38

    # Act / Assert: DropDは演奏可、標準6弦は不可（調弦回避の妥協を防ぐ）
    assert PROFILES["guitar_dropd"].is_playable(d2)
    assert not PROFILES["guitar6"].is_playable(d2)
