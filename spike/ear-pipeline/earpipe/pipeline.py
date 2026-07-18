"""パイプライン統括とCLI: 音声ファイル → 耳 → 量子化 → 五線譜MusicXML/MIDI。

使い方: pipeline.py transcribe input.wav -o out.musicxml [--midi out.mid]
完全ローカル処理(外部送信なし)。
"""

import argparse
import json
from pathlib import Path

import librosa

from earpipe.ear import detect_events
from earpipe.notate import to_score, write_midi, write_musicxml
from earpipe.quantize import BPM_DEFAULT, estimate_tempo, quantize_events


def transcribe_file(in_path, out_musicxml=None, out_midi=None) -> dict:
    """音声ファイルを採譜する。戻り値: n_events / n_notes / bpm / notes。"""
    y, sr = librosa.load(str(in_path), sr=None, mono=True)
    events = detect_events(y, sr)

    if events:
        bpm = estimate_tempo(events)
        notes = quantize_events(events, bpm)
    else:
        bpm = BPM_DEFAULT
        notes = []

    score = to_score(notes, bpm)
    if out_musicxml:
        write_musicxml(score, out_musicxml)
    if out_midi:
        write_midi(score, out_midi)

    return {
        "input": str(in_path),
        "n_events": len(events),
        "n_notes": len(notes),
        "bpm": bpm,
        "notes": notes,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="earpipe — 採譜エンジン spike v0")
    sub = p.add_subparsers(dest="command", required=True)
    pt = sub.add_parser("transcribe", help="音声ファイルを五線譜MusicXMLに採譜")
    pt.add_argument("input", help="入力音声(wav/mp3等)")
    pt.add_argument("-o", "--output", help="MusicXML出力先(既定: 入力名.musicxml)")
    pt.add_argument("--midi", help="MIDI出力先(任意)")
    args = p.parse_args(argv)

    out = args.output or str(Path(args.input).with_suffix(".musicxml"))
    result = transcribe_file(args.input, out_musicxml=out, out_midi=args.midi)
    summary = {k: v for k, v in result.items() if k != "notes"}
    summary["output"] = out
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
