"""MusicXML → 量子化ノート列の復元(#116)。

採譜済みの中間物(MusicXML)から派生形式(簡譜/度数/移動ド/GP5/UST/ABC 等)を
再生成する際、音声からのフル再採譜(Demucs 分離 + basic-pitch 多声検出)を
やり直すのは遅く状態も共有されない。本モジュールは MusicXML を music21 で
読み直して QuantizedNote 列とテンポを復元し、dispatch_format/dispatch_analysis
がそのまま使える中間物を提供する(採譜処理を再実行しない)。
"""

from __future__ import annotations

from pathlib import Path

from earpipe.contracts import QuantizedNote

_DEFAULT_BPM = 120.0


def notes_from_musicxml(path: str | Path) -> tuple[list[QuantizedNote], float]:
    """MusicXML を読み、(QuantizedNote 列, bpm) を返す。

    - start_beats/dur_beats は music21 の offset/quarterLength(四分音符=1.0)。
    - 和音(Chord)は構成音を同一 start_beats の個別ノートへ展開する。
    - confidence は記譜由来のため 1.0(確定値)とする。
    - テンポは最初の MetronomeMark。無ければ既定 120。

    Raises:
        FileNotFoundError: パスが存在しない。
        ValueError: music21 が解析できない/音符が1つも無い。
    """
    import music21

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"MusicXML が見つかりません: {p}")
    try:
        score = music21.converter.parse(str(p))
    except Exception as e:  # music21 の多様な例外を単一の入力エラーへ畳む
        raise ValueError(f"MusicXML を解析できません: {p} ({e})") from e

    flat = score.flatten()
    bpm = _DEFAULT_BPM
    marks = list(flat.getElementsByClass(music21.tempo.MetronomeMark))
    if marks and marks[0].number:
        bpm = float(marks[0].number)

    notes: list[QuantizedNote] = []
    for el in flat.notes:  # Note と Chord
        start = float(el.offset)
        dur = float(el.quarterLength)
        for pitch in el.pitches:
            notes.append(
                QuantizedNote(
                    start_beats=start,
                    dur_beats=dur,
                    midi=int(pitch.midi),
                    confidence=1.0,
                )
            )
    if not notes:
        raise ValueError(f"MusicXML に音符がありません: {p}")

    notes.sort(key=lambda n: (n.start_beats, n.midi))
    return notes, bpm
