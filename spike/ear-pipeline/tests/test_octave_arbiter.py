"""#144: オクターブ構成音の裁定(偶数/奇数倍音比の同一ルート内クラスタリング)。

正解付き実曲(夢見る)の実測: パワーコードのオクターブ重ね(+12)の有無は
検出器の信頼度では分離不能だが、ルートの偶数倍音比で物理的に分離できる
(実在0.98-4.8 vs 不在0.38-1.04・同一ルート内で明確な2クラスタ)。
"""

import numpy as np

from earpipe.contracts import PitchEvent
from earpipe.services.ear.octave_arbiter import arbitrate_octaves

SR = 22050


def _tone(midi: int, dur: float, harmonics: tuple[float, ...]) -> np.ndarray:
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(SR * dur)) / SR
    y = np.zeros_like(t)
    for k, a in enumerate(harmonics, start=1):
        y += a * np.sin(2 * np.pi * f0 * k * t)
    return y * 0.2


def _chord_audio(hits: list[tuple[float, int, bool]], total: float) -> np.ndarray:
    """hits: (開始秒, ルートmidi, オクターブ重ねの有無)。root+5th(+octave)を合成。"""
    y = np.zeros(int(SR * total))
    for t0, root, octv in hits:
        seg = _tone(root, 0.4, (1.0, 0.3, 0.2)) + _tone(root + 7, 0.4, (0.8, 0.25))
        if octv:
            seg = seg + _tone(root + 12, 0.4, (0.9, 0.3))
        i = int(t0 * SR)
        y[i:i + len(seg)] += seg[: len(y) - i]
    return y


def _ev(t0: float, midi: int, conf: float = 0.8) -> PitchEvent:
    return PitchEvent(onset=t0, offset=t0 + 0.4, midi=midi, confidence=conf)


class TestOctaveArbitration:
    def test_adds_missing_octave_in_doubled_hits(self):
        # 4打中2打がオクターブ重ねあり。検出器は全打で+12を見落とした想定
        hits = [(0.5, 49, True), (1.5, 49, True), (2.5, 49, False), (3.5, 49, False)]
        y = _chord_audio(hits, 4.5)
        events = [e for t0, r, _ in hits for e in (_ev(t0, r), _ev(t0, r + 7))]
        out = arbitrate_octaves(events, y, SR)
        added = [e for e in out if e.midi == 61]
        assert len(added) == 2, f"重ねあり2打にだけ+12が補完される: {len(added)}"
        assert all(abs(e.onset - t) < 0.1 for e, t in zip(sorted(added, key=lambda e: e.onset), (0.5, 1.5)))

    def test_removes_ghost_octave_in_undoubled_hits(self):
        # 全打オクターブなし音源なのに検出器が+12幽霊を出した想定(2クラスタ形成用に
        # 重ねあり打も混在させる)
        hits = [(0.5, 47, True), (1.5, 47, True), (2.5, 47, False), (3.5, 47, False)]
        y = _chord_audio(hits, 4.5)
        events = []
        for t0, r, _ in hits:
            events += [_ev(t0, r), _ev(t0, r + 7), _ev(t0, r + 12, conf=0.3)]
        out = arbitrate_octaves(events, y, SR)
        octs = sorted(e.onset for e in out if e.midi == 59)
        assert len(octs) == 2, f"重ねなし打の+12幽霊が除去される: {octs}"
        assert all(t < 2.0 for t in octs)

    def test_unimodal_hits_left_unchanged(self):
        # 全打同条件(クラスタ分離なし)なら検出器の判断を尊重して不変
        hits = [(0.5, 45, True), (1.5, 45, True), (2.5, 45, True), (3.5, 45, True)]
        y = _chord_audio(hits, 4.5)
        events = [e for t0, r, _ in hits for e in (_ev(t0, r), _ev(t0, r + 7))]
        out = arbitrate_octaves(events, y, SR)
        assert [e.midi for e in out] == [e.midi for e in sorted(events, key=lambda e: (e.onset, e.midi))]

    def test_sibling_completion_recovers_missing_member(self):
        # #144: 同一和音テンプレが繰り返される中で、1打だけメンバー欠落
        # (音源にはエネルギーが実在)なら補完される。
        hits = [(0.5, 45, True), (1.5, 45, True), (2.5, 45, True), (3.5, 45, True)]
        y = _chord_audio(hits, 4.5)
        events = []
        for k, (t0, r, _) in enumerate(hits):
            events.append(_ev(t0, r))
            events.append(_ev(t0, r + 7))
            if k != 2:  # 3打目だけ+12を検出し損ねた想定
                events.append(_ev(t0, r + 12))
        out = arbitrate_octaves(events, y, SR)
        octs = [e for e in out if e.midi == 57 and abs(e.onset - 2.5) < 0.1]
        assert octs, "欠落メンバーが兄弟音の証拠で補完される"

    def test_sibling_completion_skips_absent_member(self):
        # 音源に+12が無い(2声のみ)打には補完しない(エネルギー比ゲート)
        hits = [(0.5, 45, False), (1.5, 45, False), (2.5, 45, False), (3.5, 45, False)]
        y = _chord_audio(hits, 4.5)
        events = []
        for k, (t0, r, _) in enumerate(hits):
            events.append(_ev(t0, r))
            events.append(_ev(t0, r + 7))
            if k == 0:
                events.append(_ev(t0, r + 12, conf=0.3))  # 1打目だけ幽霊+12
        out = arbitrate_octaves(events, y, SR)
        added = [e for e in out if e.midi == 57 and e.onset > 1.0]
        assert not added, "実在しないメンバーは補完されない"

    def test_no_fifth_context_untouched(self):
        # 5度が無い(パワーコード文脈外)は裁定対象外
        y = _tone(49, 0.4, (1.0, 0.3)) 
        events = [_ev(0.0, 49)]
        out = arbitrate_octaves(events, np.concatenate([y, np.zeros(SR)]), SR)
        assert [e.midi for e in out] == [49]
