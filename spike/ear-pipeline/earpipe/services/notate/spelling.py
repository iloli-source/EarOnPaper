"""C4 調整合ピッチスペリング(Issue #36)。

調推定(Krumhansl-Schmuckler, music21委譲) → 調文脈に整合する異名同音選択。
「AI下書きの修正が最初から書くより遅い」問題の最頻要因(綴りの乱れ)への対策。

限界(正直な記録):
- 全体1調のみ。転調・区間調(例: Romanze Em→E)は将来課題(受入条件C4の転調追従は未達)
- 半音階・借用和音の綴りは「調号方向優先」の単純規則(声部進行文脈は見ない)
"""

from collections.abc import Sequence

import music21

from earpipe.contracts import QuantizedNote


def estimate_key(notes: Sequence[QuantizedNote]) -> music21.key.Key:
    """量子化済み音符列から全体の調を推定する(Krumhansl-Schmuckler)。

    音価を重みとして反映するため、実際のdurでStreamを組んで analyze('key') に委譲。
    音符が無い場合はハ長調を返す(無理に推定しない)。
    """
    if not notes:
        return music21.key.Key("C")
    s = music21.stream.Stream()
    for n in notes:
        el = music21.note.Note(int(n.midi))
        el.quarterLength = max(float(n.dur_beats), 0.25)
        s.insert(float(n.start_beats), el)
    try:
        key = s.analyze("key")
    except Exception:
        return music21.key.Key("C")
    return _normalize_enharmonic_key(key)


def _normalize_enharmonic_key(key: music21.key.Key) -> music21.key.Key:
    """調号が過剰な異名同音調を簡単な側へ正規化する(C#major 7#→D♭major 5♭ 等)。

    KS推定はMIDI入力から異名同音調を区別できないため、|調号|>6 は同音の
    より簡単な調号に置き換える(6個どうしのF#/G♭は据え置き)。
    """
    if abs(key.sharps) <= 6:
        return key
    tonic = key.tonic.getEnharmonic()
    return music21.key.Key(tonic.name, key.mode)


def spell_midi(midi: int, key: music21.key.Key) -> music21.pitch.Pitch:
    """MIDIノート番号を、調文脈に整合する綴りのPitchにする。

    選択規則(優先順):
    1. 調の音階に含まれる綴り(調号内=臨時記号なしで書ける)
    2. 臨時記号の向きが調号の向きと一致する綴り(シャープ系の調→#、フラット系→b)
    3. 変化量が小さい綴り(ダブルシャープ/フラットは常に除外)
    """
    base = music21.pitch.Pitch(midi=int(midi))
    candidates = [base]
    enh = base.getEnharmonic()
    if enh.midi == base.midi:
        candidates.append(enh)
    enh2 = enh.getEnharmonic()
    if enh2.midi == base.midi and enh2.name not in {c.name for c in candidates}:
        candidates.append(enh2)

    # ダブル臨時記号は除外(全滅したらbaseに戻す)
    simple = [c for c in candidates if abs(c.alter) <= 1]
    if not simple:
        return base

    scale_names = {p.name for p in key.getScale().getPitches()}

    def rank(p: music21.pitch.Pitch) -> tuple[int, int, int]:
        in_scale = 0 if p.name in scale_names else 1
        # 調号の向き(sharps>=0なら#優先、<0ならb優先)。ナチュラルは常に許容
        if p.alter == 0:
            direction = 0
        elif (key.sharps >= 0 and p.alter > 0) or (key.sharps < 0 and p.alter < 0):
            direction = 0
        else:
            direction = 1
        return (in_scale, direction, abs(int(p.alter)))

    best = min(simple, key=rank)
    # octaveを維持(getEnharmonicはoctaveを保持するがmidi一致を最終確認)
    assert best.midi == int(midi)
    return best
