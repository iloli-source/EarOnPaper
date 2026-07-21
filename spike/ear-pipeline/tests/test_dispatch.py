"""出力形式ディスパッチ層(notate/dispatch.py)の単体テスト。

登録簿を source of truth に、未登録キーは KeyError、ディスパッチ非対応キー(レガシー/未結線)
は ValueError で早期・明示的に失敗することを固定する。各対応キーはファイルを実生成する。
"""

from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.dispatch import (
    DispatchContext,
    default_out_path,
    dispatch_format,
    dispatchable_keys,
)

# ハ長調のドレミファ相当。全 adapter が処理できる最小の量子化ノート列。
_NOTES = [
    QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
    QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=62, confidence=1.0),
    QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=64, confidence=1.0),
    QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=65, confidence=1.0),
]


def _ctx() -> DispatchContext:
    return DispatchContext(notes=_NOTES, bpm=120.0, title="test")


@pytest.mark.parametrize("key", ["jianpu", "leadsheet", "ust", "abc"])
def test_dispatch_generates_nonempty_file(key, tmp_path):
    # Arrange
    out = tmp_path / f"{key}.out"
    # Act
    path, meta = dispatch_format(key, _ctx(), out)
    # Assert
    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0
    assert meta.key == key


def test_unknown_key_raises_keyerror(tmp_path):
    # Arrange / Act / Assert
    with pytest.raises(KeyError):
        dispatch_format("does_not_exist", _ctx(), tmp_path / "x")


def test_legacy_or_unwired_key_raises_valueerror(tmp_path):
    """登録簿にはあるがディスパッチ非対応(gp5=producer欠陥/レガシーmusicxml)は ValueError。"""
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        dispatch_format("gp5", _ctx(), tmp_path / "x.gp5")
    with pytest.raises(ValueError):
        dispatch_format("musicxml", _ctx(), tmp_path / "x.musicxml")


def test_lilypond_requires_musicxml(tmp_path):
    """lilypond は musicxml が無いと ValueError(握りつぶさず正直に失敗)。"""
    # Arrange: musicxml_path 無し
    ctx = DispatchContext(notes=_NOTES, bpm=120.0, title="t", musicxml_path=None)
    # Act / Assert
    with pytest.raises(ValueError):
        dispatch_format("lilypond", ctx, tmp_path / "x.ly")


def test_default_out_path_uses_registry_ext(tmp_path):
    # Arrange
    inp = tmp_path / "song.wav"
    # Act
    out = default_out_path("jianpu", inp)
    # Assert: 入力名.KEY.拡張子(形式間の衝突回避)
    assert out.endswith("song.jianpu.txt")


def test_dispatchable_keys_are_stable():
    # Assert: 現在の対応形式(gp5 は producer 欠陥のため除外)
    assert dispatchable_keys() == ["abc", "jianpu", "leadsheet", "lilypond", "ust"]
