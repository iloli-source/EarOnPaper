"""移動ド階名付け(F-100・Issue #75)。

量子化済み音符列を、調の主音を基準にした相対階名(移動ド)へ変換する。
style="solfege" は英語式ソルフェージュ(Do Re Mi Fa Sol La Ti、半音は
Di/Ri/Fi/Si/Li もしくは Ra/Me/Se/Le/Te)、style="numeric" は首調 jianpu
(简谱)式の数字譜(1-7、半音は前置の #/b)を返す。

本関数は music21 非依存で、ピッチクラス算術のみで完結する(重依存追加禁止の
制約に適合し、テスト容易・軽量)。呼び出し側は spelling.estimate_key が返す
music21.key.Key の key.tonic.pitchClass を key_tonic_pc として渡す想定。

限界(正直な記録):
- 半音(相対度数 1/3/6/8/10)は上行綴り(Di 等)と下行綴り(Ra 等)の2通りがあり、
  Wikipedia のソルフェージュ表も両者を併記するのみで単一正解を規定しない。
  本関数は midi 情報しか持たないため、完全な音楽的正解は原理的に不可能。
  直前実音との旋律方向(生 midi 差の符号)で綴りを分岐するヒューリスティックを
  採り、先頭音・同高は上行(raised)を既定とする。この方向判定は前段の
  spelling.py の実際の綴り(調号方向規則)と食い違う場合がある。
- 3度(Mi)と7度(Ti)は raised 綴りを持たない(Wikipedia 表で「—」)。相対度数
  として 3/6/8/10... のうち該当する半音のみ綴り替えし、全音階音はそのまま。
- 英語式 Ti/Sol を単一採用する(固定ド伊仏語圏の Si/So は使わない。移動ド
  raised Sol=Si との衝突を避けるため)。
- key_tonic_pc は %12 で正規化して用いる(範囲外でも明示エラーにせず丸める。
  実用上、主音は 0-11 の想定で呼ばれる)。
"""

from __future__ import annotations

from typing import Literal

from earpipe.contracts import QuantizedNote

# 半音の周期(オクターブ)。
_OCTAVE = 12

# 全音階7音(相対度数 pc -> 階名)。半音位置(1/3/6/8/10)はここに無い。
DIATONIC_SOLFEGE: dict[int, str] = {
    0: "Do", 2: "Re", 4: "Mi", 5: "Fa", 7: "Sol", 9: "La", 11: "Ti",
}
# 上行(raised, iベース)の半音綴り。Mi/Ti は raised を持たない(Wikipedia)。
RAISED_SOLFEGE: dict[int, str] = {
    1: "Di", 3: "Ri", 6: "Fi", 8: "Si", 10: "Li",
}
# 下行(lowered, e/aベース)の半音綴り。Re のみ末尾eのため不規則に Ra。
LOWERED_SOLFEGE: dict[int, str] = {
    1: "Ra", 3: "Me", 6: "Se", 8: "Le", 10: "Te",
}

# 首調 jianpu(简谱)の全音階数字(相対度数 pc -> 数字)。
DIATONIC_NUMERIC: dict[int, str] = {
    0: "1", 2: "2", 4: "3", 5: "4", 7: "5", 9: "6", 11: "7",
}

# 半音位置の集合(全音階に含まれない相対度数)。
_SEMITONE_DEGREES: frozenset[int] = frozenset({1, 3, 6, 8, 10})

Style = Literal["solfege", "numeric"]


def _degree_from_tonic(midi: int, key_tonic_pc: int) -> int:
    """実音 midi の、調主音を基準にした相対度数(0-11)を返す。

    (midi%12 - 主音pc) は負になり得るため、必ず %12 で 0-11 に再正規化する
    (Python の % は非負を返す)。float 混入を避けるため int で計算する。
    """
    return (int(midi) % _OCTAVE - int(key_tonic_pc) % _OCTAVE) % _OCTAVE


def _is_lowered(midi: int, prev_midi: int | None) -> bool:
    """旋律方向から半音を下行綴り(lowered)にすべきか判定する。

    直前実音より低ければ下行(lowered)、そうでなければ(高い・同高・先頭)上行
    (raised)を既定とする。方向は生 midi の差で見る(オクターブ跨ぎの向きを
    正しく取るため。pc 化すると 60→72 の跳躍が差0になり誤る)。
    """
    if prev_midi is None:
        return False
    return int(midi) < int(prev_midi)


def _spell_degree(degree: int, lowered: bool, style: Style) -> str:
    """相対度数(0-11)を、指定 style・旋律方向の階名文字列へ変換する。

    全音階音はテーブル直引き、半音は方向で raised/lowered を選ぶ。
    numeric は全音階数字の前に #(上行)/ b(下行)を付す。
    """
    if degree not in _SEMITONE_DEGREES:
        if style == "solfege":
            return DIATONIC_SOLFEGE[degree]
        return DIATONIC_NUMERIC[degree]

    if style == "solfege":
        table = LOWERED_SOLFEGE if lowered else RAISED_SOLFEGE
        return table[degree]

    # numeric: 半音は下側の全音階数字に b、上側の全音階数字に # を付す。
    if lowered:
        return "b" + DIATONIC_NUMERIC[(degree + 1) % _OCTAVE]
    return "#" + DIATONIC_NUMERIC[(degree - 1) % _OCTAVE]


def to_movable_do(
    notes: list[QuantizedNote],
    key_tonic_pc: int,
    style: str = "solfege",
) -> list[str]:
    """音符列を、調主音基準の相対階名(移動ド)へ変換する純関数。

    引数:
        notes: 量子化済み音符列。旋律順は入力 list の順序を信頼する
            (onset_sec は NaN 既定でソートの根拠に使えないため。contracts.py 参照)。
        key_tonic_pc: 調の主音ピッチクラス(0-11)。%12 で正規化して用いる。
            spelling.estimate_key(...).tonic.pitchClass を渡す想定。
        style: "solfege"(Do Re Mi Fa Sol La Ti / 半音 Di/Ra 等)または
            "numeric"(首調 jianpu の 1-7 / 半音 #1・b2 等)。

    戻り値:
        各音に対応する階名文字列の list(入力と同じ順序・同じ長さ)。
        空入力には空 list を返す(無理に推定しない)。

    例外:
        ValueError: style が "solfege"/"numeric" 以外のとき(静かに失敗しない)。

    限界: 半音の上行/下行綴りは直前音との生 midi 差で決めるヒューリスティックで
    あり、前段のピッチスペリングと食い違う場合がある(モジュール docstring 参照)。
    """
    if style not in ("solfege", "numeric"):
        raise ValueError(
            f"style は 'solfege' か 'numeric' のいずれか。受領値: {style!r}"
        )

    result: list[str] = []
    prev_midi: int | None = None
    for note in notes:
        degree = _degree_from_tonic(note.midi, key_tonic_pc)
        lowered = _is_lowered(note.midi, prev_midi)
        result.append(_spell_degree(degree, lowered, style))
        prev_midi = int(note.midi)
    return result
