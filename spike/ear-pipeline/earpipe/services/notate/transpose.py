"""F-060 移調・キー変更(Issue #87)。

音符列(QuantizedNote)を半音単位で移調し、調号は music21 のスペリングで
「臨時記号が最少」の異名同音を選んで散乱を避ける。TAB音域外は注記で返す。

設計の要点(先行研究 F-060-grok / F-060-codex の失敗例を反映):

- 譜面移調と再生移調は別レイヤ(codex §0 二層モデル)。本モジュールは
  「譜面/データ側の移調」のみを扱う。音源のピッチシフト(位相ボコーダ由来の
  transient smearing / formant ずれ)はスコープ外であり、混同しない。

- music21 の整数移調は ChromaticInterval になり異名同音を保持しない
  (codex §1.1)。さらに素朴な Key.transpose(chromatic) は D→+6 で G#major
  (シャープ7個超)のような「調号だらけ」を平気で返す(実測)。これは
  「臨時記号散乱」「勝手に読みにくい調へ飛ぶ」失敗(grok F.5/F.7, codex §1.2/§1.6)
  の温床。そこで調は pitch class から異名同音候補を列挙し、|調号| 最小を選ぶ
  (F#/Gb など同数の場合のみ移調方向で決める)。

- QuantizedNote は MIDIノート番号(整数)のみを持ち綴り情報を含まない
  (contracts.py)。音符側の移調は整数の加算で音高は厳密に保たれる。綴りは
  後段の spelling.py(調文脈整合)に委ねる二段構え(codex §1.8: MIDIは
  note number であって flats/sharps ではない)。

- TAB は移調で弦・フレット・演奏可能音域が壊れる(codev §2.4-2.6, grok F.6)。
  色付けだけの見逃しを避けるため、tab.py の音域外音を明示リストで返す
  (transpose_tab_out_of_range)。実際の再割当は tab.py の責務で、ここでは
  「移調でどの音が音域外に出るか」を正直に検出するだけ。
"""

from __future__ import annotations

from dataclasses import replace

import music21

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.tab import TUNING_GUITAR, MAX_FRET

# TAB(ギター6弦標準)の演奏可能MIDI音域。tab.fold_to_range と同一境界を参照する
# ことでモジュール間のずれを防ぐ(codex §2.6: 色付け見逃しの回避)。
TAB_MIDI_LOW = TUNING_GUITAR[0]              # 40 (6弦開放E)
TAB_MIDI_HIGH = TUNING_GUITAR[-1] + MAX_FRET  # 64 + 19 = 83 (1弦最高フレット)

_PITCH_CLASSES = 12


def transpose_notes(notes: list[QuantizedNote], semitones: int) -> list[QuantizedNote]:
    """音符列を半音単位で移調する(音高=MIDIのみを変え、拍・実タイミングは不変)。

    QuantizedNote は綴りを持たず整数MIDIのみを保持するため、移調は midi への
    整数加算で音高が厳密に保たれる(codex §1.8: MIDIは note number であって
    sharps/flats ではない ― 綴りは後段 spelling.py が調文脈で決める)。
    C3二重表現の原則どおり start_beats/dur_beats と onset_sec/offset_sec は
    保持し、immutability のため dataclasses.replace で新インスタンスを返す。

    semitones=0 は恒等(入力と等価な新リストを返す)。
    """
    if not isinstance(semitones, int):
        raise TypeError(f"semitones must be int, got {type(semitones).__name__}")
    return [replace(n, midi=int(n.midi) + semitones) for n in notes]


def transpose_key(key_tonic_pc: int, semitones: int) -> int:
    """調の主音ピッチクラス(0-11)を半音移調し、移調後の主音ピッチクラスを返す。

    純粋なピッチクラス演算(mod 12)。異名同音の綴りは持たない値なので、
    綴り込みの調は spell_transposed_key で別途決める(責務分離)。
    """
    if not isinstance(key_tonic_pc, int):
        raise TypeError(f"key_tonic_pc must be int, got {type(key_tonic_pc).__name__}")
    if not isinstance(semitones, int):
        raise TypeError(f"semitones must be int, got {type(semitones).__name__}")
    if not 0 <= key_tonic_pc < _PITCH_CLASSES:
        raise ValueError(f"key_tonic_pc must be in 0..11, got {key_tonic_pc}")
    return (key_tonic_pc + semitones) % _PITCH_CLASSES


# 各ピッチクラスの異名同音候補(major用のトニック名)。|調号| が小さい順に
# 並べ、同数(F#/Gb)は移調方向で選び分ける。素朴な music21 の
# Key.transpose(chromatic) が返す G#major(8#)/C#major(7#) のような
# 「調号だらけ」を避けるための明示テーブル(先行研究の臨時記号散乱対策)。
_MAJOR_TONIC_CANDIDATES: dict[int, tuple[str, ...]] = {
    0: ("C",),
    1: ("D-", "C#"),
    2: ("D",),
    3: ("E-", "D#"),
    4: ("E", "F-"),
    5: ("F", "E#"),
    6: ("F#", "G-"),   # 同数6#/6b。方向で選ぶ
    7: ("G",),
    8: ("A-", "G#"),
    9: ("A",),
    10: ("B-", "A#"),
    11: ("B", "C-"),
}


def spell_transposed_key(
    key: music21.key.Key, semitones: int
) -> music21.key.Key:
    """調を半音移調し、臨時記号が最少の異名同音の調号を選ぶ(散乱回避)。

    素朴な music21 の Key.transpose(chromatic) は D major を +6 すると
    G# major(シャープ8個)を返し、譜面が二重シャープ/臨時記号だらけになる
    (先行研究 codex §1.2/§1.6・grok F.5/F.7 の「勝手に読みにくい調へ飛ぶ」失敗)。
    ここでは移調後の主音ピッチクラスから |調号| 最小の異名同音を選ぶ。

    選択規則:
    1. |sharps| が最小の綴りを優先(臨時記号を減らす)
    2. F#/Gb のように同数の場合は移調方向で決める
       (上行=シャープ系、下行/ユニゾン=フラット系)。方向情報を尊重することで
       元譜との一貫性を保つ(spelling.py の向き優先と同じ思想)
    """
    new_pc = (key.tonic.pitchClass + semitones) % _PITCH_CLASSES
    prefer_sharp = semitones > 0
    candidates = _MAJOR_TONIC_CANDIDATES[new_pc]

    def rank(tonic_name: str) -> tuple[int, int]:
        cand = music21.key.Key(tonic_name, key.mode)
        # 主目標: 調号の絶対数を最小化(臨時記号散乱の抑制)
        magnitude = abs(cand.sharps)
        # 同数タイブレーク: 移調方向に合う綴りを優先(上行#/下行b)
        direction_penalty = 0 if (cand.sharps >= 0) == prefer_sharp else 1
        return (magnitude, direction_penalty)

    best_name = min(candidates, key=rank)
    return music21.key.Key(best_name, key.mode)


def transpose_tab_out_of_range(
    notes: list[QuantizedNote], semitones: int
) -> list[QuantizedNote]:
    """移調後にTAB(ギター6弦標準)の演奏可能音域を外れる音符を正直に列挙する。

    先行研究(codex §2.4-2.6, grok F.6)の失敗: 移調で弦・フレット・演奏可能音域が
    壊れるのに「色付けだけ」で export に反映されず見逃される。ここでは移調後 midi が
    40..83(6弦開放E〜1弦最高フレット)を外れる音符を返し、呼び出し側がオクターブ
    畳み込み(tab.fold_to_range)や注記を判断できるようにする。

    返すのは「移調後」の音符(midi が加算済み)。空リストなら全音域内。
    """
    shifted = transpose_notes(notes, semitones)
    return [n for n in shifted if not TAB_MIDI_LOW <= n.midi <= TAB_MIDI_HIGH]
