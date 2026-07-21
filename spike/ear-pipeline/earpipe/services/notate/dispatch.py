"""出力形式ディスパッチ層(F-104 #109 結線)。

FORMAT_REGISTRY(format_registry.py)は「何を出せるか」のメタ情報を宣言するが、
それを実採譜フローから呼び出す配線が無かった(登録簿はあるが未結線=偽成功リスク、
docs/debug/root-cause-analysis.md)。本モジュールは登録簿の各形式を、transcribe
中間物(notes / bpm / score / musicxml)から実際に生成する **adapter** を明示テーブルで
持ち、`transcribe --format KEY` から到達可能にする。

producer のシグネチャは不均一(テキスト返却 vs ファイル書込、必要引数の差)なため、
リフレクションではなく key ごとの明示 adapter で安全に吸収する(KISS)。登録簿を
source of truth とし、未登録 key は KeyError で早期・明示的に失敗する。lossy_note は
呼び出し側でユーザーへ提示する(F-104の「lossy を隠さない」設計)。

五線譜/MIDI/PDF/TAB は従来どおり pipeline.py の専用オプション(-o/--midi/--pdf/--tab)で
出力する。本ディスパッチが担うのは登録簿の非レガシー形式(簡譜/リードシート/GP5/UST/
ABC/LilyPond)。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import estimate_chords
from earpipe.services.notate.engrave import render_svg_pages
from earpipe.services.notate.format_registry import OutputFormat, get_format
from earpipe.services.notate.jianpu import to_jianpu
from earpipe.services.notate.leadsheet import to_leadsheet
from earpipe.services.notate.llm_export import to_llm_text
from earpipe.services.notate.spelling import estimate_key
from earpipe.services.notate.vocal_synth_export import to_ust


@dataclass(frozen=True)
class DispatchContext:
    """採譜中間物。各 adapter はここから必要な材料を取り出す。

    Attributes:
        notes: 量子化済みノート列(格子側)。
        bpm: 推定テンポ。
        title: 譜面タイトル(メタデータ用)。
        musicxml_path: MusicXML 出力先(-o 指定時)。musicxml を要する形式
            (LilyPond/SVG)が temp を作らず再利用するための任意入力。
    """

    notes: list[QuantizedNote]
    bpm: float
    title: str
    musicxml_path: Path | None = None


def _tonic_pc(notes: list[QuantizedNote]) -> int:
    return estimate_key(notes).tonic.pitchClass


def _write_text(text: str, out_path: str | Path) -> Path:
    p = Path(out_path)
    p.write_text(text, encoding="utf-8")
    return p


def _adapt_jianpu(ctx: DispatchContext, out_path: str | Path) -> Path:
    return _write_text(to_jianpu(ctx.notes, _tonic_pc(ctx.notes)), out_path)


def _adapt_leadsheet(ctx: DispatchContext, out_path: str | Path) -> Path:
    chords = estimate_chords(ctx.notes, ctx.bpm)
    return _write_text(to_leadsheet(ctx.notes, chords, ctx.bpm), out_path)


def _adapt_ust(ctx: DispatchContext, out_path: str | Path) -> Path:
    return to_ust(ctx.notes, out_path, bpm=ctx.bpm)


def _adapt_abc(ctx: DispatchContext, out_path: str | Path) -> Path:
    chords = estimate_chords(ctx.notes, ctx.bpm)
    text = to_llm_text(ctx.notes, chords, ctx.bpm, key_tonic_pc=_tonic_pc(ctx.notes))
    return _write_text(text, out_path)


def _adapt_lilypond(ctx: DispatchContext, out_path: str | Path) -> Path:
    """LilyPond/SVG(experimental)。musicxml が要るため -o 済みの前提。"""
    if ctx.musicxml_path is None or not Path(ctx.musicxml_path).is_file():
        raise ValueError("--format lilypond には MusicXML 出力(-o)が必要です")
    pages = render_svg_pages(ctx.musicxml_path)
    return _write_text("\n".join(pages), out_path)


# key -> adapter。登録簿の非レガシー形式のみ(レガシーは pipeline の専用オプション)。
# gp5(write_guitarpro)は producer が2拍音符等でクラッシュするため未対応(別Issue)。
# status="stable" だが実際は e2e で落ちる — 結線せず allowlist に留める。
_ADAPTERS: dict[str, Callable[[DispatchContext, "str | Path"], Path]] = {
    "jianpu": _adapt_jianpu,
    "leadsheet": _adapt_leadsheet,
    "ust": _adapt_ust,
    "abc": _adapt_abc,
    "lilypond": _adapt_lilypond,
}


def dispatchable_keys() -> list[str]:
    """本ディスパッチで生成できる形式キー一覧(CLI ヘルプ・検証用)。"""
    return sorted(_ADAPTERS)


def default_out_path(key: str, input_path: str | Path) -> str:
    """出力先未指定時の既定パス。``入力名.KEY.拡張子``(形式間の衝突を避ける)。"""
    fmt = get_format(key)  # 未登録は KeyError
    stem = Path(input_path).stem
    return str(Path(input_path).with_name(f"{stem}.{key}.{fmt.ext}"))


def dispatch_format(key: str, ctx: DispatchContext, out_path: str | Path) -> tuple[Path, OutputFormat]:
    """登録形式 ``key`` を ``out_path`` に生成する。

    Returns:
        (生成パス, 形式メタデータ)。メタの lossy_note を呼び出し側が提示する。

    Raises:
        KeyError: 未登録キー(get_format が利用可能一覧付きで送出)。
        ValueError: ディスパッチ非対応キー(レガシー形式は専用オプションを使う)。
    """
    fmt = get_format(key)  # 未登録は KeyError(登録簿=source of truth)
    adapter = _ADAPTERS.get(key)
    if adapter is None:
        raise ValueError(
            f"形式 {key!r} は --format ディスパッチ非対応です"
            f"(対応: {dispatchable_keys()})。五線譜/MIDI/PDF/TAB は -o/--midi/--pdf/--tab を使用。"
        )
    return adapter(ctx, out_path), fmt
