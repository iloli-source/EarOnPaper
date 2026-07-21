#!/usr/bin/env python3
"""孤立エクスポート検査ゲート。

`earpipe/services/*/__init__.py` の `__all__` に載っているが、実採譜フロー
`earpipe/pipeline.py` から import グラフで一度も到達されない = 「孤立エクスポート」
を検出する。ユニットテストが緑でも製品に反映されていない機能(root-cause-analysis.md §0)
を機械的に捕捉するのが目的。

判定:
  - pipeline.py を起点に、intra-earpipe の import を辿って「実際に使われる名前」を集める。
  - barrel(__init__.py)経由の `from earpipe.services.X import a, b` は、barrel の
    再エクスポート定義(`from .sub import a`)を辿って a の定義モジュールまで展開する。
  - `__all__` の各シンボルが used_names に無ければ孤立。

既知の孤立は scripts/orphan_allowlist.txt で凍結する(債務を増やさない・#109で消化)。
allowlist に載っているのに実は配線済み(=used)になったシンボルは stale として fail し、
allowlist から削除させる(結線が進んだことをゲートが強制記録する)。

exit code: 孤立(非allowlist) or stale allowlist があれば 1、無ければ 0。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # spike/ear-pipeline
PKG = ROOT / "earpipe"
ENTRY = PKG / "pipeline.py"
ALLOWLIST = Path(__file__).resolve().parent / "orphan_allowlist.txt"
BARRELS = sorted((PKG / "services").glob("*/__init__.py"))
# エミッタ(#109 B-2)は registry が実行時に emitters/*.py を全て動的 import するため、
# 静的 import グラフには現れないが実採譜フローから到達可能。各ファイルを BFS の起点に
# 加えて実際の到達性を正しくモデル化する(新規エミッタは手編集なしで自動的に配線判定)。
EMITTERS = sorted((PKG / "services" / "emitters").glob("*.py"))


def _module_to_file(mod: str) -> Path | None:
    """"earpipe.services.notate" 等のドット表記をファイルに解決。"""
    rel = mod.split(".")
    if rel and rel[0] == "earpipe":
        base = PKG.joinpath(*rel[1:])
    else:
        return None
    if base.with_suffix(".py").exists():
        return base.with_suffix(".py")
    init = base / "__init__.py"
    if init.exists():
        return init
    return None


def _resolve_from(node: ast.ImportFrom, current: Path) -> str | None:
    """ImportFrom の絶対モジュール名を返す(相対 import も解決)。"""
    if node.level == 0:
        return node.module
    # 相対 import: current の親から level 段上る
    pkg_parts = current.parent.relative_to(ROOT).parts  # ("earpipe", "services", "notate")
    up = node.level - 1
    base = list(pkg_parts[: len(pkg_parts) - up]) if up else list(pkg_parts)
    if node.module:
        base += node.module.split(".")
    return ".".join(base)


def _barrel_reexports(barrel: Path) -> dict[str, Path]:
    """barrel __init__ の `from .sub import name` を name->定義ファイル に写像。"""
    mapping: dict[str, Path] = {}
    tree = ast.parse(barrel.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        mod = _resolve_from(node, barrel)
        if not mod:
            continue
        f = _module_to_file(mod)
        if f is None:
            continue
        for alias in node.names:
            mapping[alias.asname or alias.name] = f
    return mapping


def _all_symbols(barrel: Path) -> list[str]:
    tree = ast.parse(barrel.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "__all__" for t in node.targets
        ):
            return [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
    return []


def compute_reachable() -> tuple[set[str], set[Path]]:
    """pipeline.py を起点に import グラフを辿り、(実際にimportされる名前, 到達したファイル) を返す。"""
    # barrel名 -> {reexport名: 定義ファイル}
    reexport = {b: _barrel_reexports(b) for b in BARRELS}
    reexport_by_file = {b.parent.name: reexport[b] for b in BARRELS}
    barrel_files = set(BARRELS)

    used: set[str] = set()
    seen_files: set[Path] = set()
    queue: list[Path] = [ENTRY, *EMITTERS]  # emitters は registry が実行時に全 import

    while queue:
        f = queue.pop()
        if f in seen_files or not f.exists():
            continue
        seen_files.add(f)
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # 直接呼び出し name() を「使用」に含める(モジュール内ヘルパの到達性を捉える。
            # 例: run_compare が同一モジュールの build_compare_command を呼ぶ)。
            # obj.name() の属性呼び出しは含めない — 同名メソッドで本物の孤立関数を誤って
            # 隠す(mask する)のを避けるため(孤立の見逃しは厳禁)。
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                used.add(node.func.id)
            if not isinstance(node, ast.ImportFrom):
                continue
            mod = _resolve_from(node, f)
            if not mod or "earpipe" not in mod:
                continue
            target = _module_to_file(mod)
            # barrel からの import なら、名前を定義モジュールへ展開
            barrel_name = mod.rsplit(".", 1)[-1]
            bmap = reexport_by_file.get(barrel_name, {})
            for alias in node.names:
                name = alias.name
                used.add(name)
                if name in bmap:
                    queue.append(bmap[name])
            # barrel(__init__)自体は展開しない: 入れると全再エクスポートが used に混入し、
            # 「import されていない孤立」まで配線済みに見えてしまう。名前ごとに bmap で辿る。
            if target is not None and target not in barrel_files:
                queue.append(target)
    return used, seen_files


def load_allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    out = set()
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip()
        if s:
            out.add(s)
    return out


def _is_function(deffile: Path | None, sym: str) -> bool:
    """deffile 内で sym が関数(def/async def)として定義されているか。"""
    if deffile is None or not deffile.exists():
        return False
    try:
        tree = ast.parse(deffile.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == sym
        for n in tree.body
    )


def find_orphans() -> tuple[set[str], set[str]]:
    """(現在の孤立集合, used集合) を返す。

    **関数(=機能/挙動)は「実際に名前で import される」ことを厳密に要求する。**
    以前は「定義モジュールが seen_files にあれば配線済み」という緩い条件があり、到達モジュールに
    *同居するだけで一度も呼ばれない関数*(detect_sustain_audio / render_png_preview 等)まで
    配線済みに数える抜け穴だった(外部レビュー指摘: emitter に import を1行足すだけで同モジュールの
    __all__ を丸ごと孤立から隠せた)。よって関数は名前 import 必須に厳格化した。

    型・定数(データ契約)は、定義モジュールが到達可能なら配線済みとみなす。これらは wired 関数の
    返り値や引数として流通し、必ずしも名前 import されないため(例: validate_musicxml が返す
    ValidationReport)。ただし「関数」はこの緩和の対象外(挙動の死は隠さない)。
    """
    used, seen_files = compute_reachable()
    orphans: set[str] = set()
    for b in BARRELS:
        defmap = _barrel_reexports(b)
        for sym in _all_symbols(b):
            if sym in used:
                continue
            deffile = defmap.get(sym)
            # 型/定数のみモジュール到達で許容。関数は名前 import されないと孤立。
            if deffile in seen_files and not _is_function(deffile, sym):
                continue
            orphans.add(sym)
    return orphans, used


def main() -> int:
    orphans, used = find_orphans()
    allow = load_allowlist()

    new_orphans = sorted(orphans - allow)
    stale = sorted(a for a in allow if a not in orphans)  # allowlist済だが今は配線された

    if new_orphans:
        print("❌ 新規の孤立エクスポート(実採譜フロー未配線・allowlist未登録):", file=sys.stderr)
        for s in new_orphans:
            print(f"   - {s}", file=sys.stderr)
        print(
            "\n   → pipeline/CLI/app へ結線するか、意図的なら scripts/orphan_allowlist.txt に追記。",
            file=sys.stderr,
        )
    if stale:
        print("❌ allowlist が古い(配線されたので削除が必要):", file=sys.stderr)
        for s in stale:
            print(f"   - {s}", file=sys.stderr)
        print("\n   → scripts/orphan_allowlist.txt から上記を削除してください(#109 の進捗)。", file=sys.stderr)

    if new_orphans or stale:
        return 1
    print(f"✅ 孤立エクスポート検査OK (used={len(used)} / 凍結中の既知孤立={len(allow)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
