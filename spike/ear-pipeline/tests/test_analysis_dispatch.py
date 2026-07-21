"""解析テキスト出力ディスパッチ(notate/analysis_dispatch.py)の単体テスト。

移動ド(F-100)/ローマ数字度数・ナッシュビル(F-091)は FORMAT_REGISTRY の「出力形式」
ではなく採譜結果から派生する解析注釈。専用アダプタ表で結線し、未対応キーは ValueError
で早期・明示的に失敗する。各キーは非空テキストファイルを実生成する。AAA形式。
"""

from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.analysis_dispatch import (
    AnalysisContext,
    analysis_keys,
    default_analysis_path,
    dispatch_analysis,
)

# ハ長調 I(C E G)→ IV(F A C)相当。度数/コード推定が動く最小のノート列。
_NOTES = [
    QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0),
    QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=1.0),
    QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=67, confidence=1.0),
    QuantizedNote(start_beats=3.0, dur_beats=1.0, midi=65, confidence=1.0),
]


def _ctx() -> AnalysisContext:
    return AnalysisContext(notes=_NOTES, bpm=120.0)


@pytest.mark.parametrize("key", ["movable_do", "roman", "nashville"])
def test_dispatch_generates_nonempty_file(key, tmp_path):
    # Arrange
    out = tmp_path / f"{key}.txt"
    # Act
    path = dispatch_analysis(key, _ctx(), out)
    # Assert
    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0


def test_unknown_key_raises_valueerror(tmp_path):
    # Arrange / Act / Assert: 未対応キーは静かに失敗しない
    with pytest.raises(ValueError):
        dispatch_analysis("does_not_exist", _ctx(), tmp_path / "x.txt")


def test_analysis_keys_are_stable():
    # Assert: 現在の対応解析キー
    assert analysis_keys() == ["movable_do", "nashville", "roman"]


def test_default_analysis_path_uses_key(tmp_path):
    # Arrange
    inp = tmp_path / "song.wav"
    # Act
    out = default_analysis_path("movable_do", inp)
    # Assert: 入力名.KEY.txt(形式間の衝突回避)
    assert out.endswith("song.movable_do.txt")


def test_empty_notes_do_not_crash(tmp_path):
    """空入力でも例外を投げず、ヘッダのみの非空ファイルを出す(無理に推定しない)。"""
    # Arrange
    ctx = AnalysisContext(notes=[], bpm=120.0)
    out = tmp_path / "empty.txt"
    # Act
    path = dispatch_analysis("movable_do", ctx, out)
    # Assert
    assert Path(path).is_file() and Path(path).stat().st_size > 0
