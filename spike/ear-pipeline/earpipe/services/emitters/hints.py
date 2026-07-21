"""エミッタ: 解析ヒント適用レポート(F-009/#106・#109 B-2 結線)。

ear/hints の apply_hints / AnalysisHints を実採譜フローへ結線する(孤立解消)。
CLI から与えたヒント(テンポ/キー/拍子/チューニング/カポ)を、この採譜で実際に
使われた既定解析パラメータ辞書へ適用し、「既定 → 適用後」の差分を人間可読テキストで
出力する副次成果物型エミッタ。既定の五線譜/MIDI 出力は一切変えない(オプトイン)。

既定辞書は本採譜の中間物から構成する: tempo_bpm は ctx.bpm、key_tonic_pc は notes から
estimate_key で推定した主音ピッチクラス。ここへユーザーヒントを apply_hints で重ねる
ことで、「自動推定のまま行くか / 人手で拘束するか」の分岐を1枚のレポートに可視化する
(研究 3.3: 誤ったヒントの連鎖失敗を人が判断できるよう、両者を並べて示す)。

パラメータ(すべて任意。未指定フィールドは None=指定なしとして既定を維持):
  --emit hints:tempo_bpm=140 : テンポ(正の値)
  --emit hints:key_tonic_pc=2 : 主音ピッチクラス(0=C..11=B)
  --emit hints:time_sig=7/8 : 拍子(分子/分母)
  --emit hints:tuning_offset_cents=-13.0 : A=440 からのずれ(cents)
  --emit hints:capo=2 : カポ位置(フレット数, 0=なし)
"""

from __future__ import annotations

from pathlib import Path

from earpipe.services.ear.hints import AnalysisHints, apply_hints
from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.spelling import estimate_key

KEY = "hints"
EXT = "txt"
NEEDS_MUSICXML = False
NEEDS_AUDIO = False

_UNSET = "__unset__"


def _parse_time_sig(raw: str) -> tuple[int, int] | None:
    """"7/8" 形式を (7, 8) に。未指定センチネルなら None を返す。"""
    if raw == _UNSET:
        return None
    num_str, _, den_str = raw.partition("/")
    return (int(num_str), int(den_str))


def _hints_from_ctx(ctx: EmitContext) -> AnalysisHints:
    """CLI パラメータから AnalysisHints を構築する。未指定はすべて None(既定維持)。

    センチネル _UNSET を既定に使い、「指定なし(=None でヒント不適用)」と
    「明示的にその値を指定した」を区別する。境界検証は AnalysisHints 側が行う。
    """
    tempo_raw = ctx.param_float("tempo_bpm", float("nan"))
    key_pc_raw = ctx.param_int("key_tonic_pc", -1)
    tuning_raw = ctx.param_str("tuning_offset_cents", _UNSET)
    capo_raw = ctx.param_int("capo", -1)
    return AnalysisHints(
        tempo_bpm=None if tempo_raw != tempo_raw else tempo_raw,  # NaN=未指定
        key_tonic_pc=None if key_pc_raw < 0 else key_pc_raw,
        time_sig=_parse_time_sig(ctx.param_str("time_sig", _UNSET)),
        tuning_offset_cents=None if tuning_raw == _UNSET else float(tuning_raw),
        capo=None if capo_raw < 0 else capo_raw,
    )


def _defaults_from_ctx(ctx: EmitContext) -> dict:
    """本採譜の中間物から既定解析パラメータ辞書を構成する(自動推定の値)。"""
    key = estimate_key(ctx.notes)
    return {
        "tempo_bpm": ctx.bpm,
        "key_tonic_pc": key.tonic.pitchClass,
        "time_sig": (4, 4),
        "tuning_offset_cents": 0.0,
        "capo": 0,
    }


def emit(ctx: EmitContext, out_path: Path) -> Path:
    defaults = _defaults_from_ctx(ctx)
    hints = _hints_from_ctx(ctx)
    applied = apply_hints(hints, defaults)  # ← 結線対象の公開関数

    param_order = ("tempo_bpm", "key_tonic_pc", "time_sig", "tuning_offset_cents", "capo")
    lines = [
        f"# 解析ヒント適用 (F-009/#106): {ctx.title}",
        "# key=既定(自動推定) → 適用後(ヒント反映)。* は上書きされた項目",
        "",
    ]
    for name in param_order:
        before = defaults.get(name)
        after = applied.get(name)
        mark = " *" if before != after else ""
        lines.append(f"{name}: {before} -> {after}{mark}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
