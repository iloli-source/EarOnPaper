"""孤立エクスポート検査ゲート(scripts/check_orphan_exports.py)自体のテスト。

このゲートは「ユニット緑なのに実採譜フロー未配線」(root-cause-analysis.md §0)を
機械的に捕捉するためのもの。ゲート自体が壊れたら再発検知が効かないので回帰固定する。

AAA形式。
"""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_orphan_exports",
    Path(__file__).resolve().parent.parent / "scripts" / "check_orphan_exports.py",
)
orphan = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(orphan)


def test_known_wired_symbols_are_not_orphans():
    """pipeline.py が実際に import する中核記号は孤立と判定されない。"""
    # Arrange / Act
    orphans, used = orphan.find_orphans()
    # Assert: transcribe 本番経路が使う中核記号
    for sym in ["to_score", "write_pdf", "write_musicxml", "write_midi", "write_tab_pdf"]:
        assert sym not in orphans, f"{sym} は配線済みのはず"
        assert sym in used


def test_dispatch_wired_formats_are_not_orphans():
    """#109 B-1/B-2a で結線した形式・解析は孤立でない(結線の回帰固定)。"""
    # Arrange / Act
    orphans, _ = orphan.find_orphans()
    # Assert: B-1 dispatch.py の producer + B-2a analysis_dispatch.py の producer
    wired = [
        "to_jianpu", "to_leadsheet", "to_ust", "to_llm_text",  # B-1 --format
        "to_movable_do", "to_roman", "to_nashville",  # B-2a --analysis
    ]
    for sym in wired:
        assert sym not in orphans, f"{sym} は #109 で結線済みのはず"


def test_emitter_wired_symbols_are_not_orphans():
    """#109 B-2 汎用エミッタ(emitters/*.py)経由で結線した機能は孤立でない。

    ゲートは emitters/*.py を BFS 起点に加えるため、エミッタが import する producer は
    自動的に配線判定になる(手編集レジストリ不要)。この回帰を固定する。
    """
    # Arrange / Act
    orphans, _ = orphan.find_orphans()
    # Assert: validate エミッタ→musicxml_validate / simplify エミッタ→density
    for sym in ["validate_musicxml", "simplify_density"]:
        assert sym not in orphans, f"{sym} は #109 B-2 エミッタで結線済みのはず"


def test_known_unwired_features_are_detected_as_orphans():
    """export 済みだが今も pipeline 未配線の機能は孤立として検出される。"""
    # Arrange / Act
    orphans, _ = orphan.find_orphans()
    # Assert: まだ結線されていない孤立機能の代表(B-2 エミッタ生成の対象)
    for sym in ["transpose_notes", "write_guitarpro", "detect_drums", "assign_fingering"]:
        assert sym in orphans, f"{sym} は孤立のはず(未配線・B-2対象)"


def test_baseline_passes_with_allowlist():
    """現在の allowlist で main() は 0(既知債務は凍結されている)。"""
    # Arrange / Act
    rc = orphan.main()
    # Assert
    assert rc == 0


def test_allowlist_covers_all_current_orphans():
    """全ての現孤立が allowlist に入っている(=新規孤立ゼロ)。"""
    # Arrange
    orphans, _ = orphan.find_orphans()
    allow = orphan.load_allowlist()
    # Act
    uncovered = orphans - allow
    # Assert
    assert uncovered == set(), f"allowlist 未登録の孤立: {sorted(uncovered)}"


def test_gate_fails_on_new_orphan(monkeypatch):
    """allowlist から1件外すと new_orphan として検知され main() が 1 を返す(ゲート実効性)。"""
    # Arrange: 現孤立から1件を allowlist 対象外にする
    orphans, _ = orphan.find_orphans()
    victim = sorted(orphans)[0]
    full_allow = orphan.load_allowlist()
    monkeypatch.setattr(orphan, "load_allowlist", lambda: full_allow - {victim})
    # Act
    rc = orphan.main()
    # Assert
    assert rc == 1


def test_gate_fails_on_stale_allowlist(monkeypatch):
    """配線済み記号を allowlist に残すと stale として検知され main() が 1 を返す。"""
    # Arrange: 配線済みの to_score を余分に allowlist へ足す
    full_allow = orphan.load_allowlist()
    monkeypatch.setattr(orphan, "load_allowlist", lambda: full_allow | {"to_score"})
    # Act
    rc = orphan.main()
    # Assert
    assert rc == 1
