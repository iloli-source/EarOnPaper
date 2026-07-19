"""C4 調整合ピッチスペリング(Issue #36)。

調推定(Krumhansl-Schmuckler, music21委譲) → 調文脈に整合する異名同音選択。
「AI下書きの修正が最初から書くより遅い」問題の最頻要因(綴りの乱れ)への対策。

限界(正直な記録):
- 全体1調のみ。転調・区間調(例: Romanze Em→E)は将来課題(受入条件C4の転調追従は未達)
- 半音階・借用和音の綴りは「調号方向優先」の単純規則(声部進行文脈は見ない)
- 平行調(相対長短調)の主音/旋法弁別はKS単体では弱いため、主音強調による
  タイブレークを併用する(下記 _resolve_relative_tonic)。主音が第1音でも
  最終音でもエネルギー集中でもない曲では従来どおりKS結果に従う。受入条件C4の
  主調正解率はPD15曲で ≥80%(詳細は bench/bench_key_spelling.py)
"""

from collections import Counter
from collections.abc import Sequence

import music21

from earpipe.contracts import QuantizedNote

# 平行調タイブレークの重み(主音強調)。第1音/最終音のボーナスと
# 主音・属音のエネルギー質量から相対長短調のどちらを主調とするか決める。
_LAST_NOTE_BONUS = 3.0
_FIRST_NOTE_BONUS = 1.0
_TONIC_MASS_WEIGHT = 2.0
_DOMINANT_MASS_WEIGHT = 1.0


def estimate_key(notes: Sequence[QuantizedNote]) -> music21.key.Key:
    """量子化済み音符列から全体の調を推定する(Krumhansl-Schmuckler + 平行調タイブレーク)。

    音価を重みとして反映するため、実際のdurでStreamを組んで analyze('key') に委譲。
    KS結果は平行調(相対長短調)の弁別が弱いため、主音強調で長短調を決め直す
    (_resolve_relative_tonic)。音符が無い場合はハ長調を返す(無理に推定しない)。
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
    except music21.analysis.discrete.DiscreteAnalysisException:
        # KS推定が成立しない入力(単一音の反復等)のみ既定調へ。
        # それ以外の例外は握りつぶさず表面化させる(レビュー#40 M1)
        return music21.key.Key("C")
    return _resolve_relative_tonic(_normalize_enharmonic_key(key), notes)


def _resolve_relative_tonic(
    key: music21.key.Key, notes: Sequence[QuantizedNote]
) -> music21.key.Key:
    """KS結果とその平行調のうち、主音強調スコアが高い側を主調に選ぶ。

    KS(Krumhansl-Schmuckler)はMIDI入力から相対長短調(例: C-dur / a-moll)を
    弁別しにくい。実曲では主音が終止音・冒頭音になりやすく、主音/属音に音価が
    集まる傾向を使い、平行調のどちらが主音かを決め直す(平行調は調号が同一なので
    綴り・調号は変えず、主音/旋法のみを是正する)。
    """
    relative = key.relative
    if relative.tonic.pitchClass == key.tonic.pitchClass:
        return key  # 相対調が存在しない構成(通常あり得ない)は据え置き

    pc_mass: Counter[int] = Counter()
    for n in notes:
        pc_mass[int(n.midi) % 12] += max(float(n.dur_beats), 0.25)
    first_pc = int(notes[0].midi) % 12
    last_pc = int(notes[-1].midi) % 12

    def tonic_score(k: music21.key.Key) -> float:
        tonic_pc = k.tonic.pitchClass
        dominant_pc = (tonic_pc + 7) % 12
        score = (
            pc_mass.get(tonic_pc, 0.0) * _TONIC_MASS_WEIGHT
            + pc_mass.get(dominant_pc, 0.0) * _DOMINANT_MASS_WEIGHT
        )
        if tonic_pc == last_pc:
            score += _LAST_NOTE_BONUS
        if tonic_pc == first_pc:
            score += _FIRST_NOTE_BONUS
        return score

    # 僅差ならKS結果を尊重(タイブレークは主音強調が明確なときだけ覆す)
    return relative if tonic_score(relative) > tonic_score(key) else key


def _normalize_enharmonic_key(key: music21.key.Key) -> music21.key.Key:
    """調号が過剰な異名同音調を簡単な側へ正規化する(C#major 7#→D♭major 5♭ 等)。

    KS推定はMIDI入力から異名同音調を区別できないため、|調号|>6 は同音の
    より簡単な調号に置き換える(6個どうしのF#/G♭は据え置き)。
    """
    if abs(key.sharps) <= 6:
        return key
    tonic = key.tonic.getEnharmonic()
    return music21.key.Key(tonic.name, key.mode)


_SCALE_NAME_CACHE: dict[str, frozenset[str]] = {}


def _scale_names(key: music21.key.Key) -> frozenset[str]:
    """調→音階構成音名の集合。spell_midiが音符ごとに音階を再構築しないためのキャッシュ
    (レビュー#40 M3)。"""
    cache_key = f"{key.tonic.name}:{key.mode}"
    if cache_key not in _SCALE_NAME_CACHE:
        _SCALE_NAME_CACHE[cache_key] = frozenset(
            p.name for p in key.getScale().getPitches()
        )
    return _SCALE_NAME_CACHE[cache_key]


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

    scale_names = _scale_names(key)

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
    # midi一致の最終確認。assertは-O実行で消えるため明示チェックで安全側へ倒す
    # (万一の不一致は綴りより音高が正しいことを優先しbaseへフォールバック。レビュー#40 M2)
    if best.midi != int(midi):
        return base
    return best
