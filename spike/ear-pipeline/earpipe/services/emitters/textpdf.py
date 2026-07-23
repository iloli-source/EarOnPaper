"""エミッタ: テキスト記譜PDF(簡譜/リードシート・F-RENDER Issue #88・#109 B-2 結線)。

`render_text` の PDF 描画層(自前SVG→cairosvg→pypdf、Verovio非依存)を実採譜
フローへ結線する(孤立解消)。notes から簡譜(数字譜)またはリードシート
(コード+メロディ)のテキスト記譜を組版し、副次成果物として1つのPDFを書き出す。
既定の五線譜/MIDI 出力は一切変えない(オプトイン)。

format=jianpu のとき主音のピッチクラスを estimate_key で推定し(唯一の真実として
to_jianpu に渡す)、format=leadsheet のとき estimate_chords でコード進行を推定して
リードシートにする。simplify(notes変換型)/validate(レポート型)の中間で、
notes→PDF出力型のエミッタとなる。

パラメータ: --emit textpdf:format=jianpu(既定 jianpu)。他に leadsheet /
roman(=degrees) / nashville / movable_do。度数(roman/nashville)と移動ド
(movable_do)も簡譜/リードシートと同じ text→SVG→PDF 経路で描画する(#122)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.chord import estimate_chords
from earpipe.services.notate.render_text import (
    render_degrees_pdf,
    render_jianpu_pdf,
    render_leadsheet_pdf,
    render_movable_do_pdf,
)
from earpipe.services.notate.spelling import estimate_key

KEY = "textpdf"
EXT = "pdf"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    fmt = ctx.param_str("format", "jianpu").strip().lower()
    if fmt == "leadsheet":
        chords = estimate_chords(ctx.notes, ctx.bpm)
        return render_leadsheet_pdf(
            ctx.notes, chords, ctx.bpm, out_path, title=ctx.title
        )
    if fmt == "jianpu":
        tonic_pc = estimate_key(ctx.notes).tonic.pitchClass
        return render_jianpu_pdf(ctx.notes, tonic_pc, out_path, title=ctx.title)
    if fmt in ("roman", "nashville", "degrees"):
        # 度数のPDF化(#122)。degrees はローマ数字の別名。
        key = estimate_key(ctx.notes)
        chords = estimate_chords(ctx.notes, ctx.bpm)
        style = "nashville" if fmt == "nashville" else "roman"
        return render_degrees_pdf(
            chords, key.tonic.pitchClass, key.mode, out_path,
            title=ctx.title, style=style,
        )
    if fmt in ("movable_do", "movabledo", "solfege"):
        # 移動ド階名のPDF化(#122)。
        tonic_pc = estimate_key(ctx.notes).tonic.pitchClass
        return render_movable_do_pdf(ctx.notes, tonic_pc, out_path, title=ctx.title)
    raise ValueError(
        f"未知の format={fmt!r}"
        "(jianpu/leadsheet/roman/nashville/degrees/movable_do を指定してください)"
    )
