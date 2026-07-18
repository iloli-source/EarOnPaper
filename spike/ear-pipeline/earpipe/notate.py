"""記譜層: 音符列 → 五線譜(music21 Score) → MusicXML / MIDI。

デフォルト出力は五線譜MusicXML(ユーザー裁定 2026-07-19)。
記譜法の追加(TAB/简谱等)は出力プロファイル層の将来拡張(NF-045)。
"""

from pathlib import Path

import music21

TIME_SIGNATURE = "4/4"


def to_score(notes, bpm: float) -> music21.stream.Score:
    """量子化済み音符列を4/4の五線譜スコアにする(小節分割・タイはmusic21に委譲)。"""
    part = music21.stream.Part()
    part.insert(0, music21.meter.TimeSignature(TIME_SIGNATURE))
    part.insert(0, music21.tempo.MetronomeMark(number=float(bpm)))

    if notes:
        for n in notes:
            m21n = music21.note.Note(int(n.midi))
            m21n.quarterLength = float(n.dur_beats)
            part.insert(float(n.start_beats), m21n)
    else:
        part.insert(0, music21.note.Rest(quarterLength=4.0))

    part.makeRests(fillGaps=True, inPlace=True)
    notated = part.makeNotation(inPlace=False)

    score = music21.stream.Score()
    score.insert(0, notated)
    return score


def write_musicxml(score: music21.stream.Score, path) -> None:
    score.write("musicxml", fp=str(Path(path)))


def write_midi(score: music21.stream.Score, path) -> None:
    score.write("midi", fp=str(Path(path)))
