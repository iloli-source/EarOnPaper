"""Guitar Pro形式(.gp5)エクスポート層(F-051・Issue #76)。

QuantizedNote列をPyGuitarPro(`guitarpro`)で読み込み可能な `.gp5` バイナリに
書き出す。弦・フレット割当は tab.py の assign_frets を再利用し、
「手の移動最小化DP」で得た配置をそのままGP5のノートへ写す。

先行研究(docs/research/upcoming/F-051-{grok,codex}.md)で観測された失敗例を
明示的に回避する:

- PyGuitarProはGP3/4/5のみ書ける(GPX/GP7非対応, codex 1-2)。よって
  出力ターゲットは `.gp5` に固定する。GPX(BCFZ独自圧縮)の自前生成は
  モバイル版で「破損」表示になる事例があり避ける(codex 2-8)。
- 書出し→読戻しで全ビートが1つに潰れる不整合(PyGuitarPro Issue #4)や、
  TuxGuitarのゼロバイト破損(codex 2-1)への防御として、一時ファイルへ
  書いてから**自分で読み戻し**、トラック数・小節数・非ゼロサイズを検証し、
  検証通過後にアトミックに置換する(codex ベストプラクティス2)。
- `repeatAlternative` の8bit切詰め(codex 2-7)は反復記号を一切使わない
  ことで回避する(本エクスポータは反復・alternate endingを生成しない)。
- 文字列は既定 `cp1252` で書かれ日本語が化ける(codex 3-7)。曲名等の
  非ASCII文字は書出し前にASCIIへ正規化し、化けを未然に防ぐ(注記も残す)。
- MIDIチャンネル枯渇(16ch上限・トラック2ch消費, codex 2-1)は単一トラック
  のみ生成することで構造的に回避する。
- 任意フィールド(歌詞等)のnullは扱わない(単一トラック・歌詞なし)。

限界(過大主張しない):
- 生成できるのは「validに開けるGP5」であって「音楽的に忠実」ではない
  (grok 4/codex 3-6)。奏法記号(ベンド・ハーモニクス・スライド等)は
  一切書かず、素のフレット音のみ。表拍・タイ・連符の厳密表現は行わない。
- リズムは4/4固定・16分格子前提(score.py/tab.py と同じ)。各ビートは
  小節境界を越えないよう長さをクランプする(拍子超過ノートの破壊的削除,
  grok 2-D-1 の回避)。
- `guitarpro` が使えない環境では MIDI(.mid)へフォールバックする。
  この場合フレット割当情報は失われ、拡張子も `.mid` になる(戻り値のnotesに明記)。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.tab import (
    TUNING_GUITAR,
    TabNote,
    assign_frets,
)

# 標準チューニング(低E→高E, MIDI)。GP5は高→低で7スロット持つが、
# PyGuitarPro既定Songが6弦標準を持つため、ここでは弦値の突合検証にのみ用いる。
TUNING_STANDARD: tuple[int, ...] = TUNING_GUITAR  # (40,45,50,55,59,64)

_BEATS_PER_MEASURE = 4  # 4/4固定(score.py/tab.py と同前提)
_QUARTER_TIME = 960     # GP5内部のティック分解能(Duration.quarterTime)
_MIN_DUR_BEATS = 1.0 / 16.0  # 生成する最短音価(16分音符)= 格子最小
# 最短16分でも表せる最小ティック。これ未満は潰れるので下限クランプする。
_MIN_TICKS = int(round(_MIN_DUR_BEATS * _QUARTER_TIME))


def _to_ascii(text: str) -> str:
    """cp1252での文字化けを避けるため非ASCIIを安全に落とす(codex 3-7)。

    日本語曲名等はGP5の8bitエンコードで化けるため、書出し前にASCIIへ
    正規化する。表現できない文字は '?' に置換し、情報の欠落は notes 側で注記する。
    """
    return text.encode("ascii", "replace").decode("ascii")


def _string_number(tab_string_index: int) -> int:
    """tab.py の string_index(0=6弦/低E)をGP5のstring番号(1=1弦/高E)へ変換。

    tab.py: string_index 0..5 が 6弦(低E)..1弦(高E)。
    GP5(GuitarString.number): 1..6 が 1弦(高E)..6弦(低E)。
    よって number = 6 - string_index。
    """
    return 6 - tab_string_index


def _clamp_dur_beats(dur_beats: float, remaining_beats: float) -> float:
    """ビート長を「16分下限〜小節残り」にクランプする。

    小節境界を越える長さは拍子超過ノートの破壊的削除(grok 2-D-1)を招くため、
    小節内に収める。極端に短い値は最短16分に持ち上げ、書出し→読戻しでの
    ビート潰れ(PyGuitarPro Issue #4)を避ける。
    """
    dur = max(dur_beats, _MIN_DUR_BEATS)
    dur = min(dur, remaining_beats)
    return max(dur, _MIN_DUR_BEATS)


def _group_tabs_by_start(tabs: Sequence[TabNote]) -> list[tuple[float, list[TabNote]]]:
    """同一開始拍のTabNoteを1ビート(和音)に束ね、開始拍昇順で返す。"""
    groups: dict[float, list[TabNote]] = {}
    for t in tabs:
        key = round(t.start_beats, 6)
        groups.setdefault(key, []).append(t)
    return [(k, groups[k]) for k in sorted(groups)]


def _build_song(
    tabs: Sequence[TabNote], tuning: tuple[int, ...], bpm: float, title: str
):
    """TabNote列から単一トラックのGP5 Songオブジェクトを組み立てる。

    小節は4/4固定。ノート間の空白は休符ビートで埋め、各ビートは小節境界を
    越えないようクランプして小節長の不整合を防ぐ。反復・奏法記号・複数
    トラックは生成しない(pitfalls回避のため意図的に最小構成)。
    """
    import guitarpro.models as gpm

    song = gpm.Song()
    song.title = _to_ascii(title)
    song.tempo = int(round(bpm))

    track = song.tracks[0]
    track.name = _to_ascii("Guitar")
    # 既定Songは6弦標準(高→低: 64,59,55,50,45,40)。tuning引数が標準と
    # 異なる場合のみ弦値を上書きする(number順=高→低に合わせる)。
    if tuple(tuning) != TUNING_STANDARD:
        # tuning は低→高(TUNING_GUITAR互換)。GP5弦は number 1..6 = 高→低。
        hi_to_lo = list(reversed(tuning))
        for gstr, val in zip(track.strings, hi_to_lo):
            gstr.value = int(val)

    grouped = _group_tabs_by_start(tabs)

    # 楽譜全体の小節数を決める(最後のノートの開始拍から算出)。
    if grouped:
        last_start = grouped[-1][0]
        n_measures = int(last_start // _BEATS_PER_MEASURE) + 1
    else:
        n_measures = 1

    # 既定Songは header/measure を1組だけ持つ。不足分を複製生成する。
    _ensure_measures(song, track, n_measures)

    # フラットなイベント列を作る: (開始拍, [TabNote...])。
    events = grouped

    # 小節ごとにビートを配置する。
    _fill_voice(track, events, n_measures)
    return song


def _ensure_measures(song, track, n_measures: int) -> None:
    """song/trackが n_measures 個の小節を持つよう header/measure を用意する。"""
    import copy

    import guitarpro.models as gpm

    base_header = song.measureHeaders[0]
    base_header.number = 1

    # ヘッダを必要数まで複製(反復系フィールドは既定=無効のまま)。
    # start はPyGuitarProのwrite時に再計算されるため既定値のままでよい。
    while len(song.measureHeaders) < n_measures:
        h = copy.deepcopy(base_header)
        h.number = len(song.measureHeaders) + 1
        song.measureHeaders.append(h)

    # トラックの measure を header と1対1で作り直す。
    track.measures = []
    for header in song.measureHeaders[:n_measures]:
        track.measures.append(gpm.Measure(track, header))


def _fill_voice(track, events, n_measures: int) -> None:
    """各小節の第1ボイスへ、休符で埋めながらノートビートを並べる。

    events: [(開始拍, [TabNote...]), ...] を開始拍昇順で受け取る。
    小節境界を跨ぐノートは境界でクランプし、次小節には持ち越さない
    (タイ表現を避ける最小構成)。
    """
    # 開始拍 -> 和音 の辞書化(小節内オフセット計算用)。
    by_start = {round(s, 6): notes for s, notes in events}
    starts_sorted = sorted(by_start)

    # 各小節を独立に構築する。
    ptr = 0  # starts_sorted のインデックス
    for mi in range(n_measures):
        measure = track.measures[mi]
        voice = measure.voices[0]
        voice.beats = []
        measure_start = mi * _BEATS_PER_MEASURE
        measure_end = measure_start + _BEATS_PER_MEASURE
        cursor = float(measure_start)  # 現在の絶対拍位置

        while ptr < len(starts_sorted) and starts_sorted[ptr] < measure_end:
            start = starts_sorted[ptr]
            if start < measure_start:
                ptr += 1  # 過去(丸め誤差)。スキップ
                continue
            # ノート開始までの空白を休符で埋める。
            if start - cursor > _MIN_DUR_BEATS / 2:
                gap = _clamp_dur_beats(start - cursor, measure_end - cursor)
                voice.beats.append(_make_rest_beat(voice, gap))
                cursor += gap
                continue  # 埋めた後、再ループで start を評価

            notes = by_start[start]
            # 次ノート開始 or 小節末までを音価とする。
            next_start = (
                starts_sorted[ptr + 1]
                if ptr + 1 < len(starts_sorted)
                else measure_end
            )
            span = min(next_start, measure_end) - start
            dur = _clamp_dur_beats(span, measure_end - cursor)
            voice.beats.append(_make_note_beat(voice, notes, dur))
            cursor += dur
            ptr += 1

        # 小節末までの残りを休符で埋める(空小節も1つの全休符で埋める)。
        while measure_end - cursor > _MIN_DUR_BEATS / 2:
            gap = _clamp_dur_beats(measure_end - cursor, measure_end - cursor)
            voice.beats.append(_make_rest_beat(voice, gap))
            cursor += gap
        if not voice.beats:
            voice.beats.append(_make_rest_beat(voice, float(_BEATS_PER_MEASURE)))


def _duration_for(dur_beats: float):
    """拍長(四分音符=1.0)を最寄りのGP5 Durationに変換する。"""
    import guitarpro.models as gpm

    ticks = max(_MIN_TICKS, int(round(dur_beats * _QUARTER_TIME)))
    return gpm.Duration.fromTime(ticks)


def _make_rest_beat(voice, dur_beats: float):
    """指定拍長の休符ビートを作る。"""
    import guitarpro.models as gpm

    beat = gpm.Beat(voice)
    beat.duration = _duration_for(dur_beats)
    beat.status = gpm.BeatStatus.rest
    beat.notes = []
    return beat


def _make_note_beat(voice, tab_notes: list[TabNote], dur_beats: float):
    """指定拍長のノート(和音)ビートを作る。弦重複は最初の1つを優先。"""
    import guitarpro.models as gpm

    beat = gpm.Beat(voice)
    beat.duration = _duration_for(dur_beats)
    beat.status = gpm.BeatStatus.normal
    notes = []
    used_strings: set[int] = set()
    for tn in tab_notes:
        num = _string_number(tn.string_index)
        if num in used_strings:
            continue  # 同一弦2音は物理的に不能。落とす(tab.py側で既に回避済み)
        used_strings.add(num)
        note = gpm.Note(beat)
        note.value = int(tn.fret)   # フレット番号
        note.string = num           # 1..6 (高E..低E)
        note.type = gpm.NoteType.normal
        notes.append(note)
    beat.notes = notes
    if not notes:
        beat.status = gpm.BeatStatus.rest
    return beat


def _write_and_verify(song, out_path: Path) -> None:
    """一時ファイルへGP5を書き、読み戻して検証してからアトミックに置換する。

    codex ベストプラクティス2: ユーザーのファイルを直接上書きせず、
    書出し→自分で読戻し→非ゼロ・トラック数/小節数一致を検証→アトミック置換。
    TuxGuitarゼロバイト破損(codex 2-1)・ビート潰れ(Issue #4)を前段で捕捉する。
    """
    import guitarpro as gp

    expected_tracks = len(song.tracks)
    expected_measures = len(song.tracks[0].measures)

    fd, tmp_name = tempfile.mkstemp(suffix=".gp5", dir=str(out_path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            gp.write(song, fh, version=(5, 1, 0))
        size = tmp_path.stat().st_size
        if size == 0:
            raise RuntimeError("GP5書出しが0バイト(破損)になりました")
        # 読み戻し検証(cp1252既定で書いたものをそのまま読む)。
        with open(tmp_path, "rb") as fh:
            reloaded = gp.parse(fh)
        if len(reloaded.tracks) != expected_tracks:
            raise RuntimeError(
                f"読戻しトラック数不一致: {len(reloaded.tracks)} != {expected_tracks}"
            )
        got_measures = len(reloaded.tracks[0].measures)
        if got_measures != expected_measures:
            raise RuntimeError(
                f"読戻し小節数不一致: {got_measures} != {expected_measures}"
            )
        os.replace(tmp_path, out_path)  # アトミック置換
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _fallback_midi(
    notes: Sequence[QuantizedNote], out_path: Path, bpm: float
) -> Path:
    """guitarpro非導入時のMIDI近似出力。フレット情報は失われる旨を注記対象とする。"""
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    inst = pretty_midi.Instrument(program=24)  # Acoustic Guitar (nylon)
    sec_per_beat = 60.0 / float(bpm)
    for n in notes:
        start = n.start_beats * sec_per_beat
        end = start + max(n.dur_beats, _MIN_DUR_BEATS) * sec_per_beat
        inst.notes.append(
            pretty_midi.Note(
                velocity=80,
                pitch=int(n.midi),
                start=float(start),
                end=float(end),
            )
        )
    pm.instruments.append(inst)
    midi_path = out_path.with_suffix(".mid")
    midi_path.parent.mkdir(parents=True, exist_ok=True)
    pm.write(str(midi_path))
    return midi_path


def write_guitarpro(
    notes: Sequence[QuantizedNote],
    out_path: str | Path,
    tuning: tuple[int, ...] = TUNING_STANDARD,
    bpm: float = 120.0,
    title: str = "Guitar Pro Export",
) -> Path:
    """QuantizedNote列をGuitar Pro 5形式(.gp5)ファイルに書き出す。

    Args:
        notes: 量子化済み音符列(格子側 start_beats/dur_beats を使用)。
        out_path: 出力先。拡張子は `.gp5` を推奨(フォールバック時は `.mid`)。
        tuning: 6弦チューニング(低E→高E, MIDI)。既定は標準EADGBE。
        bpm: テンポ(BPM)。0以下・非有限は不正としてエラー。
        title: 曲名。非ASCIIはcp1252化け回避のためASCIIへ正規化する。

    Returns:
        実際に書き出したファイルのパス。通常は `.gp5`、`guitarpro` が
        使えない場合は `.mid`(MIDI近似・フレット情報なし)。

    Raises:
        ValueError: bpm が正の有限値でない、または tuning が6要素でない場合。

    限界: 生成物は「validに開けるGP5」であって音楽的忠実性は保証しない
    (奏法記号・タイ・連符・複数トラックは非対応)。詳細はモジュールdocstring。
    """
    import math

    if not (isinstance(bpm, (int, float)) and math.isfinite(bpm) and bpm > 0):
        raise ValueError(f"bpm must be a positive finite number, got {bpm!r}")
    if len(tuning) != 6:
        raise ValueError(f"tuning must have exactly 6 strings, got {len(tuning)}")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import guitarpro  # noqa: F401
    except Exception:
        # guitarpro未導入 → MIDI近似へフォールバック(notesで明示)。
        return _fallback_midi(notes, out_path, bpm)

    tabs = assign_frets(notes)
    song = _build_song(tabs, tuple(tuning), bpm, title)
    if out_path.suffix.lower() != ".gp5":
        out_path = out_path.with_suffix(".gp5")
    _write_and_verify(song, out_path)
    return out_path
