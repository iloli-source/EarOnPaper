"""任意SF2試聴レンダリング(F-097・Issue #104)のテスト。

pretty_midi で既知の数音MIDIを構成し、render_soundfont_preview の
WAV出力・フォールバック挙動・SF2ロード失敗の拒否をAAA形式で検証する。
本環境は pyfluidsynth 未導入のため、SF2指定経路も実際にはサイン波合成へ
フォールバックし、その事実がサイドカーへ記録されることを確認する。
"""

from pathlib import Path

import numpy as np
import pretty_midi
import pytest
import soundfile as sf

from earpipe.services.notate.soundfont_preview import (
    DEFAULT_SR,
    _NOTE_SUFFIX,
    fluidsynth_available,
    render_soundfont_preview,
)


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


def _make_fake_sf2(tmp_path: Path) -> Path:
    """存在する(ただし中身は非正規の)SF2パスを作る。

    本環境では pyfluidsynth 未導入のため合成には到達せず、存在検証のみ通す用途。
    """
    sf2 = tmp_path / "fake.sf2"
    sf2.write_bytes(b"RIFF____sfbkfake")
    return sf2


def _note_path(wav: Path) -> Path:
    """WAVに対応するフォールバック通知サイドカーのパスを返す。"""
    return wav.with_name(wav.name + _NOTE_SUFFIX)


class TestRenderSoundfontPreviewBasic:
    def test_returns_wav_with_matching_samplerate_and_content(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_wav = tmp_path / "out.wav"
        sr = 44100

        # Act
        result = render_soundfont_preview(midi_path, out_wav, sr=sr)

        # Assert
        assert result.exists()
        assert result.suffix == ".wav"
        data, read_sr = sf.read(str(result))
        assert read_sr == sr
        assert len(data) > 0

    def test_default_samplerate_is_applied(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_wav = tmp_path / "out.wav"

        # Act
        result = render_soundfont_preview(midi_path, out_wav)

        # Assert
        _, read_sr = sf.read(str(result))
        assert read_sr == DEFAULT_SR

    def test_non_wav_suffix_is_coerced_to_wav(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_path = tmp_path / "audition.mp3"

        # Act
        result = render_soundfont_preview(midi_path, out_path)

        # Assert
        assert result.suffix == ".wav"
        assert result.exists()

    def test_empty_midi_still_writes_nonzero_wav(self, tmp_path):
        # Arrange
        midi_path = _make_empty_midi(tmp_path)
        out_wav = tmp_path / "silence.wav"

        # Act
        result = render_soundfont_preview(midi_path, out_wav)

        # Assert: 0バイトWAVを書かない(最低1サンプルの無音)。
        assert result.exists()
        data, _ = sf.read(str(result))
        assert len(data) >= 1

    def test_output_amplitude_is_normalized(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path, pitches=(60, 62, 64, 65, 67))
        out_wav = tmp_path / "norm.wav"

        # Act
        result = render_soundfont_preview(midi_path, out_wav)

        # Assert: クリップしない範囲に収まっている。
        data, _ = sf.read(str(result))
        assert float(np.max(np.abs(data))) <= 1.0


class TestSoundfontValidation:
    def test_missing_soundfont_raises_not_found(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_wav = tmp_path / "out.wav"
        missing = tmp_path / "nope.sf2"

        # Act / Assert: サイレント無音ではなく明示的に拒否する(codex 2-1)。
        with pytest.raises(FileNotFoundError):
            render_soundfont_preview(midi_path, out_wav, soundfont_path=missing)

    def test_directory_as_soundfont_raises_not_found(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_wav = tmp_path / "out.wav"
        a_dir = tmp_path / "sf2_dir"
        a_dir.mkdir()

        # Act / Assert
        with pytest.raises(FileNotFoundError):
            render_soundfont_preview(midi_path, out_wav, soundfont_path=a_dir)


class TestFallbackBehavior:
    def test_no_soundfont_writes_fallback_note(self, tmp_path):
        # Arrange
        midi_path = _make_midi(tmp_path)
        out_wav = tmp_path / "out.wav"

        # Act
        result = render_soundfont_preview(midi_path, out_wav, soundfont_path=None)

        # Assert: SF2未指定はフォールバックし、その旨を必ず記録する。
        note = _note_path(result)
        assert note.exists()
        text = note.read_text(encoding="utf-8")
        assert "未指定" in text

    def test_existing_sf2_without_fluidsynth_falls_back_and_notes(self, tmp_path):
        # Arrange: 存在するSF2を渡すが、本環境は pyfluidsynth 未導入。
        midi_path = _make_midi(tmp_path)
        out_wav = tmp_path / "out.wav"
        sf2 = _make_fake_sf2(tmp_path)

        # Act
        result = render_soundfont_preview(midi_path, out_wav, soundfont_path=sf2)

        # Assert: WAVは書け、フォールバック通知にSF2パスと非反映の注意がある。
        assert result.exists()
        # フォールバックが起きた場合のみ通知が出る(fluidsynthが実在すれば出ない)。
        if not fluidsynth_available():
            note = _note_path(result)
            assert note.exists()
            text = note.read_text(encoding="utf-8")
            assert str(sf2) in text
            assert "SF2音色は反映されていません" in text

    def test_fluidsynth_available_returns_bool(self):
        # Arrange / Act
        available = fluidsynth_available()

        # Assert: 型契約(粗い事前判定)。
        assert isinstance(available, bool)
