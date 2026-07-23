"""信頼度ハイライト＋波形の解析ビュー(analysis_view.py)のテスト(#121一部)。

波形の上に採譜音符を信頼度で色分け(緑=高/橙=中/赤=低)して重ね、妥当なPDFを
書き出すことを検証する。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pypdf

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.analysis_view import (
    _confidence_color,
    _render_confidence_svg,
    render_confidence_view_pdf,
)


def _audio() -> tuple[np.ndarray, int]:
    sr = 22050
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    y = (0.3 * np.sin(2 * np.pi * 440 * t)).astype("float32")
    return y, sr


def _notes() -> list[QuantizedNote]:
    # 信頼度をばらけさせる(高/中/低が1つずつ以上)
    return [
        QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.95),
        QuantizedNote(start_beats=1.0, dur_beats=1.0, midi=64, confidence=0.65),
        QuantizedNote(start_beats=2.0, dur_beats=1.0, midi=67, confidence=0.30),
    ]


def test_confidence_color_buckets():
    # 高=緑系 / 中=橙系 / 低=赤系 が異なる色になる
    hi = _confidence_color(0.95)
    mid = _confidence_color(0.65)
    lo = _confidence_color(0.30)
    assert hi != mid and mid != lo and hi != lo


def test_svg_has_waveform_and_confidence_colored_notes():
    y, sr = _audio()
    svg = _render_confidence_svg(y, sr, _notes(), bpm=120.0, title="解析")
    # 波形(背景バー群)＋音符が描かれる
    assert "<rect" in svg
    # 3段階の信頼度色がすべてSVGに現れる(色分けが効いている)
    for conf in (0.95, 0.65, 0.30):
        assert _confidence_color(conf) in svg
    # 凡例(高/中/低)が載る
    for label in ("高", "中", "低"):
        assert label in svg


def test_render_confidence_view_pdf_valid(tmp_path: Path):
    y, sr = _audio()
    out = tmp_path / "conf.pdf"
    result = render_confidence_view_pdf(y, sr, _notes(), 120.0, out, title="信頼度")
    assert result == out
    assert out.read_bytes().startswith(b"%PDF")
    assert len(pypdf.PdfReader(str(out)).pages) >= 1


def test_empty_notes_still_valid(tmp_path: Path):
    y, sr = _audio()
    out = tmp_path / "empty.pdf"
    render_confidence_view_pdf(y, sr, [], 120.0, out, title="empty")
    assert out.exists() and out.stat().st_size > 0
