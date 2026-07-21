"""エミッタ自動発見レジストリ(#109 B-2 結線基盤)。

`emitters/` パッケージ内の各モジュールを走査し、`KEY` 属性を持つものを
エミッタとして自動登録する。**並列生成した新規エミッタを手編集なしで取り込む**
ための仕組み(register の共有編集を無くし、40並列でも競合しない)。

登録簿(FORMAT_REGISTRY)とは別レイヤ: こちらは「孤立実装をオプトインで
副次出力する」汎用口で、既定の記譜出力には一切影響しない。
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

from earpipe.services.emitters.base import EmitContext, Emitter

_RESERVED = {"base"}


def _iter_emitter_modules() -> list[ModuleType]:
    """本パッケージ配下で KEY を持つモジュールを import して返す。"""
    mods: list[ModuleType] = []
    for info in pkgutil.iter_modules(__path__):
        if info.name in _RESERVED or info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        if hasattr(mod, "KEY") and hasattr(mod, "emit"):
            mods.append(mod)
    return mods


def registry() -> dict[str, ModuleType]:
    """KEY -> エミッタモジュール の辞書(自動発見)。

    Raises:
        ValueError: KEY 重複(どちらを使うべきか曖昧なので静かに上書きしない)。
    """
    reg: dict[str, ModuleType] = {}
    for mod in _iter_emitter_modules():
        key = mod.KEY
        if key in reg:
            raise ValueError(f"エミッタ KEY 重複: {key!r}({mod.__name__} と {reg[key].__name__})")
        reg[key] = mod
    return reg


def emitter_keys() -> list[str]:
    """利用可能なエミッタキー一覧(CLI ヘルプ・検証用)。"""
    return sorted(registry())


def default_emit_path(key: str, input_path: str | Path) -> str:
    """出力先未指定時の既定パス。``入力名.KEY.拡張子``(衝突回避)。"""
    reg = registry()
    if key not in reg:
        raise KeyError(f"未知のエミッタ {key!r}(対応: {emitter_keys()})")
    ext = reg[key].EXT
    stem = Path(input_path).stem
    return str(Path(input_path).with_name(f"{stem}.{key}.{ext}"))


def emit(key: str, ctx: EmitContext, out_path: str | Path) -> Path:
    """エミッタ ``key`` を ``out_path`` に生成する。

    Raises:
        KeyError: 未知のキー(対応一覧付き)。
        ValueError: 必須入力(musicxml/audio)欠如。
    """
    reg = registry()
    mod = reg.get(key)
    if mod is None:
        raise KeyError(f"未知のエミッタ {key!r}(対応: {emitter_keys()})")
    if getattr(mod, "NEEDS_MUSICXML", False) and ctx.musicxml_path is None:
        raise ValueError(f"--emit {key} には MusicXML 出力(-o)が必要です")
    if getattr(mod, "NEEDS_AUDIO", False) and ctx.audio_path is None:
        raise ValueError(f"--emit {key} には入力音声パスが必要です")
    return mod.emit(ctx, Path(out_path))


# registry() は内部アクセサ(テスト用に import 可能だが公開APIには含めない)。
__all__ = ["EmitContext", "Emitter", "emit", "emitter_keys", "default_emit_path"]
