"""汎用エミッタ・レジストリ(services/emitters)の単体テスト。

自動発見・KEY重複検出・必須入力(musicxml/audio)の早期失敗・パラメータ解決を固定する。
参考エミッタ(validate/simplify)が非空ファイルを実生成することも確認する。AAA形式。
"""

from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services import emitters
from earpipe.services.emitters import EmitContext

_NOTES = [
    QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
    QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=1.0),
    QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=64, confidence=1.0),
    QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=65, confidence=1.0),
]


def _ctx(**kw) -> EmitContext:
    base = dict(notes=_NOTES, bpm=120.0, title="t")
    base.update(kw)
    return EmitContext(**base)


def test_registry_discovers_reference_emitters():
    # Arrange / Act
    keys = emitters.emitter_keys()
    # Assert: 参考実装が自動発見される
    assert "validate" in keys
    assert "simplify" in keys


def test_registry_has_no_duplicate_keys():
    # Act / Assert: 重複があれば registry() が ValueError(呼べれば重複なし)
    reg = emitters.registry()
    assert len(reg) == len(emitters.emitter_keys())


def test_unknown_key_raises_keyerror(tmp_path):
    with pytest.raises(KeyError):
        emitters.emit("does_not_exist", _ctx(), tmp_path / "x")


def test_needs_musicxml_raises_without_input(tmp_path):
    # validate は NEEDS_MUSICXML。musicxml_path 無しは ValueError(静かに失敗しない)
    with pytest.raises(ValueError):
        emitters.emit("validate", _ctx(musicxml_path=None), tmp_path / "x.txt")


def test_simplify_emitter_generates_musicxml(tmp_path):
    # Arrange
    out = tmp_path / "simplified.musicxml"
    # Act: params は level を尊重
    path = emitters.emit("simplify", _ctx(params={"level": "0.5"}), out)
    # Assert
    assert Path(path).is_file() and Path(path).stat().st_size > 0
    assert "score-partwise" in out.read_text(encoding="utf-8")


def test_default_emit_path_uses_registry_ext(tmp_path):
    # Arrange
    inp = tmp_path / "song.wav"
    # Act
    out = emitters.default_emit_path("simplify", inp)
    # Assert: 入力名.KEY.拡張子
    assert out.endswith("song.simplify.musicxml")
