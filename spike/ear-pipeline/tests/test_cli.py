"""CLIの実挙動テスト。"""

import json

import music21
from earpipe.pipeline import main


class TestCli:
    def test_transcribe_command(self, simple_wav, tmp_path, capsys):
        wav, _, _ = simple_wav
        out = tmp_path / "cli_out.musicxml"
        midi = tmp_path / "cli_out.mid"
        rc = main(["transcribe", str(wav), "-o", str(out), "--midi", str(midi)])
        assert rc == 0
        assert out.exists() and midi.exists()
        summary = json.loads(capsys.readouterr().out)
        assert summary["n_notes"] > 0
        assert summary["output"] == str(out)
        assert "notes" not in summary  # サマリーは軽量表示

    def test_default_output_path(self, silence_wav_path, tmp_path, capsys, monkeypatch):
        # -o 省略時は入力と同じ場所に .musicxml
        import shutil
        wav = tmp_path / "in.wav"
        shutil.copy(silence_wav_path, wav)
        rc = main(["transcribe", str(wav)])
        assert rc == 0
        assert (tmp_path / "in.musicxml").exists()
        summary = json.loads(capsys.readouterr().out)
        assert summary["n_notes"] == 0
        reparsed = music21.converter.parse(str(tmp_path / "in.musicxml"))
        assert len(list(reparsed.recurse().notes)) == 0
