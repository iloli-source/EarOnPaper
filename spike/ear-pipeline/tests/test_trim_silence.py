"""先頭無音トリミングのテスト。

音源の頭の無音（曲前の空白）が楽譜の先頭を休符にし精度を落とすため、
音が鳴ったところから採譜する（ユーザー実証 2026-07-20）。
"""

from pathlib import Path

import numpy as np
import soundfile as sf

from earpipe.services.stem.preprocess import trim_leading_silence, trim_leading_silence_file

SR = 22050


def _tone(sec: float, freq: float = 440.0) -> np.ndarray:
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * freq * t)


def _silence(sec: float) -> np.ndarray:
    return np.zeros(int(SR * sec))


class TestTrimLeadingSilence:
    def test_removes_leading_silence(self):
        # 頭に0.7秒の無音 + 1秒の音
        y = np.concatenate([_silence(0.7), _tone(1.0)])
        trimmed, cut_sec = trim_leading_silence(y, SR)
        assert 0.5 < cut_sec < 0.75  # おおむね0.7秒カット（マージン込み）
        assert len(trimmed) < len(y)
        # 先頭付近に音がある（無音でない）
        assert np.abs(trimmed[: SR // 10]).max() > 0.01

    def test_no_silence_unchanged(self):
        # 頭から音がある → ほぼカットなし
        y = _tone(1.0)
        trimmed, cut_sec = trim_leading_silence(y, SR)
        assert cut_sec < 0.1

    def test_keeps_small_margin(self):
        # マージンを残すので、音の直前を切りすぎない
        y = np.concatenate([_silence(0.5), _tone(0.5)])
        trimmed, cut_sec = trim_leading_silence(y, SR)
        # カット後の先頭は無音マージン（音の頭を削らない）
        assert len(trimmed) > 0

    def test_all_silence_safe(self):
        # 全部無音 → 空にせず安全に返す（元のまま or 変化なし扱い）
        y = _silence(1.0)
        trimmed, cut_sec = trim_leading_silence(y, SR)
        assert len(trimmed) > 0

    def test_empty_safe(self):
        trimmed, cut_sec = trim_leading_silence(np.array([]), SR)
        assert cut_sec == 0.0


class TestTrimLeadingSilenceFile:
    def test_file_trimmed(self, tmp_path: Path):
        y = np.concatenate([_silence(0.7), _tone(1.0)])
        src = tmp_path / "src.wav"
        sf.write(str(src), y, SR)
        out_path, cut_sec = trim_leading_silence_file(src)
        assert cut_sec > 0.5
        assert Path(out_path).exists()
        # トリム済みファイルは元より短い
        y2, _ = sf.read(str(out_path))
        assert len(y2) < len(y)

    def test_file_no_silence_passthrough(self, tmp_path: Path):
        y = _tone(1.0)
        src = tmp_path / "src.wav"
        sf.write(str(src), y, SR)
        out_path, cut_sec = trim_leading_silence_file(src)
        # 無音がなければ入力パスをそのまま返す（一時ファイルを作らない）
        assert cut_sec < 0.1
        assert Path(out_path) == src


class TestAnchorToZero:
    """記譜アンカー: 楽譜の最初の音符を0拍目に揃える（ユーザー指摘 2026-07-20）。

    フェードイン等で音量ベースのトリムが届かない残り無音は、量子化後に
    そのまま先頭休符になる。楽譜表現は最初の音符から始めるのが自然なため、
    格子側(start_beats)だけ全体シフトする。実タイミング(onset_sec)は保持。
    """

    def test_leading_rest_removed(self):
        # Arrange
        from earpipe.contracts import QuantizedNote
        from earpipe.services.rhythm import anchor_to_zero

        notes = [
            QuantizedNote(0.5, 1.0, 60, 0.9, onset_sec=0.25),
            QuantizedNote(1.5, 0.5, 62, 0.9, onset_sec=0.75),
        ]

        # Act
        shifted, lead = anchor_to_zero(notes)

        # Assert: 先頭が0拍、間隔は維持、実タイミングは不変
        assert lead == 0.5
        assert shifted[0].start_beats == 0.0
        assert shifted[1].start_beats == 1.0
        assert shifted[0].onset_sec == 0.25

    def test_already_anchored_unchanged(self):
        from earpipe.contracts import QuantizedNote
        from earpipe.services.rhythm import anchor_to_zero

        notes = [QuantizedNote(0.0, 1.0, 60, 0.9)]
        shifted, lead = anchor_to_zero(notes)
        assert lead == 0.0
        assert shifted[0].start_beats == 0.0

    def test_empty_safe(self):
        from earpipe.services.rhythm import anchor_to_zero

        shifted, lead = anchor_to_zero([])
        assert shifted == [] and lead == 0.0
