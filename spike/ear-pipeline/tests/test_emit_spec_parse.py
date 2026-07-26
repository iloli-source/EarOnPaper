"""--emit 指定のパース単体テスト(#147派生: パス内 '#' の黙殺バグ)。

GuitarSet の 'C#' 入り曲名のように出力パス自体が '#' を含むと、
旧実装は最初の '#' で無条件分割しパスを黙って切り詰めていた。
'#'以降をパラメータとみなすのは k=v(,k=v)* 文法に合致する場合のみとする。
"""

from __future__ import annotations

from earpipe.pipeline import _parse_emit_specs


def test_plain_key_and_path():
    # Arrange / Act
    parsed = _parse_emit_specs(["simplify=out.xml"], "in.wav")

    # Assert
    assert parsed == [("simplify", "out.xml", {})]


def test_params_after_hash():
    # Arrange / Act
    parsed = _parse_emit_specs(["simplify=out.xml#level=0.7"], "in.wav")

    # Assert
    assert parsed == [("simplify", "out.xml", {"level": "0.7"})]


def test_multiple_params_comma_separated():
    # Arrange / Act
    parsed = _parse_emit_specs(["transpose=t.xml#semitones=2,mode=up"], "in.wav")

    # Assert
    assert parsed == [("transpose", "t.xml", {"semitones": "2", "mode": "up"})]


def test_hash_in_path_is_not_param_separator():
    # Arrange: GuitarSet 'C#' 入り曲名由来のパス。'#'後が k=v 文法でないなら
    # パラメータではなくパスの一部として扱う(黙った切り詰め禁止)
    spec = "notesjson=out/00_Rock1-90-C#_comp/notes.json"

    # Act
    parsed = _parse_emit_specs([spec], "in.wav")

    # Assert
    assert parsed == [("notesjson", "out/00_Rock1-90-C#_comp/notes.json", {})]


def test_hash_in_path_with_trailing_params():
    # Arrange: パスに '#' があり、さらに末尾に正規のパラメータも付くケース
    spec = "simplify=out/C#_song/simple.xml#level=0.5"

    # Act
    parsed = _parse_emit_specs([spec], "in.wav")

    # Assert
    assert parsed == [("simplify", "out/C#_song/simple.xml", {"level": "0.5"})]


def test_key_only_uses_default_path():
    # Arrange / Act
    parsed = _parse_emit_specs(["validate"], "song.wav")

    # Assert
    key, path, params = parsed[0]
    assert key == "validate"
    assert params == {}
    assert path  # 既定パスが解決される
