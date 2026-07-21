"""エミッタ: MuseScore ローカル受け渡しパッケージ(F-055/Issue #102・#109 B-2)。

出力済み MusicXML から、MuseScore(または他記譜ソフト)へ**完全ローカルで**
渡すハンドオフ・パッケージを準備する。musescore_handoff モジュールを実採譜
フローへ結線する(孤立解消)。musicxml-in 型エミッタ(validate 参照)。

主成果物は W3C準拠の .mxl(ZIP圧縮MusicXML)。同じディレクトリに README メモと
デバッグ用の非圧縮 .musicxml コピーも併置される(prepare_handoff の仕様)。
online変換・外部送信・MuseScore自動起動は一切行わない(NF-023)。

パラメータ: なし(入力 MusicXML と出力先だけで完結)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.musescore_handoff import prepare_handoff

KEY = "musescore"
EXT = "mxl"
NEEDS_MUSICXML = True
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    # prepare_handoff は out_dir にソースの stem を踏襲した .mxl・.musicxml・README を置く。
    # 主ファイル(.mxl)を out_path に一致させ、エミッタ契約(out_path に非空を書く)を満たす。
    main = prepare_handoff(ctx.musicxml_path, out_path.parent)
    if main.resolve() != out_path.resolve():
        # stem 由来のファイル名を契約上の out_path 名へ揃える(既存があれば置換)。
        out_path.write_bytes(main.read_bytes())
        if main.exists():
            main.unlink()
    return out_path
