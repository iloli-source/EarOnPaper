"""中間資産I/O(asset_io.py・F-096/Issue #98)のテスト。

AAA(Arrange-Act-Assert)形式で、往復(export→import)の不変性を中心に、
研究(F-096-grok.md)の失敗モード(BPM 120 落ち・単位不一致・グリッド破壊・
NaN実側の復元)への堅牢性を検証する。
"""

import json
import math

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.asset_io import (
    SCHEMA_VERSION,
    export_asset,
    import_asset,
)


def qn(
    start: float,
    dur: float,
    midi: int,
    conf: float = 0.9,
    onset: float = float("nan"),
    offset: float = float("nan"),
) -> QuantizedNote:
    """量子化音符を1つ作るヘルパ(実側は既定 NaN)。"""
    return QuantizedNote(
        start_beats=start,
        dur_beats=dur,
        midi=midi,
        confidence=conf,
        onset_sec=onset,
        offset_sec=offset,
    )


def assert_note_equal(actual: QuantizedNote, expected: QuantizedNote) -> None:
    """音符の全フィールド一致を照合する(NaN 実側は math.isnan で個別照合)。

    contracts.py の注意どおり NaN != NaN のため == は使わず、格子側は厳密一致、
    実側は「両方 NaN」または「値一致」を確認する。
    """
    assert actual.start_beats == expected.start_beats
    assert actual.dur_beats == expected.dur_beats
    assert actual.midi == expected.midi
    assert actual.confidence == expected.confidence
    _assert_sec_equal(actual.onset_sec, expected.onset_sec)
    _assert_sec_equal(actual.offset_sec, expected.offset_sec)


def _assert_sec_equal(actual: float, expected: float) -> None:
    """実タイミング秒の一致(両方 NaN も一致とみなす)。"""
    if math.isnan(expected):
        assert math.isnan(actual)
    else:
        assert actual == expected


class TestRoundTrip:
    def test_notes_bpm_grid_survive_round_trip(self, tmp_path) -> None:
        # Arrange: 格子側のみの音符列＋テンポ・グリッド
        notes = [qn(0, 1, 60), qn(1, 0.5, 64, conf=0.7), qn(2, 2, 67)]
        path = tmp_path / "asset.json"

        # Act: 書き出し→読み戻し
        export_asset(notes, bpm=128.0, grid_per_beat=4, path=path)
        got_notes, got_bpm, got_grid = import_asset(path)

        # Assert: 音符・bpm・grid_per_beat が完全一致(往復不変)
        assert got_bpm == 128.0
        assert got_grid == 4
        assert len(got_notes) == len(notes)
        for actual, expected in zip(got_notes, notes):
            assert_note_equal(actual, expected)

    def test_real_timing_seconds_survive_round_trip(self, tmp_path) -> None:
        # Arrange: 実側(onset/offset 秒)を持つ音符(C3二重表現の実側)
        notes = [qn(0, 1, 60, onset=0.02, offset=0.51)]
        path = tmp_path / "asset.json"

        # Act
        export_asset(notes, bpm=90.0, grid_per_beat=2, path=path)
        got_notes, _, _ = import_asset(path)

        # Assert: 実タイミング秒が損失なく復元される
        assert got_notes[0].onset_sec == 0.02
        assert got_notes[0].offset_sec == 0.51

    def test_nan_real_timing_restored_as_nan(self, tmp_path) -> None:
        # Arrange: 実側が未設定(NaN)の音符
        notes = [qn(0, 1, 60)]
        path = tmp_path / "asset.json"

        # Act
        export_asset(notes, bpm=120.0, grid_per_beat=4, path=path)
        got_notes, _, _ = import_asset(path)

        # Assert: NaN のまま復元される(null → NaN)
        assert math.isnan(got_notes[0].onset_sec)
        assert math.isnan(got_notes[0].offset_sec)

    def test_empty_notes_round_trip(self, tmp_path) -> None:
        # Arrange: 空の音符列(ヘッダのみの資産)
        path = tmp_path / "empty.json"

        # Act
        export_asset([], bpm=100.0, grid_per_beat=3, path=path)
        got_notes, got_bpm, got_grid = import_asset(path)

        # Assert: 例外なく空列＋メタが復元される
        assert got_notes == []
        assert got_bpm == 100.0
        assert got_grid == 3

    def test_double_round_trip_is_stable(self, tmp_path) -> None:
        # Arrange: 一度往復した結果をもう一度往復させても不変であること
        notes = [qn(0, 1, 60, onset=0.1, offset=0.6), qn(1, 1, 62)]
        p1 = tmp_path / "a.json"
        p2 = tmp_path / "b.json"

        # Act
        export_asset(notes, bpm=110.0, grid_per_beat=4, path=p1)
        n1, b1, g1 = import_asset(p1)
        export_asset(n1, bpm=b1, grid_per_beat=g1, path=p2)
        n2, b2, g2 = import_asset(p2)

        # Assert: 二重往復でも一致
        assert (b1, g1) == (b2, g2) == (110.0, 4)
        for actual, expected in zip(n2, notes):
            assert_note_equal(actual, expected)


class TestExportContract:
    def test_export_returns_path_and_writes_file(self, tmp_path) -> None:
        # Arrange
        path = tmp_path / "out.json"

        # Act
        result = export_asset([qn(0, 1, 60)], bpm=120.0, grid_per_beat=4, path=path)

        # Assert: 返り値が書き出しパスで、ファイルが存在する
        assert result == path
        assert path.exists()

    def test_json_has_bpm_and_grid_as_first_class_fields(self, tmp_path) -> None:
        # Arrange
        path = tmp_path / "out.json"

        # Act: JSON を直接読み、bpm/grid_per_beat が明示保存されている
        export_asset([qn(0, 1, 60)], bpm=140.0, grid_per_beat=6, path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))

        # Assert: 研究の「BPM 落ち」防止のため第一級フィールドとして存在
        assert payload["bpm"] == 140.0
        assert payload["grid_per_beat"] == 6
        assert payload["version"] == SCHEMA_VERSION

    def test_json_writes_null_for_nan_real_timing(self, tmp_path) -> None:
        # Arrange: 実側 NaN の音符
        path = tmp_path / "out.json"

        # Act
        export_asset([qn(0, 1, 60)], bpm=120.0, grid_per_beat=4, path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))

        # Assert: NaN は null で書かれ、標準JSONとして妥当(NaN リテラル非出力)
        assert payload["notes"][0]["onset_sec"] is None
        assert "NaN" not in path.read_text(encoding="utf-8")


class TestValidation:
    @pytest.mark.parametrize("bad_bpm", [0.0, -10.0, float("nan"), float("inf")])
    def test_export_rejects_invalid_bpm(self, tmp_path, bad_bpm) -> None:
        # Arrange / Act / Assert: 不正 bpm は書かず ValueError(120 落ち防止)
        with pytest.raises(ValueError):
            export_asset([qn(0, 1, 60)], bpm=bad_bpm, grid_per_beat=4, path=tmp_path / "x.json")

    @pytest.mark.parametrize("bad_grid", [0, -1])
    def test_export_rejects_invalid_grid_per_beat(self, tmp_path, bad_grid) -> None:
        # Arrange / Act / Assert: 単位不一致を防ぐため 1 未満は拒否
        with pytest.raises(ValueError):
            export_asset([qn(0, 1, 60)], bpm=120.0, grid_per_beat=bad_grid, path=tmp_path / "x.json")

    def test_import_rejects_missing_bpm(self, tmp_path) -> None:
        # Arrange: bpm 欠落の手書きJSON
        path = tmp_path / "nobpm.json"
        path.write_text(
            json.dumps(
                {"schema": "earpipe.asset_io", "version": SCHEMA_VERSION,
                 "grid_per_beat": 4, "notes": []}
            ),
            encoding="utf-8",
        )

        # Act / Assert: BPM 欠落を黙って 120 で埋めず ValueError
        with pytest.raises(ValueError):
            import_asset(path)

    def test_import_rejects_wrong_schema_signature(self, tmp_path) -> None:
        # Arrange: 別スキーマの JSON(取り違え)
        path = tmp_path / "wrong.json"
        path.write_text(
            json.dumps({"schema": "something.else", "version": 1, "bpm": 120.0,
                        "grid_per_beat": 4, "notes": []}),
            encoding="utf-8",
        )

        # Act / Assert
        with pytest.raises(ValueError):
            import_asset(path)

    def test_import_rejects_unsupported_version(self, tmp_path) -> None:
        # Arrange: 未来版(非対応)の JSON
        path = tmp_path / "future.json"
        path.write_text(
            json.dumps({"schema": "earpipe.asset_io", "version": SCHEMA_VERSION + 99,
                        "bpm": 120.0, "grid_per_beat": 4, "notes": []}),
            encoding="utf-8",
        )

        # Act / Assert
        with pytest.raises(ValueError):
            import_asset(path)

    def test_import_rejects_note_missing_grid_field(self, tmp_path) -> None:
        # Arrange: 格子側キー(start_beats)欠落の音符
        path = tmp_path / "badnote.json"
        path.write_text(
            json.dumps({"schema": "earpipe.asset_io", "version": SCHEMA_VERSION,
                        "bpm": 120.0, "grid_per_beat": 4,
                        "notes": [{"dur_beats": 1, "midi": 60, "confidence": 0.9}]}),
            encoding="utf-8",
        )

        # Act / Assert: 黙って 0 埋めせず KeyError
        with pytest.raises(KeyError):
            import_asset(path)
