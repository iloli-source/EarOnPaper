"""記譜層: 音符列＋コード進行 → ASCIIリードシート(F-034・Issue #71)。

リードシート(功能谱/lead sheet)は「メロディ音名＋コード記号」だけを表し、
ボイシング・内声・詳細リズムは意図的に省く記法(Wikipedia/MasterClass)。
本モジュールは既存のコード推定(chord.py の ChordSpan)と調整合スペリング
(spelling.py)を二次加工せずそのまま信頼し、モノスペース前提の2段テキスト
(上=コード行/下=メロディ行)を小節 `|` 区切りで組み立てる純関数を提供する。

慣例(Impro-Visor / JJazzLab): 小節は縦棒で区切り、コードは小節頭(第1拍)配置。
スパンが複数小節にまたがる場合は先頭小節にのみコード名を書き、後続小節は空欄
(=直前コードを継続=hold)にする。1小節に複数コードがあれば出現順に併記する。

正直な限界:
- 小節長は estimate_meter(score.py と同一)で推定するが、score.py が行う
  「先頭空小節のシフト(_drop_leading_silence)」は本モジュールでは行わない。
  弱起・冒頭休符がある入力では五線譜と小節番号がずれ得る(表示位置のみ・
  実タイミングは不変)。用途は素早い俯瞰であり厳密な小節整合は score.py に委ねる。
- 同時発音(和音)のメロディは先頭(最初に現れた)音のみを音名化する。声部分離や
  転回・内声は出さない(リードシートの定義に沿う)。
- コード名の綴り(#/♭・テンション)は ChordSpan.name をそのまま用いる。自前で
  音名生成しないため、メロディ音名も spelling.py 経由に統一し綴りソースを一本化する。
- 自動コード/メロディ推定自体が誤り得る(和声・旋律・リズムは相互依存)。誤りは
  N.C. や hold(空欄)としてそのまま表れる。過信しないこと。
"""

from __future__ import annotations

from collections.abc import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.spelling import estimate_key, spell_midi

# 空入力・退避時の小節あたり拍数(estimate_meter と同じ既定)。
BEATS_PER_MEASURE: int = 4
# 各小節列の固定幅(半角)。上下の列を縦に揃えるための ljust パディング幅。
COL_WIDTH: int = 10
# メロディ音のない小節に置くプレースホルダ(休符・音なし)。
REST_PLACEHOLDER: str = "-"
# 拍位置の丸め許容誤差(浮動小数の格子ゆらぎ吸収)。
_BEAT_EPS: float = 1e-6


def _bar_beats(notes: Sequence[QuantizedNote]) -> int:
    """小節あたりの拍数を決める(score.py と整合する estimate_meter を使用)。

    estimate_meter は list を要求するため list 化して委譲する。音符が空・
    証拠不足のときは 4/4 相当(BEATS_PER_MEASURE)へ退避する。
    """
    if not notes:
        return BEATS_PER_MEASURE
    # 遅延 import 回避のためトップで import 済み関数を使う。
    from earpipe.services.rhythm.meter import estimate_meter

    beats = estimate_meter(list(notes))
    return beats if beats > 0 else BEATS_PER_MEASURE


def _end_beats(
    notes: Sequence[QuantizedNote], chords: Sequence[ChordSpan]
) -> float:
    """総尺(拍)= メロディ終端とコード終端の大きい方。空列は 0.0(guard)。"""
    note_end = max(
        (float(n.start_beats) + float(n.dur_beats) for n in notes), default=0.0
    )
    chord_end = max((float(c.end_beats) for c in chords), default=0.0)
    return max(note_end, chord_end)


def _num_measures(end_beats: float, bar_beats: int) -> int:
    """総尺と小節長から総小節数を求める(最小 1 小節)。"""
    if end_beats <= _BEAT_EPS:
        return 1
    import math

    return max(1, math.ceil(end_beats / bar_beats))


def _chord_cell(
    chords: Sequence[ChordSpan], measure_start: float, measure_end: float
) -> str:
    """1小節ぶんのコード表記を作る。

    小節区間 [measure_start, measure_end) に start_beats が入るスパンを
    出現(開始拍)順に並べ、名前をスペース区切りで併記する。またぎスパンは
    開始小節でのみ名前が出る(この小節に start_beats が無ければ空欄=hold)。
    """
    names = [
        c.name
        for c in sorted(chords, key=lambda c: float(c.start_beats))
        if measure_start - _BEAT_EPS <= float(c.start_beats) < measure_end - _BEAT_EPS
    ]
    return " ".join(names)


def _melody_cell(
    notes: Sequence[QuantizedNote],
    measure_start: float,
    measure_end: float,
    key: object,
) -> str:
    """1小節ぶんのメロディ音名を作る。

    小節区間 [measure_start, measure_end) に start_beats が入る音符を開始拍順に
    並べ、調整合スペリング(spell_midi)で音名化する。同時発音(同一開始拍)は
    先頭音のみを採る。音符が無ければ休符プレースホルダを返す。
    """
    in_bar = [
        n
        for n in notes
        if measure_start - _BEAT_EPS <= float(n.start_beats) < measure_end - _BEAT_EPS
    ]
    if not in_bar:
        return REST_PLACEHOLDER

    seen_starts: set[float] = set()
    tokens: list[str] = []
    for n in sorted(in_bar, key=lambda n: float(n.start_beats)):
        # 同一開始拍(和音)は先頭音のみを音名化する。
        key_pos = round(float(n.start_beats), 6)
        if key_pos in seen_starts:
            continue
        seen_starts.add(key_pos)
        pitch = spell_midi(int(n.midi), key)  # type: ignore[arg-type]
        tokens.append(pitch.name)
    return " ".join(tokens) if tokens else REST_PLACEHOLDER


def _pad(cell: str) -> str:
    """列を固定幅に左詰めパディングする(モノスペース前提の縦揃え用)。"""
    return cell.ljust(COL_WIDTH)


def to_leadsheet(
    notes: list[QuantizedNote], chords: list[ChordSpan], bpm: float
) -> str:
    """音符列とコード進行から ASCII リードシート文字列を組み立てる(F-034)。

    小節ごとに「コード行(上)」「メロディ行(下)」を作り、小節を `|` で区切って
    2段のモノスペーステキストにする。コードは小節頭配置・またぎは hold(空欄)、
    メロディは調整合スペリングでの音名(和音は先頭音のみ)。

    Args:
        notes: 量子化済み音符列(拍単位 start_beats/dur_beats を使う)。
        chords: 既存 chord.py で推定した ChordSpan 列(name/start_beats/end_beats)。
        bpm: テンポ。小節割りは拍ベースで完結するため割り当てには使わず、
            ヘッダ表示(BPM=...)にのみ用いる(bpm を小節割りに使うと二重換算になる)。

    Returns:
        ヘッダ行 + コード行 + メロディ行から成る複数行文字列。コード行と
        メロディ行は同数の小節列(`|` 区切り)を持ち縦に揃う。

    Note:
        score.py と異なり先頭空小節のシフトは行わない(限界はモジュール docstring)。
    """
    bar_beats = _bar_beats(notes)
    end_beats = _end_beats(notes, chords)
    n_measures = _num_measures(end_beats, bar_beats)
    key = estimate_key(notes)

    chord_cells: list[str] = []
    melody_cells: list[str] = []
    for m in range(n_measures):
        m_start = float(m * bar_beats)
        m_end = float((m + 1) * bar_beats)
        chord_cells.append(_pad(_chord_cell(chords, m_start, m_end)))
        melody_cells.append(_pad(_melody_cell(notes, m_start, m_end, key)))

    header = f"BPM={bpm:g}  {bar_beats}/4"
    chord_line = "|" + "|".join(chord_cells) + "|"
    melody_line = "|" + "|".join(melody_cells) + "|"
    return f"{header}\n{chord_line}\n{melody_line}"
