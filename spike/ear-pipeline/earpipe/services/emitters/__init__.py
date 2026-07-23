"""エミッタの遅延自動発見レジストリ。

各エミッタの ``KEY`` / ``EXT`` / 必須入力フラグはソースをASTで読み取り、
実際に指定されたエミッタだけを import する。これにより、任意依存を持つ一つの
エミッタが未導入でも、無関係なエミッタ一覧や軽量出力まで全滅しない。
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from earpipe.services.emitters.base import EmitContext, Emitter

_RESERVED = {"base"}
_METADATA_NAMES = {"KEY", "EXT", "NEEDS_MUSICXML", "NEEDS_AUDIO"}


@dataclass
class EmitterSpec:
    """import前に取得できるエミッタ宣言と、遅延ロード状態。"""

    module_name: str
    KEY: str
    EXT: str
    NEEDS_MUSICXML: bool = False
    NEEDS_AUDIO: bool = False
    _module: ModuleType | None = field(default=None, init=False, repr=False)

    def load(self) -> ModuleType:
        if self._module is not None:
            return self._module
        try:
            mod = importlib.import_module(self.module_name)
        except ModuleNotFoundError as exc:
            missing = exc.name or "不明な依存"
            raise RuntimeError(
                f"エミッタ {self.KEY!r} の依存パッケージ {missing!r} がありません"
            ) from exc
        if getattr(mod, "KEY", None) != self.KEY or getattr(mod, "EXT", None) != self.EXT:
            raise RuntimeError(f"エミッタ宣言が検出時から変化しました: {self.module_name}")
        self._module = mod
        return mod

    def emit(self, ctx: EmitContext, out_path: Path) -> Path:
        return self.load().emit(ctx, out_path)


def _literal_metadata(source_path: Path) -> dict[str, object]:
    """モジュールを実行せず、トップレベル定数だけを安全に抽出する。"""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        for target in targets:
            if isinstance(target, ast.Name) and target.id in _METADATA_NAMES and value_node is not None:
                try:
                    values[target.id] = ast.literal_eval(value_node)
                except (ValueError, TypeError):
                    pass
    return values


def _iter_emitter_specs() -> list[EmitterSpec]:
    specs: list[EmitterSpec] = []
    package_dir = Path(__file__).resolve().parent
    for info in pkgutil.iter_modules(__path__):
        if info.name in _RESERVED or info.name.startswith("_"):
            continue
        source = package_dir / f"{info.name}.py"
        if not source.is_file():
            continue
        meta = _literal_metadata(source)
        key = meta.get("KEY")
        ext = meta.get("EXT")
        if not isinstance(key, str) or not key or not isinstance(ext, str) or not ext:
            continue
        specs.append(
            EmitterSpec(
                module_name=f"{__name__}.{info.name}",
                KEY=key,
                EXT=ext,
                NEEDS_MUSICXML=bool(meta.get("NEEDS_MUSICXML", False)),
                NEEDS_AUDIO=bool(meta.get("NEEDS_AUDIO", False)),
            )
        )
    return specs


def registry() -> dict[str, EmitterSpec]:
    """KEY -> 遅延エミッタ仕様。重複KEYは即時エラー。"""
    reg: dict[str, EmitterSpec] = {}
    for spec in _iter_emitter_specs():
        if spec.KEY in reg:
            raise ValueError(
                f"エミッタ KEY 重複: {spec.KEY!r}({spec.module_name} と {reg[spec.KEY].module_name})"
            )
        reg[spec.KEY] = spec
    return reg


def emitter_keys() -> list[str]:
    """宣言済みエミッタキー一覧。個別依存のimportは行わない。"""
    return sorted(registry())


def default_emit_path(key: str, input_path: str | Path) -> str:
    reg = registry()
    if key not in reg:
        raise KeyError(f"未知のエミッタ {key!r}(対応: {emitter_keys()})")
    stem = Path(input_path).stem
    return str(Path(input_path).with_name(f"{stem}.{key}.{reg[key].EXT}"))


def emit(key: str, ctx: EmitContext, out_path: str | Path) -> Path:
    reg = registry()
    spec = reg.get(key)
    if spec is None:
        raise KeyError(f"未知のエミッタ {key!r}(対応: {emitter_keys()})")
    if spec.NEEDS_MUSICXML and ctx.musicxml_path is None:
        raise ValueError(f"--emit {key} には MusicXML 出力(-o)が必要です")
    if spec.NEEDS_AUDIO and ctx.audio_path is None:
        raise ValueError(f"--emit {key} には入力音声パスが必要です")
    return spec.emit(ctx, Path(out_path))


__all__ = ["EmitContext", "Emitter", "emit", "emitter_keys", "default_emit_path"]
