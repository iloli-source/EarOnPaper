"""記譜層(F-098): 単旋律 QuantizedNote 列 → 歌声合成向けエクスポート。

出力は2系統:
- to_vocal_midi: 歌声合成エディタ(SynthV/OpenUtau/VOCALOID)が受け取れる単旋律MIDI。
- to_ust: UTAU/OpenUtau の UST(Sequence Text)。最小構成(Tempo・Length・Lyric・NoteNum)。

設計思想(先行研究 F-098-grok / F-098-codex より):
本機能は「完成した歌声」ではなく「歌える骨格(ノート列 + BPM + 任意の歌詞)」を
渡すもの。連続的な歌唱表現を離散ノートへ切る段階が最大のリスクであるため、
ノート分割は保守的に行う。具体的には次のpitfallを反映している。

1. ビブラート過分割(codex 2.1/3): 揺れを音高変化と解釈して1つのロングトーンを
   短音符列にしない。→ 同一音高の隣接ノートを保守的に結合する。
2. しゃくり誤ノート化(codex 3): 目標音へ到達する直前の極短い低音は装飾であって
   独立ノートではない。→ 短時間・直後に音高の異なる本体が続く先行ノートは
   本体へ吸収する(ピッチカーブ相当はMIDI/USTの本表現には焼き込まない)。
3. ブレスのノート化(codex 4/7): 休符・無声区間に音高ノートを与えない。
   → MIDIは隙間を単に無音とし、USTは休符 `R` として明示する。音高は付けない。

限界(過大主張しないための正直な注記・notesにも記載):
- 本モジュールは QuantizedNote(既に音高・タイミングが確定した離散ノート)を
  入力とする。F0曲線・ビブラート/ポルタメントのピッチカーブ・DYN・音素境界は
  QuantizedNote が保持しないため、MIDI/USTのいずれにも書き出せない(構造的天井)。
- しゃくり/ビブラートの補正は入力ノート列に対する保守的なヒューリスティックで
  あり、真のF0曲線からの分離ではない。過補正を避けるため既定閾値は控えめ。
- 歌詞は既定で母音 "あ"(UST)/歌詞なし(MIDI)。melisma(1音節複数ノート)の
  歌詞割りや UST 方言(単独音/VCV/CVVC)・Phonemizer選択は本モジュールの対象外。
- USTは配布時パス漏洩(grok 2E)を避けるため、音源パス・プロジェクトパスを一切
  書かない最小ヘッダとする。
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from earpipe.contracts import QuantizedNote

# --- 保守的ノート整理のパラメータ ---
# しゃくり(装飾前置音)とみなす最大長(拍)。四分音符=1.0拍基準。
# 16分(0.25拍)より短い前置音のみ装飾候補とし、過補正を避ける。
SCOOP_MAX_DUR_BEATS = 0.2
# 同一音高の隣接ノートを結合する際に許す隙間(拍)。ビブラート由来の
# 微小分割のみを対象とし、本物の休符(発音の途切れ)は保存する。
MERGE_MAX_GAP_BEATS = 0.05
# UST の tick 解像度。OpenUtau/UTAU の四分音符=480 tick 固定(codex 1)。
UST_TICKS_PER_QUARTER = 480
# ブレス/休符を表す UST 歌詞。音高は付けない(codex 4)。
UST_REST_LYRIC = "R"
# 既定の歌詞(母音)。melisma/方言は対象外(grok 5)。
DEFAULT_LYRIC = "あ"
# MIDIノート番号の有効域(GM準拠)。範囲外は書き出しできない。
MIDI_MIN = 0
MIDI_MAX = 127


@dataclass(frozen=True)
class _VocalNote:
    """歌声書き出し用の内部中間表現(拍単位・不変)。

    QuantizedNote の格子側(start_beats/dur_beats)のみを使う。歌声合成の
    ノートは拍位置と音高で決まり、実秒のずれはエディタ側で再調声されるため。
    """

    start_beats: float
    dur_beats: float
    midi: int
    lyric: str


def _validate_bpm(bpm: float) -> None:
    """テンポの境界検証(quantize.py と同じく黙認せず明示エラー)。"""
    if not isinstance(bpm, (int, float)):
        raise TypeError(f"bpm must be a number, got {type(bpm).__name__}")
    if not (bpm == bpm) or bpm <= 0 or bpm == float("inf"):  # NaN/非正/inf を弾く
        raise ValueError(f"bpm must be a positive finite number, got {bpm}")


def _sanitized_monophonic(notes: Sequence[QuantizedNote]) -> list[QuantizedNote]:
    """単旋律として妥当なノート列に整える(音域外除去・単旋律化)。

    - 音高がMIDI域外のノートは書き出し不能のため除去する。
    - 同一開始拍に複数音高がある(和音)場合は最高音のみ残す(歌声は1声・grok 5)。
    - 開始拍順にソートして返す。
    """
    valid = [n for n in notes if MIDI_MIN <= int(n.midi) <= MIDI_MAX]
    ordered = sorted(valid, key=lambda n: (float(n.start_beats), -int(n.midi)))
    mono: list[QuantizedNote] = []
    seen_starts: set[float] = set()
    for n in ordered:
        start = float(n.start_beats)
        if start in seen_starts:
            continue  # 同一開始の下位音(和音の重なり)は捨てる
        seen_starts.add(start)
        mono.append(n)
    return mono


def _absorb_scoops(notes: list[QuantizedNote]) -> list[QuantizedNote]:
    """しゃくり(装飾前置音)を直後の本体ノートへ吸収する(codex 3)。

    条件: ある音符が極短(SCOOP_MAX_DUR_BEATS未満)かつ、直後に音高の異なる
    ノートが隙間なく続く場合、それは本体音への滑り出し装飾とみなし、独立
    ノートにせず本体の開始を前置音の開始へ延ばして1音に統合する。

    保守的方針: 音高が同じ場合は装飾ではなくビブラート系の分割(結合側で処理)。
    隙間がある場合は独立した音とみなし吸収しない(過補正回避)。
    """
    if not notes:
        return []
    result: list[QuantizedNote] = []
    i = 0
    while i < len(notes):
        cur = notes[i]
        if i + 1 < len(notes):
            nxt = notes[i + 1]
            gap = float(nxt.start_beats) - (
                float(cur.start_beats) + float(cur.dur_beats)
            )
            is_short = float(cur.dur_beats) < SCOOP_MAX_DUR_BEATS
            is_scoop = (
                is_short
                and int(cur.midi) != int(nxt.midi)
                and abs(gap) <= MERGE_MAX_GAP_BEATS
            )
            if is_scoop:
                # 本体(nxt)の開始を前置音の開始まで延ばし、前置音は捨てる
                merged = replace(
                    nxt,
                    start_beats=float(cur.start_beats),
                    dur_beats=float(nxt.dur_beats)
                    + (float(nxt.start_beats) - float(cur.start_beats)),
                )
                result.append(merged)
                i += 2
                continue
        result.append(cur)
        i += 1
    return result


def _merge_vibrato(notes: list[QuantizedNote]) -> list[QuantizedNote]:
    """ビブラート由来の同一音高の微小分割を結合する(codex 2.1/3)。

    条件: 隣接する2ノートが同一音高で、隙間が MERGE_MAX_GAP_BEATS 以下なら、
    元は1つのロングトーンが揺れで割れたものとみなし、後続の終端まで1音に結合する。

    保守的方針: 音高が違えば結合しない。隙間が閾値を超える(本物の休符・
    ブレスによる途切れ)場合も結合しない(ブレスを潰さない・codex 4)。
    """
    if not notes:
        return []
    merged: list[QuantizedNote] = [notes[0]]
    for n in notes[1:]:
        last = merged[-1]
        same_pitch = int(n.midi) == int(last.midi)
        gap = float(n.start_beats) - (
            float(last.start_beats) + float(last.dur_beats)
        )
        if same_pitch and gap <= MERGE_MAX_GAP_BEATS:
            end = float(n.start_beats) + float(n.dur_beats)
            merged[-1] = replace(last, dur_beats=end - float(last.start_beats))
        else:
            merged.append(n)
    return merged


def _to_vocal_notes(
    notes: Sequence[QuantizedNote], lyric: str
) -> list[_VocalNote]:
    """QuantizedNote列を保守的に整理して歌声用中間表現へ変換する。

    手順: 単旋律化 → しゃくり吸収 → ビブラート結合 → 歌詞付与。
    分割を「増やす」処理は一切行わない(過分割は歌声合成で最も破綻しやすい)。
    """
    mono = _sanitized_monophonic(notes)
    mono = _absorb_scoops(mono)
    mono = _merge_vibrato(mono)
    return [
        _VocalNote(
            start_beats=float(n.start_beats),
            dur_beats=max(float(n.dur_beats), 0.0),
            midi=int(n.midi),
            lyric=lyric,
        )
        for n in mono
        if float(n.dur_beats) > 0.0
    ]


def to_vocal_midi(
    notes: list[QuantizedNote],
    out_path: str | Path,
    bpm: float = 120.0,
) -> Path:
    """単旋律QuantizedNote列を歌声合成向けの単旋律MIDIに書き出す。

    - 1トラック・単旋律(同時発音なし)。歌声合成エンジンは単声を前提とする(grok 5)。
    - ブレス/休符は隙間として無音のまま残す(音高ノート化しない・codex 4)。
    - しゃくり/ビブラート由来の過分割を保守的に抑制してから書き出す。
    - 拍→秒は指定BPMの一定テンポで変換する(テンポ変化はスコープ外)。

    歌詞・音素はMIDI標準では弱く、ここでは書き込まない(骨格exportに徹する)。
    ピッチカーブ(ビブラート/ポルタメント)はQuantizedNoteが持たないため
    書き出せない — これは構造的な限界(docstring冒頭・notes参照)。

    戻り値: 書き出したMIDIファイルの Path。
    """
    _validate_bpm(bpm)
    import pretty_midi  # 重い依存のため遅延import(score.py と同方針)

    vnotes = _to_vocal_notes(notes, DEFAULT_LYRIC)
    spb = 60.0 / float(bpm)  # seconds per beat(四分音符)

    pm = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    inst = pretty_midi.Instrument(program=53)  # GM 54: Voice Oohs(歌声用途の目印)
    for v in vnotes:
        start = v.start_beats * spb
        end = start + v.dur_beats * spb
        if end <= start:
            end = start + 0.05
        inst.notes.append(
            pretty_midi.Note(velocity=90, pitch=v.midi, start=start, end=end)
        )
    pm.instruments.append(inst)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pm.write(str(out))
    return out


def _beats_to_ust_ticks(dur_beats: float) -> int:
    """拍(四分音符=1.0)を UST の tick(四分音符=480)へ変換する。

    最短は1 tick(0長ノートを作らない)。UTAU/OpenUtau は480 TPQ(codex 1)。
    """
    ticks = int(round(dur_beats * UST_TICKS_PER_QUARTER))
    return max(1, ticks)


def _ust_note_block(index: int, length: int, lyric: str, note_num: int) -> list[str]:
    """UST の1ノートブロック(`[#NNNN]` セクション)の行を組み立てる。

    最小構成: Length / Lyric / NoteNum のみ。PreUtterance/VoiceOverlap/
    ピッチベンド(PBS等)は音源・方言依存のため書かない(受け側デフォルトに委ねる)。
    休符は Lyric=R・NoteNum は直前保持のためダミー(60)を置く。
    """
    return [
        f"[#{index:04d}]",
        f"Length={length}",
        f"Lyric={lyric}",
        f"NoteNum={note_num}",
    ]


def to_ust(
    notes: list[QuantizedNote],
    out_path: str | Path,
    bpm: float = 120.0,
    tempo: float | None = None,
) -> Path:
    """単旋律QuantizedNote列を UTAU の UST テキストに書き出す(最小構成)。

    - ヘッダは Tempo と Tracks/Project の最小情報のみ。音源パス・プロジェクト
      パス・エンジンパスは一切書かない(配布時のパス漏洩回避・grok 2E)。
    - 音符間の隙間(ブレス/休符)は休符ノート `R` として明示する(音高は付けない)。
    - しゃくり/ビブラート由来の過分割を保守的に抑制してから書き出す。
    - 歌詞は既定で母音「あ」。melisma・方言(単独音/VCV/CVVC)は対象外。
    - Tempo は tempo 引数があればそれを、なければ bpm を使う。

    tempo: UST ヘッダに書くテンポ(BPM)。None のとき bpm を採用。
    戻り値: 書き出した UST ファイルの Path。
    """
    _validate_bpm(bpm)
    effective_tempo = bpm if tempo is None else tempo
    _validate_bpm(effective_tempo)

    vnotes = _to_vocal_notes(notes, DEFAULT_LYRIC)

    lines: list[str] = [
        "[#VERSION]",
        "UST Version1.2",
        "[#SETTING]",
        f"Tempo={effective_tempo:.2f}",
        "Tracks=1",
        "Mode2=True",
    ]

    index = 0
    prev_end_beats = 0.0
    prev_note_num = 60  # 休符の NoteNum ダミー(直前音高を引き継ぐ)
    for v in vnotes:
        gap = v.start_beats - prev_end_beats
        if gap > MERGE_MAX_GAP_BEATS:
            # 発音の途切れ = ブレス/休符。音高を与えず R として明示(codex 4)。
            lines.extend(
                _ust_note_block(
                    index, _beats_to_ust_ticks(gap), UST_REST_LYRIC, prev_note_num
                )
            )
            index += 1
        lines.extend(
            _ust_note_block(
                index, _beats_to_ust_ticks(v.dur_beats), v.lyric, v.midi
            )
        )
        index += 1
        prev_end_beats = v.start_beats + v.dur_beats
        prev_note_num = v.midi

    lines.append("[#TRACKEND]")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # UST は Shift-JIS が伝統的だが、OpenUtau は UTF-8 も読む(codex 7)。
    # 母音「あ」等の日本語歌詞のため UTF-8 で書く(受け側で選択可能)。
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
