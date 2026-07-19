"""記譜層: 音符列 → 五線譜(music21 Score) → MusicXML / MIDI。

デフォルト出力は五線譜MusicXML(ユーザー裁定 2026-07-19)。
記譜法の追加(TAB/简谱等)は出力プロファイル層の将来拡張(NF-045)。
"""

from collections.abc import Sequence
from pathlib import Path

import music21

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.spelling import estimate_key, spell_midi

TIME_SIGNATURE = "4/4"


def _group_simultaneous(
    notes: Sequence[QuantizedNote],
) -> list[tuple[float, float, list[int]]]:
    """同一開始拍の音をまとめる: [(start_beats, dur_beats, [midi...])]。

    和音の長さはメンバー最長に合わせる(v0.2の簡略化。声部分離は将来課題)。
    """
    groups: dict[float, list[QuantizedNote]] = {}
    for n in notes:
        groups.setdefault(float(n.start_beats), []).append(n)
    out: list[tuple[float, float, list[int]]] = []
    for start in sorted(groups):
        member = groups[start]
        dur = max(float(m.dur_beats) for m in member)
        out.append((start, dur, sorted({int(m.midi) for m in member})))
    return out


def to_score(notes: Sequence[QuantizedNote], bpm: float) -> music21.stream.Score:
    """量子化済み音符列を4/4の五線譜スコアにする(小節分割・タイはmusic21に委譲)。

    同一開始拍に複数音があれば和音(Chord)として記譜する。
    調を推定して調号を挿入し、綴りは調文脈に整合させる(C4スペリング・Issue #36)。
    """
    part = music21.stream.Part()
    part.insert(0, music21.meter.TimeSignature(TIME_SIGNATURE))
    part.insert(0, music21.tempo.MetronomeMark(number=float(bpm)))

    if notes:
        key = estimate_key(notes)
        part.insert(0, music21.key.KeySignature(key.sharps))
        for start, dur, midis in _group_simultaneous(notes):
            if len(midis) == 1:
                el = music21.note.Note(spell_midi(midis[0], key))
            else:
                el = music21.chord.Chord([spell_midi(m, key) for m in midis])
            el.quarterLength = dur
            part.insert(start, el)
    else:
        part.insert(0, music21.note.Rest(quarterLength=4.0))

    part.makeRests(fillGaps=True, inPlace=True)
    notated = part.makeNotation(inPlace=False)

    score = music21.stream.Score()
    score.insert(0, notated)
    return score


def write_musicxml(score: music21.stream.Score, path: str | Path) -> None:
    score.write("musicxml", fp=str(Path(path)))


def write_midi(score: music21.stream.Score, path: str | Path) -> None:
    score.write("midi", fp=str(Path(path)))
