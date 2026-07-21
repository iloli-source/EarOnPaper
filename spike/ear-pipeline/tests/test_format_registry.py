"""F-104 プラグイン型出力形式 登録簿(NF-045・Issue #101)のユニットテスト。

``OutputFormat`` の不変性、``FORMAT_REGISTRY`` の整合性(キー一意・拡張子・
lossy正直性・分類)、``available_formats``/``get_format`` の契約を AAA 形式で
検証する。先行研究(F-104-grok.md)の pitfalls を回帰観点に落とす:
lossyを隠さない・記譜方言/容器/演奏の役割分離・宣伝と実装の乖離をstatusで明示。
"""

import dataclasses

import pytest

from earpipe.services.notate.format_registry import (
    FORMAT_REGISTRY,
    OutputFormat,
    available_formats,
    get_format,
)

# 研究が「用途別出力」の本丸として繰り返し挙げる基幹3形式。
_CORE_KEYS = {"musicxml", "midi", "pdf"}
# 仕様が明示的に要求する形式キー(実装仕様の列挙)。
_REQUIRED_KEYS = {
    "musicxml", "midi", "pdf", "tab_pdf",
    "jianpu", "leadsheet", "gp5", "ust", "abc", "lilypond",
}
_VALID_KINDS = {
    "notation_container", "performance", "engraving",
    "notation_dialect", "tablature",
}
_VALID_STATUS = {"stable", "approx", "experimental"}


class TestOutputFormatDataclass:
    """OutputFormat が要件どおり不変(frozen)であることを検証する。"""

    def test_output_format_is_frozen(self):
        # Arrange
        fmt = get_format("musicxml")
        # Act / Assert
        with pytest.raises(dataclasses.FrozenInstanceError):
            fmt.key = "changed"  # type: ignore[misc]

    def test_output_format_is_hashable(self):
        # Arrange
        fmt = get_format("midi")
        # Act
        result = {fmt}
        # Assert
        assert fmt in result


class TestAvailableFormats:
    """available_formats の返却契約(順序・網羅・防御的コピー)を検証する。"""

    def test_returns_all_registry_entries_in_order(self):
        # Arrange
        expected_keys = [f.key for f in FORMAT_REGISTRY]
        # Act
        result = available_formats()
        # Assert
        assert [f.key for f in result] == expected_keys

    def test_returns_output_format_instances(self):
        # Arrange / Act
        result = available_formats()
        # Assert
        assert all(isinstance(f, OutputFormat) for f in result)

    def test_returns_defensive_copy(self):
        # Arrange
        first = available_formats()
        # Act: 返却リストを変更しても登録簿は不変であるべき
        first.clear()
        second = available_formats()
        # Assert
        assert len(second) == len(FORMAT_REGISTRY)
        assert len(second) > 0

    def test_includes_all_required_formats(self):
        # Arrange / Act
        keys = {f.key for f in available_formats()}
        # Assert: 実装仕様が要求する形式が全て公開されている
        assert _REQUIRED_KEYS <= keys


class TestGetFormat:
    """get_format のルックアップと未登録キーのエラー契約を検証する。"""

    def test_returns_matching_format(self):
        # Arrange / Act
        fmt = get_format("jianpu")
        # Assert
        assert fmt.key == "jianpu"
        assert fmt.kind == "notation_dialect"

    def test_unknown_key_raises_keyerror(self):
        # Arrange / Act / Assert
        with pytest.raises(KeyError):
            get_format("nonexistent_format")

    def test_unknown_key_message_lists_available(self):
        # Arrange / Act
        with pytest.raises(KeyError) as exc_info:
            get_format("nope")
        # Assert: エラーは利用可能キーを含み、デバッグ可能(明示的失敗)
        assert "musicxml" in str(exc_info.value)

    def test_every_registry_key_is_retrievable(self):
        # Arrange
        keys = [f.key for f in FORMAT_REGISTRY]
        # Act / Assert
        for key in keys:
            assert get_format(key).key == key


class TestRegistryIntegrity:
    """登録簿の内部整合性(研究pitfallsの回帰観点)を検証する。"""

    def test_keys_are_unique(self):
        # Arrange
        keys = [f.key for f in FORMAT_REGISTRY]
        # Act / Assert
        assert len(keys) == len(set(keys))

    def test_keys_are_machine_readable(self):
        # Arrange / Act / Assert: 小文字英数と _ のみ(API/CLI識別子として安全)
        for fmt in FORMAT_REGISTRY:
            assert fmt.key
            assert fmt.key == fmt.key.lower()
            assert all(c.isalnum() or c == "_" for c in fmt.key)

    def test_extensions_have_no_leading_dot(self):
        # Arrange / Act / Assert
        for fmt in FORMAT_REGISTRY:
            assert fmt.ext
            assert not fmt.ext.startswith(".")

    def test_labels_and_producers_present(self):
        # Arrange / Act / Assert: 表示名と配線手掛かりが空でない
        for fmt in FORMAT_REGISTRY:
            assert fmt.label.strip()
            assert fmt.producer.strip()

    def test_kinds_are_valid(self):
        # Arrange / Act / Assert
        for fmt in FORMAT_REGISTRY:
            assert fmt.kind in _VALID_KINDS

    def test_status_values_are_valid(self):
        # Arrange / Act / Assert
        for fmt in FORMAT_REGISTRY:
            assert fmt.status in _VALID_STATUS

    def test_lossy_formats_declare_what_is_lost(self):
        # Arrange / Act / Assert: lossyを隠さない(研究の中心示唆)。
        # lossy=True なら失われるものの説明が必須。
        for fmt in FORMAT_REGISTRY:
            if fmt.lossy:
                assert fmt.lossy_note.strip(), f"{fmt.key} は lossy だが説明が空"

    def test_notation_and_performance_roles_are_separated(self):
        # Arrange: 研究「記譜が欲しいのにMIDIだけ」の混同を防ぐ役割分離。
        musicxml = get_format("musicxml")
        midi = get_format("midi")
        # Act / Assert: 容器と演奏は別kind
        assert musicxml.kind == "notation_container"
        assert midi.kind == "performance"
        assert musicxml.kind != midi.kind

    def test_core_interchange_formats_present(self):
        # Arrange / Act
        keys = {f.key for f in FORMAT_REGISTRY}
        # Assert: 用途別出力の本丸(交換/再生/配布)が揃う
        assert _CORE_KEYS <= keys

    def test_dialect_formats_marked_non_stable_when_approximate(self):
        # Arrange: テキスト近似の方言は stable を騙らない(宣伝と実装の乖離回避)。
        jianpu = get_format("jianpu")
        # Act / Assert
        assert jianpu.status in {"approx", "experimental"}
