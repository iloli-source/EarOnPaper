"""コードダイアグラム（押さえ図）のフォーム。

主要な開放コードは辞書、辞書外はバレーコード計算（Eシェイプ/Aシェイプを
ルート音フレットへ平行移動）で全コードを網羅する。

shape形式: 長さ6のリスト。index0=6弦(低E)〜5=1弦(高E)。
値は フレット番号(0=開放) または None(ミュート)。
"""

from __future__ import annotations

# 開放弦のMIDI（6弦→1弦）
_OPEN_MIDI = (40, 45, 50, 55, 59, 64)

# 主要開放コード辞書。[6弦, 5弦, 4弦, 3弦, 2弦, 1弦]、None=ミュート
OPEN_SHAPES: dict[tuple[int, str], list[int | None]] = {
    (0, "major"): [None, 3, 2, 0, 1, 0],   # C
    (2, "major"): [None, None, 0, 2, 3, 2],  # D
    (4, "major"): [0, 2, 2, 1, 0, 0],       # E
    (5, "major"): [1, 3, 3, 2, 1, 1],       # F (バレー)
    (7, "major"): [3, 2, 0, 0, 0, 3],       # G
    (9, "major"): [None, 0, 2, 2, 2, 0],    # A
    (0, "minor"): [None, 3, 5, 5, 4, 3],    # Cm (バレー)
    (2, "minor"): [None, None, 0, 2, 3, 1],  # Dm
    (4, "minor"): [0, 2, 2, 0, 0, 0],       # Em
    (7, "minor"): [3, 5, 5, 3, 3, 3],       # Gm (バレー)
    (9, "minor"): [None, 0, 2, 2, 1, 0],    # Am
    (2, "dom7"): [None, None, 0, 2, 1, 2],  # D7
    (4, "dom7"): [0, 2, 0, 1, 0, 0],        # E7
    (7, "dom7"): [3, 2, 0, 0, 0, 1],        # G7
    (9, "dom7"): [None, 0, 2, 0, 2, 0],     # A7
    (0, "dom7"): [None, 3, 2, 3, 1, 0],     # C7
    (9, "min7"): [None, 0, 2, 0, 1, 0],     # Am7
    (4, "min7"): [0, 2, 0, 0, 0, 0],        # Em7
    (2, "min7"): [None, None, 0, 2, 1, 1],  # Dm7
    (0, "maj7"): [None, 3, 2, 0, 0, 0],     # Cmaj7
    (5, "maj7"): [None, None, 3, 2, 1, 0],  # Fmaj7
}

# バレーの基準フォーム（0フレット基準の相対フレット）。ルート弦つき。
# Eシェイプ: ルートが6弦。Aシェイプ: ルートが5弦。
_E_SHAPES: dict[str, list[int | None]] = {
    "major": [0, 2, 2, 1, 0, 0],
    "minor": [0, 2, 2, 0, 0, 0],
    "dom7": [0, 2, 0, 1, 0, 0],
    "min7": [0, 2, 0, 0, 0, 0],
    "maj7": [0, 2, 1, 1, 0, 0],
    "dim": [0, 1, 2, 0, 2, 0],
    "sus4": [0, 2, 2, 2, 0, 0],
}
_A_SHAPES: dict[str, list[int | None]] = {
    "major": [None, 0, 2, 2, 2, 0],
    "minor": [None, 0, 2, 2, 1, 0],
    "dom7": [None, 0, 2, 0, 2, 0],
    "min7": [None, 0, 2, 0, 1, 0],
    "maj7": [None, 0, 2, 1, 2, 0],
    "dim": [None, 0, 1, 2, 1, None],
    "sus4": [None, 0, 2, 2, 3, 0],
}


def _barre(quality: str, root_pc: int) -> list[int | None]:
    """バレーコード計算。低い方のポジションを選ぶ（Eシェイプ優先、無理ならAシェイプ）。"""
    # Eシェイプ: 6弦ルート。フレット = root - 40 を 0-11 に正規化
    e_fret = (root_pc - _OPEN_MIDI[0]) % 12
    a_fret = (root_pc - _OPEN_MIDI[1]) % 12
    # 低いポジション（0は開放扱いだが辞書で拾うのでここは1以上を想定）優先
    e_fret = e_fret or 12
    a_fret = a_fret or 12
    if e_fret <= a_fret and quality in _E_SHAPES:
        base = _E_SHAPES[quality]
        return [None if f is None else f + e_fret for f in base]
    if quality in _A_SHAPES:
        base = _A_SHAPES[quality]
        return [None if f is None else f + a_fret for f in base]
    # fallback: Eシェイプmajor
    return [None if f is None else f + e_fret for f in _E_SHAPES["major"]]


def shape_for(root_pc: int, quality: str) -> list[int | None]:
    """コードの押さえフォームを返す（開放辞書優先、無ければバレー計算）。"""
    key = (root_pc % 12, quality)
    if key in OPEN_SHAPES:
        return list(OPEN_SHAPES[key])
    return _barre(quality, root_pc)


def diagram_svg(shape: list[int | None], name: str, x: float, y: float, scale: float = 1.0) -> str:
    """コードダイアグラムのSVG断片を返す。(x, y)は左上。6弦×4フレットの図。

    図(弦・フレット・押さえ点)は反時計回りに90度回転して横向きに描く
    (見やすさ優先・MIE要望 2026-07-23)。コード名テキストは正立のまま。
    """
    frets_shown = 4
    cw = 9 * scale   # 弦間隔
    ch = 11 * scale  # フレット間隔
    w = cw * 5
    h = ch * frets_shown
    # 押弦フレットの基準（最小の正フレット）。0/Noneを除く
    fretted = [f for f in shape if f and f > 0]
    base = min(fretted) if fretted and max(fretted) > frets_shown else 1
    top = y + 4
    rcx = x + w / 2   # 図の回転中心
    rcy = top + h / 2
    grid: list[str] = []   # 図の中身(回転対象)
    # ナット or 開始フレット表示
    if base > 1:
        grid.append(f'<text x="{x - 4}" y="{top + ch*0.8:.1f}" font-size="{7*scale:.1f}" '
                    f'text-anchor="end" fill="#666">{base}</text>')
    else:
        # ナット（太線）
        grid.append(f'<rect x="{x}" y="{top-1.5}" width="{w}" height="2.5" fill="#333"/>')
    # 弦（縦線6本）
    for s in range(6):
        sx = x + s * cw
        grid.append(f'<line x1="{sx}" y1="{top}" x2="{sx}" y2="{top + h}" stroke="#555" stroke-width="{0.8*scale:.1f}"/>')
    # フレット（横線）
    for fr in range(frets_shown + 1):
        fy = top + fr * ch
        grid.append(f'<line x1="{x}" y1="{fy}" x2="{x + w}" y2="{fy}" stroke="#555" stroke-width="{0.8*scale:.1f}"/>')
    # 各弦の押弦点/開放/ミュート
    for s in range(6):
        sx = x + s * cw
        f = shape[s]
        if f is None:
            grid.append(f'<text x="{sx}" y="{top - 2}" font-size="{7*scale:.1f}" text-anchor="middle" fill="#999">×</text>')
        elif f == 0:
            grid.append(f'<circle cx="{sx}" cy="{top - 4}" r="{2.2*scale:.1f}" fill="none" stroke="#666" stroke-width="0.8"/>')
        else:
            rel = f - base + 1
            cy = top + (rel - 0.5) * ch
            grid.append(f'<circle cx="{sx}" cy="{cy:.1f}" r="{3*scale:.1f}" fill="#222"/>')
    # コード名(正立・回転の外)
    name_svg = (f'<text x="{rcx:.1f}" y="{y - 3:.1f}" font-size="{11*scale:.1f}" '
                f'text-anchor="middle" font-weight="bold">{_esc(name)}</text>')
    # 図本体を反時計回り90度回転
    body = f'<g transform="rotate(-90 {rcx:.1f} {rcy:.1f})">' + "".join(grid) + "</g>"
    return name_svg + body


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
