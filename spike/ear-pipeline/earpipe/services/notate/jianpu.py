"""F-033 簡譜(jianpu / 数字譜)テキスト出力(Issue #70)。

量子化済み音符列(QuantizedNote)と主音のピッチクラス(key_tonic_pc)から、
中国式・日本式で使われる簡譜(数字譜)のテキスト近似を1行で生成する。

設計方針:
- 音度写像は「渡された key_tonic_pc を唯一の真実」とし、music21 の調推定や
  spelling.py の異名同音ロジックには依存しない(親パイプラインが調を注入する
  設計に合わせる)。これにより本関数は純関数として単体テスト可能になる。
- 出力はあくまで monospace テキストでの近似であって、印刷用の厳密な簡譜組版
  (数字の上下に載る上下点、数字の下段に敷く減時線、右に伸ばす増時線の段組)
  ではない。上下点・音価線は ASCII サフィックスで近似する(下記「限界」)。

記法(一次情報に整合):
- 音度: 長音階の音度 1-7。SEMITONE_TO_DEGREE で半音差→音度に写像。
- 臨時記号: 長音階外の半音(pc=1,3,6,8,10)は直下の音度に "#" を前置(例 #1)。
  調号の向き(シャープ系/フラット系)は key_tonic_pc だけでは長短が判別できず
  決められないため、常に "#" 前置で近似する(限界参照)。
- オクターブ: jianpu-ly(ssb22)の ASCII 慣習に倣い、高オクターブは音度の後に
  "'" を、低オクターブは "," を、オクターブ差の個数だけ後置する(例 高8度=1'、
  低8度=1,、高2オクターブ=1'')。中音域(点なし)の基準は MIDI 絶対オクターブで
  固定する(下記 MIDDLE_OCTAVE_MIN..MAX)。
- 音価: 四分音符(dur_beats≈1.0)を素の数字とし、長い音は後置ダッシュ " -" で
  増時線を、短い音は "_" サフィックスで減時線を近似する(8分=1_、16分=1__)。
  付点相当の端数は "." を後置して近似する。
- 休符: "0"。ただし QuantizedNote に休符表現は無いため、入力に休符ノート
  (midi<0)が含まれる場合のみ 0 を出す。ギャップからの休符挿入は行わない。

限界(正直な記録):
- テキスト近似: 上下点・減時線・増時線は本来 monospace の数字に段組で載るが、
  ここでは ASCII サフィックスで近似する。厳密な簡譜組版は将来の engrave 層の責務。
- 中音域基準の恣意性: 簡譜の「点なし中音域」は曲・調により動くが、key_tonic_pc
  だけでは基準オクターブが一意に決まらない。よって MIDI 絶対オクターブ
  (C4=60 を含む 60-71)を点なし中音域に固定する。属音など主音より低い音が
  下点になり得るが、これは仕様上の割り切りである。
- 臨時記号の綴り方向: 常に "#" 前置。同じ主音でも長短で調号方向が異なるため、
  key_tonic_pc からフラット方向を選べない(spelling.py の direction ロジックは
  調オブジェクト前提で流用不可)。
- 転調追従なし: 単一 key_tonic_pc を全音符に適用するため、転調曲では転調後の
  音度がずれる。これは本関数の責務外(親が区間ごとに調を注入すべき問題)。
- 音価近似: 三連符(dur≈0.333)や付点(0.75/1.5)は整数ダッシュ・半減下線に
  完全には載らないため閾値で近似する。厳密な音価段組はテキストでは不可。
"""

from types import MappingProxyType
from typing import Final

from earpipe.contracts import QuantizedNote

# 長音階の半音差(主音からのピッチクラス差)→ 音度文字。
# 表に無い半音(1,3,6,8,10)は臨時記号(直下の音度 + "#")で近似する。
SEMITONE_TO_DEGREE: Final[MappingProxyType[int, str]] = MappingProxyType(
    {0: "1", 2: "2", 4: "3", 5: "4", 7: "5", 9: "6", 11: "7"}
)

# 点なし中音域とする MIDI オクターブ(midi // 12)。C4=60 → 60 // 12 == 5。
# 60-71(C4-B4)を点なし中音域に固定する(限界: 中音域基準の恣意性を参照)。
MIDDLE_OCTAVE: Final[int] = 5

# 音価近似の閾値(dur_beats は四分音符=1.0 の倍率とみなす)。
_DOTTED_HALF_MIN: Final[float] = 2.75   # 付点二分(3拍)以上の下限
_HALF_MIN: Final[float] = 1.75          # 二分(2拍)相当の下限
_DOTTED_QUARTER_MIN: Final[float] = 1.375  # 付点四分(1.5拍)相当の下限
_QUARTER_MIN: Final[float] = 0.75       # 四分(1拍)相当の下限
_EIGHTH_MIN: Final[float] = 0.375       # 8分(0.5拍)相当の下限
# これ未満は 16分(0.25拍)相当として近似する。

# 休符を表す音度文字。
_REST_DEGREE: Final[str] = "0"


def _degree_for_midi(midi: int, key_tonic_pc: int) -> str:
    """MIDI ノート番号を主音基準の音度文字にする(臨時記号は "#" 前置で近似)。

    長音階外の半音は直下の音度に "#" を前置する(例: 主音からの半音差 1 → "#1")。
    key_tonic_pc は呼び出し側で 0-11 に正規化済みである前提。
    """
    deg_pc = (midi % 12 - key_tonic_pc) % 12
    if deg_pc in SEMITONE_TO_DEGREE:
        return SEMITONE_TO_DEGREE[deg_pc]
    # 直下の長音階音(deg_pc - 1)に "#" を前置して近似する。
    lower = SEMITONE_TO_DEGREE[(deg_pc - 1) % 12]
    return f"#{lower}"


def _octave_suffix(midi: int) -> str:
    """MIDI ノート番号のオクターブ点(上点 "'" / 下点 ",")サフィックスを返す。

    点なし中音域(MIDDLE_OCTAVE)より高い/低いオクターブ差の個数だけ
    "'"(高)または ","(低)を後置する。中音域なら空文字。
    """
    octave = midi // 12
    diff = octave - MIDDLE_OCTAVE
    if diff > 0:
        return "'" * diff
    if diff < 0:
        return "," * (-diff)
    return ""


def _duration_suffix(dur_beats: float) -> str:
    """dur_beats(四分音符=1.0 の倍率)を音価近似サフィックスにする。

    増時線はダッシュ " -" の後置、減時線は "_" の後置、付点相当の端数は "." で
    近似する(いずれもテキスト近似。厳密な段組は不可)。
    負値・NaN・0 以下は素の四分音符相当(空サフィックス)として安全側に倒す。
    """
    # NaN(dur != dur)や非正値は四分音符相当とみなしクラッシュさせない。
    if not (dur_beats > 0.0):
        return ""
    if dur_beats >= _DOTTED_HALF_MIN:
        # 3拍以上: 増時線を (round(dur) - 1) 本後置して近似する。
        dashes = max(int(round(dur_beats)) - 1, 1)
        return " -" * dashes
    if dur_beats >= _HALF_MIN:
        return " -"          # 二分音符(2拍)相当: 増時線1本
    if dur_beats >= _DOTTED_QUARTER_MIN:
        return "."           # 付点四分(1.5拍)相当: 付点
    if dur_beats >= _QUARTER_MIN:
        return ""            # 四分音符(1拍)相当: 素の数字
    if dur_beats >= _EIGHTH_MIN:
        return "_"           # 8分音符(0.5拍)相当: 減時線1本
    return "__"              # 16分音符(0.25拍)相当: 減時線2本


def to_jianpu(notes: list[QuantizedNote], key_tonic_pc: int) -> str:
    """量子化音符列を簡譜(数字譜)テキスト近似の1行に変換する。

    各音を主音基準の音度 1-7 に写像し、オクターブ点・音価線を ASCII サフィックスで
    近似して空白区切りで連結する。休符ノート(midi<0)は "0" とする。

    Args:
        notes: 量子化済み音符列(QuantizedNote)。空リストなら "" を返す。
        key_tonic_pc: 主音のピッチクラス。0-11 前提だが 12 以上/負値は % 12 で
            正規化してから使う(未正規化のまま音度表を引くと欠落しうるため)。

    Returns:
        簡譜トークンを半角空白で連結した1行文字列。入力が空なら空文字列。

    Notes:
        本関数はテキスト近似であり厳密な簡譜組版ではない。臨時記号は常に "#" 前置、
        中音域基準は MIDI 絶対オクターブ固定、転調追従なし。詳細はモジュール
        docstring の「限界」を参照。
    """
    if not notes:
        return ""

    tonic_pc = key_tonic_pc % 12
    tokens: list[str] = []
    for note in notes:
        midi = int(note.midi)
        if midi < 0:
            # 休符ノート: 音度 "0" + 音価近似(オクターブ点は付けない)。
            tokens.append(f"{_REST_DEGREE}{_duration_suffix(float(note.dur_beats))}")
            continue
        degree = _degree_for_midi(midi, tonic_pc)
        octave = _octave_suffix(midi)
        duration = _duration_suffix(float(note.dur_beats))
        tokens.append(f"{degree}{octave}{duration}")

    return " ".join(tokens)
