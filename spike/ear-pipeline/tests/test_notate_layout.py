"""記譜品質バンドル(Issue #42)のテスト: 大譜表・左右手割当・休符統合・stem・メタデータ。

受入基準はデモ批判(codex解剖)の実測指標に対応する:
- ピアノ音域は大譜表(ト音/ヘ音2段)になり、低音がト音記号の加線に積まれない
- 休符の細切れ連鎖(最大15)が統合される(全休符/まとまった音価)
- <stem>が音符に付与される
- 曲名メタデータが movement-title に貫通する(「Music21 Fragment」の根絶)
"""

import xml.etree.ElementTree as ET

import music21
import pytest
from earpipe.contracts import QuantizedNote
from earpipe.services.notate.score import split_hands, to_score, write_musicxml


def _q(start: float, dur: float, midi: int) -> QuantizedNote:
    return QuantizedNote(start_beats=start, dur_beats=dur, midi=midi, confidence=0.9)


def _export_root(score: music21.stream.Score, tmp_path) -> ET.Element:
    path = tmp_path / "out.musicxml"
    write_musicxml(score, path)
    return ET.parse(path).getroot()


PIANO_NOTES = [
    # 右手: 中央C以上のメロディ
    _q(0.0, 1.0, 72),
    _q(1.0, 1.0, 76),
    _q(2.0, 1.0, 79),
    _q(3.0, 1.0, 72),
    # 左手: 低音(E2/A2) — 旧実装ではト音記号の加線に積まれていた
    _q(0.0, 2.0, 40),
    _q(2.0, 2.0, 45),
]


class TestSplitHands:
    def test_low_notes_go_bass(self):
        treble, bass = split_hands(PIANO_NOTES)
        assert sorted(n.midi for n in bass) == [40, 45]
        assert sorted(n.midi for n in treble) == [72, 72, 76, 79]

    def test_wide_chord_is_split_at_middle_c(self):
        chord = [_q(0.0, 1.0, 36), _q(0.0, 1.0, 48), _q(0.0, 1.0, 64), _q(0.0, 1.0, 72)]
        treble, bass = split_hands(chord)
        assert sorted(n.midi for n in bass) == [36, 48]
        assert sorted(n.midi for n in treble) == [64, 72]

    def test_coherent_low_group_stays_together(self):
        # 全員が低域の和音は分割せずまとめてヘ音側へ
        chord = [_q(0.0, 1.0, 43), _q(0.0, 1.0, 47), _q(0.0, 1.0, 50)]
        treble, bass = split_hands(chord)
        assert not treble
        assert len(bass) == 3


class TestGrandStaff:
    def test_two_staves_with_clefs(self, tmp_path):
        root = _export_root(to_score(PIANO_NOTES, bpm=120), tmp_path)
        # 大譜表: 1パートに<staff>1/2が現れ、G/Fクレフが両方ある
        staves = {s.text for s in root.iter("staff")}
        assert staves >= {"1", "2"}
        clef_signs = {c.findtext("sign") for c in root.iter("clef")}
        assert {"G", "F"} <= clef_signs

    def test_bass_notes_not_on_treble_ledger(self, tmp_path):
        root = _export_root(to_score(PIANO_NOTES, bpm=120), tmp_path)
        # 低音(E2=40)がヘ音記号のstaffに配置されていること
        for note in root.iter("note"):
            pitch = note.find("pitch")
            if pitch is None:
                continue
            octave = int(pitch.findtext("octave"))
            staff = note.findtext("staff")
            if octave <= 2:
                assert staff == "2", "低音がヘ音記号(staff 2)に居ない"

    def test_treble_only_input_stays_single_staff(self, tmp_path):
        melody = [_q(float(i), 1.0, 72 + (i % 3)) for i in range(4)]
        root = _export_root(to_score(melody, bpm=120), tmp_path)
        clef_signs = {c.findtext("sign") for c in root.iter("clef")}
        assert clef_signs == {"G"}


class TestRestConsolidation:
    def test_sparse_notes_do_not_fragment_rests(self, tmp_path):
        # 1小節目と6小節目にだけ音 → 中間はまとまった休符(全休符)であるべき。
        # 連鎖は小節内で数える(小節ごとの全休符1個は正しい記譜。codex指摘の
        # 「細切れ」は小節内の断片化を指す)。
        sparse = [_q(0.0, 1.0, 72), _q(20.0, 1.0, 74)]
        root = _export_root(to_score(sparse, bpm=120), tmp_path)
        max_chain = 0
        for measure in root.iter("measure"):
            chain = 0
            for note in measure.iter("note"):
                if note.find("rest") is not None:
                    chain += 1
                    max_chain = max(max_chain, chain)
                else:
                    chain = 0
        assert max_chain <= 4, f"小節内の休符連鎖が長すぎる: {max_chain}"

    def test_empty_measures_use_whole_rests(self, tmp_path):
        sparse = [_q(0.0, 1.0, 72), _q(20.0, 1.0, 74)]
        score = to_score(sparse, bpm=120)
        # 空小節は単一の全休符1個で表現される
        for m in score.recurse().getElementsByClass(music21.stream.Measure):
            rests = list(m.recurse().getElementsByClass(music21.note.Rest))
            notes = list(m.recurse().notes)
            if not notes and rests:
                assert len(rests) == 1, f"空小節に休符{len(rests)}個"


class TestStemsAndMeta:
    def test_stems_present_on_notes(self, tmp_path):
        root = _export_root(to_score(PIANO_NOTES, bpm=120), tmp_path)
        pitched = [n for n in root.iter("note") if n.find("pitch") is not None]
        with_stem = [n for n in pitched if n.find("stem") is not None]
        assert pitched, "音符が出力されていない"
        assert len(with_stem) / len(pitched) >= 0.9, (
            f"stem付与率が低い: {len(with_stem)}/{len(pitched)}"
        )

    def test_title_metadata_propagates(self, tmp_path):
        root = _export_root(
            to_score(PIANO_NOTES, bpm=120, title="トルコ行進曲"), tmp_path
        )
        assert root.findtext("movement-title") == "トルコ行進曲"

    def test_default_title_is_not_music21_fragment(self, tmp_path):
        root = _export_root(to_score(PIANO_NOTES, bpm=120), tmp_path)
        title = root.findtext("movement-title")
        assert title != "Music21 Fragment"


class TestVoiceSanity:
    def test_overlapping_notes_do_not_explode_voices(self, tmp_path):
        # 重なりの多い入力でも staff あたりの声部数は2以下に保つ
        overlap = [
            _q(0.0, 4.0, 72),
            _q(1.0, 3.0, 76),
            _q(2.0, 2.0, 79),
            _q(0.0, 4.0, 40),
            _q(2.0, 3.0, 45),
        ]
        root = _export_root(to_score(overlap, bpm=120), tmp_path)
        voices_by_staff: dict[str, set[str]] = {}
        for note in root.iter("note"):
            staff = note.findtext("staff") or "1"
            voice = note.findtext("voice") or "1"
            voices_by_staff.setdefault(staff, set()).add(voice)
        for staff, voices in voices_by_staff.items():
            assert len(voices) <= 2, f"staff {staff} の声部が過剰: {voices}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


class TestIssue49Layout:
    """Issue #49: 弱起の巨大休符解消と小ギャップ吸収。"""

    @staticmethod
    def _qn(midi, start, dur):
        import math

        from earpipe.contracts import QuantizedNote

        return QuantizedNote(midi=midi, start_beats=start, dur_beats=dur,
                             confidence=0.9, onset_sec=math.nan, offset_sec=math.nan)

    def test_leading_full_measures_are_dropped(self):
        # 先頭2小節ぶんの無音(弱起入力)が巨大休符にならず、シフトされる
        import music21

        from earpipe.services.notate.score import to_score

        score = to_score([self._qn(72, 9.5, 1.0), self._qn(74, 11.0, 1.0)], bpm=120)
        part = score.parts[0]
        measures = list(part.recurse().getElementsByClass(music21.stream.Measure))
        first_with_note = next(
            m.measureNumber for m in measures if list(m.recurse().notes)
        )
        assert first_with_note == 1  # 旧実装では3小節目まで音がない

    def test_small_gap_absorbed_into_previous_note(self):
        # 0.25拍のギャップ(オフセット検出の切れ端)は前の音の持続に吸収される
        from earpipe.services.notate.score import to_score

        score = to_score([self._qn(72, 0.0, 0.75), self._qn(74, 1.0, 1.0)], bpm=120)
        part = score.parts[0]
        notes = list(part.recurse().notes)
        assert float(notes[0].quarterLength) == 1.0  # 0.75→1.0に延長
        import music21

        m1 = list(part.recurse().getElementsByClass(music21.stream.Measure))[0]
        rest_len = sum(float(r.quarterLength) for r in m1.recurse().getElementsByClass(music21.note.Rest))
        assert rest_len <= 2.0  # 音間の断片休符が消えている(残るのは末尾のみ)

    def test_large_gap_keeps_rest(self):
        # 2拍の本物のギャップは吸収せず休符として残す(音価の嘘をつかない)
        import music21

        from earpipe.services.notate.score import to_score

        score = to_score([self._qn(72, 0.0, 1.0), self._qn(74, 3.0, 1.0)], bpm=120)
        part = score.parts[0]
        notes = list(part.recurse().notes)
        assert float(notes[0].quarterLength) == 1.0  # 延長されない
        m1 = list(part.recurse().getElementsByClass(music21.stream.Measure))[0]
        rests = list(m1.recurse().getElementsByClass(music21.note.Rest))
        assert rests  # ギャップの休符が実在
