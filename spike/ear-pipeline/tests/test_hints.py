"""解析ヒント入力(F-009・#106)のユニットテスト。

AnalysisHints の frozen/境界検証と、apply_hints の上書き規則
(None は既定維持・非None のみ上書き・defaults 非破壊)を AAA で検証する。
研究(F-009-grok.md)の失敗例「誤ったヒントで悪化」「ヒントは強制でなく補助」を
反映し、None フィールドが既定を潰さないことを重点的に確認する。
"""

import dataclasses

import pytest

from earpipe.services.ear.hints import AnalysisHints, apply_hints


def test_defaults_are_all_none() -> None:
    # Arrange / Act
    hints = AnalysisHints()

    # Assert: 何も指定しなければ全項目「指定なし」
    assert hints.tempo_bpm is None
    assert hints.key_tonic_pc is None
    assert hints.time_sig is None
    assert hints.tuning_offset_cents is None
    assert hints.capo is None


def test_hints_is_frozen() -> None:
    # Arrange
    hints = AnalysisHints(tempo_bpm=120.0)

    # Act / Assert: frozen dataclass は再代入不可
    with pytest.raises(dataclasses.FrozenInstanceError):
        hints.tempo_bpm = 90.0  # type: ignore[misc]


def test_apply_hints_overrides_only_specified_fields() -> None:
    # Arrange: テンポとキーだけ指定、拍子/チューニング/カポは未指定
    defaults = {
        "tempo_bpm": 100.0,
        "key_tonic_pc": 0,
        "time_sig": (4, 4),
        "tuning_offset_cents": 0.0,
        "capo": 0,
    }
    hints = AnalysisHints(tempo_bpm=128.0, key_tonic_pc=7)

    # Act
    merged = apply_hints(hints, defaults)

    # Assert: 指定は上書き、未指定(None)は既定維持
    assert merged["tempo_bpm"] == 128.0
    assert merged["key_tonic_pc"] == 7
    assert merged["time_sig"] == (4, 4)
    assert merged["tuning_offset_cents"] == 0.0
    assert merged["capo"] == 0


def test_apply_hints_none_fields_keep_defaults() -> None:
    # Arrange: 全項目 None(何も指定しない)
    defaults = {"tempo_bpm": 90.0, "key_tonic_pc": 2, "time_sig": (3, 4)}
    hints = AnalysisHints()

    # Act
    merged = apply_hints(hints, defaults)

    # Assert: 既定がそのまま(強制でなく補助 = 指定なしなら推定/既定に委ねる)
    assert merged == defaults


def test_apply_hints_does_not_mutate_defaults() -> None:
    # Arrange
    defaults = {"tempo_bpm": 100.0, "capo": 0}
    original = dict(defaults)
    hints = AnalysisHints(tempo_bpm=140.0, capo=3)

    # Act
    merged = apply_hints(hints, defaults)

    # Assert: defaults は破壊されない(immutable原則)、新しい辞書が返る
    assert defaults == original
    assert merged is not defaults
    assert merged["tempo_bpm"] == 140.0
    assert merged["capo"] == 3


def test_apply_hints_zero_values_are_applied() -> None:
    # Arrange: 0.0(基準ちょうど)/0(カポなし)は None と区別され有効な指定
    defaults = {"tuning_offset_cents": 12.0, "capo": 5, "key_tonic_pc": 9}
    hints = AnalysisHints(tuning_offset_cents=0.0, capo=0, key_tonic_pc=0)

    # Act
    merged = apply_hints(hints, defaults)

    # Assert: 0 でも falsy ではなく明示指定として上書きされる
    assert merged["tuning_offset_cents"] == 0.0
    assert merged["capo"] == 0
    assert merged["key_tonic_pc"] == 0


def test_apply_hints_adds_key_when_default_missing() -> None:
    # Arrange: 既定に無いキーもヒント指定があれば追加される
    defaults: dict = {}
    hints = AnalysisHints(time_sig=(7, 8))

    # Act
    merged = apply_hints(hints, defaults)

    # Assert
    assert merged["time_sig"] == (7, 8)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tempo_bpm": 0.0},        # 非正のBPM
        {"tempo_bpm": -120.0},     # 負のBPM
        {"key_tonic_pc": 12},      # 範囲外(0-11)
        {"key_tonic_pc": -1},      # 範囲外
        {"time_sig": (0, 4)},      # 分子非正
        {"time_sig": (4, 0)},      # 分母非正
        {"capo": -1},              # 負のカポ
    ],
)
def test_invalid_hints_raise_value_error(kwargs: dict) -> None:
    # Arrange / Act / Assert: 物理的にありえない値は生成時に弾く
    with pytest.raises(ValueError):
        AnalysisHints(**kwargs)


def test_valid_boundary_hints_accepted() -> None:
    # Arrange / Act: 境界の有効値は通る
    hints = AnalysisHints(
        tempo_bpm=0.001,
        key_tonic_pc=11,
        time_sig=(1, 1),
        tuning_offset_cents=-50.0,
        capo=0,
    )

    # Assert
    assert hints.key_tonic_pc == 11
    assert hints.time_sig == (1, 1)
    assert hints.capo == 0
