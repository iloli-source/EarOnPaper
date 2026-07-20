"""記譜前MIDIクリーンアップ工程(F-084・Issue #78)。

量子化済み音符列(QuantizedNote)を記譜に渡す前に、極短ノート・重複・微小音価を
「保守的に・可逆に」整理する。目的は「読める楽譜のための最終仕上げ」であって、
本物の音を削ることではない。

先行研究(docs/research/upcoming/F-084-{grok,codex}.md)の教訓を反映:

- 過剰削除(false-positive pruning)が最大の失敗類型(codex §2)。前打音・装飾音・
  速い経過音・ゴーストノートは「短い・弱い・格子外」の単独条件で消えやすい。
  → 本モジュールは削除に必ず複数根拠を要求する(単独条件では消さない)。
- 「短いから削除」の固定ミリ秒ルールは危険(codex §2.1)。ここでは拍相対の
  min_dur_beats を使い、かつ低信頼を併せて要求する。
- 削除は非破壊・可逆であるべき(codex §4-1/§4-9, grok BP-3)。削除した音符は
  すべて理由付きで report["removed"] に元インスタンスごと保持し、呼び出し側が
  復元・レビューできる(「消した音を可視化」)。
- 完全重複(exact duplicate)のみ音楽的損失なく統合できる(quantize.py の dedup と
  同じ格子キー方針: (start_beats, midi))。

限界(正直な記録):
- 本工程は倍音誤検出・奏法(ハンマリング等)の意図までは判定できない。倍音疑いの
  除去は「同拍の強い持続音に完全内包される・極短・低信頼」の三条件が揃った
  ときのみ行い、それ以外は保持する(取りこぼしより取り過ぎを避ける)。
- 声部進行・和声・楽器制約を用いた高度な除去(codex §1.5 の統合推定)は
  スコープ外。ここは記譜直前の軽量な最終整理に留める。
"""

from dataclasses import dataclass

from earpipe.contracts import QuantizedNote

# --- 保守的な既定しきい値(拍単位・BPM非依存) ---
MIN_DUR_BEATS = 0.125          # 32分音符。これ未満を「微小音価」の候補とする
CONF_FLOOR = 0.35              # これ未満を「低信頼」とみなす(幽霊除けの下限)
HARMONIC_OCTAVE_SEMITONES = 12  # ちょうど1オクターブ上のみを倍音誤検出の対象とする(保守的)


@dataclass(frozen=True)
class RemovedNote:
    """削除された音符の可逆記録(非破壊クリーンアップの復元情報)。

    note は削除前の元インスタンスそのもの。reason で削除根拠を、detail で
    人間可読な補足(併合先など)を保持する。呼び出し側はこれを使って復元・
    レビューUI表示ができる。
    """

    note: QuantizedNote
    reason: str      # "exact_duplicate" | "micro_low_conf" | "subsumed_harmonic"
    detail: str      # 併合先や判定根拠の人間可読な説明


def _dedup_exact(
    notes: list[QuantizedNote],
) -> tuple[list[QuantizedNote], list[RemovedNote]]:
    """完全重複((start_beats, midi)一致)を統合する。音楽的損失のない安全操作。

    残す基準は quantize.py の dedup と同じ「長い方」。同音価なら高信頼を残す。
    格子キーで判定するのは QuantizedNote の実側が NaN のとき == が成立しない
    (contracts.py の注意書き)ためで、格子側キーが同一性の正しい基準。
    """
    best: dict[tuple[float, int], QuantizedNote] = {}
    order: list[tuple[float, int]] = []
    losers: list[QuantizedNote] = []

    for n in notes:
        key = (n.start_beats, n.midi)
        cur = best.get(key)
        if cur is None:
            best[key] = n
            order.append(key)
            continue
        # より長い、または同音価なら高信頼を勝者に。敗者は削除記録へ。
        if (n.dur_beats, n.confidence) > (cur.dur_beats, cur.confidence):
            best[key] = n
            losers.append(cur)
        else:
            losers.append(n)

    kept = [best[k] for k in order]
    removed = [
        RemovedNote(
            note=l,
            reason="exact_duplicate",
            detail=f"同一格子(start={l.start_beats}, midi={l.midi})の重複を統合",
        )
        for l in losers
    ]
    return kept, removed


def _is_micro_low_conf(
    note: QuantizedNote, min_dur_beats: float, conf_floor: float
) -> bool:
    """微小音価かつ低信頼か(削除には両条件を要求する・単独条件では消さない)。"""
    return note.dur_beats < min_dur_beats and note.confidence < conf_floor


def _octave_parent(
    target: QuantizedNote, notes: list[QuantizedNote], min_dur_beats: float
) -> QuantizedNote | None:
    """target をオクターブ倍音の誤検出とみなせる「強い基音」を探す。

    AMT では基音の1オクターブ上に部分音由来の偽ピークが出やすい(codex §2.4)。
    ただし過剰削除を避けるため、相手が明確に本物の基音である場合のみ親と認める:

    - 同じ start_beats から始まる(同拍発音)
    - target のちょうど1オクターブ下(基音側)
    - 親は微小音価でない(min_dur_beats 以上・本物の持続音)
    - 親は高信頼(conf_floor 以上)かつ target より高信頼

    見つからなければ None。
    """
    for other in notes:
        if other is target:
            continue
        if other.start_beats != target.start_beats:
            continue
        if target.midi - other.midi != HARMONIC_OCTAVE_SEMITONES:
            continue
        if other.dur_beats < min_dur_beats:
            continue
        if other.confidence <= target.confidence:
            continue
        return other
    return None


def cleanup_notes(
    notes: list[QuantizedNote],
    min_dur_beats: float = MIN_DUR_BEATS,
    conf_floor: float = CONF_FLOOR,
) -> tuple[list[QuantizedNote], dict]:
    """記譜前に音符列を保守的・可逆に整理し、削除理由の集計を返す。

    整理する対象と順序(先行研究の順序制御を反映: まず安全な統合、次に多根拠削除):

    1. exact_duplicate: 完全重複((start_beats, midi)一致)の統合。音楽的損失なし。
    2. micro_low_conf: 微小音価(dur < min_dur_beats)かつ低信頼(conf < conf_floor)の
       ノート除去。単独条件では消さない(過剰削除の主犯を避ける)。ただしその拍で
       他に音が無くなる場合は残す(本物の単音を消さない安全弁)。
    3. octave_harmonic: 同拍の強い基音のちょうど1オクターブ上に出た低信頼ノート
       (倍音誤検出の典型)のみ除去。単独条件(オクターブ上・低信頼・強い親)を
       すべて満たす場合に限る。両方が本物(高信頼)なら残す。

    Args:
        notes: 量子化済み音符列。空でもよい。
        min_dur_beats: 微小音価の閾値(拍単位・既定 0.125=32分)。保守的に小さく。
        conf_floor: 低信頼の閾値(既定 0.35)。これ未満のみ削除候補に入る。

    Returns:
        (cleaned, report):
        - cleaned: 整理後の音符列(start_beats, midi 昇順)。
        - report: {
            "input_count": int,
            "output_count": int,
            "removed_count": int,
            "reasons": {reason: count, ...},   # 削除理由ごとの件数
            "removed": list[RemovedNote],       # 可逆情報(元インスタンス+理由)
          }

    Raises:
        ValueError: min_dur_beats <= 0 または conf_floor が [0,1] 外のとき。
    """
    if min_dur_beats <= 0:
        raise ValueError(f"min_dur_beats must be positive, got {min_dur_beats}")
    if not (0.0 <= conf_floor <= 1.0):
        raise ValueError(f"conf_floor must be in [0,1], got {conf_floor}")

    input_count = len(notes)
    removed: list[RemovedNote] = []

    if not notes:
        return [], _build_report(input_count, [], [])

    # 1. 完全重複の統合(安全・可逆)
    kept, dup_removed = _dedup_exact(list(notes))
    removed.extend(dup_removed)

    # 拍(start_beats)ごとの残数を数え、「その拍の最後の1音」を守る安全弁に使う
    per_onset: dict[float, int] = {}
    for n in kept:
        per_onset[n.start_beats] = per_onset.get(n.start_beats, 0) + 1

    survivors: list[QuantizedNote] = []
    for n in kept:
        # 2. 微小音価かつ低信頼 → 削除候補。ただし拍の最後の1音は残す。
        if _is_micro_low_conf(n, min_dur_beats, conf_floor):
            if per_onset[n.start_beats] > 1:
                per_onset[n.start_beats] -= 1
                removed.append(
                    RemovedNote(
                        note=n,
                        reason="micro_low_conf",
                        detail=(
                            f"微小音価(dur={n.dur_beats} < {min_dur_beats})かつ"
                            f"低信頼(conf={n.confidence} < {conf_floor})"
                        ),
                    )
                )
                continue
        survivors.append(n)

    # 3. オクターブ倍音の誤検出(同拍の強い基音の1オクターブ上・低信頼)のみ除去。
    #    micro は要求しない(倍音は必ずしも短くない)。過剰削除を避けるため、
    #    低信頼かつ「強い基音」が同拍に存在する場合に限る。
    cleaned: list[QuantizedNote] = []
    for n in survivors:
        if (
            n.confidence < conf_floor
            and per_onset[n.start_beats] > 1
            and _octave_parent(n, survivors, min_dur_beats) is not None
        ):
            parent = _octave_parent(n, survivors, min_dur_beats)
            per_onset[n.start_beats] -= 1
            removed.append(
                RemovedNote(
                    note=n,
                    reason="octave_harmonic",
                    detail=(
                        f"同拍の強い基音(midi={parent.midi})の1オクターブ上に出た"
                        f"低信頼ノート(midi={n.midi})を倍音誤検出として除去"
                    ),
                )
            )
            continue
        cleaned.append(n)

    cleaned.sort(key=lambda n: (n.start_beats, n.midi))
    return cleaned, _build_report(input_count, cleaned, removed)


def _build_report(
    input_count: int, cleaned: list[QuantizedNote], removed: list[RemovedNote]
) -> dict:
    """削除集計レポートを構築する(理由別件数と可逆情報を含む)。"""
    reasons: dict[str, int] = {}
    for r in removed:
        reasons[r.reason] = reasons.get(r.reason, 0) + 1
    return {
        "input_count": input_count,
        "output_count": len(cleaned),
        "removed_count": len(removed),
        "reasons": reasons,
        "removed": removed,
    }
