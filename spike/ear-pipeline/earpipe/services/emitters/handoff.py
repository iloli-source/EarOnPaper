"""エミッタ: 人手仕上げ作業パッケージ(F-093・#109 B-2 結線)。

出力済み MusicXML(下書き)と notes(信頼度つき)から、外部採譜者向けの
引き継ぎ一式(draft.musicxml / 低信頼サマリ / regions / manifest / README、
音源があれば低信頼区間の区間音源)を 1 ファイルの zip にまとめて出力する。
handoff_package モジュールを実採譜フローへ結線する(孤立解消)。

副次成果物は「1 ファイル(.zip)」に収まるため emitter として成立する。
audio_path があれば区間音源も同梱するが必須ではない(NEEDS_AUDIO=False)。

パラメータ: --emit handoff:audio=1(既定 1=元音源があれば区間音源を同梱)。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.handoff_package import build_handoff_package

KEY = "handoff"
EXT = "zip"
NEEDS_MUSICXML = True
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    include_audio = ctx.param_bool("audio", True)
    audio_path = ctx.audio_path if include_audio else None

    # build_handoff_package は自前の out_dir に handoff_package.zip を作る。
    # 作業ディレクトリで生成し、成果物を out_path へ移して 1 ファイルに収める。
    with TemporaryDirectory() as work:
        built = build_handoff_package(
            musicxml_path=ctx.musicxml_path,
            notes=ctx.notes,
            out_dir=work,
            audio_path=audio_path,
        )
        # zip 化に成功していれば built は .zip、失敗時はディレクトリ。
        # いずれも out_path(.zip)へ 1 ファイルとして畳み込む。
        if built.is_file():
            shutil.copyfile(built, out_path)
        else:
            base = out_path.with_suffix("")
            archive = shutil.make_archive(str(base), "zip", root_dir=built)
            if Path(archive) != out_path:
                shutil.move(archive, out_path)
    return out_path
