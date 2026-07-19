"""記譜層: 音符列 → 五線譜(music21 Score) → MusicXML / MIDI。

デフォルト出力は五線譜MusicXML(ユーザー裁定 2026-07-19)。
Issue #42(記譜品質バンドル): ピアノ音域は大譜表(ト音/ヘ音2段)・左右手割当・
休符統合・stem付与・曲名メタデータの貫通を行う。
記譜法の追加(TAB/简谱等)は出力プロファイル層の将来拡張(NF-045)。
"""

import math
from collections.abc import Sequence
from fractions import Fraction
from pathlib import Path

import music21

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.spelling import estimate_key, spell_midi

TIME_SIGNATURE = "4/4"
BEATS_PER_MEASURE = 4
MIDDLE_C = 60
# staffの中央線(これより上は符幹down、下はup): ト音=B4(71) / ヘ音=D3(50)
TREBLE_MIDLINE = 71
BASS_MIDLINE = 50
DEFAULT_TITLE = "Untitled Transcription"
# 休符統合で使う標準音価(拍)。大きい順に貪欲に充填する。
_REST_DURATIONS: tuple[Fraction, ...] = (
    Fraction(4),
    Fraction(3),
    Fraction(2),
    Fraction(3, 2),
    Fraction(1),
    Fraction(3, 4),
    Fraction(1, 2),
    Fraction(1, 4),
    Fraction(1, 3),
    Fraction(1, 6),
    Fraction(1, 12),
)
_MIN_DUR = Fraction(1, 12)


def _group_simultaneous(
    notes: Sequence[QuantizedNote],
) -> list[tuple[Fraction, Fraction, list[int]]]:
    """同一開始拍の音をまとめる: [(start_beats, dur_beats, [midi...])]。

    和音の長さはメンバー最長に合わせる(声部分離は将来課題)。
    三連格子(1/3拍)の浮動小数は有理数に固定してmusic21の連符表現を安定させる。
    """
    groups: dict[Fraction, list[QuantizedNote]] = {}
    for n in notes:
        start = Fraction(float(n.start_beats)).limit_denominator(12)
        groups.setdefault(start, []).append(n)
    out: list[tuple[Fraction, Fraction, list[int]]] = []
    for start in sorted(groups):
        member = groups[start]
        dur = max(
            Fraction(float(m.dur_beats)).limit_denominator(12) for m in member
        )
        out.append((start, max(dur, _MIN_DUR), sorted({int(m.midi) for m in member})))
    return out


def split_hands(
    notes: Sequence[QuantizedNote],
) -> tuple[list[QuantizedNote], list[QuantizedNote]]:
    """同時発音グループ単位で左右手(ト音/ヘ音)に割り当てる。

    規則(Issue #42・シンプルな高さ基準から開始):
    - グループ全員が中央C(60)以上 → ト音 / 全員が未満 → ヘ音
    - 中央Cをまたぐ広い和音は境界で分割する
    転調帯域(B3-C4付近)でのヒステリシスは将来改善(docstringに明記)。
    """
    groups: dict[float, list[QuantizedNote]] = {}
    for n in notes:
        groups.setdefault(float(n.start_beats), []).append(n)
    treble: list[QuantizedNote] = []
    bass: list[QuantizedNote] = []
    for start in sorted(groups):
        member = groups[start]
        midis = [int(m.midi) for m in member]
        if min(midis) >= MIDDLE_C:
            treble.extend(member)
        elif max(midis) < MIDDLE_C:
            bass.extend(member)
        else:
            for m in member:
                (treble if int(m.midi) >= MIDDLE_C else bass).append(m)
    return treble, bass


def _cap_overlaps(
    groups: list[tuple[Fraction, Fraction, list[int]]],
) -> list[tuple[Fraction, Fraction, list[int]]]:
    """staff内の音価重なりを次グループ開始で打ち切り、声部の爆発を防ぐ。

    旧実装は重なりをmusic21のmakeVoicesに委ね、全小節休符で埋めた5声部
    (帳尻合わせ・codex指摘)を生んでいた。v1は「staffあたり実質1声部+和音」
    に単純化し、失われる持続はデモ批判の再設計課題として記録する。
    """
    out: list[tuple[Fraction, Fraction, list[int]]] = []
    for i, (start, dur, midis) in enumerate(groups):
        if i + 1 < len(groups):
            gap = groups[i + 1][0] - start
            if dur > gap:
                dur = max(gap, _MIN_DUR)
        out.append((start, dur, midis))
    return out


def _decompose_rest(offset: Fraction, length: Fraction) -> list[Fraction]:
    """休符の長さを標準音価に分解する(小節先頭からのoffsetで整列)。"""
    pieces: list[Fraction] = []
    off = offset
    remaining = length
    guard = 0
    while remaining > 0 and guard < 64:
        guard += 1
        for d in _REST_DURATIONS:
            aligned = (off % d == 0) if d >= 1 else True
            if d <= remaining and aligned:
                pieces.append(d)
                off += d
                remaining -= d
                break
        else:
            pieces.append(remaining)
            break
    return pieces


def _consolidate_rests(part: music21.stream.Stream) -> None:
    """小節内の細切れ休符を統合する(Issue #42受入: 連鎖15→小節内4以下)。

    - 音符のない小節 → 全休符1個
    - 小節内の連続休符run → 標準音価の貪欲充填で置き換え
    """
    for measure in part.recurse().getElementsByClass(music21.stream.Measure):
        containers: list[music21.stream.Stream] = (
            list(measure.voices) if measure.voices else [measure]
        )
        for container in containers:
            notes = list(container.notes)
            rests = list(container.getElementsByClass(music21.note.Rest))
            if not rests:
                continue
            if not notes:
                for r in rests:
                    container.remove(r)
                full = music21.note.Rest(
                    quarterLength=float(measure.barDuration.quarterLength)
                )
                container.insert(0, full)
                continue
            # 連続休符runを検出して統合
            rests.sort(key=lambda r: r.offset)
            runs: list[list[music21.note.Rest]] = []
            for r in rests:
                if runs and Fraction(runs[-1][-1].offset).limit_denominator(48) + Fraction(
                    runs[-1][-1].quarterLength
                ).limit_denominator(48) == Fraction(r.offset).limit_denominator(48):
                    runs[-1].append(r)
                else:
                    runs.append([r])
            for run in runs:
                if len(run) <= 1:
                    continue
                start = Fraction(run[0].offset).limit_denominator(48)
                total = sum(
                    (Fraction(r.quarterLength).limit_denominator(48) for r in run),
                    Fraction(0),
                )
                pieces = _decompose_rest(start, total)
                if len(pieces) >= len(run):
                    continue  # 改善しないなら触らない
                for r in run:
                    container.remove(r)
                off = start
                for d in pieces:
                    rest = music21.note.Rest(quarterLength=float(d))
                    container.insert(float(off), rest)
                    off += d


def _set_stems(part: music21.stream.Stream, midline_midi: int) -> None:
    """staff中央線を基準に符幹の向きを設定する(MusicXMLに<stem>を出す)。"""
    for n in part.recurse().notes:
        pitches = n.pitches
        if not pitches:
            continue
        mean = sum(p.midi for p in pitches) / len(pitches)
        n.stemDirection = "down" if mean >= midline_midi else "up"


def _build_staff(
    notes: Sequence[QuantizedNote],
    spell_key: music21.key.Key,
    clef_obj: music21.clef.Clef,
    midline_midi: int,
    bpm: float | None,
    ref_end: Fraction,
    part_cls: type[music21.stream.Part] = music21.stream.Part,
) -> music21.stream.Part:
    """1段ぶんの譜表を構築する(休符充填→記譜化→休符統合→stem付与)。"""
    part = part_cls()
    part.insert(0, clef_obj)
    part.insert(0, music21.meter.TimeSignature(TIME_SIGNATURE))
    part.insert(0, music21.key.KeySignature(spell_key.sharps))
    if bpm is not None:
        part.insert(0, music21.tempo.MetronomeMark(number=float(bpm)))

    for start, dur, midis in _cap_overlaps(_group_simultaneous(notes)):
        if len(midis) == 1:
            el: music21.note.NotRest = music21.note.Note(spell_midi(midis[0], spell_key))
        else:
            el = music21.chord.Chord([spell_midi(m, spell_key) for m in midis])
        el.quarterLength = dur
        part.insert(start, el)

    part.makeRests(
        refStreamOrTimeRange=[0.0, float(ref_end)], fillGaps=True, inPlace=True
    )
    notated = part.makeNotation(inPlace=False)
    _consolidate_rests(notated)
    _set_stems(notated, midline_midi)
    return notated


def _measure_ceil(beats: Fraction) -> Fraction:
    whole = Fraction(BEATS_PER_MEASURE)
    measures = math.ceil(beats / whole) if beats > 0 else 1
    return whole * measures


def to_score(
    notes: Sequence[QuantizedNote],
    bpm: float,
    title: str | None = None,
) -> music21.stream.Score:
    """量子化済み音符列を4/4の五線譜スコアにする。

    ピアノ音域(中央Cをまたぐ入力)は大譜表(ト音+ヘ音)にし、左右手を
    高さ基準で割り当てる。単一域の入力は1段のまま。曲名はmovement-titleへ。
    """
    score = music21.stream.Score()
    md = music21.metadata.Metadata()
    md.movementName = title or DEFAULT_TITLE
    score.metadata = md

    if not notes:
        part = music21.stream.Part()
        part.insert(0, music21.clef.TrebleClef())
        part.insert(0, music21.meter.TimeSignature(TIME_SIGNATURE))
        part.insert(0, music21.tempo.MetronomeMark(number=float(bpm)))
        part.insert(0, music21.note.Rest(quarterLength=float(BEATS_PER_MEASURE)))
        score.insert(0, part.makeNotation(inPlace=False))
        return score

    key = estimate_key(notes)
    treble, bass = split_hands(notes)
    ref_end = _measure_ceil(
        max(
            Fraction(float(n.start_beats)).limit_denominator(12)
            + Fraction(float(n.dur_beats)).limit_denominator(12)
            for n in notes
        )
    )

    if treble and bass:
        upper = _build_staff(
            treble,
            key,
            music21.clef.TrebleClef(),
            TREBLE_MIDLINE,
            bpm,
            ref_end,
            part_cls=music21.stream.PartStaff,
        )
        lower = _build_staff(
            bass,
            key,
            music21.clef.BassClef(),
            BASS_MIDLINE,
            None,
            ref_end,
            part_cls=music21.stream.PartStaff,
        )
        group = music21.layout.StaffGroup(
            [upper, lower], symbol="brace", barTogether=True
        )
        score.insert(0, upper)
        score.insert(0, lower)
        score.insert(0, group)
        return score

    single = treble or bass
    clef_obj: music21.clef.Clef = (
        music21.clef.TrebleClef() if treble else music21.clef.BassClef()
    )
    midline = TREBLE_MIDLINE if treble else BASS_MIDLINE
    score.insert(
        0,
        _build_staff(
            single,
            key,
            clef_obj,
            midline,
            bpm,
            ref_end,
        ),
    )
    return score


def write_musicxml(score: music21.stream.Score, path: str | Path) -> None:
    score.write("musicxml", fp=str(Path(path)))


def write_midi(score: music21.stream.Score, path: str | Path) -> None:
    score.write("midi", fp=str(Path(path)))


def write_midi_raw(
    notes: Sequence[QuantizedNote], path: str | Path, bpm: float = 120.0
) -> None:
    """実タイミング(秒)でMIDIを書く(C3二重表現のraw側・Issue #38)。

    格子に吸着させず onset_sec/offset_sec をそのまま使うため、
    正解音源とのタイミング比較(F1@100ms等)に格子化ロスが混入しない。
    実秒を持たない旧型データ(NaN)は bpm による格子秒へフォールバックする。
    """
    import pretty_midi  # 重い依存のため遅延import(モジュールロードを軽く保つ)

    pm = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    inst = pretty_midi.Instrument(program=0)
    spb = 60.0 / float(bpm)
    for n in notes:
        if math.isnan(n.onset_sec) or math.isnan(n.offset_sec):
            start = float(n.start_beats) * spb
            end = start + float(n.dur_beats) * spb
        else:
            start = float(n.onset_sec)
            end = float(n.offset_sec)
        if end <= start:
            end = start + 0.05
        inst.notes.append(
            pretty_midi.Note(
                velocity=int(round(64 + 63 * max(0.0, min(1.0, n.confidence)))),
                pitch=int(n.midi),
                start=start,
                end=end,
            )
        )
    pm.instruments.append(inst)
    pm.write(str(Path(path)))
