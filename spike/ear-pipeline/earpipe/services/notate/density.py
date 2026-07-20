"""F-095 譜面密度の連続簡略化(音符の意味保存つき間引き)。

`level`(0.0〜1.0)で音符密度を連続的に落とす。level=0.0 は無変更、
level=1.0 は最大間引き。各音符に「保護スコア」を与え、スコアの低い
(=弱拍・短音・非最上声部・低確信の)音から順に間引く。重要音
(小節頭・各時刻の最上声部=skyline・長音・高確信)は保護する。

本モジュールは music21 非依存で、QuantizedNote の格子側フィールド
(start_beats/dur_beats/midi/confidence)のみを用いる純算術で完結する
(重依存追加禁止・テスト容易・軽量。scale_cleanse.py と同方針)。

設計方針(先行研究 F-095-grok.md の失敗例を回帰対策として反映):
- 失敗パターンD(skyline の固定間引きが重要情報を落とす): 「常に最高音だけ
  残す」はしない。各時刻の最上声部(skyline)は保護するが、それだけを残す
  のではなく、長音・小節頭・高確信の内声/バスも保護スコアで守る。
- 失敗パターンK(コントロール不能な変換は使われない): level→間引き量は決定的
  かつ単調。同じ入力+levelは常に同じ出力。何を消したかを removed に理由付きで
  返し(「meaningful control」要求への回答)、非破壊(不変)で新 list を返す。
- 失敗パターンJ(間引き前後で拍位置が死ぬ): 生き残る音符の start_beats/midi/
  timing は一切改変しない。間引きは「削除のみ」で、量子化・スナップはしない。
- 失敗パターンH(下げすぎで音楽性が崩壊): level=1.0 でも骨格(各時刻の最上音+
  小節頭の音)は必ず残す下限を設け、無音の五線譜にはしない。
- 失敗パターンG(何が音符かが未定義): 音符/ノイズの選別は上流(F-108分類・
  midi_cleanup)の責務。本モジュールは音符列を受け取り「薄くする」だけ。

限界(正直な記録・過大主張しない):
- 旋律順は入力 list の順序と start_beats を信頼する(onset_sec は NaN 既定で
  ソート根拠に使えない。contracts.py 参照)。声部分離はしない=同時発音の
  「主旋律」を意味理解で選べない。skyline(最高音)を主旋律の粗い代理とするため、
  内声主題やバスの対旋律が主役の曲では最上音保護が誤ることがある(grok 失敗D)。
- 拍子・小節長を知らない。小節頭は既定 4 拍周期の整数拍を代理とする(bar_beats
  引数で変更可)。真の拍子記号は見ない。
- 和声機能(ガイドトーン)は同定できない。長音・高確信を「重要」の代理にする
  だけで、和声的に重要な短い経過音は落ちうる(grok の「落としてはいけないもの」
  を完全には守れない=単一 level 軸の原理的限界)。
- 楽器・声部別の最適密度差(grok 失敗L)は単一 level では扱えない。呼び出し側で
  声部ごとに分けて適用する運用を想定する。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isnan

from earpipe.contracts import QuantizedNote

# 拍子未知のため、小節頭の代理として使う既定の小節長(拍)。4/4 を仮定。
_DEFAULT_BAR_BEATS = 4.0

# 強拍・小節頭の整数拍判定の許容誤差(量子化後の浮動小数誤差吸収)。
_BEAT_EPS = 1e-6

# 「長音」とみなす拍長のしきい値(四分音符=1.0)。これ以上は保護加点。
_LONG_DUR_BEATS = 1.0

# 「短音」とみなす拍長のしきい値。これ以下は間引かれやすさを加点(減点)。
_SHORT_DUR_BEATS = 0.25

# 保護スコアの重み(大きいほど「残すべき」)。合算して優先順位に使う。
_W_SKYLINE = 4.0      # 各時刻の最上声部(skyline)。主旋律の粗い代理
_W_BAR_HEAD = 3.0     # 小節頭に乗る音。リズムの骨格
_W_LONG = 2.0         # 長音。構造上目立つ
_W_BEAT_HEAD = 1.0    # 拍頭(整数拍)に乗る音。弱拍より保護
_W_CONFIDENCE = 1.0   # 確信度(0-1)そのままを加点
_P_SHORT = 1.5        # 短音への減点(間引き優先)

# level を「間引く割合」に写す上限。level=1.0 でも骨格を残すため 1.0 未満に抑える。
# skyline+小節頭は常に保護されるので実効削除率はこれより低くなりうる。
_MAX_DROP_RATIO = 0.85


@dataclass(frozen=True)
class DroppedNote:
    """間引いた音符の記録(不変)。何を・なぜ落としたかを監査可能にする。

    grok 失敗K(コントロール不能)への回答: 消えた音を理由付きで残し、
    呼び出し側が before/after を差分表示できるようにする。
    """

    note: QuantizedNote  # 落とした元インスタンス(復元可能)
    index: int           # 入力 notes 内の元位置
    protect_score: float  # 算出した保護スコア(低いほど落ちやすい)
    reason: str          # 日本語の理由文


def _safe_conf(value: float) -> float:
    """confidence を 0-1 の実数へ正規化する(NaN は 0.0 とみなす)。"""
    f = float(value)
    if isnan(f):
        return 0.0
    return min(1.0, max(0.0, f))


def _is_on_integer_beat(start_beats: float) -> bool:
    """開始拍が整数拍(拍頭)に乗るかの粗い判定。"""
    return abs(start_beats - round(start_beats)) <= _BEAT_EPS


def _is_bar_head(start_beats: float, bar_beats: float) -> bool:
    """開始拍が小節頭(bar_beats 周期の境界)に乗るかの粗い判定。

    拍子未知のため bar_beats 周期の整数倍を小節頭の代理とする(限界)。
    """
    if bar_beats <= 0:
        return False
    phase = start_beats % bar_beats
    return phase <= _BEAT_EPS or abs(phase - bar_beats) <= _BEAT_EPS


def _skyline_indices(notes: list[QuantizedNote]) -> set[int]:
    """各開始時刻(start_beats)で最も高い MIDI を持つ音符の index 集合。

    skyline(最上声部)の粗い抽出。同じ start_beats に複数音があるとき、
    最高 MIDI の音を主旋律候補として保護する。start_beats はキー化のため
    _BEAT_EPS で丸めて量子化誤差を吸収する。同点(同一 MIDI が複数)は
    最初に現れた index を採用する。
    """
    best_at_time: dict[int, tuple[int, int]] = {}  # key -> (midi, index)
    for i, n in enumerate(notes):
        # 浮動小数の start_beats を安定キーへ(1e-6 精度)。
        key = round(n.start_beats / _BEAT_EPS)
        cur = best_at_time.get(key)
        if cur is None or int(n.midi) > cur[0]:
            best_at_time[key] = (int(n.midi), i)
    return {idx for _, idx in best_at_time.values()}


def _protect_score(
    note: QuantizedNote,
    is_skyline: bool,
    bar_beats: float,
) -> float:
    """音符の保護スコアを算出する(大きいほど残すべき)。

    小節頭・skyline・長音・拍頭・高確信を加点し、短音を減点する。
    重要音(小節頭 or skyline)は加点により自然にスコア上位へ集まり、
    間引き対象から外れやすくなる(grok 失敗Dの直接対策)。
    """
    score = 0.0
    if is_skyline:
        score += _W_SKYLINE
    if _is_bar_head(note.start_beats, bar_beats):
        score += _W_BAR_HEAD
    if note.dur_beats >= _LONG_DUR_BEATS:
        score += _W_LONG
    if _is_on_integer_beat(note.start_beats):
        score += _W_BEAT_HEAD
    score += _W_CONFIDENCE * _safe_conf(note.confidence)
    if note.dur_beats <= _SHORT_DUR_BEATS:
        score -= _P_SHORT
    return score


def _reason_text(
    is_skyline: bool,
    is_bar_head: bool,
    is_long: bool,
) -> str:
    """落とした/残した根拠を監査ログ向けの日本語文で組み立てる。"""
    parts: list[str] = []
    if not is_skyline:
        parts.append("非最上声部")
    if not is_bar_head:
        parts.append("小節頭でない")
    if not is_long:
        parts.append("短〜中音価")
    if not parts:
        parts.append("低保護スコア")
    return "・".join(parts) + "のため弱拍側から間引き"


def simplify_density(
    notes: list[QuantizedNote],
    level: float,
    bar_beats: float = _DEFAULT_BAR_BEATS,
) -> list[QuantizedNote]:
    """音符密度を level(0.0〜1.0)に応じて連続的に簡略化する(非破壊)。

    level=0.0 は無変更(入力と同一内容を返す)、level=1.0 は最大間引き。
    保護スコアの低い音符から順に落とし、重要音(各時刻の最上声部=skyline・
    小節頭・長音・高確信)は保護する。生き残る音符の timing/pitch/duration は
    一切改変しない(削除のみ・不変)。

    引数:
        notes: 量子化済み音符列(音符/ノイズ選別は上流の責務)。旋律順は入力
            list の順序と start_beats を信頼する(onset_sec は NaN 既定で
            ソート根拠に使えない。contracts.py 参照)。
        level: 間引き強度(0.0〜1.0)。範囲外は ValueError。0.0=無変更、
            1.0=最大間引き。決定的かつ単調(同じ入力+level は同じ出力)。
        bar_beats: 小節長(拍)。既定 4.0(4/4 仮定)。小節頭保護の周期に使う。
            0 以下は ValueError。真の拍子記号は見ない(限界)。

    戻り値:
        簡略化後の音符列(新規 list・不変)。入力の元順序を保って返す。
        level=0.0 では入力と同一内容(非破壊)。

    例外:
        ValueError: level が [0.0, 1.0] 外、または bar_beats <= 0 のとき
            (静かに失敗しない)。

    設計の要点(過大主張しない): 単一 level 軸は声部別最適密度や和声的ガイド
    トーン保護を原理的に扱えない(grok 失敗D/L)。skyline は主旋律の粗い代理で
    あり、内声主題が主役の曲では最上音保護が誤りうる。間引きは「削除のみ」で
    拍位置を破壊しないが、和声機能の意味理解はしない(モジュール docstring の
    限界参照)。詳細な落下記録が必要なら simplify_density_verbose を使う。
    """
    kept, _ = simplify_density_verbose(notes, level, bar_beats)
    return kept


def simplify_density_verbose(
    notes: list[QuantizedNote],
    level: float,
    bar_beats: float = _DEFAULT_BAR_BEATS,
) -> tuple[list[QuantizedNote], list[DroppedNote]]:
    """simplify_density と同じ間引きを行い、落とした音符の記録も返す。

    grok 失敗K(コントロール不能)への回答: 消えた音を理由付き(DroppedNote)で
    返し、before/after 差分表示を可能にする。

    戻り値:
        (kept, dropped) のタプル。
        - kept: 簡略化後の音符列(新規 list・不変・元順序保持)。
        - dropped: 落とした音符の DroppedNote list(元 index 昇順)。
    """
    if not (0.0 <= float(level) <= 1.0):
        raise ValueError(f"level は 0.0〜1.0 の範囲。受領値: {level!r}")
    if bar_beats <= 0:
        raise ValueError(f"bar_beats は正の数。受領値: {bar_beats!r}")

    n = len(notes)
    if n == 0 or float(level) <= 0.0:
        # 無変更(非破壊)。入力の元順序で新規 list を返す。
        return list(notes), []

    skyline = _skyline_indices(notes)

    # 各音の保護スコアを算出(元 index を保持)。
    scored: list[tuple[float, int]] = [
        (_protect_score(note, i in skyline, bar_beats), i)
        for i, note in enumerate(notes)
    ]

    # 目標削除数: level に比例、ただし _MAX_DROP_RATIO で上限。
    target_drop = int(round(n * float(level) * _MAX_DROP_RATIO))
    target_drop = min(target_drop, n)
    if target_drop <= 0:
        return list(notes), []

    # 保護スコア昇順(=落としやすい順)。同点は元 index 昇順で決定的に。
    order = sorted(scored, key=lambda si: (si[0], si[1]))

    drop_set: set[int] = set()
    for _score, idx in order:
        if len(drop_set) >= target_drop:
            break
        note = notes[idx]
        # 骨格保護(下限): skyline かつ 小節頭 の音は最大 level でも落とさない。
        # 「最上声部だけ残す」ではなく「最上声部の骨格は必ず残す」下限として働く。
        if idx in skyline and _is_bar_head(note.start_beats, bar_beats):
            continue
        drop_set.add(idx)

    kept: list[QuantizedNote] = [
        note for i, note in enumerate(notes) if i not in drop_set
    ]
    dropped: list[DroppedNote] = []
    for _score, idx in order:
        if idx not in drop_set:
            continue
        note = notes[idx]
        dropped.append(
            DroppedNote(
                note=note,
                index=idx,
                protect_score=_score,
                reason=_reason_text(
                    is_skyline=idx in skyline,
                    is_bar_head=_is_bar_head(note.start_beats, bar_beats),
                    is_long=note.dur_beats >= _LONG_DUR_BEATS,
                ),
            )
        )
    dropped.sort(key=lambda d: d.index)
    return kept, dropped
