"""F-086 調内制約クレンジング(調外音の最近傍調内音への「候補」提示)。

推定スケール(既定は自然長/短音階)に対し、調外(out-of-scale)の音を
最近傍の調内音へスナップする「候補」を提示する。既定は非破壊で、候補
リストを返すのみ。apply=True のときだけ高信頼候補を実際に適用する。

本モジュールは music21 非依存で、ピッチクラス算術のみで完結する
(重依存追加禁止の制約に適合し、テスト容易・軽量)。呼び出し側は
spelling.estimate_key が返す music21.key.Key の key.tonic.pitchClass を
key_tonic_pc として渡す想定(movable_do.py と同じIF)。

設計方針(先行研究 F-086-grok / F-086-codex の失敗例を反映):
- 「全音符を即スナップ」しない。調外音でも音楽的に正しい場合(転調・借用和音・
  セカンダリードミナント・クロマチック経過音・ブルーノート・装飾音)が多いため、
  自動一括補正は表現を壊す(codex(2)(3)、grok 2-8/2-9/2-10)。
- したがって既定は「根拠付き候補リスト(非破壊)」。apply=True でも、隣接音へ
  半音進行する短い経過/装飾音は既定で保持(keep)し、破壊しない。
- 各候補は元音(original_midi)・確信度(confidence)・理由(reason)・リスクラベル
  (risk)を保持する(codex(4) の human-in-the-loop 前提)。
- 最近傍が等距離のとき、Ableton "Fit to Scale" 準拠で低い側へ寄せる
  (codex(1))。ただし方向は候補に明示し、上下両方の代替も candidates に残す。

限界(正直な記録・過大主張しない):
- 全体1調・単一スケール仮定。転調・区間調・局所調は見ない(spelling.py と同じ
  制約)。推定キーが誤っていれば候補も連鎖的に誤る(codex(3) の cascade)。
  そのため誤りが目立ちにくいよう、確信度と元音を必ず候補に残す。
- 経過音/装飾音の保護は「短い + 隣接調内音へ半音進行」という粗いヒューリスティック
  であり、真の声部進行解析ではない。セカンダリードミナントの導音(V/V の第3音等)
  を機能的に同定はできない。強拍・長音の孤立調外音のみ高信頼として扱う。
- 微分音・非12-TET・非西洋音階は対象外(12-TETダイアトニック前提。grok 2-15)。
- mode は "major"(自然長音階)/"minor"(自然短音階)のみ。harmonic/melodic
  minor やモードは将来課題(調外だが正しい導音 G# 等を誤検出しうる。codex(3))。
"""

from __future__ import annotations

from dataclasses import replace
from math import isnan
from typing import Literal

from earpipe.contracts import QuantizedNote

# 半音の周期(オクターブ)。
_OCTAVE = 12

# スケール別の調内ピッチクラス(主音を0とした相対度数の集合)。
# major=自然長音階(全全半全全全半)、minor=自然短音階(全半全全半全全)。
_SCALE_DEGREES: dict[str, frozenset[int]] = {
    "major": frozenset({0, 2, 4, 5, 7, 9, 11}),
    "minor": frozenset({0, 2, 3, 5, 7, 8, 10}),
}

Mode = Literal["major", "minor"]

# --- 経過/装飾音の保護しきい値(先行研究の失敗例対策) ---
# 拍長がこの値以下の調外音は「短い」とみなし、隣接調内音へ半音進行するなら
# 経過/装飾音候補として保持(keep)を既定にする(codex(2) クロマチック経過音)。
_SHORT_DUR_BEATS = 0.5     # 8分音符以下を短音とみなす
# 強拍判定: 拍位置がこの許容誤差で整数拍(1拍目基準)に乗るなら強拍とみなす。
_STRONG_BEAT_EPS = 1e-6

# リスクラベル(codex(4) の色分けに対応する語彙)。
RISK_LIKELY_ERROR = "likely_error"     # 誤採譜らしい調外音(赤): 高信頼で補正候補
RISK_PASSING = "passing_or_ornament"   # 経過/装飾候補(黄): 既定保持
RISK_WEAK = "low_confidence"           # 低確信/弱拍等(黄〜紫): 既定保持


def _snap_pitch_class(rel_pc: int, degrees: frozenset[int]) -> tuple[int, int]:
    """相対ピッチクラス rel_pc(0-11) を最近傍の調内度数へ寄せる。

    戻り値: (最近傍の相対度数, 符号付き移動半音数)。移動は最短距離で、
    等距離(±1 と ∓1 が同点、例: 半音上と半音下)のときは低い側(負方向)を
    選ぶ(Ableton "Fit to Scale" 準拠・codex(1))。rel_pc が既に調内なら
    (rel_pc, 0) を返す。
    """
    if rel_pc in degrees:
        return rel_pc, 0
    # 距離1,2,... と順に探索し、同距離で上下が両方調内なら下(負)を優先する。
    for dist in range(1, _OCTAVE):
        down = (rel_pc - dist) % _OCTAVE
        up = (rel_pc + dist) % _OCTAVE
        if down in degrees:
            return down, -dist
        if up in degrees:
            return up, dist
    return rel_pc, 0  # 論理上到達しない(調内度数は必ず存在する)


def _alt_snaps(rel_pc: int, degrees: frozenset[int]) -> list[int]:
    """rel_pc の上下それぞれ最近傍の調内度数(代替候補)を返す(重複除去)。

    codex(4): 一括適用前に up/down/nearest/keep を見せるため、最近傍以外の
    方向候補も残す。戻り値は相対度数(0-11)の list(近い順)。
    """
    found: list[int] = []
    for dist in range(1, _OCTAVE):
        down = (rel_pc - dist) % _OCTAVE
        if down in degrees and down not in found:
            found.append(down)
        up = (rel_pc + dist) % _OCTAVE
        if up in degrees and up not in found:
            found.append(up)
        if len(found) >= 2:
            break
    return found


def _is_strong_beat(start_beats: float) -> bool:
    """開始拍が(1拍単位の)整数拍に乗るなら強拍とみなす粗い判定。

    量子化後の start_beats は四分音符=1.0。拍頭(整数拍)を強拍の代理とする。
    真の拍子・小節境界は見ない(限界)。
    """
    frac = start_beats - round(start_beats)
    return abs(frac) <= _STRONG_BEAT_EPS


def _classify_risk(
    note: QuantizedNote,
    move: int,
    prev_snapped_in_scale: bool,
    next_in_scale_toward: bool,
) -> str:
    """調外音のリスク種別を決める(補正の安全側=保持を優先)。

    高信頼(likely_error)にするのは「強拍 かつ 長め かつ 半音の経過らしくない」
    調外音のみ。短音で隣接調内音へ半音進行する音は経過/装飾候補として保持。
    それ以外(弱拍・確信度低)は low_confidence として保持を既定にする。
    """
    is_short = note.dur_beats <= _SHORT_DUR_BEATS
    is_semitone_move = abs(move) == 1
    # 経過/装飾: 短い + 半音移動で調内音へ吸着 + 前後が調内(隣接ステップ運動)
    if is_short and is_semitone_move and (prev_snapped_in_scale or next_in_scale_toward):
        return RISK_PASSING
    if _is_strong_beat(note.start_beats) and not is_short:
        return RISK_LIKELY_ERROR
    return RISK_WEAK


def cleanse_to_scale(
    notes: list[QuantizedNote],
    key_tonic_pc: int,
    mode: str = "major",
    apply: bool = False,
) -> tuple[list[QuantizedNote], list[dict]]:
    """調外音を最近傍の調内音へスナップする「候補」を提示する(既定は非破壊)。

    引数:
        notes: 量子化済み音符列。旋律順は入力 list の順序を信頼する
            (onset_sec は NaN 既定でソート根拠に使えない。contracts.py 参照)。
        key_tonic_pc: 調の主音ピッチクラス(0-11)。%12 で正規化して用いる。
            spelling.estimate_key(...).tonic.pitchClass を渡す想定。
        mode: "major"(自然長音階)または "minor"(自然短音階)。
        apply: False(既定)は非破壊で notes をそのまま返し候補のみ提示する。
            True のときは高信頼候補(risk=likely_error)だけを実際に適用し、
            経過/装飾・低確信候補(passing/low_confidence)は保持する。

    戻り値:
        (out_notes, candidates) のタプル。
        - out_notes: apply=False なら入力と同一内容(非破壊)。apply=True なら
          高信頼候補を snap 済みの新しい list(元 list は変更しない=不変)。
        - candidates: 調外音ごとの候補 dict の list。各 dict のキー:
            index          入力 notes 内の位置
            original_midi  元の MIDI ノート番号
            snapped_midi   最近傍調内音へ寄せた MIDI(適用候補)
            move_semitones 符号付き移動半音数(負=下行)
            alt_midis      代替スナップ先(上下最近傍)の MIDI list
            confidence     元音の確信度(0-1、そのまま保持)
            risk           リスクラベル(likely_error/passing_or_ornament/low_confidence)
            reason         判断理由の日本語文字列
            applied        apply=True で実際に適用したか(bool)

    例外:
        ValueError: mode が "major"/"minor" 以外のとき(静かに失敗しない)。

    設計の要点(過大主張しない): 調外=誤りとは決めつけない。既定は候補提示のみで、
    apply=True でも半音の経過/装飾らしい音は保持する。推定キーが誤れば候補も
    誤るため、元音と確信度を必ず候補に残す(モジュール docstring の限界参照)。
    """
    if mode not in _SCALE_DEGREES:
        raise ValueError(
            f"mode は 'major' か 'minor' のいずれか。受領値: {mode!r}"
        )
    tonic = int(key_tonic_pc) % _OCTAVE
    degrees = _SCALE_DEGREES[mode]

    # 各音の調内フラグ(前後文脈判定に使う)を先に算出する。
    in_scale = [
        (int(n.midi) % _OCTAVE - tonic) % _OCTAVE in degrees for n in notes
    ]

    candidates: list[dict] = []
    # 適用結果は不変則を守り新規 list を構築(元 notes は破壊しない)。
    out_notes: list[QuantizedNote] = list(notes)

    for i, note in enumerate(notes):
        rel_pc = (int(note.midi) % _OCTAVE - tonic) % _OCTAVE
        if rel_pc in degrees:
            continue  # 調内音は候補にしない

        snapped_rel, move = _snap_pitch_class(rel_pc, degrees)
        snapped_midi = int(note.midi) + move
        alt_rels = _alt_snaps(rel_pc, degrees)
        alt_midis = [int(note.midi) + _signed_step(rel_pc, a) for a in alt_rels]

        prev_in_scale = in_scale[i - 1] if i > 0 else False
        next_in_scale = in_scale[i + 1] if i + 1 < len(notes) else False
        risk = _classify_risk(note, move, prev_in_scale, next_in_scale)

        applied = apply and risk == RISK_LIKELY_ERROR
        if applied:
            out_notes[i] = replace(out_notes[i], midi=snapped_midi)

        candidates.append(
            {
                "index": i,
                "original_midi": int(note.midi),
                "snapped_midi": snapped_midi,
                "move_semitones": move,
                "alt_midis": alt_midis,
                "confidence": float(note.confidence)
                if not isnan(float(note.confidence))
                else 0.0,
                "risk": risk,
                "reason": _reason_text(risk, move),
                "applied": applied,
            }
        )

    return out_notes, candidates


def _signed_step(rel_pc: int, target_rel: int) -> int:
    """rel_pc から調内度数 target_rel への最短の符号付き半音差を返す。

    代替候補の MIDI を元音基準で復元するため。±6 の同距離は下(負)を優先する。
    """
    diff = (target_rel - rel_pc) % _OCTAVE
    return diff - _OCTAVE if diff > _OCTAVE // 2 else diff


def _reason_text(risk: str, move: int) -> str:
    """リスクラベルと移動量から、監査ログ向けの日本語理由文を組み立てる。"""
    direction = "下" if move < 0 else "上"
    amount = abs(move)
    if risk == RISK_LIKELY_ERROR:
        return f"強拍の長い調外音。最近傍調内音へ半音{amount}個{direction}行で補正候補(誤採譜らしい)"
    if risk == RISK_PASSING:
        return f"短い半音の経過/装飾らしく既定は保持。適用時は{direction}へ半音{amount}個スナップ"
    return f"弱拍または低確信の調外音。既定は保持。適用時は{direction}へ半音{amount}個スナップ"
