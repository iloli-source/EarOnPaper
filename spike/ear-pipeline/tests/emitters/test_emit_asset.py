"""asset エミッタのテスト(F-096/Issue #98・#109 B-2 結線)。

export_asset/import_asset を実採譜フロー(EmitContext→emit)へ結線したことを、
非空ファイル出力と往復不変の両面で検証する。
"""

from __future__ import annotations

import json

from earpipe.contracts import QuantizedNote
from earpipe.services.emitters.asset import (
    EXT,
    KEY,
    NEEDS_AUDIO,
    NEEDS_MUSICXML,
    emit,
)
from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.asset_io import import_asset


def _ctx() -> EmitContext:
    notes = [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
        QuantizedNote(start_beats=1.0, dur_beats=0.5, midi=64, confidence=0.8),
    ]
    return EmitContext(notes=notes, bpm=120.0, title="テスト")


def test_module_contract():
    # Arrange / Act / Assert: レジストリが期待する公開属性が揃っている
    assert KEY == "asset"
    assert EXT == "json"
    assert NEEDS_MUSICXML is False
    assert NEEDS_AUDIO is False


def test_emit_writes_nonempty_asset(tmp_path):
    # Arrange
    ctx = _ctx()
    out_path = tmp_path / "song.asset.json"

    # Act
    result = emit(ctx, out_path)

    # Assert: 非空ファイルを返し、asset_io の署名JSONになっている
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "earpipe.asset_io"


def test_emit_roundtrip_invariant(tmp_path):
    # Arrange
    ctx = _ctx()
    out_path = tmp_path / "song.asset.json"

    # Act: emit が書いた資産を import_asset で読み戻す
    emit(ctx, out_path)
    notes, bpm, grid = import_asset(out_path)

    # Assert: 件数・bpm・格子解像度が往復不変
    assert len(notes) == len(ctx.notes)
    assert bpm == ctx.bpm
    assert grid == 4
    assert notes[0].midi == 60


def test_emit_honors_grid_param(tmp_path):
    # Arrange
    ctx = EmitContext(
        notes=[QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=1.0)],
        bpm=100.0,
        title="grid",
        params={"grid_per_beat": "3"},
    )
    out_path = tmp_path / "triplet.asset.json"

    # Act
    emit(ctx, out_path)
    _, _, grid = import_asset(out_path)

    # Assert: パラメータで格子解像度を上書きできる
    assert grid == 3
