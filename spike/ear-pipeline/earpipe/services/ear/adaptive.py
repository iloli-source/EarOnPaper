"""耳層(密度適応): normal/high感度の自動選択 (Issue #54)。

#32の実測で「高感度(rescue)は高密度曲で劇的改善・疎な曲で逆効果」という
トレードオフが判明した(bench_out/results_rhythm_configs.json)。正解なしで
使える選択信号として「high検出数 / normal検出数」の比を用いる:
normal感度が音符を大量に取りこぼす曲(高速・高密度)ほど比が跳ね上がる。

PD15曲の実測分離(2026-07-20):
  rescue勝ち3曲(トルコ行進曲4.06 / 小犬のワルツ3.02 / Romanze 2.56) vs
  それ以外12曲(最大2.03) — 閾値2.3で完全分離。
閾値はこのベンチで調律した値であり、コーパス外での汎化は未検証(正直な限界)。
"""

from dataclasses import dataclass
from pathlib import Path

from earpipe.contracts import PitchEvent

from .poly import detect_events_poly

# high/normal 検出数比がこの値以上なら「normalが取りこぼしている」と判定しhighを採用
DENSITY_RATIO_THRESHOLD = 2.3


@dataclass(frozen=True)
class AdaptiveSelection:
    """密度適応の選択結果(選択根拠も含めて返す=説明可能性)。"""

    events: list[PitchEvent]
    profile: str  # 採用した感度 "normal" / "high"
    ratio: float  # high検出数 / normal検出数
    n_normal: int
    n_high: int


def detect_events_adaptive(path: str | Path) -> AdaptiveSelection:
    """normal/high両感度で検出し、密度比で適応選択する。

    - normal検出ゼロ・high検出ありの極端ケースは high を採用(比は無限大相当)
    - 両方ゼロは normal 扱いの空選択(無音・ノイズのみ入力で音符ゼロを維持)
    """
    normal = detect_events_poly(path, sensitivity="normal")
    high = detect_events_poly(path, sensitivity="high")
    if not normal:
        if high:
            return AdaptiveSelection(high, "high", float("inf"), 0, len(high))
        return AdaptiveSelection([], "normal", 0.0, 0, 0)
    ratio = len(high) / len(normal)
    if ratio >= DENSITY_RATIO_THRESHOLD:
        return AdaptiveSelection(high, "high", ratio, len(normal), len(high))
    return AdaptiveSelection(normal, "normal", ratio, len(normal), len(high))
