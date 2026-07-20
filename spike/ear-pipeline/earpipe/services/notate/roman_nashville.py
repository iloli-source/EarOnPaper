"""F-091 度数表記(ローマ数字 / ナッシュビル・ナンバー)への写像(Issue #74)。

各コード(ChordSpan)の根音 root_pc を調の主音 key_tonic_pc からの度数へ写像し、
quality から和音の質(大小・7th 等)を付してローマ数字とナッシュビル番号に変換する。

方式(決定論的・自前実装。music21 委譲はしない):
    1. interval = (root_pc - key_tonic_pc) % 12 で主音からの半音距離を求める
    2. 半音距離 -> (度数番号 1-7, 変化記号) を major/minor 別の表で引く
    3. quality から (大小, 接尾辞) を決めローマ数字/ナッシュビル記号を合成する

music21 の romanNumeralFromChord に委譲しない理由:
    - 本タスクは「主音からの度数写像」であり機能和声解析ではない
    - music21 は Chord 再構築が必要で ChordSpan の root_pc/quality から直接使えない
    - 短調の 6/7 度既定が RomanNumeral と romanNumeralFromChord で食い違う既知の
      不整合(cuthbertLab/music21 #437, correctRNAlterationForMinor)を踏む

短調(mode='minor')の方針(最重要の設計判断):
    - ローマ数字・ナッシュビルとも key_tonic_pc をそのまま主音として扱う。
      relative-major(平行長調)への変換は行わない。親が調を渡す責務であり、
      ここで二重変換すると親の調推定と衝突するため。
    - 短調のダイアトニック度数(自然的短音階 1,2,♭3,4,5,♭6,♭7 に相当する
      半音位置)には変化記号を付けない(例: ハ短調の A♭ は ♭VI ではなく VI)。
      これは music21 #437 と同種の「変化度数の番号付け」誤りを避けるための明示表。
    - 導音(和声的短音階の第7音=長7度)も第7度として扱う(V が長三和音になり
      うる点は quality 由来の大小で表現される)。

限界(正直な注記):
    - トライトーン(6半音)の綴りは文脈依存(#4 か ♭5 か一意に決まらない)。
      既定を #4 / #IV に固定する。他の変化音は最近傍ダイアトニック度数への
      下方向 ♭ を既定とする(トライトーンのみ #4 例外)。
    - ナッシュビル実務の「短調曲を平行長調の 6- として書く」表記は採用しない
      (上記のとおり relative-major 変換を行わないため)。
    - 上付き数字は使わず ASCII の '7' を用いる(テスト比較・MusicXML 往来で
      崩れるのを避け、上付き表示はレンダラの責務とする)。
    - 増三和音(aug)や半減/全減(°7)は現状の CHORD_TEMPLATES(7種)に無いため
      未対応。将来テンプレートに aug が加わる場合は '+' 接尾辞が必要。
"""

from __future__ import annotations

from typing import Sequence

from earpipe.services.notate.chord import ChordSpan

# ---- 定数表(すべて module-level の不変オブジェクト) ----

# 度数番号(1-7) -> ローマ数字(常に大文字で保持し quality で小文字化する)
_ROMAN_NUMERALS: tuple[str, ...] = ("I", "II", "III", "IV", "V", "VI", "VII")

# 変化記号(表示は Unicode の ♭/♯。ローマ数字・数字とも前置する)
_FLAT = "♭"   # ♭
_SHARP = "♯"  # ♯

# N.C.(root_pc < 0 / quality == "")の表現
_NO_CHORD = "N.C."

# 長調: 半音距離 -> (度数番号 1-7, 変化記号)。
# ダイアトニック{0,2,4,5,7,9,11}は無記号。変化音は最近傍度数へ下方向♭優先、
# ただしトライトーン(6半音)のみ #4 に固定する(限界: docstring 参照)。
_MAJOR_DEGREE: dict[int, tuple[int, str]] = {
    0: (1, ""),
    1: (2, _FLAT),    # ♭2
    2: (2, ""),
    3: (3, _FLAT),    # ♭3
    4: (3, ""),
    5: (4, ""),
    6: (4, _SHARP),   # #4(トライトーンは #4 固定)
    7: (5, ""),
    8: (6, _FLAT),    # ♭6
    9: (6, ""),
    10: (7, _FLAT),   # ♭7
    11: (7, ""),
}

# 短調: 自然的短音階のダイアトニック{0,2,3,5,7,8,10}は無記号(♭3/♭6/♭7 も
# 短調では正規の度数のため記号を付けない)。変化音{1,4,6,9,11}のみ記号を付す。
# 6半音は長調同様 #4 に固定。第7度は長短どちらも「7」(導音は quality で表現)。
_MINOR_DEGREE: dict[int, tuple[int, str]] = {
    0: (1, ""),
    1: (2, _FLAT),    # ♭2(ナポリ等の変化音)
    2: (2, ""),
    3: (3, ""),       # 短調の第3度(無記号)
    4: (3, _SHARP),   # #3(ピカルディ等の変化音)
    5: (4, ""),
    6: (4, _SHARP),   # #4(トライトーンは #4 固定)
    7: (5, ""),
    8: (6, ""),       # 短調の第6度(無記号。ハ短調 A♭ は VI)
    9: (6, _SHARP),   # #6(旋律的短音階の上行第6度等)
    10: (7, ""),      # 短調の第7度(♭VII ではなく VII)
    11: (7, _SHARP),  # 導音を別綴りで来た場合の保険(#7)
}

# quality -> (大文字にするか, 接尾辞)。ローマ数字用。
# 大文字=長三和音系(major/dom7/maj7/sus4)、小文字=短三和音系(minor/min7)、
# dim は小文字 + '°'。7th はトライアド由来の case に ASCII '7' を付す。
_DEGREE = "°"  # ° (diminished)
_ROMAN_QUALITY: dict[str, tuple[bool, str]] = {
    "major": (True, ""),        # 例: I
    "minor": (False, ""),       # 例: vi
    "dom7": (True, "7"),        # 例: V7
    "min7": (False, "7"),       # 例: ii7
    "maj7": (True, "maj7"),     # 例: Imaj7
    "dim": (False, _DEGREE),    # 例: vii°
    "sus4": (True, "sus4"),     # 例: Vsus4(3度を持たず大小不能→慣例で大文字)
}

# quality -> ナッシュビル接尾辞(数字1-7に付す)。minor/min7 は '-'、dim は '°'、
# dom7/min7/maj7 の 7th は ASCII '7'、sus4 は 'sus4'。
_NASHVILLE_QUALITY: dict[str, str] = {
    "major": "",
    "minor": "-",
    "dom7": "7",
    "min7": "-7",
    "maj7": "maj7",
    "dim": _DEGREE,
    "sus4": "sus4",
}

_VALID_MODES = ("major", "minor")


def _degree_table(mode: str) -> dict[int, tuple[int, str]]:
    """mode に応じた半音距離->度数表を返す。不正な mode は明示エラー。"""
    if mode == "major":
        return _MAJOR_DEGREE
    if mode == "minor":
        return _MINOR_DEGREE
    raise ValueError(
        f"mode は {_VALID_MODES} のいずれかである必要があります: {mode!r}"
    )


def _interval(root_pc: int, key_tonic_pc: int) -> int:
    """根音の主音からの半音距離(0-11)を返す。"""
    return (root_pc - key_tonic_pc) % 12


def to_roman(
    chords: Sequence[ChordSpan],
    key_tonic_pc: int,
    mode: str = "major",
) -> list[str]:
    """コード列をローマ数字度数表記の列へ写像する。

    各 ChordSpan の root_pc を key_tonic_pc からの度数へ写像し、quality から
    大小(長=大文字/短=小文字)と接尾辞(7/maj7/°/sus4)を付す。変化音は
    ♭/♯ をローマ数字の前に置く(例 ♭VII, #iv°)。N.C.(root_pc<0)は 'N.C.'。

    引数:
        chords: ChordSpan の列。
        key_tonic_pc: 調の主音のピッチクラス(0-11)。
        mode: 'major' または 'minor'。それ以外は ValueError。

    戻り値:
        各コードのローマ数字文字列の list(入力と同順・同数)。空入力は空 list。
    """
    table = _degree_table(mode)
    return [_roman_symbol(chord, key_tonic_pc, table) for chord in chords]


def to_nashville(
    chords: Sequence[ChordSpan],
    key_tonic_pc: int,
    mode: str = "major",
) -> list[str]:
    """コード列をナッシュビル・ナンバー表記の列へ写像する。

    各 ChordSpan の root_pc を key_tonic_pc からの度数(1-7)へ写像し、quality
    から修飾を付す(minor/min7 は '-'、dim は '°'、7th は '7'、sus4 は 'sus4')。
    変化音は ♭/♯ を数字の前に置く(例 ♭7, #4)。N.C.(root_pc<0)は 'N.C.'。

    短調では key_tonic_pc をそのまま主音として扱い、平行長調の 6- 表記へは
    変換しない(docstring 冒頭の方針を参照)。

    引数:
        chords: ChordSpan の列。
        key_tonic_pc: 調の主音のピッチクラス(0-11)。
        mode: 'major' または 'minor'。それ以外は ValueError。

    戻り値:
        各コードのナッシュビル番号文字列の list(入力と同順・同数)。空入力は空 list。
    """
    table = _degree_table(mode)
    return [_nashville_symbol(chord, key_tonic_pc, table) for chord in chords]


def _roman_symbol(
    chord: ChordSpan,
    key_tonic_pc: int,
    table: dict[int, tuple[int, str]],
) -> str:
    """単一コードのローマ数字表記を組み立てる。"""
    if chord.root_pc < 0 or chord.quality == "":
        return _NO_CHORD
    degree, accidental = table[_interval(chord.root_pc, key_tonic_pc)]
    is_upper, suffix = _ROMAN_QUALITY[chord.quality]
    numeral = _ROMAN_NUMERALS[degree - 1]
    if not is_upper:
        numeral = numeral.lower()
    # 変化記号は必ず前置(大小変換の後に付与し ♭vii が ♭VII 化しない事故を防ぐ)
    return f"{accidental}{numeral}{suffix}"


def _nashville_symbol(
    chord: ChordSpan,
    key_tonic_pc: int,
    table: dict[int, tuple[int, str]],
) -> str:
    """単一コードのナッシュビル番号表記を組み立てる。"""
    if chord.root_pc < 0 or chord.quality == "":
        return _NO_CHORD
    degree, accidental = table[_interval(chord.root_pc, key_tonic_pc)]
    suffix = _NASHVILLE_QUALITY[chord.quality]
    return f"{accidental}{degree}{suffix}"
