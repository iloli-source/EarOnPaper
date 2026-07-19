"""パイプライン統括とCLI: 音声ファイル → 耳 → 量子化 → 五線譜MusicXML/MIDI。

使い方: pipeline.py transcribe input.wav -o out.musicxml [--midi out.mid]
完全ローカル処理(外部送信なし)。
"""

import argparse
import json
from pathlib import Path

import librosa

from earpipe.ear import detect_events
from earpipe.ear_poly import detect_events_poly
from earpipe.notate import to_score, write_midi, write_musicxml
from earpipe.postfilter import apply_postfilter
from earpipe.quantize import BPM_DEFAULT, estimate_tempo, quantize_events


def transcribe_file(
    in_path: str | Path,
    out_musicxml: str | Path | None = None,
    out_midi: str | Path | None = None,
    engine: str = "mono",
    sensitivity: str = "normal",
    postfilter: bool = False,
) -> dict:
    """音声ファイルを採譜する。engine: mono(pYIN単音) / poly(basic-pitch多声)。

    poly では #32(感度可変 sensitivity。high は PDベンチの score_rhythm で最良)と
    #31(幽霊除去 postfilter)を適用できる。postfilter の既定は False —
    PD15曲実測で倍音フィルタが本物のオクターブ重ねを誤除去し平均で逆効果だったため
    (bench_out/results_rhythm_configs.json)。合成ケースでは設計どおり動くため
    オプトインで残し、再設計の方向性は Issue #31 クローズコメントに記録。
    戻り値: engine / n_events / n_notes / bpm / notes。
    """
    if engine == "poly":
        events = detect_events_poly(in_path, sensitivity=sensitivity)
        if postfilter:
            events = apply_postfilter(events)
    else:
        y, sr = librosa.load(str(in_path), sr=None, mono=True)
        events = detect_events(y, sr)

    if events:
        bpm = estimate_tempo(events)
        notes = quantize_events(events, bpm, mono=(engine == "mono"))
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
        "engine": engine,
        "n_events": len(events),
        "n_notes": len(notes),
        "bpm": bpm,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="earpipe — 採譜エンジン spike v0")
    sub = p.add_subparsers(dest="command", required=True)
    pt = sub.add_parser("transcribe", help="音声ファイルを五線譜MusicXMLに採譜")
    pt.add_argument("input", help="入力音声(wav/mp3等)")
    pt.add_argument("-o", "--output", help="MusicXML出力先(既定: 入力名.musicxml)")
    pt.add_argument("--midi", help="MIDI出力先(任意)")
    pt.add_argument(
        "--engine", choices=("mono", "poly"), default="mono",
        help="mono=pYIN単音(既定) / poly=basic-pitch多声",
    )
    pt.add_argument(
        "--sensitivity", choices=("normal", "high"), default="normal",
        help="poly検出感度。high=弱音を拾う低閾値(#32。postfilterと併用推奨)",
    )
    pt.add_argument(
        "--postfilter", action="store_true",
        help="幽霊除去の後処理(#31)を有効化(既定OFF: PD実測で平均逆効果のため。詳細はIssue #31)",
    )
    args = p.parse_args(argv)

    out = args.output or str(Path(args.input).with_suffix(".musicxml"))
    result = transcribe_file(
        args.input,
        out_musicxml=out,
        out_midi=args.midi,
        engine=args.engine,
        sensitivity=args.sensitivity,
        postfilter=args.postfilter,
    )
    summary = {k: v for k, v in result.items() if k != "notes"}
    summary["output"] = out
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
