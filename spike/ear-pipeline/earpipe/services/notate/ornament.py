"""F-082 装飾音・演奏ノイズの記譜解釈(微小音符の装飾候補分類・Issue #91)。

拍長が閾値(min_main_beats)未満の微小音符を、隣接する「主音」への装飾音
(grace / acciaccatura 候補)として分類し、候補リストで返す。既定は非破壊
(注記のみ)で、入力 notes をそのまま返す。

設計方針(先行研究 F-082-grok の失敗例を保守的に反映):
- 「聞こえたピッチ=書くべき音符」の一本道を採らない(grok 10章の一行結論)。
  微小音符は本音符化する前に「装飾候補 / 判定保留」として仕分け、既定は
  非破壊で人間確認に委ねる(grok BP5「自動出力は常に下書き」)。
- 装飾音は「音符の縮小版」ではなく主音へ密着する「解釈オブジェクト」として扱う
  (grok BP2 / F3・F4 のグレース vs スペーシング衝突)。よって各候補は必ず
  「どの主音に付くか(main_index)」と付く向き(before/after)を持つ。
- 32分音符の羅列・偽音符化を避ける(grok F8「量子化が装飾を潰す」/ F10・F16
  「RipX の usual noise = 弦こすれ・息音の偽音符」)。極端に短く・低確信で・
  隣接主音とピッチが近い微小音符ほど「装飾らしい」とし、孤立して長め・高確信の
  微小音符は本音符側(judgement=keep_as_note)に倒す。
- trill 開始音の単一グローバルルール等、時代・楽器依存の再生規則は実装しない
  (grok F1・F2・避けるべき設計)。本モジュールは「本音符か装飾かの前段仕分け」に
  限定し、装飾の演奏解釈(前打/長前打/turn 展開)には踏み込まない。

限界(正直な記録・過大主張しない):
- 弦こすれ・フィンガーノイズ・息音そのものを音響的に同定はしない。それらは F-108
  の SoundEvent 分類(is_notable=False)で本来は前段除外される想定であり、本
  モジュールはあくまで「短い音符イベント」だけを対象にした記譜側の保守判定。
  すなわち非楽音の識別は上流(ear/SoundEvent)責務で、ここは二次防波堤。
- appoggiatura(長前打音)と acciaccatura(短前打音)の楽理的区別、装飾の
  臨時記号適用範囲(grok F7)、移調楽器の実音ずれ(grok F2)は扱わない。
- 主音の対応付けは「時間的に隣接する非微小音符のうち近い側」という粗い規則で、
  真の声部進行・フレーズ解析ではない。入力 list の順序を旋律順として信頼する
  (onset_sec は NaN 既定でソート根拠に使えない。contracts.py 参照)。
- min_main_beats 未満が全て装飾とは限らない(速いパッセージの正規音符)。ゆえに
  既定は非破壊、判定は confidence/risk 付きで返し、確定は呼び出し側に委ねる。
"""

from __future__ import annotations

from math import isnan

from earpipe.contracts import QuantizedNote

# --- 分類しきい値(先行研究の失敗例対策) ---
# 微小音符と隣接主音のピッチ差(半音)がこの値以下なら「主音への装飾らしい」。
# 装飾音は主音の近傍を彩る用途が多く、遠く跳躍する微小音は装飾より本音符寄り。
_ORNAMENT_MAX_INTERVAL = 4  # 長3度まで(これを超える跳躍は装飾らしさが下がる)
# acciaccatura(短前打音)とみなす拍長の上限。これ以下は「極短」で最も装飾らしい。
_ACCIACCATURA_MAX_BEATS = 0.125  # 32分音符以下
# 装飾候補として採用する確信度の下限に満たない場合、判定保留(indeterminate)へ倒す。
# grok F10/F16: 低確信の微小イベントは偽音符(ノイズ)の可能性が高く保守的に扱う。
_LOW_CONFIDENCE = 0.5

# 判定ラベル(呼び出し側の色分け・確定 UI 向け語彙)。
JUDGE_GRACE = "grace"            # 隣接主音への装飾候補(既定は非破壊で注記のみ)
JUDGE_INDETERMINATE = "indeterminate"  # 装飾ともノイズとも決めきれない(要人間確認)
JUDGE_KEEP_AS_NOTE = "keep_as_note"    # 微小だが本音符として残す(隣接主音が無い等)

# 装飾の種別(前打の長短。楽理展開はしない粗い区別)。
KIND_ACCIACCATURA = "acciaccatura"  # 短前打音候補(極短)
KIND_GRACE = "grace"                # 一般の装飾候補(短いが極短ではない)


def _is_tiny(note: QuantizedNote, min_main_beats: float) -> bool:
    """音符が「微小(本音符の閾値未満)」かを判定する。"""
    return float(note.dur_beats) < min_main_beats


def _safe_confidence(note: QuantizedNote) -> float:
    """confidence を 0-1 の float に正規化する(NaN は 0.0 とみなす)。"""
    conf = float(note.confidence)
    return 0.0 if isnan(conf) else conf


def _nearest_main_index(
    tiny_index: int,
    tiny_flags: list[bool],
    notes: list[QuantizedNote],
) -> tuple[int, str] | None:
    """微小音符が付くべき隣接主音の index と向き(before/after)を返す。

    向きの意味は「装飾音が主音の直前(before)か直後(after)に置かれるか」。
    直後の非微小音符(after)を優先し、無ければ直前(before)を採る。装飾音は
    後続主音への前打が一般的だが、末尾装飾のために直前も許す。隣接主音が
    どちらにも無ければ None(=keep_as_note 側へ)。
    """
    for j in range(tiny_index + 1, len(notes)):
        if not tiny_flags[j]:
            return j, "before"  # 後続の主音に「前打」で付く
    for j in range(tiny_index - 1, -1, -1):
        if not tiny_flags[j]:
            return j, "after"   # 先行主音に「後打」で付く
    return None


def _interval_semitones(a: QuantizedNote, b: QuantizedNote) -> int:
    """2音の絶対ピッチ差(半音)。装飾らしさ(近傍性)判定に用いる。"""
    return abs(int(a.midi) - int(b.midi))


def _judge(
    tiny: QuantizedNote,
    main: QuantizedNote | None,
    direction: str | None,
) -> tuple[str, str, str]:
    """微小音符の判定ラベル・装飾種別・日本語理由を決める(保守側=非音符化しない)。

    戻り値: (judgement, kind, reason)。judgement が JUDGE_GRACE のときのみ
    kind は KIND_* を持ち、それ以外は kind="" とする。
    """
    conf = _safe_confidence(tiny)
    # 隣接主音が無い微小音符は装飾の付け先が無い。孤立音として本音符に倒す
    # (無理に装飾化すると宙に浮いた grace になり grok F14 の再生ハック的破綻)。
    if main is None or direction is None:
        return JUDGE_KEEP_AS_NOTE, "", "隣接する主音が無く装飾の付け先が無いため本音符として保持"

    interval = _interval_semitones(tiny, main)
    # 低確信 or 主音から遠い跳躍は、装飾と断定せず判定保留にする
    # (grok F10/F16 の偽音符=ノイズ混入を装飾に化けさせない安全弁)。
    if conf < _LOW_CONFIDENCE:
        return (
            JUDGE_INDETERMINATE,
            "",
            f"確信度{conf:.2f}が低く装飾ともノイズとも断定できないため判定保留(要人間確認)",
        )
    if interval > _ORNAMENT_MAX_INTERVAL:
        return (
            JUDGE_INDETERMINATE,
            "",
            f"主音との音程{interval}半音が広く装飾より跳躍音符の可能性があるため判定保留",
        )

    # ここまで来れば「主音に密着する短い装飾候補」。極短なら acciaccatura。
    dur = float(tiny.dur_beats)
    if dur <= _ACCIACCATURA_MAX_BEATS:
        kind = KIND_ACCIACCATURA
        kind_label = "短前打音(acciaccatura)"
    else:
        kind = KIND_GRACE
        kind_label = "装飾音(grace)"
    side = "前" if direction == "before" else "後"
    return (
        JUDGE_GRACE,
        kind,
        f"主音の直{side}に密着する{kind_label}候補(音程{interval}半音・拍長{dur:g})。既定は非破壊で注記のみ",
    )


def interpret_ornaments(
    notes: list[QuantizedNote],
    min_main_beats: float = 0.25,
) -> tuple[list[QuantizedNote], list[dict]]:
    """微小音符を隣接主音への装飾候補として分類する(既定は非破壊=注記のみ)。

    引数:
        notes: 量子化済み音符列。旋律順は入力 list の順序を信頼する
            (onset_sec は NaN 既定でソート根拠に使えない。contracts.py 参照)。
        min_main_beats: 本音符とみなす拍長の下限(四分音符=1.0)。既定 0.25
            (16分音符)。これ未満の音符を「微小」とし装飾候補の検討対象にする。

    戻り値:
        (out_notes, ornaments) のタプル。
        - out_notes: 既定は非破壊のため入力と同一内容の新規 list(元 list は
          変更しない=不変則)。本モジュールは装飾を削除・変換しない。
        - ornaments: 微小音符ごとの候補 dict の list。各 dict のキー:
            index          入力 notes 内の微小音符の位置
            midi           微小音符の MIDI ノート番号
            dur_beats      微小音符の拍長
            confidence     微小音符の確信度(0-1、NaN は 0.0)
            judgement      判定(grace / indeterminate / keep_as_note)
            kind           装飾種別(acciaccatura / grace。grace 判定時のみ非空)
            main_index     付く主音の index(隣接主音が無ければ None)
            direction      主音への向き(before=前打 / after=後打。無ければ None)
            interval_semitones 主音との絶対音程(半音。主音が無ければ None)
            reason         判断理由の日本語文字列

    設計の要点(過大主張しない): min_main_beats 未満=装飾とは決めつけない。
    既定は非破壊で、装飾らしさ(隣接主音への密着・確信度)を判定として返し、
    確定は呼び出し側に委ねる(モジュール docstring の限界・grok BP5 参照)。
    非楽音(弦こすれ・息音)の識別は上流 SoundEvent 責務で、本モジュールは
    「短い音符イベント」の記譜側二次仕分けに限定する。
    """
    if min_main_beats <= 0:
        raise ValueError(
            f"min_main_beats は正の拍長。受領値: {min_main_beats!r}"
        )

    tiny_flags = [_is_tiny(n, min_main_beats) for n in notes]

    ornaments: list[dict] = []
    for i, note in enumerate(notes):
        if not tiny_flags[i]:
            continue  # 本音符(閾値以上)は装飾候補にしない

        nearest = _nearest_main_index(i, tiny_flags, notes)
        if nearest is None:
            main_index: int | None = None
            direction: str | None = None
            main_note: QuantizedNote | None = None
            interval: int | None = None
        else:
            main_index, direction = nearest
            main_note = notes[main_index]
            interval = _interval_semitones(note, main_note)

        judgement, kind, reason = _judge(note, main_note, direction)

        ornaments.append(
            {
                "index": i,
                "midi": int(note.midi),
                "dur_beats": float(note.dur_beats),
                "confidence": _safe_confidence(note),
                "judgement": judgement,
                "kind": kind,
                "main_index": main_index,
                "direction": direction,
                "interval_semitones": interval,
                "reason": reason,
            }
        )

    # 非破壊: 元 list を変更せず同一内容の新規 list を返す(不変則)。
    out_notes: list[QuantizedNote] = list(notes)
    return out_notes, ornaments
