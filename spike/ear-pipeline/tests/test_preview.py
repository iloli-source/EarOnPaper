"""プレビュー音声生成(F-054・Issue #69)のテスト。

pretty_midi で既知の単純MIDIを構成し、render_preview のWAV/MP3出力と
空MIDI(無音)経路の防御をAAA形式で検証する。合成経路は本環境では
必ず内蔵サイン波合成(Fluidsynth未導入)に落ちる。
"""

import shutil
from pathlib import Path

import pretty_midi
import pytest
import soundfile as sf

from earpipe.services.notate.preview import DEFAULT_SR, render_preview


def _make_midi(tmp_path: Path, pitches: tuple[int, ...] = (60, 64, 67)) -> Path:
    """既知の数音からなるMIDIファイルを生成して返す(正解が構成的に既知)。"""
    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=0)
    for i, pitch in enumerate(pitches):
        start = i * 0.5
        inst.notes.append(
            pretty_midi.Note(velocity=100, pitch=pitch, start=start, end=start + 0.4)
        )
    pm.instruments.append(inst)
    midi_path = tmp_path / "in.mid"
    pm.write(str(midi_path))
    return midi_path


def _make_empty_midi(tmp_path: Path) -> Path:
    """音符ゼロ(無音)のMIDIファイルを生成して返す。"""
    pm = pretty_midi.PrettyMIDI()
    midi_path = tmp_path / "empty.mid"
    pm.write(str(midi_path))
    return midi_path


class TestRenderPreviewWav:
    def test_wav_output_has_expected_samplerate_and_length(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_path = tmp_path / "out.wav"
        sr = 22050

        # Act
        result = render_preview(midi_path, out_path, sr=sr)

        # Assert
        assert result.exists()
        assert result.suffix == ".wav"
        data, read_sr = sf.read(str(result))
        assert read_sr == sr
        assert len(data) > 0

    def test_default_samplerate_is_applied(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_path = tmp_path / "default_sr.wav"

        # Act
        result = render_preview(midi_path, out_path)

        # Assert
        _, read_sr = sf.read(str(result))
        assert read_sr == DEFAULT_SR

    def test_accepts_str_paths(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_path = tmp_path / "strpath.wav"

        # Act
        result = render_preview(str(midi_path), str(out_path), sr=22050)

        # Assert
        assert isinstance(result, Path)
        assert result.exists()


class TestRenderPreviewMp3:
    def test_mp3_output_when_ffmpeg_available(self, tmp_path):
        # Arrange
        if shutil.which("ffmpeg") is None:
            pytest.skip("ffmpeg 未導入のためMP3経路をスキップ")
        midi_path = _make_midi(tmp_path)
        out_path = tmp_path / "out.mp3"

        # Act
        result = render_preview(midi_path, out_path, sr=22050)

        # Assert
        assert result.suffix == ".mp3"
        assert result.exists()
        assert result.stat().st_size > 0
        # 中間WAVはMP3成功時に削除されている。
        assert not out_path.with_suffix(".wav").exists()

    def test_mp3_falls_back_to_wav_without_ffmpeg(self, tmp_path, monkeypatch):
        # Arrange: ffmpegを見つけられない状況を強制する。
        monkeypatch.setattr(
            "earpipe.services.notate.preview.shutil.which", lambda name: None
        )
        midi_path = _make_midi(tmp_path)
        out_path = tmp_path / "fallback.mp3"

        # Act
        result = render_preview(midi_path, out_path, sr=22050)

        # Assert: MP3化できず .wav へフォールバックし、実在するパスを返す。
        assert result.suffix == ".wav"
        assert result.exists()
        _, read_sr = sf.read(str(result))
        assert read_sr == 22050


class TestRenderPreviewEmpty:
    def test_empty_midi_produces_nonzero_wav(self, tmp_path):
        # Arrange
        midi_path = _make_empty_midi(tmp_path)
        out_path = tmp_path / "silence.wav"

        # Act
        result = render_preview(midi_path, out_path, sr=22050)

        # Assert: 空MIDIでも0バイトにならず読み出せる(最低1サンプルの無音)。
        assert result.exists()
        data, read_sr = sf.read(str(result))
        assert read_sr == 22050
        assert len(data) >= 1
