"""解析テキスト出力ディスパッチ(F-091/F-100 #109 B-2a 結線)。

移動ド階名(F-100)・ローマ数字度数/ナッシュビル番号(F-091)は、採譜結果から
派生する **解析注釈** であって FORMAT_REGISTRY の「出力形式」ではない(五線譜や
MIDI のように registry から選べる成果物ではなく、調・コード推定を前提に導出する
テキスト)。そのため dispatch.py(登録簿=source of truth)とは分離し、専用の
アダプタ表で `transcribe --analysis KEY[=PATH]` から到達可能にする。

これらの producer は実装済み・ユニット緑だが実採譜フローから一度も呼ばれておらず
孤立していた(docs/debug/root-cause-analysis.md「ユニット緑≠製品反映」)。本モジュールが
その結線を担う。producer のシグネチャは不均一(音符ベース vs コードベース)なため、
リフレクションではなく key ごとの明示 adapter で吸収する(KISS)。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import music21

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import estimate_chords
from earpipe.services.notate.movable_do import to_movable_do
from earpipe.services.notate.roman_nashville import to_nashville, to_roman
from earpipe.services.notate.spelling import estimate_key

_EXT = "txt"


@dataclass(frozen=True)
class AnalysisContext:
    """採譜中間物のうち解析注釈が必要とする材料。

    Attributes:
        notes: 量子化済みノート列(旋律順は list 順を信頼)。
        bpm: 推定テンポ(コード推定の窓に使う)。
    """

    notes: list[QuantizedNote]
    bpm: float


def _with_header(label: str, key: music21.key.Key, body: str) -> str:
    """推定した調を明記したヘッダを付ける(何調基準の度数/階名かを隠さない)。"""
    text = f"# {label}(推定調: {key.name})\n{body}"
    return text if text.endswith("\n") else text + "\n"


def _adapt_movable_do(ctx: AnalysisContext) -> str:
    key = estimate_key(ctx.notes)
    syllables = to_movable_do(ctx.notes, key.tonic.pitchClass)
    return _with_header("移動ド階名", key, " ".join(syllables))


def _adapt_roman(ctx: AnalysisContext) -> str:
    key = estimate_key(ctx.notes)
    chords = estimate_chords(ctx.notes, ctx.bpm)
    symbols = to_roman(chords, key.tonic.pitchClass, key.mode)
    return _with_header("ローマ数字度数", key, " ".join(symbols))


def _adapt_nashville(ctx: AnalysisContext) -> str:
    key = estimate_key(ctx.notes)
    chords = estimate_chords(ctx.notes, ctx.bpm)
    symbols = to_nashville(chords, key.tonic.pitchClass, key.mode)
    return _with_header("ナッシュビル番号", key, " ".join(symbols))


# key -> adapter。解析注釈のみ(出力形式は dispatch.py が担う)。
_ADAPTERS: dict[str, Callable[[AnalysisContext], str]] = {
    "movable_do": _adapt_movable_do,
    "roman": _adapt_roman,
    "nashville": _adapt_nashville,
}


def analysis_keys() -> list[str]:
    """本ディスパッチで生成できる解析キー一覧(CLI ヘルプ・検証用)。"""
    return sorted(_ADAPTERS)


def default_analysis_path(key: str, input_path: str | Path) -> str:
    """出力先未指定時の既定パス。``入力名.KEY.txt``(形式間の衝突を避ける)。"""
    stem = Path(input_path).stem
    return str(Path(input_path).with_name(f"{stem}.{key}.{_EXT}"))


def dispatch_analysis(key: str, ctx: AnalysisContext, out_path: str | Path) -> Path:
    """解析 ``key`` を ``out_path`` に生成する。

    Raises:
        ValueError: 未対応キー(対応一覧付きで送出。静かに失敗しない)。
    """
    adapter = _ADAPTERS.get(key)
    if adapter is None:
        raise ValueError(
            f"解析 {key!r} は --analysis 非対応です(対応: {analysis_keys()})。"
        )
    p = Path(out_path)
    p.write_text(adapter(ctx), encoding="utf-8")
    return p
