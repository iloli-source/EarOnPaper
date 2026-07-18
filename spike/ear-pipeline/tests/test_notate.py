"""記譜層（music21 → 五線譜MusicXML/MIDI）のユニットテスト。"""

import music21
from earpipe.notate import to_score, write_midi, write_musicxml
from earpipe.quantize import QuantizedNote

NOTES = [
    QuantizedNote(start_beats=0.0, dur_beats=1.0, midi=60, confidence=0.9),
    QuantizedNote(start_beats=1.0, dur_beats=0.5, midi=64, confidence=0.9),
    QuantizedNote(start_beats=1.5, dur_beats=0.5, midi=67, confidence=0.9),
    QuantizedNote(start_beats=2.0, dur_beats=2.0, midi=72, confidence=0.9),
    # 小節線をまたぐ音 → タイで表現されること
    QuantizedNote(start_beats=3.0 + 0.5, dur_beats=1.5, midi=65, confidence=0.9),
]


class TestToScore:
    def test_score_structure(self):
        score = to_score(NOTES, bpm=120)
        assert isinstance(score, music21.stream.Score)
        measures = list(score.recurse().getElementsByClass(music21.stream.Measure))
        assert len(measures) >= 2
        ts = score.recurse().getElementsByClass(music21.meter.TimeSignature).first()
        assert ts is not None and ts.ratioString == "4/4"

    def test_note_pitches_preserved(self):
        score = to_score(NOTES, bpm=120)
        got = sorted(n.pitch.midi for n in score.recurse().notes if not n.tie or n.tie.type == "start")
        assert got == sorted(n.midi for n in NOTES)

    def test_cross_barline_tie(self):
        score = to_score(NOTES, bpm=120)
        ties = [n for n in score.recurse().notes if n.tie is not None]
        assert len(ties) >= 2  # start と stop の両端

    def test_empty_notes_gives_valid_empty_score(self):
        score = to_score([], bpm=120)
        assert isinstance(score, music21.stream.Score)
        assert len(list(score.recurse().notes)) == 0


class TestWrite:
    def test_musicxml_roundtrip(self, tmp_path):
        score = to_score(NOTES, bpm=120)
        path = tmp_path / "out.musicxml"
        write_musicxml(score, path)
        assert path.exists() and path.stat().st_size > 0
        reparsed = music21.converter.parse(str(path))
        got = sorted(n.pitch.midi for n in reparsed.recurse().notes if not n.tie or n.tie.type == "start")
        assert got == sorted(n.midi for n in NOTES)

    def test_midi_write(self, tmp_path):
        import pretty_midi
        score = to_score(NOTES, bpm=120)
        path = tmp_path / "out.mid"
        write_midi(score, path)
        pm = pretty_midi.PrettyMIDI(str(path))
        got = sorted(n.pitch for inst in pm.instruments for n in inst.notes)
        assert got == sorted(n.midi for n in NOTES)

    def test_empty_musicxml_roundtrip(self, tmp_path):
        score = to_score([], bpm=120)
        path = tmp_path / "empty.musicxml"
        write_musicxml(score, path)
        reparsed = music21.converter.parse(str(path))
        assert len(list(reparsed.recurse().notes)) == 0
