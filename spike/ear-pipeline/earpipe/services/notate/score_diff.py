"""F-094 譜面差分ハイライト(2つの音符列のピッチ・リズム差分分類)。

2つの QuantizedNote 列 a/b(例: 正解譜 vs 自動採譜結果、または版違い)を
開始拍近傍でマッチングし、各対応を match / pitch_diff / timing_diff /
only_in_a / only_in_b に分類した dict のリストを返す。

先行研究(F-094-grok / F-094-codex)の失敗例を反映した設計判断:

- **生XML/生MIDIのtext diffはしない**(grok F1, codex §4)。人間が欲しいのは
  musical semantic diff(pitch/onset/duration)であって属性順・レイアウト・
  エンコーディング差分ではない。本モジュールは既に正規化済みの QuantizedNote
  (拍単位の start_beats/dur_beats)のみを入力に取り、シリアライゼーション層を
  一切見ない。

- **対応付けの失敗を「譜面差分」と誤表示しない**(codex エグゼクティブサマリー)。
  単純な pitch+onset 近接では対応が決まらない。特に「同音連打の対応入れ替わり」
  (codex §2)を避けるため、候補ペアを (開始拍差, ピッチ差, 入力順) で安定に
  ソートして貪欲に確定し、一度使った音符は再利用しない(bipartite 近似・
  mir_eval と同様に1対1)。split/merge は only_in_* に落ちることを notes 相当の
  docstring で明示する(codex §2: split/merge が insertion/deletion に落ちる限界)。

- **境界誤差(onset ズレ)を rhythm difference にしない**(codex §1.6, Devaney
  77-118ms)。マッチング窓 onset_tol_beats(既定0.25拍=16分)以内は「対応する
  音符」とみなす。窓内でピッチが同じでも開始拍が僅かにずれる程度なら match、
  はっきりずれる(タイミング窓を実質使い切る/音価が食い違う)場合のみ
  timing_diff とする二段判定で、微小ズレの誤警告を抑える。

- **12平均律・整数MIDI前提の限界を隠さない**(grok F6, codex §2)。QuantizedNote は
  整数MIDIのみを持ち綴り(enharmonic)を保持しない(contracts.py)。したがって
  本 diff は G#/Ab を区別できず octave 違いは半音12の pitch_diff として出る。
  これは原理的限界であり、綴りレベル差分は spelling.py 後段の責務。

- **休符はイベントではなく「音符の不在」として扱う**。QuantizedNote 列に休符
  イベントは含まれないため、休符差は only_in_* / timing_diff に自然に現れる。
"""

from __future__ import annotations

from dataclasses import dataclass

from earpipe.contracts import QuantizedNote

# 開始拍マッチング窓の既定(拍)。0.25拍=四分音符の1/4=16分音符相当。
# codex §1.6 の onset 境界誤差(77-118ms)を rhythm diff に化けさせない緩衝。
DEFAULT_ONSET_TOL_BEATS = 0.25

# 音価(dur_beats)がこの割合を超えて食い違えば timing_diff とみなす下限比。
# 例: 0.5 なら「音価が1.5倍以上/0.67倍以下」で長さ差と判定。微小な量子化揺れを
# timing_diff に化けさせないための閾値(codex: quantization 差の過剰罰回避)。
DURATION_REL_TOL = 0.5

# 開始拍ズレをタイミング差と呼ぶ下限(窓に対する割合)。窓の半分未満のズレは
# 「境界誤差」とみなし match 側に倒す(Devaney 由来の二段判定)。
TIMING_SHIFT_FRACTION = 0.5

DiffType = str  # "match" | "pitch_diff" | "timing_diff" | "only_in_a" | "only_in_b"


@dataclass(frozen=True)
class _Candidate:
    """マッチング候補ペア(内部用・安定ソートのためのキーを保持)。"""

    onset_gap: float   # |a.start_beats - b.start_beats|
    pitch_gap: int     # |a.midi - b.midi|
    order: int         # 入力順(同点タイブレーク・同音連打の入れ替わり防止)
    ia: int            # a 側インデックス
    ib: int            # b 側インデックス


def _validate(notes: list[QuantizedNote], name: str) -> None:
    """入力境界の検証(信頼しない・早期失敗・common/coding-style)。"""
    if not isinstance(notes, list):
        raise TypeError(f"{name} は list[QuantizedNote] であること")
    for i, n in enumerate(notes):
        if not isinstance(n, QuantizedNote):
            raise TypeError(f"{name}[{i}] は QuantizedNote であること")


def _duration_differs(dur_a: float, dur_b: float) -> bool:
    """音価が有意に食い違うか(相対許容 DURATION_REL_TOL)。"""
    longer = max(dur_a, dur_b)
    shorter = min(dur_a, dur_b)
    if longer <= 0.0:
        # 両方0(またはゼロ長)なら差なしとみなす。片方だけ0は下で差ありに倒す。
        return shorter < 0.0
    if shorter <= 0.0:
        return True
    return (longer - shorter) / longer > DURATION_REL_TOL


def _build_candidates(
    a: list[QuantizedNote],
    b: list[QuantizedNote],
    onset_tol_beats: float,
) -> list[_Candidate]:
    """窓内の全候補ペアを列挙し、安定な確定順にソートして返す。

    ソートキー: (開始拍差, ピッチ差, 入力順)。開始拍が最も近いものを最優先し、
    同点なら音高が近いもの、さらに同点なら入力順の早いものを選ぶ。これにより
    同音連打(同一 pitch の隣接音)でも対応が隣に滑らない(codex §2)。
    """
    candidates: list[_Candidate] = []
    order = 0
    for ia, na in enumerate(a):
        for ib, nb in enumerate(b):
            gap = abs(na.start_beats - nb.start_beats)
            if gap <= onset_tol_beats:
                candidates.append(
                    _Candidate(
                        onset_gap=gap,
                        pitch_gap=abs(na.midi - nb.midi),
                        order=order,
                        ia=ia,
                        ib=ib,
                    )
                )
                order += 1
    candidates.sort(key=lambda c: (c.onset_gap, c.pitch_gap, c.order))
    return candidates


def _classify_match(
    na: QuantizedNote,
    nb: QuantizedNote,
    onset_tol_beats: float,
) -> DiffType:
    """確定した1対1ペアを match / pitch_diff / timing_diff に分類する。

    優先順位: ピッチが違えば pitch_diff(音高差は最重要)。ピッチが同じで
    開始拍のはっきりしたズレ or 音価の食い違いがあれば timing_diff。どちらも
    僅かなら match。境界誤差(窓の半分未満のズレ)は match に倒す(codex §1.6)。
    """
    if na.midi != nb.midi:
        return "pitch_diff"
    onset_gap = abs(na.start_beats - nb.start_beats)
    shift_threshold = onset_tol_beats * TIMING_SHIFT_FRACTION
    if onset_gap > shift_threshold or _duration_differs(na.dur_beats, nb.dur_beats):
        return "timing_diff"
    return "match"


def diff_notes(
    a: list[QuantizedNote],
    b: list[QuantizedNote],
    onset_tol_beats: float = DEFAULT_ONSET_TOL_BEATS,
) -> list[dict]:
    """2つの音符列の意味論的差分を分類した dict のリストを返す。

    Args:
        a: 基準側の音符列(例: 正解譜)。
        b: 比較側の音符列(例: 自動採譜結果)。
        onset_tol_beats: 開始拍マッチング窓(拍・既定0.25=16分相当)。この窓内の
            a/b 音符を「対応しうる」とみなす。負値は不可。

    Returns:
        各要素が下記キーを持つ dict のリスト。start_beats の昇順、同拍は
        a 側→b 側の順で安定に並ぶ。
        - type: "match" | "pitch_diff" | "timing_diff" | "only_in_a" | "only_in_b"
        - a_index / b_index: 元配列のインデックス(該当なしは None)
        - a_midi / b_midi: MIDIノート番号(該当なしは None)
        - a_start_beats / b_start_beats: 開始拍(該当なしは None)
        - onset_shift_beats: b_start - a_start(両側ある場合のみ、なければ None)
        - pitch_shift_semitones: b_midi - a_midi(両側ある場合のみ、なければ None)

    分類規則(先行研究の失敗回避を反映):
        1. 開始拍が onset_tol_beats 以内の a/b 音符を候補とし、(開始拍差, ピッチ差,
           入力順)の安定順に貪欲に1対1確定する(同音連打の入れ替わり防止)。
        2. 確定ペアは _classify_match で match / pitch_diff / timing_diff に分類。
           ピッチ差が最優先、次に開始拍の有意ズレ/音価差で timing_diff。
        3. 未対応の a は only_in_a、未対応の b は only_in_b。
           注意: 1音→2音の split/merge は分割の一方が only_in_* に落ちる(原理的
           限界・codex §2)。整数MIDIのみのため enharmonic(G#/Ab)は区別できず
           octave 違いは半音12の pitch_diff として現れる。

    Raises:
        TypeError: a/b が list[QuantizedNote] でない場合。
        ValueError: onset_tol_beats が負の場合。
    """
    _validate(a, "a")
    _validate(b, "b")
    if onset_tol_beats < 0.0:
        raise ValueError("onset_tol_beats は非負であること")

    candidates = _build_candidates(a, b, onset_tol_beats)

    used_a: set[int] = set()
    used_b: set[int] = set()
    pairs: list[tuple[int, int, DiffType]] = []
    for c in candidates:
        if c.ia in used_a or c.ib in used_b:
            continue
        used_a.add(c.ia)
        used_b.add(c.ib)
        diff_type = _classify_match(a[c.ia], b[c.ib], onset_tol_beats)
        pairs.append((c.ia, c.ib, diff_type))

    results: list[dict] = []
    for ia, ib, diff_type in pairs:
        na, nb = a[ia], b[ib]
        results.append(
            {
                "type": diff_type,
                "a_index": ia,
                "b_index": ib,
                "a_midi": na.midi,
                "b_midi": nb.midi,
                "a_start_beats": na.start_beats,
                "b_start_beats": nb.start_beats,
                "onset_shift_beats": nb.start_beats - na.start_beats,
                "pitch_shift_semitones": nb.midi - na.midi,
            }
        )

    for ia, na in enumerate(a):
        if ia not in used_a:
            results.append(_only_entry("only_in_a", ia=ia, note=na))
    for ib, nb in enumerate(b):
        if ib not in used_b:
            results.append(_only_entry("only_in_b", ib=ib, note=nb))

    results.sort(key=_sort_key)
    return results


def _only_entry(
    diff_type: DiffType,
    note: QuantizedNote,
    ia: int | None = None,
    ib: int | None = None,
) -> dict:
    """片側のみに存在する音符の dict を組み立てる。"""
    is_a = ia is not None
    return {
        "type": diff_type,
        "a_index": ia,
        "b_index": ib,
        "a_midi": note.midi if is_a else None,
        "b_midi": note.midi if not is_a else None,
        "a_start_beats": note.start_beats if is_a else None,
        "b_start_beats": note.start_beats if not is_a else None,
        "onset_shift_beats": None,
        "pitch_shift_semitones": None,
    }


def _sort_key(entry: dict) -> tuple[float, int]:
    """出力の安定ソートキー: 開始拍(a優先→b)昇順, 同拍は a 側を先に。"""
    start = entry["a_start_beats"]
    if start is None:
        start = entry["b_start_beats"]
    # a 側情報を持つ行(match/pitch/timing/only_in_a)を同拍で先に置く。
    a_first = 0 if entry["a_index"] is not None else 1
    return (float(start), a_first)
