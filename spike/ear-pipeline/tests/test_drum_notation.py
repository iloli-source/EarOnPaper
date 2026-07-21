"""drums_to_musicxml(F-036 / Issue #89)のテスト。

先行研究(F-036-{grok,codex}.md)で最重要とされた罠を固定検証する:
  - `<midi-unpitched>` の 1-based off-by-one(GM+1)を数値で固定
  - percussion clef が出ること
  - hihat=x / cymbal=diamond の notehead 音色区別が保存されること
  - MusicXML が music21 で再パースできる妥当な文書であること
  - 描画スタック(Verovio→PDF/PNG)で「ファイルが生成され再読込で妥当」まで
    (OCR/目視は親が別途)

AAA形式(Arrange-Act-Assert)。
"""

import re
from pathlib import Path

import pytest
from music21 import converter
from music21.clef import PercussionClef
from music21.note import Unpitched

from earpipe.services.notate.drum_notation import (
    drums_to_musicxml,
    gm_note_to_musicxml_unpitched,
)
from earpipe.services.notate.engrave import write_pdf, write_png_preview

_BPM = 120.0


def _hits(*pairs: tuple[float, str]) -> list[dict]:
    """(onset_sec, kit) の並びから detect_drums 互換の打点列を作る。"""
    return [
        {"onset_sec": t, "kit": k, "confidence": 0.4} for t, k in pairs
    ]


def _midi_unpitched_values(xml: str) -> list[int]:
    """XML 内の <midi-unpitched> 値を出現順に整数リストで返す。"""
    return [int(v) for v in re.findall(r"<midi-unpitched>(\d+)</midi-unpitched>", xml)]


# --- off-by-one(研究の最重要ポイント) -------------------------------------
def test_gm_offset_is_plus_one_for_kick() -> None:
    # Arrange: GM Kick = 36(0-based)
    gm_kick = 36

    # Act
    result = gm_note_to_musicxml_unpitched(gm_kick)

    # Assert: MusicXML は 1-based なので 37(半音下の別楽器化を防ぐ)
    assert result == 37


def test_gm_offset_table_matches_w3c_examples() -> None:
    # Arrange: W3C percussion tutorial の実例(GM → MusicXML)
    cases = {36: 37, 38: 39, 42: 43, 49: 50, 56: 57}

    # Act / Assert
    for gm, expected in cases.items():
        assert gm_note_to_musicxml_unpitched(gm) == expected


def test_gm_offset_rejects_out_of_range() -> None:
    # Arrange / Act / Assert: 0..127 の範囲外は弾く
    with pytest.raises(ValueError):
        gm_note_to_musicxml_unpitched(128)
    with pytest.raises(ValueError):
        gm_note_to_musicxml_unpitched(-1)


def test_midi_unpitched_in_xml_is_one_based() -> None:
    # Arrange: kick/snare/hihat/cymbal を1発ずつ
    hits = _hits((0.0, "kick"), (0.5, "snare"), (1.0, "hihat"), (1.5, "cymbal"))

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert: 拍位置昇順に 37/39/43/50 が並ぶ(GM 36/38/42/49 の +1)
    assert _midi_unpitched_values(xml) == [37, 39, 43, 50]


# --- 記譜要素(clef / notehead / unpitched) ---------------------------------
def test_percussion_clef_is_emitted() -> None:
    # Arrange
    hits = _hits((0.0, "snare"))

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert: 中立譜号(percussion clef)
    assert "<sign>percussion</sign>" in xml


def test_notehead_distinguishes_hihat_and_cymbal() -> None:
    # Arrange: hihat=x / cymbal=diamond で音色を符頭区別する
    hits = _hits((0.0, "hihat"), (1.0, "cymbal"))

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert
    noteheads = re.findall(r"<notehead[^>]*>([^<]+)</notehead>", xml)
    assert "x" in noteheads
    assert "diamond" in noteheads


def test_notes_use_unpitched_not_pitch() -> None:
    # Arrange
    hits = _hits((0.0, "kick"), (0.5, "snare"))

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert: percussion は <unpitched> を使い <pitch> は使わない
    assert "<unpitched>" in xml
    assert "<pitch>" not in xml


def test_unknown_kit_gets_no_midi_unpitched() -> None:
    # Arrange: 未対応 kit は unknown レーンへ倒し音色付けしない
    hits = _hits((0.0, "unknown"))

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert: unknown は音色マップを持たない(誤音色を付けない)
    assert "<unpitched>" in xml
    assert _midi_unpitched_values(xml) == []


# --- 妥当性・再パース --------------------------------------------------------
def test_output_is_reparseable_musicxml() -> None:
    # Arrange
    hits = _hits((0.0, "kick"), (0.5, "hihat"), (1.0, "snare"), (1.5, "hihat"))

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert: music21 で再パースでき、5線に unpitched note が載る
    score = converter.parseData(xml)
    unpitched = list(score.recurse().getElementsByClass(Unpitched))
    clefs = list(score.recurse().getElementsByClass(PercussionClef))
    assert len(unpitched) == 4
    assert len(clefs) >= 1


def test_empty_hits_yield_valid_rest_score() -> None:
    # Arrange: 打点ゼロでも妥当なスコアになる(1小節休符)
    hits: list[dict] = []

    # Act
    xml = drums_to_musicxml(hits, _BPM)

    # Assert: 再パース可能で unpitched note は無い
    score = converter.parseData(xml)
    assert list(score.recurse().getElementsByClass(Unpitched)) == []
    assert "<sign>percussion</sign>" in xml


# --- 入力検証 ----------------------------------------------------------------
def test_invalid_bpm_raises() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        drums_to_musicxml(_hits((0.0, "kick")), 0.0)
    with pytest.raises(ValueError):
        drums_to_musicxml(_hits((0.0, "kick")), 10000.0)


def test_malformed_hit_raises() -> None:
    # Arrange: onset_sec を欠いた打点
    bad = [{"kit": "kick", "confidence": 0.4}]

    # Act / Assert
    with pytest.raises(ValueError):
        drums_to_musicxml(bad, _BPM)


def test_negative_onset_raises() -> None:
    # Arrange
    bad = [{"onset_sec": -1.0, "kit": "kick"}]

    # Act / Assert
    with pytest.raises(ValueError):
        drums_to_musicxml(bad, _BPM)


# --- ファイル出力 ------------------------------------------------------------
def test_out_path_writes_file(tmp_path: Path) -> None:
    # Arrange
    hits = _hits((0.0, "kick"), (0.5, "snare"))
    out = tmp_path / "sub" / "drum.musicxml"

    # Act
    returned = drums_to_musicxml(hits, _BPM, out)

    # Assert: パスを返し、書き出したファイルが再パースできる
    assert returned == out
    assert out.exists() and out.stat().st_size > 0
    score = converter.parse(str(out))
    assert len(list(score.recurse().getElementsByClass(Unpitched))) == 2


# --- 描画スタック(PDF/PNG が生成され再読込で妥当) --------------------------
def test_engrave_pdf_is_generated_and_valid(tmp_path: Path) -> None:
    # Arrange
    from pypdf import PdfReader

    hits = _hits((0.0, "kick"), (0.5, "hihat"), (1.0, "snare"), (1.5, "hihat"))
    xml_path = tmp_path / "drum.musicxml"
    drums_to_musicxml(hits, _BPM, xml_path)
    pdf_path = tmp_path / "drum.pdf"

    # Act
    meta = write_pdf(xml_path, pdf_path)

    # Assert: PDF が生成され、再読込でページが妥当
    assert pdf_path.exists()
    assert meta["pages"] >= 1
    assert meta["notes_engraved"] == 4
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == meta["pages"]


def test_engrave_png_preview_is_generated(tmp_path: Path) -> None:
    # Arrange
    hits = _hits((0.0, "snare"), (0.5, "hihat"))
    xml_path = tmp_path / "drum.musicxml"
    drums_to_musicxml(hits, _BPM, xml_path)
    png_path = tmp_path / "drum.png"

    # Act
    result = write_png_preview(xml_path, png_path)

    # Assert: PNG が生成され PNG シグネチャを持つ
    assert Path(result).exists()
    assert png_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
