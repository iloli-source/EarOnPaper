"""記譜層: 音符列＋コード進行 → LLM/人間可読の構造化テキスト(F-099・Issue #82)。

目的: 採譜結果(量子化音符＋推定コード)を、LLM が二次加工(要約・移調・
アレンジ提案・誤り指摘)しやすく、かつ人間も読める平文へ落とす。MusicXML は
機械には厳密だが LLM には冗長でトークン効率が悪く、ASCII リードシート
(leadsheet.py)は俯瞰向きで細部(拍位置・音価・信頼度)を落とす。本モジュールは
その中間として「小節ごとに 拍グリッド＋コード＋音符列 を明示ラベル付きで並べる」
行指向フォーマットを純関数で提供する。パースは `key: value` と `Bar N:` の
単純な行走査で足り、正規表現も専用パーサも要らない。

フォーマット概要(1行1情報・行頭ラベルでパース容易):
    # EarPipe LLM Export v1
    bpm: 120
    meter: 4/4
    key: C major
    bars: 2
    # 注記(情報欠落) ... 数行
    # ---
    Bar 1 | beats 0.0-4.0
      chord: C
      notes: C4@0.0(1.0) E4@1.0(1.0) G4@2.0(2.0)
    Bar 2 | beats 4.0-8.0
      chord: (hold)
      notes: (rest)

音符トークンは `音名オクターブ@開始拍(音価拍)` 形式。開始拍・音価は小節先頭を
0.0 とした「小節内相対拍」で書く(小節をまたぐ音は開始小節に置き、音価は原値の
まま=小節境界で切らない。これは leadsheet.py と同じ hold 方針)。

正直な限界(情報欠落・pitfall。エクスポートは推定結果を"確定"に見せがちなので明記):
- 実タイミング欠落: start/dur は量子化格子(拍)であり onset_sec/offset_sec の
  実タイミング(C3二重表現の実側)は書かない。演奏の揺れ・ルバートは失われる。
- 信頼度の縮約: 音符ごとの confidence は数値としては出さず、低信頼音に `?`
  マーカーを付すだけ(既定閾値 _LOW_CONF)。「自信のない推定」を確定表記しない配慮。
- 和声の縮約: chord は ChordSpan.name をそのまま信頼する。誤コード・N.C. は
  そのまま現れる。内声・転回・ボイシングは出さない。
- 拍子/調の誤り: meter は estimate_meter、key は estimate_key に委譲するため、
  短い断片・弱起・証拠不足では 4/4・ハ長調へ退避し得る(各モジュールの限界を継承)。
- 小節整合: score.py の先頭空小節シフト(_drop_leading_silence)は行わない。
  弱起・冒頭休符では五線譜と小節番号がずれ得る(表示位置のみ・実タイミング不変)。
- 多声の同時発音: 和音(同一開始拍)は全音を列挙するが、声部分離はしない。
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.spelling import estimate_key, spell_midi

# 空入力・退避時の小節あたり拍数(estimate_meter と同じ既定=4/4)。
BEATS_PER_MEASURE: int = 4
# 拍位置の丸め許容誤差(浮動小数の格子ゆらぎ吸収)。
_BEAT_EPS: float = 1e-6
# 拍値の表示桁(格子は最小 1/4 拍程度なので小数1桁で十分)。
_BEAT_NDIGITS: int = 3
# この confidence 未満の音符に不確実マーカー `?` を付す。
_LOW_CONF: float = 0.5
# コード継続(またぎ・空欄)を表す語。leadsheet の hold と同義。
_HOLD: str = "(hold)"
# 音符が無い小節のプレースホルダ。
_REST: str = "(rest)"


def _fmt_beat(value: float) -> str:
    """拍値を短く整形する(整数はそのまま、端数は _BEAT_NDIGITS 桁で丸め末尾0除去)。"""
    rounded = round(float(value), _BEAT_NDIGITS)
    if abs(rounded - round(rounded)) < _BEAT_EPS:
        return str(int(round(rounded)))
    # 末尾の余分な 0 を落として "1.5" のように書く。
    return f"{rounded:.{_BEAT_NDIGITS}f}".rstrip("0").rstrip(".")


def _bar_beats(notes: Sequence[QuantizedNote]) -> int:
    """小節あたりの拍数を決める(score.py/leadsheet.py と整合する estimate_meter)。

    音符が空・証拠不足のときは 4/4 相当(BEATS_PER_MEASURE)へ退避する。
    """
    if not notes:
        return BEATS_PER_MEASURE
    from earpipe.services.rhythm.meter import estimate_meter

    beats = estimate_meter(list(notes))
    return beats if beats > 0 else BEATS_PER_MEASURE


def _end_beats(
    notes: Sequence[QuantizedNote], chords: Sequence[ChordSpan]
) -> float:
    """総尺(拍)= 音符終端とコード終端の大きい方。空列は 0.0(guard)。"""
    note_end = max(
        (float(n.start_beats) + float(n.dur_beats) for n in notes), default=0.0
    )
    chord_end = max((float(c.end_beats) for c in chords), default=0.0)
    return max(note_end, chord_end)


def _num_measures(end_beats: float, bar_beats: int) -> int:
    """総尺と小節長から総小節数を求める(最小 1 小節)。"""
    if end_beats <= _BEAT_EPS:
        return 1
    return max(1, math.ceil(end_beats / bar_beats))


def _key_label(key: object) -> str:
    """music21 Key を "C major" 形式のラベルにする(失敗時は unknown)。"""
    tonic = getattr(getattr(key, "tonic", None), "name", None)
    mode = getattr(key, "mode", None)
    if tonic is None or mode is None:
        return "unknown"
    return f"{tonic} {mode}"


def _chord_cell(
    chords: Sequence[ChordSpan], measure_start: float, measure_end: float
) -> str:
    """1小節ぶんのコード表記。start_beats がこの小節に入るスパンを開始拍順に併記。

    この小節に開始スパンが無ければ hold(直前コード継続)とする。またぎスパンは
    開始小節でのみ名前が出る(leadsheet.py と同じ方針)。
    """
    names = [
        c.name
        for c in sorted(chords, key=lambda c: float(c.start_beats))
        if measure_start - _BEAT_EPS <= float(c.start_beats) < measure_end - _BEAT_EPS
    ]
    return " ".join(names) if names else _HOLD


def _note_token(note: QuantizedNote, measure_start: float, key: object) -> str:
    """音符を `音名オクターブ@小節内開始拍(音価拍)` トークンにする。

    低信頼(confidence < _LOW_CONF)には末尾 `?` を付し、確定推定に見せない。
    綴りは spelling.py に一本化(調整合スペリング)する。
    """
    pitch = spell_midi(int(note.midi), key)  # type: ignore[arg-type]
    rel_start = float(note.start_beats) - measure_start
    dur = float(note.dur_beats)
    mark = "?" if float(note.confidence) < _LOW_CONF else ""
    return (
        f"{pitch.nameWithOctave}@{_fmt_beat(rel_start)}"
        f"({_fmt_beat(dur)}){mark}"
    )


def _notes_cell(
    notes: Sequence[QuantizedNote],
    measure_start: float,
    measure_end: float,
    key: object,
) -> str:
    """1小節ぶんの音符列トークン。start_beats がこの小節に入る音を開始拍順に並べる。

    同時発音(和音)は全音を列挙する(声部分離はしない)。音符が無ければ rest。
    """
    in_bar = [
        n
        for n in notes
        if measure_start - _BEAT_EPS <= float(n.start_beats) < measure_end - _BEAT_EPS
    ]
    if not in_bar:
        return _REST
    ordered = sorted(in_bar, key=lambda n: (float(n.start_beats), int(n.midi)))
    return " ".join(_note_token(n, measure_start, key) for n in ordered)


def _header_lines(
    bpm: float, bar_beats: int, key_label: str, n_measures: int
) -> list[str]:
    """先頭メタ情報＋情報欠落注記のヘッダ行群を組み立てる。"""
    return [
        "# EarPipe LLM Export v1",
        f"bpm: {bpm:g}",
        f"meter: {bar_beats}/4",
        f"key: {key_label}",
        f"bars: {n_measures}",
        "# note token = pitch@start_beat(duration_beats); "
        "beats are bar-relative; '?' marks low confidence",
        "# 情報欠落注記(pitfalls): "
        "実タイミング(秒)は非出力(拍格子のみ)/信頼度は?印のみ/"
        "和声は推定名そのまま(N.C.・誤りは残る)/拍子・調は退避し得る/"
        "弱起の小節番号ずれ・声部分離なし",
        "# ---",
    ]


def to_llm_text(
    notes: list[QuantizedNote],
    chords: list[ChordSpan] | None,
    bpm: float,
    key_tonic_pc: int | None = None,
) -> str:
    """音符列とコード進行を LLM/人間可読の構造化テキストにする(F-099)。

    小節ごとに「Bar N | beats a-b」「chord: ...」「notes: ...」の3行ブロックを
    並べる。行頭ラベルが固定なので、LLM も単純パーサも `key: value` と `Bar N:`
    の走査で読める。詳しいフォーマット・限界はモジュール docstring を参照。

    Args:
        notes: 量子化済み音符列(拍単位 start_beats/dur_beats を使う)。
        chords: chord.py で推定した ChordSpan 列。None は「コード推定なし」として
            全小節を hold 扱いにする(空リストと同義に頑健化)。
        bpm: テンポ。小節割りは拍ベースで完結するため割り当てには使わず、
            ヘッダ表示(bpm=...)にのみ用いる(bpm を小節割りに使うと二重換算)。
        key_tonic_pc: 主音のピッチクラス(0-11)を外部指定して調ラベルの主音を
            上書きする任意引数。None なら estimate_key に委譲。範囲外は無視して
            推定へフォールバックする(不正入力を黙って誤表示しない)。

    Returns:
        ヘッダ(メタ情報＋欠落注記)＋小節ブロックから成る複数行文字列。
        空入力でもヘッダ＋最小1小節枠(rest/hold)を返し、例外は投げない。
    """
    safe_chords: list[ChordSpan] = list(chords) if chords else []

    bar_beats = _bar_beats(notes)
    end_beats = _end_beats(notes, safe_chords)
    n_measures = _num_measures(end_beats, bar_beats)
    key = estimate_key(notes)
    key_label = _resolve_key_label(key, key_tonic_pc)

    lines: list[str] = _header_lines(bpm, bar_beats, key_label, n_measures)
    for m in range(n_measures):
        m_start = float(m * bar_beats)
        m_end = float((m + 1) * bar_beats)
        lines.append(
            f"Bar {m + 1} | beats {_fmt_beat(m_start)}-{_fmt_beat(m_end)}"
        )
        lines.append(f"  chord: {_chord_cell(safe_chords, m_start, m_end)}")
        lines.append(
            f"  notes: {_notes_cell(notes, m_start, m_end, key)}"
        )
    return "\n".join(lines)


# 主音ピッチクラス → 音名(シャープ表記)。外部上書き用の最小マップ。
_PC_NAMES: tuple[str, ...] = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)


def _resolve_key_label(key: object, key_tonic_pc: int | None) -> str:
    """調ラベルを決める。key_tonic_pc(0-11)が妥当なら主音を上書きする。

    上書きは主音(綴り)のみで旋法(major/minor)は推定を尊重する。範囲外・None は
    推定ラベルへフォールバックする(不正値を黙って主音0扱いにしない)。
    """
    base = _key_label(key)
    if key_tonic_pc is None:
        return base
    if not (0 <= int(key_tonic_pc) <= 11):
        return base
    mode = getattr(key, "mode", None) or "major"
    return f"{_PC_NAMES[int(key_tonic_pc) % 12]} {mode}"
