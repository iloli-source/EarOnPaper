"""#144: 5度(+7)構成音の物理プローブ補完。

パワーコードの5度は倍音の大半がルートと共有され検出器に落とされるが、
5度の奇数次倍音(基音1.5f0=+7半音・第3倍音4.5f0=+26半音)はルートの
どの倍音とも一致しない。この非重複帯の実エネルギーだけで裁定するため、
検出器が一度も縦積みを出せない曲でも復元できる(兄弟テンプレ補完との違い)。

正解付き実曲の実測(夢見る 2026-07-26): 落ちた5度4/4件で
E(+7)/E(root)=0.31〜0.94・E(+26)/E(root)=0.20〜0.62・隣接ビン対照の1.3〜2.2倍。
"""

import numpy as np

from earpipe.contracts import PitchEvent
from earpipe.services.ear.octave_arbiter import complete_fifths

SR = 22050


def _tone(midi: int, dur: float, harmonics: tuple[float, ...]) -> np.ndarray:
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(SR * dur)) / SR
    y = np.zeros_like(t)
    for k, a in enumerate(harmonics, start=1):
        y += a * np.sin(2 * np.pi * f0 * k * t)
    return y * 0.2


def _mix(hits: list[tuple[float, list[tuple[int, tuple[float, ...]]]]], total: float) -> np.ndarray:
    y = np.zeros(int(SR * total))
    for t0, tones in hits:
        seg = sum(_tone(m, 0.4, h) for m, h in tones)
        i = int(t0 * SR)
        y[i:i + len(seg)] += seg[: len(y) - i]
    return y


def _ev(t0: float, midi: int, conf: float = 0.8) -> PitchEvent:
    return PitchEvent(onset=t0, offset=t0 + 0.4, midi=midi, confidence=conf)


ROOT_H = (1.0, 0.3, 0.2)      # ルート: f0, 2f0, 3f0
FIFTH_H = (0.8, 0.25, 0.35)   # 5度: 1.5f0, 3f0(共有), 4.5f0(歪みギター相当に強め)


class TestFifthCompletion:
    def test_recovers_fifth_never_detected(self):
        # 音はパワーコード(ルート+5度)だが検出器は全打ルートのみ =
        # 兄弟テンプレでは語彙が作れない最悪ケース
        hits = [(t, [(49, ROOT_H), (56, FIFTH_H)]) for t in (0.5, 1.5, 2.5)]
        y = _mix(hits, 3.5)
        events = [_ev(t, 49) for t in (0.5, 1.5, 2.5)]
        out = complete_fifths(events, y, SR)
        added = [e for e in out if e.midi == 56]
        assert len(added) == 3, f"全打で+7が補完される: {len(added)}"

    def test_no_ghost_on_plain_single_notes(self):
        # 単音のみ(5度なし) → 非重複帯にエネルギーが無いので足さない
        hits = [(t, [(49, ROOT_H)]) for t in (0.5, 1.5, 2.5)]
        y = _mix(hits, 3.5)
        events = [_ev(t, 49) for t in (0.5, 1.5, 2.5)]
        out = complete_fifths(events, y, SR)
        assert not [e for e in out if e.midi == 56], "単音に5度幽霊を足さない"

    def test_no_ghost_on_octave_pairs(self):
        # オクターブ奏法(root+12のみ・gt-octave相当) → +7を足さない
        hits = [(t, [(48, ROOT_H), (60, ROOT_H)]) for t in (0.5, 1.5, 2.5)]
        y = _mix(hits, 3.5)
        events = [e for t in (0.5, 1.5, 2.5) for e in (_ev(t, 48), _ev(t, 60))]
        out = complete_fifths(events, y, SR)
        assert not [e for e in out if e.midi in (55, 67)], "オクターブ奏法に5度幽霊を足さない"

    def test_detected_fifth_not_duplicated(self):
        # 既に+7が検出済みの打には足さない(重複禁止)
        hits = [(0.5, [(49, ROOT_H), (56, FIFTH_H)])]
        y = _mix(hits, 1.5)
        events = [_ev(0.5, 49), _ev(0.5, 56)]
        out = complete_fifths(events, y, SR)
        assert len([e for e in out if e.midi == 56]) == 1, "検出済み5度を重複させない"

    def test_empty_events_passthrough(self):
        assert complete_fifths([], np.zeros(SR), SR) == []
