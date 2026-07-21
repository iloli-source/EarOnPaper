"""F-093 / Issue #103: build_handoff_package のAAA形式テスト。

検査対象は earpipe/services/notate/handoff_package.build_handoff_package。
下書き MusicXML は既存の to_score → write_musicxml で実生成し、区間音源は
soundfile で合成 wav を作って渡す。親の pipeline 配線を待たずテスト単体で閉じる
(既存 test_musicxml_validate.py / test_musescore_handoff の流儀)。

固定する不変条件(研究 F-093-grok/codex の失敗例を反映):
- パッケージは単一 XML でなく multi-layer(draft/confidence/regions/manifest/README)。
- draft.musicxml は入力 MusicXML と同一バイト(下書きを改変しない)。
- 低信頼(confidence < 0.5)のみ confidence CSV / regions に載る。高信頼は載らない。
- confidence を p(correct) と誤称しない: manifest は is_calibrated=False、
  README に「正しさの確率ではない」旨がある。
- 元音源があれば低信頼音の区間を pre-roll/post-roll 付きで切り出し、time_origin を残す。
- onset_sec が NaN の音は区間音源にできず、segment_file は空/None になる。
- audio_path 未指定でも壊れず、manifest.audio_included=False で正直に記す。
- 戻り値は zip で、中身に必須ファイルが全部入る。
- 壊れた/空/非XML 入力は例外を投げる(黙って壊れない)。
"""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.handoff_package import (
    _LOW_CONF_THRESHOLD,
    build_handoff_package,
)
from earpipe.services.notate.score import to_score, write_musicxml


def _make_musicxml(tmp_path: Path, n: int = 4) -> Path:
    """実データの下書き MusicXML を作って返す。"""
    notes = [
        QuantizedNote(start_beats=float(i), dur_beats=1.0, midi=60 + i, confidence=0.9)
        for i in range(n)
    ]
    score = to_score(notes, bpm=120.0)
    out = tmp_path / "draft_input.musicxml"
    write_musicxml(score, out)
    return out


def _make_wav(tmp_path: Path, seconds: float = 5.0, sr: int = 8000) -> Path:
    """合成正弦波 wav を作って返す(区間切り出しの元音源)。"""
    t = np.linspace(0.0, seconds, int(seconds * sr), endpoint=False)
    y = 0.2 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    out = tmp_path / "source.wav"
    sf.write(str(out), y, sr)
    return out


def _mixed_notes() -> list[QuantizedNote]:
    """高信頼2 + 低信頼2(うち1つは実タイミングあり、1つは NaN)を返す。"""
    return [
        QuantizedNote(0.0, 1.0, 60, 0.95, onset_sec=0.0, offset_sec=0.5),   # 高
        QuantizedNote(1.0, 1.0, 62, 0.90, onset_sec=0.5, offset_sec=1.0),   # 高
        QuantizedNote(2.0, 1.0, 64, 0.20, onset_sec=2.0, offset_sec=2.5),   # 低・実あり
        QuantizedNote(3.0, 1.0, 65, 0.10),                                  # 低・NaN実
    ]


def _read_zip(zip_path: Path) -> dict[str, bytes]:
    """zip を名前→バイトの辞書に読む。"""
    with zipfile.ZipFile(zip_path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


class TestPackageStructure:
    """パッケージが multi-layer で必須物を全部含むこと。"""

    def test_zip_contains_all_required_layers(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)
        notes = _mixed_notes()

        # Act
        result = build_handoff_package(xml, notes, tmp_path / "out")

        # Assert
        assert result.suffix == ".zip"
        names = set(_read_zip(result).keys())
        assert "draft.musicxml" in names
        assert "confidence_low_notes.csv" in names
        assert "regions.json" in names
        assert "manifest.json" in names
        assert "README_for_transcriber.txt" in names

    def test_draft_musicxml_is_unmodified(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)
        original = xml.read_bytes()

        # Act
        result = build_handoff_package(xml, _mixed_notes(), tmp_path / "out")

        # Assert: 下書きを改変しない(バイト同一)
        assert _read_zip(result)["draft.musicxml"] == original


class TestLowConfidenceSelection:
    """低信頼のみ抽出され、高信頼は載らないこと。"""

    def test_only_low_confidence_notes_listed(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)
        notes = _mixed_notes()  # 低信頼は index 2,3 の 2 件

        # Act
        result = build_handoff_package(xml, notes, tmp_path / "out")

        # Assert
        files = _read_zip(result)
        regions = json.loads(files["regions.json"])
        assert regions["count"] == 2
        listed_idx = {r["note_index"] for r in regions["regions"]}
        assert listed_idx == {2, 3}
        assert all(
            r["uncertainty_signal"] < _LOW_CONF_THRESHOLD for r in regions["regions"]
        )
        # CSV も低信頼のみ(ヘッダ + 2 行)
        csv_lines = files["confidence_low_notes.csv"].decode("utf-8").splitlines()
        assert len(csv_lines) == 1 + 2

    def test_all_high_confidence_yields_empty_list(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)
        notes = [QuantizedNote(float(i), 1.0, 60 + i, 0.99) for i in range(3)]

        # Act
        result = build_handoff_package(xml, notes, tmp_path / "out")

        # Assert
        regions = json.loads(_read_zip(result)["regions.json"])
        assert regions["count"] == 0


class TestConfidenceNotPCorrect:
    """信頼度を p(correct) と誤称しないこと(研究 codex 結論3)。"""

    def test_manifest_marks_confidence_uncalibrated(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)

        # Act
        result = build_handoff_package(xml, _mixed_notes(), tmp_path / "out")

        # Assert
        manifest = json.loads(_read_zip(result)["manifest.json"])
        assert manifest["confidence_is_calibrated"] is False
        assert manifest["is_draft"] is True
        assert manifest["feature_id"] == "F-093"

    def test_readme_states_not_probability_of_correct(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)

        # Act
        result = build_handoff_package(xml, _mixed_notes(), tmp_path / "out")

        # Assert: 「正しい確率ではない」旨と抜き取り検査注記
        readme = _read_zip(result)["README_for_transcriber.txt"].decode("utf-8")
        assert "確率" in readme
        assert "抜き取り" in readme


class TestAudioSegments:
    """元音源があれば低信頼区間を切り出し、time_origin を残すこと。"""

    def test_segments_extracted_with_time_origin(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)
        wav = _make_wav(tmp_path)
        notes = _mixed_notes()  # index2 が実タイミングあり低信頼

        # Act
        result = build_handoff_package(xml, notes, tmp_path / "out", audio_path=wav)

        # Assert
        files = _read_zip(result)
        seg_names = [n for n in files if n.startswith("audio_segments/")]
        assert len(seg_names) == 1  # 実タイミングある低信頼は1件のみ
        regions = json.loads(files["regions.json"])
        seg_region = next(r for r in regions["regions"] if r["note_index"] == 2)
        assert seg_region["segment_file"] == seg_names[0]
        # pre-roll があるので time_origin は onset(2.0) より前
        assert seg_region["time_origin_sec"] is not None
        assert seg_region["time_origin_sec"] < 2.0
        # 切り出した wav が実際に音を含む
        seg_audio, sr = sf.read(io.BytesIO(files[seg_names[0]]))
        assert seg_audio.size > 0
        manifest = json.loads(files["manifest.json"])
        assert manifest["audio_included"] is True

    def test_nan_onset_note_has_no_segment(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)
        wav = _make_wav(tmp_path)

        # Act
        result = build_handoff_package(
            xml, _mixed_notes(), tmp_path / "out", audio_path=wav
        )

        # Assert: index3(NaN実タイミング)は segment_file なし
        regions = json.loads(_read_zip(result)["regions.json"])
        nan_region = next(r for r in regions["regions"] if r["note_index"] == 3)
        assert nan_region["segment_file"] is None
        assert nan_region["time_origin_sec"] is None


class TestAudioOptional:
    """audio_path 無し/読めない場合も壊れず正直に記すこと。"""

    def test_no_audio_path_marks_audio_excluded(self, tmp_path):
        # Arrange
        xml = _make_musicxml(tmp_path)

        # Act
        result = build_handoff_package(xml, _mixed_notes(), tmp_path / "out")

        # Assert
        files = _read_zip(result)
        manifest = json.loads(files["manifest.json"])
        assert manifest["audio_included"] is False
        assert not any(n.startswith("audio_segments/") for n in files)

    def test_unreadable_audio_falls_back_gracefully(self, tmp_path):
        # Arrange: 音源として壊れたファイルを渡す
        xml = _make_musicxml(tmp_path)
        bad = tmp_path / "not_audio.wav"
        bad.write_bytes(b"not a real wav")

        # Act
        result = build_handoff_package(
            xml, _mixed_notes(), tmp_path / "out", audio_path=bad
        )

        # Assert: 例外を投げず、音なしパッケージになる
        manifest = json.loads(_read_zip(result)["manifest.json"])
        assert manifest["audio_included"] is False
        assert "読み込めなかった" in manifest["audio_note"]


class TestInputValidation:
    """壊れた/空/非XML 入力は例外を投げること。"""

    def test_missing_file_raises(self, tmp_path):
        # Arrange / Act / Assert
        with pytest.raises(FileNotFoundError):
            build_handoff_package(tmp_path / "nope.musicxml", [], tmp_path / "out")

    def test_empty_file_raises_value_error(self, tmp_path):
        # Arrange
        empty = tmp_path / "empty.musicxml"
        empty.write_text("", encoding="utf-8")

        # Act / Assert
        with pytest.raises(ValueError):
            build_handoff_package(empty, [], tmp_path / "out")

    def test_mxl_zip_input_rejected(self, tmp_path):
        # Arrange: ZIP(.mxl)を .musicxml 拡張子で渡す
        fake = tmp_path / "fake.musicxml"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("x", "y")
        fake.write_bytes(buf.getvalue())

        # Act / Assert
        with pytest.raises(ValueError):
            build_handoff_package(fake, [], tmp_path / "out")


class TestZipFallback:
    """zip 化に失敗する環境ではディレクトリを返すこと(黙って壊れない)。"""

    def test_returns_directory_when_zip_fails(self, tmp_path, monkeypatch):
        # Arrange
        xml = _make_musicxml(tmp_path)
        from earpipe.services.notate import handoff_package as mod

        monkeypatch.setattr(mod, "_zip_directory", lambda pkg, zp: False)

        # Act
        result = build_handoff_package(xml, _mixed_notes(), tmp_path / "out")

        # Assert
        assert result.is_dir()
        assert (result / "draft.musicxml").is_file()
        assert (result / "manifest.json").is_file()
