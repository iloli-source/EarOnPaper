"""合成E2E: 正解既知のwav → パイプライン → 音符列F1・MusicXML妥当性・小節整合。"""

import music21
import pytest
from earpipe.pipeline import transcribe_file

from tests.conftest import melody_to_seconds, note_f1


def quantized_to_seconds(result):
    spb = 60.0 / result["bpm"]
    return [(n.midi, n.start_beats * spb, (n.start_beats + n.dur_beats) * spb) for n in result["notes"]]


class TestEndToEnd:
    @pytest.fixture(scope="class", params=["simple", "dotted"])
    def transcribed(self, request, simple_wav, dotted_wav, tmp_path_factory):
        wav, melody, bpm = simple_wav if request.param == "simple" else dotted_wav
        out = tmp_path_factory.mktemp("e2e") / f"{request.param}.musicxml"
        midi = out.with_suffix(".mid")
        result = transcribe_file(wav, out_musicxml=out, out_midi=midi)
        return wav, melody, bpm, out, midi, result

    def test_note_f1(self, transcribed):
        _, melody, bpm, _, _, result = transcribed
        truth = melody_to_seconds(melody, bpm)
        pred = quantized_to_seconds(result)
        f1 = note_f1(truth, pred)
        assert f1 >= 0.8, f"E2E note F1 {f1:.3f} < 0.8 (bpm est={result['bpm']})"

    def test_musicxml_reparses(self, transcribed):
        _, _, _, out, _, result = transcribed
        reparsed = music21.converter.parse(str(out))
        n_starts = [n for n in reparsed.recurse().notes if not n.tie or n.tie.type == "start"]
        assert len(n_starts) == len(result["notes"])

    def test_measure_integrity(self, transcribed):
        # 全小節の実長が拍子と整合(最終小節のみ不足を許す)
        _, _, _, out, _, _ = transcribed
        reparsed = music21.converter.parse(str(out))
        part = reparsed.parts[0]
        measures = list(part.getElementsByClass(music21.stream.Measure))
        assert measures, "no measures"
        for m in measures[:-1]:
            assert m.duration.quarterLength == pytest.approx(4.0), (
                f"measure {m.number} has {m.duration.quarterLength} quarters"
            )

    def test_summary_counts(self, transcribed):
        _, melody, _, _, _, result = transcribed
        assert result["n_notes"] == len(result["notes"])
        # 音符数が正解の±20%以内
        assert abs(result["n_notes"] - len(melody)) <= max(1, len(melody) * 0.2)


class TestNegative:
    def test_silence_zero_notes(self, silence_wav_path, tmp_path):
        out = tmp_path / "silence.musicxml"
        result = transcribe_file(silence_wav_path, out_musicxml=out)
        assert result["n_notes"] == 0
        reparsed = music21.converter.parse(str(out))
        assert len(list(reparsed.recurse().notes)) == 0

    def test_noise_zero_notes(self, noise_wav_path, tmp_path):
        out = tmp_path / "noise.musicxml"
        result = transcribe_file(noise_wav_path, out_musicxml=out)
        assert result["n_notes"] == 0
