"""耳層(F-102): サステインペダル区間の「候補」推定。

研究(docs/research/upcoming/F-102-*.md)の核心的 pitfall を設計に反映する:

3層分離(codex報告 (2)(5) / grok報告 §2.2):
  - 物理 note_off  : 実際に鍵盤から指が離れた時刻(打鍵の終わり)
  - 音響 sound_off : ペダルで伸びた「共鳴の尾」が消える時刻(聴こえの終わり)
  - 記譜 音価      : 楽譜に書く音符の長さ(=物理 note_off ベースであるべき)
  これらを一つに潰すと「共鳴を音価に変換してしまう」(MAESTRO/GiantMIDI で
  offset≠duration。@ddPn08 の "pedal良・note過伸長"、@DasaemJ の指摘)。

したがって本モジュールは音符の音価を一切引き伸ばさない。ペダルは
「別トラックの候補(direction 相当)」として区間だけを返し、記譜側で
MusicXML の <pedal> 要素等に変換する判断は上位に委ねる。

MVP の方針(grok §2.1 / codex (1)):
  音声から直接 CC64 を検出するのは原理的に脆弱(SOTA でもノート精度より
  一段低く、学習ドメイン外で急落する。torch 等の重依存も禁止)。よって
  MVP は「量子化済みノートの音響的な尾(offset_sec)の重なり」から
  ペダルが踏まれていそうな区間の候補を推定するヒューリスティックに徹する。
  audio 直検出は honest に未実装として NotImplementedError を送出する。

限界(過大主張しない):
  - ここで返すのは「候補」であって CC64 の真値ではない。共鳴の尾は
    ペダル以外(残響・弦共鳴・単なる長い音)でも生じるため誤検出しうる。
  - half-pedal / 深度 / sostenuto / soft(una corda)は扱わない
    (MusicXML <pedal> グラフィックでは表現不可。codex (4))。
  - 同音連打がペダル下にある場合の打ち直し隠蔽(codex (3))は
    検出できない(重なりベースの構造的限界)。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from earpipe.contracts import QuantizedNote

# 音響の尾がこの秒数以上「次の音の打鍵」に食い込んでいれば、ペダルが
# 踏まれている候補とみなす。微小な重なり(検出誤差・自然な減衰の裾)を
# ペダルと誤認しないための下限。研究に固定値の根拠はないため保守的に置く。
DEFAULT_MIN_OVERLAP_SEC = 0.08

# 連続する重なりの間にこの秒数以上の切れ目があれば別ペダル区間に割る
# (ペダルの踏み直し=change 相当)。
DEFAULT_MERGE_GAP_SEC = 0.15


@dataclass(frozen=True)
class SustainSpan:
    """ペダル区間の候補(記譜の音価とは別レイヤ・不変)。

    start_sec/end_sec は実時間秒(音響 sound_off 層)。記譜の音価には
    一切影響させない — これは「Ped.線を引く候補位置」であって音符を
    伸ばす指示ではない(F-102 の 3層分離)。

    confidence は候補の確からしさの粗い代理(重なり量と関与ノート数から
    算出)であり、CC64 の真値ではない。
    """

    start_sec: float
    end_sec: float
    confidence: float
    note_count: int  # この区間で尾が重なっていた音符の数


def _real_timing(note: QuantizedNote) -> tuple[float, float] | None:
    """ノートの実タイミング(onset_sec, offset_sec)を取り出す。

    QuantizedNote の実側は既定 NaN(旧4引数構築との互換・contracts C3)。
    実タイミングが無いノートは重なり判定に使えないため None を返す。
    """
    on = note.onset_sec
    off = note.offset_sec
    if not (isfinite(on) and isfinite(off)):
        return None
    if off <= on:
        return None
    return on, off


def detect_sustain(
    notes: list[QuantizedNote],
    min_overlap_sec: float = DEFAULT_MIN_OVERLAP_SEC,
    merge_gap_sec: float = DEFAULT_MERGE_GAP_SEC,
) -> list[dict]:
    """ノートの音響的な尾の重なりからペダル区間の候補を推定する。

    アルゴリズム(重なりベース・音価を伸ばさない):
      1. 各ノートを実タイミング(onset_sec, offset_sec)で見る。offset_sec は
         「共鳴の尾が消える時刻」= 音響 sound_off 層。
      2. あるノートの尾(offset_sec)が、後続ノートの打鍵(onset_sec)を
         min_overlap_sec 以上越えて残っていれば「ペダルが踏まれている候補」の
         微小区間 [後続onset, 尾offset] を立てる。
      3. 近接する微小区間(切れ目 < merge_gap_sec)を1つのペダル区間に併合する。

    返り値: 候補区間の dict のリスト(音価とは独立した別トラック候補)。
      各 dict: {"start_sec", "end_sec", "confidence", "note_count", "layer"}
      layer は常に "sound_off" — この区間が音響層の推定であり、記譜の音価
      (notated)でも物理 note_off でもないことを明示する(3層分離の宣言)。

    入力検証(システム境界):
      - min_overlap_sec / merge_gap_sec が非有限・負なら ValueError。
      - 実タイミングを持たないノートは黙って無視する(格子のみのノートは
        音響層の判定に使えないため)。
    """
    if not (isfinite(min_overlap_sec) and min_overlap_sec >= 0.0):
        raise ValueError(f"min_overlap_sec must be finite and >= 0, got {min_overlap_sec}")
    if not (isfinite(merge_gap_sec) and merge_gap_sec >= 0.0):
        raise ValueError(f"merge_gap_sec must be finite and >= 0, got {merge_gap_sec}")

    timed = [t for n in notes if (t := _real_timing(n)) is not None]
    if len(timed) < 2:
        return []

    # onset 昇順に並べる(打鍵の時間順)。
    timed.sort(key=lambda t: t[0])

    # 各ノートの尾が、後続の打鍵をどれだけ越えて残っているかを微小区間として収集。
    raw_spans: list[tuple[float, float, float]] = []  # (start, end, overlap量)
    for i, (on_i, off_i) in enumerate(timed):
        for on_j, _off_j in timed[i + 1:]:
            if on_j >= off_i:
                break  # onset 昇順。以降の打鍵はこの尾より後 → 重なりなし
            overlap = off_i - on_j
            if overlap >= min_overlap_sec:
                # 尾が次の打鍵に食い込んでいる区間 [次打鍵, 尾の終わり]
                raw_spans.append((on_j, off_i, overlap))

    if not raw_spans:
        return []

    raw_spans.sort(key=lambda s: s[0])
    return _merge_spans(raw_spans, merge_gap_sec)


def _merge_spans(
    raw_spans: list[tuple[float, float, float]],
    merge_gap_sec: float,
) -> list[dict]:
    """近接する微小重なり区間を1つのペダル区間候補に併合し dict 化する。

    confidence は「区間内の平均重なり量を 0.5 秒で頭打ち正規化」した粗い
    代理値(0-1)。重なりが厚い=ペダルの尾が濃いほど高い。CC64 真値ではない。
    """
    conf_cap_sec = 0.5  # この重なり量で confidence を 1.0 に頭打ち

    merged: list[dict] = []
    cur_start, cur_end, _ = raw_spans[0]
    overlaps: list[float] = [raw_spans[0][2]]
    count = 1

    def flush() -> dict:
        mean_overlap = sum(overlaps) / len(overlaps)
        conf = min(1.0, mean_overlap / conf_cap_sec)
        return {
            "start_sec": cur_start,
            "end_sec": cur_end,
            "confidence": round(conf, 4),
            "note_count": count,
            "layer": "sound_off",  # 音響層の候補(音価でも物理offでもない)
        }

    for start, end, overlap in raw_spans[1:]:
        if start - cur_end <= merge_gap_sec:
            cur_end = max(cur_end, end)
            overlaps.append(overlap)
            count += 1
        else:
            merged.append(flush())
            cur_start, cur_end = start, end
            overlaps = [overlap]
            count = 1
    merged.append(flush())
    return merged


def detect_sustain_audio(y, sr: int) -> list[dict]:  # noqa: ANN001 - y は np.ndarray
    """音声から直接 CC64(ペダル)を検出する(MVPでは未実装・honest)。

    研究(grok §2.1・codex (1))が示す通り、音声からのペダル検出は SOTA でも
    ノート精度より一段低く、学習ドメイン外で急落する脆弱な特徴量であり、
    実用水準の実装には学習済みモデル(torch 系。本プロジェクトでは重依存禁止)を
    要する。MVP ではノート重なりベースの detect_sustain を用いること。

    引数の型・値だけは境界検証し、原理的限界を隠さず NotImplementedError で
    明示的に拒否する(黙って空を返して「検出できた」と誤認させない)。
    """
    if sr <= 0:
        raise ValueError(f"sr must be positive, got {sr}")
    if y is None or len(y) == 0:
        raise ValueError("audio signal y must be non-empty")
    raise NotImplementedError(
        "音声からの直接CC64検出はMVP未対応(研究: 重依存モデルなしでは脆弱)。"
        "detect_sustain(notes) のノート重なりベース候補を使用してください。"
    )
