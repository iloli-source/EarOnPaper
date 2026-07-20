"""変換層: 小節・拍オフセットの系統補正／リバーリング(F-083・Issue #77)。

量子化済み音符列に残る「系統的な拍位相ずれ」を検出して格子頭へ再整列する
(rebarring)。ここで扱えるのは全ノートが**格子(1拍/grid_per_beat)に対し共通の
端数だけ後ろ/前へ一様にずれている**症状(例: オンセット検出の系統遅延)であり、
その共通端数を打ち消すよう格子側(start_beats)だけを一律にずらして小節線を
正しい位置へ引き直す。音(実タイミング)は動かさない。

なお「全体が丁度8分=0.5拍/丁度1格子ずれる」ような**格子上に乗ったままの位相
誤り**(downbeatの取り違え)は、格子残差からは検出できない別問題である(下記限界)。
本関数は格子未満の共通端数=残差ベースで検出可能な系統ずれのみを対象とする。

先行研究(docs/research/upcoming/F-083-{grok,codex}.md)から得た落とし穴を反映:

- **過補正は無補正より悪い**(codex要約4・grok D群): 量子化の100%吸着が
  grooveを壊すのと同型で、確信の薄い補正はノイズを増幅する。本実装は
  「残差が単一の音楽的細分値へ密に集まる」ときだけ補正し、それ以外は
  何もしない(低信頼を返す)。
- **rubato/局所テンポ変化で固定オフセット仮定が破綻**(codex軸3・Chiu 2023):
  残差の集中度(circular resultant length R)が低い=ルバートや揺れの兆候と
  みなし、系統補正を発動しない。曲全体に効く一定端数が存在する場合のみ扱う。
- **最初のdownbeat誤認が全小節へ伝播**(codex軸2・ScoreCloud/Melodyne):
  検出したオフセットは「最も近い格子への位相補正」に限定し、半拍/整数拍の
  倍テンポ的な大移動は行わない(|offset| <= 0.5拍に制限)。
- **実タイミングは破壊しない**(C3・contracts.py): 補正は格子側のみ。
  onset_sec/offset_sec は元イベントの実時刻として保持する。
- **手動同期点の疎密不足で途中再ドリフト**(grok E群・codex軸4): add_sync_points
  は各同期点の間を線形補間する区分線形ワープとし、点が疎なら区間内は
  一定倍率で伸縮する(その限界はdocstring/notesに明記)。

いずれの関数も frozen dataclass を新規生成し、入力は一切破壊しない。
"""

from dataclasses import replace

import numpy as np

from earpipe.contracts import QuantizedNote

# --- correct_beat_offset のパラメータ ---
# 系統補正を許す最大の位相ずれ(拍)。これを超える移動は倍テンポ誤認等の
# 別問題(codex軸1/2)であり、単純な位相補正の責務外とする。
MAX_PHASE_SHIFT_BEATS = 0.5
# 残差クラスタの最小集中度(circular resultant length R・0-1)。全点が同一位相へ
# 密集すると R≈1、ルバート/一様散らばりでは R が小さい。実測(F-083検証)で
# 系統ずれ R≈0.9-1.0、ルバート(±0.2拍) R≈0.15-0.36 と明確に分離するため
# 0.7 を発動閾値とする。これ未満は補正しない(過補正回避・codex軸3)。
MIN_CONCENTRATION = 0.7
# 検出オフセットがこの値未満なら「既に合っている」とみなし補正しない。
# 量子化格子の微小丸め残差で無意味なシフトを掛けないための下限。
MIN_MEANINGFUL_OFFSET = 0.02
# 補正発動に要する最小音符数。少数では系統性を統計的に判定できない。
MIN_NOTES_FOR_CORRECTION = 4


def _phase_residuals(starts: np.ndarray, subdiv: float) -> np.ndarray:
    """各開始拍の、細分格子(subdiv拍間隔)に対する符号付き最寄り残差。

    値域は [-subdiv/2, +subdiv/2)。例: subdiv=0.5(8分格子)で 0.48拍の音符は
    最寄り格子0.5に対し残差 -0.02 を返す。
    """
    q = np.round(starts / subdiv) * subdiv
    return starts - q


def _circular_offset(residuals: np.ndarray, subdiv: float) -> tuple[float, float]:
    """残差群の代表オフセットと集中度を円周統計で求める。

    残差は subdiv 周期の循環量(subdiv/2 と -subdiv/2 は隣接)なので、素朴な
    平均・標準偏差では周期境界をまたぐ群を誤評価する。角度に写して平均ベクトルを
    取り、その位相を代表オフセット、ベクトル長(resultant length R)を集中度とする。

    集中度 R を使う理由(aliasing の罠回避・codex軸3): 周期 subdiv に対し一様に
    散ったルバート列は、位相を線形std等で測ると折り返しで見かけ上まとまって
    しまう。R は全点が同一位相へ寄るほど1へ、一様散布ほど0へ近づき、系統ずれと
    ルバートを頑健に分離できる(F-083実測で系統≈1.0・ルバート≈0.2)。

    戻り値: (代表オフセット[拍], 集中度R[0-1])。
    """
    theta = residuals / subdiv * (2.0 * np.pi)
    mean_vec = np.mean(np.exp(1j * theta))
    concentration = float(np.abs(mean_vec))
    offset = float(np.angle(mean_vec)) / (2.0 * np.pi) * subdiv
    return offset, concentration


def correct_beat_offset(
    notes: list[QuantizedNote],
    grid_per_beat: int,
    beats_per_bar: int = 4,
) -> tuple[list[QuantizedNote], float]:
    """系統的な拍位相ずれを検出し、格子頭へ再整列する(rebarring)。

    全ノートが一様に同じ端数(格子=1/grid_per_beat拍 に対する共通の残差。
    例: 0.06拍のオンセット系統遅延)へずれている場合のみ、その端数を打ち消すよう
    格子側 start_beats を一律シフトして小節頭を正す。ルバートや揺れで端数が散る
    場合、または既にほぼ合っている場合は何もしない(過補正回避)。実タイミング
    onset_sec/offset_sec は保持する(C3)。

    Args:
        notes: 量子化済み音符列(格子側 start_beats を補正対象とする)。
        grid_per_beat: 1拍あたりの格子分割数(quantize と同じ意味。16分格子=4)。
            残差はこの格子(subdiv=1/grid_per_beat)に対して測る。
        beats_per_bar: 1小節の拍数(既定4)。位相補正自体には拍単位で十分だが、
            将来の小節整合検証のため受け取る(現状は境界検証のみに使用)。

    Returns:
        (補正後の音符列, 信頼度[0-1])。補正しなかった場合は入力と等価な
        新規リストと低い信頼度を返す。信頼度は残差の集中度(circular R)。

    限界(先行研究に基づく正直な記録):
        - 検出できるのは「格子に対する共通端数」のみ。丁度1格子/半拍など格子上に
          乗ったままの位相誤り(downbeat取り違え・codex軸1/2)は残差0となり
          検出できない。これは拍子/小節頭推定(meter)側の責務。
        - 局所的なずれ・テンポ変化(rubato)は対象外で補正を見送る(codex軸3)。
        - |offset| <= 0.5拍 に制限。それ超の大移動は倍/半テンポ誤認の症状であり
          位相補正では直せない(実際には残差の値域上、格子が細かいほど自動的に
          小さく収まる)。
        - 補正は「拍位相」のみで、拍子(beats_per_bar)自体の誤りは正さない。
    """
    if grid_per_beat < 1:
        raise ValueError(f"grid_per_beat must be >= 1, got {grid_per_beat}")
    if beats_per_bar < 1:
        raise ValueError(f"beats_per_bar must be >= 1, got {beats_per_bar}")
    if len(notes) < MIN_NOTES_FOR_CORRECTION:
        # 系統性を判定できるだけの標本がない → 無補正(信頼度0)。
        return list(notes), 0.0

    subdiv = 1.0 / grid_per_beat
    starts = np.asarray([n.start_beats for n in notes], dtype=float)
    residuals = _phase_residuals(starts, subdiv)
    offset, concentration = _circular_offset(residuals, subdiv)

    # 信頼度=残差の集中度R。全点が同一位相へ密集するほど1、散るほど0。
    confidence = concentration

    too_scattered = concentration < MIN_CONCENTRATION      # ルバート/揺れ
    already_aligned = abs(offset) < MIN_MEANINGFUL_OFFSET  # 既に合っている
    too_large = abs(offset) > MAX_PHASE_SHIFT_BEATS        # 位相補正の範囲外
    if too_scattered or already_aligned or too_large:
        return list(notes), (0.0 if too_scattered else confidence)

    shifted = [replace(n, start_beats=n.start_beats - offset) for n in notes]
    # 負の開始拍を出さないよう、最小開始が負になる場合は拍単位で持ち上げる
    # (位相は保ったまま小節頭を先頭へ寄せる rebarring の一部)。
    min_start = min(n.start_beats for n in shifted)
    if min_start < 0.0:
        lift = float(np.ceil(-min_start))
        shifted = [replace(n, start_beats=n.start_beats + lift) for n in shifted]
    return shifted, confidence


def add_sync_points(
    notes: list[QuantizedNote],
    points: list[tuple[float, float]],
) -> list[QuantizedNote]:
    """手動同期点の間を区分線形補間して格子側 start_beats をワープする。

    各同期点 (measured_beat, target_beat) は「解析上この拍にある音符を、
    正しくはこの拍へ置きたい」という手動対応づけ。点の間は線形補間し、
    両端の外側は最も近い区間の傾きで外挿する(区分線形ワープ)。音は動かさず
    格子側のみを変換し、実タイミング onset_sec/offset_sec は保持する(C3)。

    Args:
        notes: 量子化済み音符列。
        points: (measured_beat, target_beat) の対応点リスト。measured_beat で
            昇順ソートして用いる。空・1点でも安全に扱う(下記参照)。

    Returns:
        ワープ後の音符列(新規リスト)。points が空なら入力と等価な新規リスト。
        points が1点なら (target - measured) の一定オフセット平行移動になる。

    限界(grok E群・codex軸4):
        - 同期点が疎だと区間内は一定倍率の伸縮になり、区間の途中でずれが
          残る/再ドリフトしうる(密に置くほど精度が上がる)。
        - measured_beat が同値の点が複数あると傾きが定義できないため弾く。
        - 単調増加でない対応(target が measured の順序を逆転)は時間反転を
          招くため ValueError で拒否する(手動誤入力の早期検出)。
    """
    if not points:
        return list(notes)

    pts = sorted(points, key=lambda p: p[0])
    xs = np.asarray([p[0] for p in pts], dtype=float)
    ys = np.asarray([p[1] for p in pts], dtype=float)

    if np.any(np.diff(xs) == 0.0):
        raise ValueError("sync points must have distinct measured_beat values")
    if np.any(np.diff(ys) < 0.0):
        raise ValueError(
            "sync points must be monotonic non-decreasing in target_beat "
            "(order-reversing mappings would invert time)"
        )

    if len(pts) == 1:
        # 1点は基準点1つぶんの平行移動(一定オフセット)として扱う。
        shift = float(ys[0] - xs[0])
        return [replace(n, start_beats=n.start_beats + shift) for n in notes]

    warped: list[QuantizedNote] = []
    for n in notes:
        new_start = _piecewise_linear(n.start_beats, xs, ys)
        warped.append(replace(n, start_beats=new_start))
    return warped


def _piecewise_linear(x: float, xs: np.ndarray, ys: np.ndarray) -> float:
    """区分線形写像 x→y。範囲外は端の区間の傾きで外挿する。

    np.interp は範囲外を端値でクランプ(平坦化)してしまい、先頭同期点より前の
    音符が全て同一拍へ潰れる。同期点の外側でも音楽は続くため、端の傾きで
    素直に外挿する。
    """
    if x <= xs[0]:
        slope = (ys[1] - ys[0]) / (xs[1] - xs[0])
        return float(ys[0] + slope * (x - xs[0]))
    if x >= xs[-1]:
        slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        return float(ys[-1] + slope * (x - xs[-1]))
    return float(np.interp(x, xs, ys))
