"""多声の耳層(v0.2)のテスト: basic-pitch(別インタプリタworker)経由の和音検出。"""

import music21
import pytest

from earpipe.ear_poly import bp_python_path, detect_events_poly
from earpipe.pipeline import transcribe_file
from tests.conftest import CHORDS_PROG, chords_to_seconds, note_f1

pytestmark = pytest.mark.skipif(
    bp_python_path() is None,
    reason="basic-pitch実行環境(tools/ai-ears/.venv312)が見つからない",
)

ONSET_TOL_POLY = 0.12  # basic-pitchのフレーム分解能を考慮し単音(0.08)より緩い窓


def test_poly_triads_f1(chords_wav):
    path, chords, bpm = chords_wav
    events = detect_events_poly(path)
    assert events, "和音進行から音符が検出されること"
    truth = chords_to_seconds(chords, bpm)
    pred = [(e.midi, e.onset, e.offset) for e in events]
    f1 = note_f1(truth, pred, onset_tol=ONSET_TOL_POLY)
    assert f1 >= 0.7, f"和音Note F1={f1:.3f} (要求>=0.7)"


def test_poly_detects_simultaneous_notes(chords_wav):
    path, chords, bpm = chords_wav
    events = detect_events_poly(path)
    # 最初の和音(C: 60,64,67)の3音が同時期(先頭0.5秒以内)に検出されること
    head = {e.midi for e in events if e.onset < 0.5}
    assert {60, 64, 67} <= head, f"先頭和音の3音が拾えていない: {sorted(head)}"


def test_poly_silence_returns_empty(silence_wav):
    assert detect_events_poly(silence_wav) == []


def test_poly_e2e_pipeline(chords_wav, tmp_path):
    path, chords, bpm = chords_wav
    out_xml = tmp_path / "chords.musicxml"
    result = transcribe_file(path, out_musicxml=out_xml, engine="poly")
    assert result["n_notes"] >= 16, "8和音×3音の大半が音符化されること"

    # パイプライン出力(拍単位)を推定BPMで秒に戻して突合
    spb = 60.0 / result["bpm"]
    pred = [
        (n.midi, n.start_beats * spb, (n.start_beats + n.dur_beats) * spb)
        for n in result["notes"]
    ]
    truth = chords_to_seconds(chords, bpm)
    f1 = note_f1(truth, pred, onset_tol=0.15)
    assert f1 >= 0.7, f"E2E(量子化後) Note F1={f1:.3f} (要求>=0.7)"

    # MusicXMLが再読込可能で和音を含むこと
    reloaded = music21.converter.parse(str(out_xml))
    n_chords = len(list(reloaded.recurse().getElementsByClass(music21.chord.Chord)))
    assert n_chords >= 4, f"五線譜に和音が含まれること (chords={n_chords})"


def test_mono_engine_unchanged(dotted_wav, tmp_path):
    """既存の単音エンジンはデフォルトのまま(回帰確認)。"""
    path, melody, bpm = dotted_wav
    result = transcribe_file(path, out_musicxml=tmp_path / "m.musicxml")
    assert result["engine"] == "mono"
    assert result["n_notes"] == len(melody)
