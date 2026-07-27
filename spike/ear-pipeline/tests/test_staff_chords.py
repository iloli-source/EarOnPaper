"""五線上部へのコードネーム合成(staff_chords.py)のテスト(#151)。

remap_spans の拍軸線形変換(別ラン由来コードのメロディ格子への写像)と、
inject_chords が music21 スコアへ harmony 要素として注入され MusicXML に
現れることを検証する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.score import to_score, write_musicxml
from earpipe.services.notate.staff_chords import inject_chords, remap_spans


def _span(s: float, e: float, name: str = "C", pc: int = 0, q: str = "major") -> ChordSpan:
    return ChordSpan(start_beats=s, end_beats=e, name=name, root_pc=pc, quality=q)


def test_remap_spans_linear_conversion():
    # src: bpm=120(1拍=0.5s)・trim=1.0s・anchor=0 → src拍4 = 1.0+2.0 = 3.0s
    # dst: bpm=60(1拍=1s)・trim=2.0s・anchor=1 → 3.0s = 1 + (3.0-2.0) = 拍2.0
    out = remap_spans([_span(4.0, 8.0)], src=(120.0, 1.0, 0.0), dst=(60.0, 2.0, 1.0))
    assert out[0].start_beats == pytest.approx(2.0)
    assert out[0].end_beats == pytest.approx(4.0)
    assert out[0].name == "C"


def test_remap_spans_identity():
    # 同一メタデータなら恒等変換
    out = remap_spans([_span(3.0, 5.0)], src=(100.0, 0.5, 1.0), dst=(100.0, 0.5, 1.0))
    assert out[0].start_beats == pytest.approx(3.0)
    assert out[0].end_beats == pytest.approx(5.0)


def _melody_8beats() -> list[QuantizedNote]:
    return [
        QuantizedNote(start_beats=float(b), dur_beats=1.0, midi=60 + b, confidence=0.9)
        for b in range(8)
    ]


def test_inject_chords_appear_in_musicxml(tmp_path: Path):
    # C(0-4拍) → F(4-8拍) が harmony 要素として五線に載る
    score = to_score(_melody_8beats(), bpm=120)
    spans = [_span(0.0, 4.0, "C", 0, "major"), _span(4.0, 8.0, "F", 5, "major")]
    n = inject_chords(score, spans, beats=4)
    assert n == 2
    out = tmp_path / "lead.musicxml"
    write_musicxml(score, out)
    xml = out.read_text()
    assert xml.count("<harmony") == 2
    assert "<root-step>C</root-step>" in xml
    assert "<root-step>F</root-step>" in xml


def test_inject_chords_skips_unparsable_and_out_of_range():
    # 解釈不能なコード名は落とさずスキップ、メロディ範囲外の小節も注入しない
    score = to_score(_melody_8beats(), bpm=120)
    spans = [
        _span(0.0, 4.0, "???", 0, "unknown"),
        _span(400.0, 404.0, "G", 7, "major"),  # メロディ(2小節)のはるか先
    ]
    n = inject_chords(score, spans, beats=4)
    assert n == 0


def test_inject_chords_continuation_elided():
    # 同一コード継続はchordchartと同じスロット整理で1回だけ注入される
    score = to_score(_melody_8beats(), bpm=120)
    n = inject_chords(score, [_span(0.0, 8.0, "Em", 4, "minor")], beats=4)
    assert n == 1
