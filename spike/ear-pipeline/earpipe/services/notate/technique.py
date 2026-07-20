"""奏法検出(F-078・Issue #73): f0軌跡のcent領域ルールベース分類。

対象奏法(kind): "bend"/"slide"(連続グライド)、"vibrato"(周期変調)、
"hammer_on"/"pull_off"(急峻なレガート跳躍)。

設計骨子はTENT(Technique-Embedded Note Tracking, TISMIR)に準拠する:
f0を有声セグメント(NaN=無声を境界)に分割し、cent領域で瞬時傾きの符号を
±1/0にラベル付けしてトレンドを抽出、各奏法の物理的軌跡ルールで分類する。
機械学習は用いない(新規重依存を追加しないため。TENTもbend短尺以外はルール)。

正直な限界(捏造せず低いconfidenceを返す方針):
- bend と slide は同一のピッチ軌跡を生むため f0 のみからの分離は原理的に困難。
  TENTでもSlideのF値は0.388でBend/Releaseと混同する。本実装は到達後の定常保持
  有無という弱シグナルで区別を試みるのみで、confidenceを低めに出す。
- hammer_on/pull_off は bend/vibrato に誤分類されやすい(TENT報告)。平滑化窓と
  LEAP_MAX_DUR_SEC のバランスに依存する。
- f0推定のオクターブエラー(±1200cents級のスパイク)は偽検出源になるため、
  非現実的ジャンプはセグメント境界扱いで無効化する。
- ベース(低周波)はf0推定が不安定で、ギターより技法検出の信頼が低い。
- 先行研究(NIME/Springer)でも多クラス分類の実精度は56.5%程度であり、
  合成理想信号では通っても実録音では混同が多い。過信しないこと。

入力の times/f0_hz は同長・実時間軸(非等間隔可)を想定し、傾きは常に
np.diff(f0)/np.diff(times) の実時間微分で扱う。NaN==NaN は False のため
無声判定は必ず np.isnan を使う。拾えないもの(空/全NaN/短すぎ/無検出)は
例外を投げず空listを返す。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- 閾値定数(全てcents単位・秒単位。TENT/Essentia/NIME先行研究由来) ---
CENTS_PER_SEMITONE: float = 100.0
# 連続グライド(bend/slide)と判定する最小の累積cents変位(概ね半音)。
GLIDE_MIN_CENTS: float = 90.0
# レガート跳躍(hammer/pull)の上限cents(3.5半音=人手/弦張力の物理限界, TENT)。
LEAP_MAX_CENTS: float = 350.0
# レガート跳躍の下限cents(1半音)。これ未満は同一音の揺れとみなす。
LEAP_MIN_CENTS: float = 80.0
# vibratoの有効変調レート帯(Hz)。Essentia std::Vibrato既定=4-8Hz。
VIBRATO_RATE_HZ: tuple[float, float] = (4.0, 8.0)
# vibratoの最小変調深さ(peak-to-peakのcents)。Essentia minExtend=50付近。
VIBRATO_MIN_EXTENT_CENTS: float = 40.0
# vibratoの最大変調深さ(cents)。これを超える揺れはグライド等とみなす。
VIBRATO_MAX_EXTENT_CENTS: float = 300.0
# vibratoと宣言する最小の半サイクル数(TENT: 交互昇降>3セグメント)。
VIBRATO_MIN_HALF_CYCLES: int = 4
# 有効な有声セグメントの最小長(秒)。TENT: 0.1秒未満はノイズ破棄。
MIN_SEG_SEC: float = 0.1
# トレンド符号化の閾値係数(TENT: α×pattern_slope, 既定α=0.05)。
TREND_ALPHA: float = 0.05
# レガート跳躍が完了する最大時間(秒)。これ以内の遷移を離散跳躍とみなす。
LEAP_MAX_DUR_SEC: float = 0.03
# f0推定の非現実的スパイク閾値(cents)。隣接フレームでこれ超の跳躍は無効化。
SPIKE_MAX_CENTS: float = 700.0
# 単発NaN(推定欠損)を真の無声境界とみなす最小連続長(秒)。
NAN_GAP_MIN_SEC: float = 0.05
# 中央値平滑化の窓サイズ(奇数フレーム)。
SMOOTH_WINDOW: int = 5
# bend/slide区別のため到達後定常部を測る割合(セグメント末尾の何割を見るか)。
GLIDE_TAIL_FRAC: float = 0.25
# 到達後定常とみなす末尾区間の最大peak-to-peak(cents)。
GLIDE_TAIL_FLAT_CENTS: float = 30.0


@dataclass(frozen=True)
class Technique:
    """検出された奏法1件(不変)。

    kind は {"bend","slide","vibrato","hammer_on","pull_off"} のいずれか。
    onset_sec/offset_sec は実times値(フレーム番号ではない)。
    confidence は各ルールの閾値超過マージンを0-1に正規化した値で、
    捏造せず控えめに出す(特にbend/slideは原理的曖昧さから低め)。
    """

    kind: str
    onset_sec: float
    offset_sec: float
    confidence: float


def _to_cents(f0_hz: np.ndarray) -> np.ndarray:
    """f0[Hz]をcentsへ変換する。無効値(<=0/NaN)は np.nan を伝播させる。

    参照周波数は固定440Hz。ただしグライド判定は累積cents差(区間内相対)で
    行うため絶対基準に依存しない(pitfall 6)。
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        cents = 1200.0 * np.log2(np.where(f0_hz > 0.0, f0_hz, np.nan) / 440.0)
    return cents.astype(np.float64)


def _voiced_segments(
    times: np.ndarray, cents: np.ndarray
) -> list[tuple[np.ndarray, np.ndarray]]:
    """cents軌跡を有声セグメント((seg_times, seg_cents)の列)へ分割する。

    - NaN(無声)を境界とする。ただし NAN_GAP_MIN_SEC 未満の単発ギャップは
      線形補間で埋め、過分割を防ぐ(pitfall 5)。
    - 隣接フレーム間で SPIKE_MAX_CENTS を超える非現実的跳躍(オクターブエラー等)
      は境界扱いにして無効化する(pitfall 3)。
    - MIN_SEG_SEC 未満のセグメントは破棄する(TENT準拠)。
    """
    n = cents.shape[0]
    valid = ~np.isnan(cents)
    # 短いNaNギャップを補間で埋める(有声↔有声を跨ぐ短欠損のみ対象)。
    filled = cents.copy()
    i = 0
    while i < n:
        if valid[i]:
            i += 1
            continue
        j = i
        while j < n and not valid[j]:
            j += 1
        gap_sec = (times[j - 1] - times[i]) if j - 1 >= i else 0.0
        if 0 < i and j < n and gap_sec < NAN_GAP_MIN_SEC:
            # 両端が有声で短ギャップ: 線形補間で埋める。
            left, right = filled[i - 1], filled[j]
            span = j - (i - 1)
            for k in range(i, j):
                frac = (k - (i - 1)) / span
                filled[k] = left + (right - left) * frac
        i = j

    good = ~np.isnan(filled)
    # スパイク(非現実的跳躍)を境界化: 前フレームとのcents差が大きい点を切る。
    cuts = np.zeros(n, dtype=bool)
    for k in range(1, n):
        if good[k] and good[k - 1]:
            if abs(filled[k] - filled[k - 1]) > SPIKE_MAX_CENTS:
                cuts[k] = True

    segments: list[tuple[np.ndarray, np.ndarray]] = []
    start: int | None = None
    for k in range(n):
        boundary = (not good[k]) or cuts[k]
        if not boundary and start is None:
            start = k
        if boundary and start is not None:
            _append_segment(segments, times, filled, start, k)
            start = None
        # cut点は新セグメントの開始になり得る。
        if cuts[k] and good[k]:
            start = k
    if start is not None:
        _append_segment(segments, times, filled, start, n)
    return segments


def _append_segment(
    segments: list[tuple[np.ndarray, np.ndarray]],
    times: np.ndarray,
    cents: np.ndarray,
    start: int,
    end: int,
) -> None:
    """[start, end) を最小長チェックのうえセグメントとして追加する。"""
    if end - start < 2:
        return
    seg_t = times[start:end]
    if seg_t[-1] - seg_t[0] < MIN_SEG_SEC:
        return
    segments.append((seg_t, _median_smooth(cents[start:end], SMOOTH_WINDOW)))


def _median_smooth(x: np.ndarray, window: int) -> np.ndarray:
    """移動中央値でごく軽く平滑化する(scipy不使用・端は縮小窓)。"""
    if window <= 1 or x.shape[0] < window:
        return x.copy()
    half = window // 2
    out = np.empty_like(x)
    for i in range(x.shape[0]):
        lo = max(0, i - half)
        hi = min(x.shape[0], i + half + 1)
        out[i] = np.median(x[lo:hi])
    return out


def _trend_signs(seg_t: np.ndarray, seg_c: np.ndarray) -> np.ndarray:
    """瞬時傾き(cents/sec)の符号列(+1/-1/0)を返す。

    TENT準拠で α×(セグメント平均傾き) を閾値に微小変動を0へ潰す。
    """
    dt = np.diff(seg_t)
    dt = np.where(dt <= 0.0, np.finfo(np.float64).eps, dt)
    slope = np.diff(seg_c) / dt
    span_sec = seg_t[-1] - seg_t[0]
    total = abs(seg_c[-1] - seg_c[0])
    pattern_slope = total / span_sec if span_sec > 0 else 0.0
    thresh = TREND_ALPHA * pattern_slope
    signs = np.zeros(slope.shape[0], dtype=np.int8)
    signs[slope > thresh] = 1
    signs[slope < -thresh] = -1
    return signs


def _count_half_cycles(signs: np.ndarray) -> int:
    """符号列の方向反転(半サイクル)回数を数える(0は直前方向を維持)。"""
    last = 0
    reversals = 0
    for s in signs:
        if s == 0:
            continue
        if last != 0 and s != last:
            reversals += 1
        last = s
    return reversals


def _clip01(x: float) -> float:
    """confidenceを0-1に丸める(捏造防止のため範囲外は端に寄せる)。"""
    return float(min(1.0, max(0.0, x)))


def _classify_vibrato(seg_t: np.ndarray, seg_c: np.ndarray) -> Technique | None:
    """周期変調(vibrato)を判定する。半サイクル数・extent・FFTレートのAND。"""
    signs = _trend_signs(seg_t, seg_c)
    half_cycles = _count_half_cycles(signs)
    if half_cycles < VIBRATO_MIN_HALF_CYCLES:
        return None

    detrended = seg_c - np.mean(seg_c)
    extent = float(np.max(detrended) - np.min(detrended))
    if not (VIBRATO_MIN_EXTENT_CENTS <= extent <= VIBRATO_MAX_EXTENT_CENTS):
        return None

    rate = _dominant_rate_hz(seg_t, detrended)
    lo, hi = VIBRATO_RATE_HZ
    if rate is None or not (lo <= rate <= hi):
        return None

    # confidence: extentとレート中心寄りをマージンとして合成。
    extent_margin = (extent - VIBRATO_MIN_EXTENT_CENTS) / VIBRATO_MIN_EXTENT_CENTS
    rate_center = (lo + hi) / 2.0
    rate_margin = 1.0 - abs(rate - rate_center) / (hi - rate_center)
    conf = _clip01(0.5 * _clip01(extent_margin) + 0.5 * _clip01(rate_margin))
    return Technique("vibrato", float(seg_t[0]), float(seg_t[-1]), conf)


def _dominant_rate_hz(seg_t: np.ndarray, detrended: np.ndarray) -> float | None:
    """DC除去済み軌跡の主要変調周波数(Hz)をrfftで推定する。等間隔化して解析。"""
    span = seg_t[-1] - seg_t[0]
    n = detrended.shape[0]
    if span <= 0 or n < 4:
        return None
    # 実効サンプルレート(平均フレーム間隔の逆数)。
    fs = (n - 1) / span
    spec = np.abs(np.fft.rfft(detrended - np.mean(detrended)))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    if spec.shape[0] <= 1:
        return None
    peak = int(np.argmax(spec[1:]) + 1)  # DC成分を除く
    return float(freqs[peak])


def _classify_glide(seg_t: np.ndarray, seg_c: np.ndarray) -> Technique | None:
    """単調な連続グライド(bend/slide)を判定する。

    到達後の定常保持有無で弱く区別する。bend/slideは原理的に曖昧なため
    confidenceは控えめに出す(pitfall 1)。
    """
    signs = _trend_signs(seg_t, seg_c)
    net = float(seg_c[-1] - seg_c[0])
    if abs(net) < GLIDE_MIN_CENTS:
        return None
    # ほぼ一方向(逆符号フレームが少数)であること。
    pos = int(np.sum(signs > 0))
    neg = int(np.sum(signs < 0))
    dominant = max(pos, neg)
    opposite = min(pos, neg)
    if dominant == 0 or opposite > 0.2 * dominant:
        return None

    # 末尾が定常ならbend(保持あり)、そうでなければslide(通過)。
    tail_len = max(2, int(len(seg_c) * GLIDE_TAIL_FRAC))
    tail = seg_c[-tail_len:]
    tail_flat = float(np.max(tail) - np.min(tail))
    kind = "bend" if tail_flat <= GLIDE_TAIL_FLAT_CENTS else "slide"

    # confidence: 変位マージン。bend/slideの曖昧さから上限を抑える。
    disp_margin = (abs(net) - GLIDE_MIN_CENTS) / GLIDE_MIN_CENTS
    conf = _clip01(0.6 * _clip01(disp_margin))
    return Technique(kind, float(seg_t[0]), float(seg_t[-1]), conf)


def _classify_leap(
    left: tuple[np.ndarray, np.ndarray],
    right: tuple[np.ndarray, np.ndarray],
) -> Technique | None:
    """隣接セグメント境界の急峻なレガート跳躍(hammer_on/pull_off)を判定する。

    無声(再アタック)を挟まず、1-2フレーム(LEAP_MAX_DUR_SEC以内)で
    LEAP_MIN_CENTS〜LEAP_MAX_CENTS の離散的段差が起きるものを跳躍とみなす。
    連続グライドとの差は「中間ピッチを通過せず数フレームで完了」する点。
    上行=hammer_on、下行=pull_off。
    """
    lt, lc = left
    rt, rc = right
    gap_sec = float(rt[0] - lt[-1])
    if gap_sec < 0 or gap_sec > LEAP_MAX_DUR_SEC:
        return None
    delta = float(rc[0] - lc[-1])
    mag = abs(delta)
    if not (LEAP_MIN_CENTS <= mag <= LEAP_MAX_CENTS):
        return None

    kind = "hammer_on" if delta > 0 else "pull_off"
    # confidence: 遷移が速いほど・段差が半音〜3半音の中心に近いほど高い。
    speed_margin = 1.0 - gap_sec / LEAP_MAX_DUR_SEC
    center = (LEAP_MIN_CENTS + LEAP_MAX_CENTS) / 2.0
    mag_margin = 1.0 - abs(mag - center) / (LEAP_MAX_CENTS - center)
    conf = _clip01(0.5 * _clip01(speed_margin) + 0.5 * _clip01(mag_margin))
    return Technique(kind, float(lt[-1]), float(rt[0]), conf)


def _classify_inner_leaps(seg_t: np.ndarray, seg_c: np.ndarray) -> list[Technique]:
    """セグメント内部の離散レガート跳躍(hammer_on/pull_off)を検出する。

    再アタック(無声)を挟まず1フレームで LEAP_MIN_CENTS〜LEAP_MAX_CENTS の段差が
    起き、その前後は概ね定常(中間ピッチを通過しない=グライドでない)ものを跳躍と
    みなす。段差近傍のフレーム間隔が LEAP_MAX_DUR_SEC 以内であること。
    """
    leaps: list[Technique] = []
    dt = np.diff(seg_t)
    dc = np.diff(seg_c)
    n = dc.shape[0]
    for i in range(n):
        mag = abs(float(dc[i]))
        if not (LEAP_MIN_CENTS <= mag <= LEAP_MAX_CENTS):
            continue
        if float(dt[i]) > LEAP_MAX_DUR_SEC:
            continue
        # 段差の前後が定常(グライドの一部でない)ことを確認する。
        before = seg_c[: i + 1]
        after = seg_c[i + 1:]
        if before.shape[0] < 2 or after.shape[0] < 2:
            continue
        before_flat = float(np.max(before) - np.min(before))
        after_flat = float(np.max(after) - np.min(after))
        if before_flat > LEAP_MIN_CENTS or after_flat > LEAP_MIN_CENTS:
            continue
        kind = "hammer_on" if dc[i] > 0 else "pull_off"
        speed_margin = 1.0 - float(dt[i]) / LEAP_MAX_DUR_SEC
        center = (LEAP_MIN_CENTS + LEAP_MAX_CENTS) / 2.0
        mag_margin = 1.0 - abs(mag - center) / (LEAP_MAX_CENTS - center)
        conf = _clip01(0.5 * _clip01(speed_margin) + 0.5 * _clip01(mag_margin))
        leaps.append(
            Technique(kind, float(seg_t[i]), float(seg_t[i + 1]), conf)
        )
    return leaps


def detect_techniques(times: np.ndarray, f0_hz: np.ndarray) -> list[Technique]:
    """f0軌跡から奏法を検出して返す(F-078)。

    Args:
        times: フレーム時刻[秒]の配列(実時間軸・非等間隔可)。
        f0_hz: 各フレームの基本周波数[Hz]。無声/欠損は NaN または <=0。

    Returns:
        検出された Technique の list。拾えないもの(空・全NaN・短すぎ・無検出)
        は空listを返す(例外は投げない)。同一セグメントからvibratoとglideの
        両方が出うるが、vibratoを優先し重複検出は避ける。

    限界: モジュールdocstring参照。bend/slideは原理的に混同しやすく、
    hammer/pullはf0推定ノイズに敏感。実録音では誤分類が増える。
    """
    times = np.asarray(times, dtype=np.float64)
    f0_hz = np.asarray(f0_hz, dtype=np.float64)
    if times.shape[0] != f0_hz.shape[0] or times.shape[0] < 2:
        return []

    cents = _to_cents(f0_hz)
    segments = _voiced_segments(times, cents)
    if not segments:
        return []

    results: list[Technique] = []
    for seg_t, seg_c in segments:
        # セグメント内部の離散跳躍(hammer/pull)を先に検出する。
        inner = _classify_inner_leaps(seg_t, seg_c)
        if inner:
            results.extend(inner)
            continue
        # vibratoを優先判定し、非該当ならグライドを試す(重複検出回避)。
        vib = _classify_vibrato(seg_t, seg_c)
        if vib is not None:
            results.append(vib)
            continue
        glide = _classify_glide(seg_t, seg_c)
        if glide is not None:
            results.append(glide)

    # 隣接セグメント境界(無声を挟む)のレガート跳躍を判定する。
    for left, right in zip(segments, segments[1:]):
        leap = _classify_leap(left, right)
        if leap is not None:
            results.append(leap)

    return results
