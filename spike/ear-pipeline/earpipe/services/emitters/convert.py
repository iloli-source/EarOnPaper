"""エミッタ: 記譜形式の相互変換レポート(F-037/Issue #85・#109 B-2 結線)。

五線(QuantizedNote列)を起点に、簡譜(jianpu)テキスト・ギターTABフレット割当へ
変換し、さらに TAB→五線 の再構築音高まで一枚のテキストレポートに書き出す。
notate.convert ファサード(staff_to_jianpu / staff_to_tab_frets / tab_to_staff)を
実採譜フローへ結線する(孤立解消)。notes→テキスト型エミッタ。

簡譜の主音は spelling.estimate_key で推定した調の主音ピッチクラスを用いる
(simplify/validate と同じく調文脈は既存推定に委譲する)。

先行研究(F-037)の「黙って壊れない」を反映し、staff→tab で落ちた音の件数
(dropped)と往復(tab→staff)で復元された音数を明示する。

パラメータ: --emit convert:tuning=guitar(現状 guitar のみ。既定 guitar)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.convert import (
    staff_to_jianpu,
    staff_to_tab_frets,
    tab_to_staff,
)
from earpipe.services.notate.spelling import estimate_key

KEY = "convert"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False


def emit(ctx: EmitContext, out_path: Path) -> Path:
    # tuning は将来の非標準チューニング差し替え用の予約。現行エンジンは標準6弦固定。
    tuning_name = ctx.param_str("tuning", "guitar")

    notes = ctx.notes
    key = estimate_key(notes)
    tonic_pc = key.tonic.pitchClass

    jianpu = staff_to_jianpu(notes, tonic_pc)
    tabs = staff_to_tab_frets(notes)
    restored = tab_to_staff(tabs)

    dropped = len(notes) - len(tabs)

    lines = [
        f"# 記譜相互変換 (F-037/Issue #85): {ctx.title}",
        f"tuning: {tuning_name}",
        f"key: {key.tonic.name} {key.mode} (tonic_pc={tonic_pc})",
        f"note_count: {len(notes)}",
        "",
        "## 簡譜 (staff->jianpu, 不可逆)",
        jianpu,
        "",
        f"## TAB (staff->tab, dropped={dropped})",
        *[
            f"  string={t.string_index} fret={t.fret} "
            f"octave_shift={t.octave_shift} "
            f"start_beats={t.start_beats} dur_beats={t.dur_beats}"
            for t in tabs
        ],
        "",
        f"## 往復復元 (tab->staff, restored={len(restored)})",
        *[
            f"  midi={n.midi} start_beats={n.start_beats} "
            f"dur_beats={n.dur_beats}"
            for n in restored
        ],
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
