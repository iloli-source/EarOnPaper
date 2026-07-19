"""サービス境界の静的検査(ADR-001・#35)。

依存方向が一方向(stem → ear → rhythm → notate)であること、
qualityがエンジン本体に依存しないことをimportのAST走査で強制する。
"""

import ast
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parent.parent / "earpipe" / "services"

# サービスの順序。後のサービスほど下流(下流から上流へのimportのみ許可)
ORDER = {"stem": 0, "ear": 1, "rhythm": 2, "notate": 3}
ALLOWED_SHARED = "earpipe.contracts"


def _imports_of(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _service_of(module_name: str) -> str | None:
    parts = module_name.split(".")
    if len(parts) >= 3 and parts[0] == "earpipe" and parts[1] == "services":
        return parts[2]
    return None


def test_dependency_direction_is_one_way():
    """各サービスは自分より下流のサービスをimportしない。"""
    violations = []
    for svc, rank in ORDER.items():
        for py in (SERVICES_DIR / svc).rglob("*.py"):
            for mod in _imports_of(py):
                target = _service_of(mod)
                if target is None:
                    continue
                if target == "quality":
                    violations.append(f"{py.name}: {svc} → quality は禁止")
                elif target in ORDER and ORDER[target] > rank:
                    violations.append(f"{py.name}: {svc} → {target} (下流への依存)")
    assert not violations, "\n".join(violations)


def test_quality_is_isolated():
    """qualityサービスはエンジン本体(stem/ear/rhythm/notate)に依存しない。"""
    violations = []
    for py in (SERVICES_DIR / "quality").rglob("*.py"):
        for mod in _imports_of(py):
            target = _service_of(mod)
            if target in ORDER:
                violations.append(f"{py.name}: quality → {target}")
    assert not violations, "\n".join(violations)


def test_services_share_only_contracts():
    """サービス間で共有される earpipe 直下モジュールは contracts のみ(シム経由の逆流禁止)。"""
    violations = []
    for py in SERVICES_DIR.rglob("*.py"):
        for mod in _imports_of(py):
            if mod.startswith("earpipe") and not mod.startswith("earpipe.services"):
                if mod != ALLOWED_SHARED:
                    violations.append(f"{py.relative_to(SERVICES_DIR)}: {mod}")
    assert not violations, "\n".join(violations)


def test_quality_client_builds_expected_command():
    """qualityクライアントの契約: ears.py compare のコマンド構成(実行はしない)。"""
    from earpipe.services.quality import build_compare_command

    cmd = build_compare_command("orig.wav", "trans.mid", report="out.md")
    assert cmd[1].endswith("ears.py")
    assert cmd[2] == "compare"
    assert "--original" in cmd and "orig.wav" in cmd
    assert "--transcription" in cmd and "trans.mid" in cmd
    assert "--report" in cmd and "out.md" in cmd
