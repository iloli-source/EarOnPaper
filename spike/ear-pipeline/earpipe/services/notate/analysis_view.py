"""信頼度ハイライト＋波形の解析ビュー(#121 の一部)。

採譜結果を「校正する」ための可視化。背景に音声波形(ピーク包絡)、前景に採譜
音符を時間×音高のピアノロールで重ね、各音符を**信頼度で色分け**(緑=高/橙=中/
赤=低)する。どこが弱く検出されたか(要校正か)を一目で分かるようにする。

波形のピーク抽出・ピッチ窓・音符時刻は visual_card の既存ロジックを再利用し、
描画スタック(自前SVG→cairosvg→pypdf)も他の記譜出力と揃える。完全ローカル処理。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

import numpy as np

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.visual_card import (
    _note_time,
    _pitch_name,
    _pitch_window,
    _total_duration,
    downsample_peaks,
)

_PAGE_W, _PAGE_H = 2100, 1200          # 横長(解析・校正向け)
_MARGIN = 90
_HEADER_H = 150
_LEGEND_H = 70
_PLOT_LEFT = _MARGIN
_PLOT_RIGHT = _PAGE_W - _MARGIN
_PLOT_TOP = _MARGIN + _HEADER_H
_PLOT_BOTTOM = _PAGE_H - _MARGIN - _LEGEND_H
_PLOT_W = _PLOT_RIGHT - _PLOT_LEFT
_PLOT_H = _PLOT_BOTTOM - _PLOT_TOP

# 信頼度の3段階しきい値と色(色覚に配慮しつつ、緑=高/橙=中/赤=低の直感)
_CONF_HIGH = 0.8
_CONF_MID = 0.5
_COLOR_HIGH = "#2e9e5b"
_COLOR_MID = "#e0a020"
_COLOR_LOW = "#d1495b"

_FONT = "'Arial Unicode MS', 'Hiragino Sans', 'Noto Sans CJK JP', Helvetica, Arial, sans-serif"


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _confidence_color(conf: float) -> str:
    """信頼度を3段階の色へ。高=緑 / 中=橙 / 低=赤。"""
    if conf >= _CONF_HIGH:
        return _COLOR_HIGH
    if conf >= _CONF_MID:
        return _COLOR_MID
    return _COLOR_LOW


def _render_confidence_svg(
    y: np.ndarray,
    sr: int,
    notes: Sequence[QuantizedNote],
    bpm: float,
    title: str | None = None,
) -> str:
    """波形＋信頼度色分けピアノロールの1ページSVGを返す。"""
    peaks = downsample_peaks(np.asarray(y, dtype=float)) if len(y) else np.array([])
    duration = _total_duration(np.asarray(y, dtype=float), sr, notes, bpm)
    pitch_lo, pitch_hi = _pitch_window(notes)
    span = max(1, pitch_hi - pitch_lo)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_PAGE_W}" height="{_PAGE_H}" '
        f'viewBox="0 0 {_PAGE_W} {_PAGE_H}" font-family="{_FONT}">',
        f'<rect width="{_PAGE_W}" height="{_PAGE_H}" fill="white"/>',
        f'<rect x="{_PLOT_LEFT}" y="{_PLOT_TOP}" width="{_PLOT_W}" height="{_PLOT_H}" '
        f'fill="#fafafa" stroke="#ddd" stroke-width="1"/>',
    ]

    # タイトル＋サブヘッダ
    parts.append(
        f'<text x="{_PLOT_LEFT}" y="{_MARGIN + 50}" font-size="48" '
        f'fill="#222">{_esc(title or "採譜プレビュー")}</text>'
    )
    parts.append(
        f'<text x="{_PLOT_LEFT}" y="{_MARGIN + 96}" font-size="26" fill="#666">'
        f'信頼度ハイライト | BPM {int(round(bpm))} | {duration:.1f}s | {len(list(notes))}音</text>'
    )

    # ピッチグリッド(オクターブ線＋音名)
    for midi in range(pitch_lo, pitch_hi + 1):
        if midi % 12 != 0:
            continue
        frac = (midi - pitch_lo) / span
        gy = _PLOT_BOTTOM - frac * _PLOT_H
        parts.append(
            f'<line x1="{_PLOT_LEFT}" y1="{gy:.1f}" x2="{_PLOT_RIGHT}" y2="{gy:.1f}" '
            f'stroke="#e6e6e6" stroke-width="1" stroke-dasharray="4 6"/>'
        )
        parts.append(
            f'<text x="{_PLOT_LEFT + 6}" y="{gy - 4:.1f}" font-size="18" '
            f'fill="#999">{_pitch_name(midi)}</text>'
        )

    # 背景波形(中央対称の包絡・低不透明度)
    if len(peaks):
        wave_mid = _PLOT_BOTTOM - _PLOT_H * 0.5
        wave_amp = _PLOT_H * 0.22
        step = _PLOT_W / len(peaks)
        bars = []
        for i, p in enumerate(peaks):
            h = max(1.0, float(p) * wave_amp)
            x = _PLOT_LEFT + i * step
            bars.append(f'<rect x="{x:.1f}" y="{wave_mid - h:.1f}" width="{max(1.0, step * 0.8):.1f}" height="{2 * h:.1f}"/>')
        parts.append(f'<g fill="#9bb8d3" fill-opacity="0.35">{"".join(bars)}</g>')

    # 前景音符(信頼度で色分け)
    lane_h = _PLOT_H / (span + 1)
    for note in notes:
        if not (pitch_lo <= note.midi <= pitch_hi):
            continue
        on, off = _note_time(note, bpm)
        x0 = _PLOT_LEFT + (on / duration) * _PLOT_W
        x1 = _PLOT_LEFT + (off / duration) * _PLOT_W
        w = max(6.0, x1 - x0)
        frac = (note.midi - pitch_lo) / span
        cy = _PLOT_BOTTOM - frac * _PLOT_H
        h = max(10.0, lane_h * 0.8)
        color = _confidence_color(min(max(note.confidence, 0.0), 1.0))
        parts.append(
            f'<rect x="{x0:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="3" fill="{color}" fill-opacity="0.9" stroke="#333" stroke-width="1"/>'
        )

    # 凡例(高/中/低)
    ly = _PLOT_BOTTOM + 34
    legend = [("高", _COLOR_HIGH, "≥0.8"), ("中", _COLOR_MID, "0.5–0.8"), ("低", _COLOR_LOW, "<0.5")]
    lx = _PLOT_LEFT
    parts.append(f'<text x="{lx}" y="{ly + 4}" font-size="22" fill="#444">信頼度:</text>')
    lx += 110
    for label, color, rng in legend:
        parts.append(f'<rect x="{lx}" y="{ly - 16}" width="26" height="26" rx="4" fill="{color}"/>')
        parts.append(
            f'<text x="{lx + 34}" y="{ly + 4}" font-size="22" fill="#444">'
            f'{_esc(label)} ({_esc(rng)})</text>'
        )
        lx += 260

    parts.append("</svg>")
    return "".join(parts)


def render_confidence_view_pdf(
    y: np.ndarray,
    sr: int,
    notes: Sequence[QuantizedNote],
    bpm: float,
    out_path: str | Path,
    title: str | None = None,
) -> Path:
    """信頼度ハイライト＋波形の解析ビューをPDFへ書き出す(再読込で妥当性検証)。"""
    import cairosvg
    import pypdf

    svg = _render_confidence_svg(y, sr, notes, bpm, title)
    pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
    writer = pypdf.PdfWriter()
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    for page in reader.pages:
        writer.add_page(page)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        writer.write(f)

    verify = pypdf.PdfReader(str(out_path))
    if len(verify.pages) < 1:
        raise RuntimeError(f"生成PDFのページが0です: {out_path}")
    return out_path
