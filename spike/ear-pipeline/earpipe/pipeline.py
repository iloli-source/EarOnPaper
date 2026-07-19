"""パイプライン統括とCLI: 音声ファイル → 耳 → 量子化 → 五線譜MusicXML/MIDI。

使い方: pipeline.py transcribe input.wav -o out.musicxml [--midi out.mid]
完全ローカル処理(外部送信なし)。
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path


from earpipe.services.ear import apply_postfilter, detect_events, detect_events_poly, select_events
from earpipe.services.notate import to_score, write_midi, write_midi_raw, write_musicxml, write_pdf
from earpipe.services.rhythm import BPM_DEFAULT, GRID_PER_BEAT, estimate_grid, quantize_events
from earpipe.services.stem import analyze_field, denoise, load_audio


def transcribe_file(
    in_path: str | Path,
    out_musicxml: str | Path | None = None,
    out_midi: str | Path | None = None,
    out_pdf: str | Path | None = None,
    engine: str = "mono",
    sensitivity: str = "normal",
    postfilter: bool = False,
    field_mode: bool = False,
    timing: str = "grid",
) -> dict:
    """音声ファイルを採譜する。engine: mono(pYIN単音) / poly(basic-pitch多声)。

    poly では #32(感度可変 sensitivity。high は PDベンチの score_rhythm で最良)と
    #31(幽霊除去 postfilter)を適用できる。postfilter の既定は False —
    PD15曲実測で倍音フィルタが本物のオクターブ重ねを誤除去し平均で逆効果だったため
    (bench_out/results_rhythm_configs.json)。合成ケースでは設計どおり動くため
    オプトインで残し、再設計の方向性は Issue #31 クローズコメントに記録。

    field_mode の制約(レビュー#40 M7): 降噪(denoise)が効くのは mono 経路のみ。
    poly は bp_worker がファイルパス入力のため降噪波形を渡せず、SNR適応の
    選択フィルタ(select_events)のみ適用される。降噪波形の一時ファイル経由は
    将来課題。
    戻り値: engine / n_events / n_notes / bpm / notes。
    """
    analysis = None
    y_loaded = None
    if field_mode:
        y_loaded, sr_loaded = load_audio(in_path)
        analysis = analyze_field(y_loaded, sr_loaded)

    if engine == "poly":
        events = detect_events_poly(in_path, sensitivity=sensitivity)
        if postfilter:
            events = apply_postfilter(events)
    else:
        # field_mode時は分析でロード済みの波形を再利用する(二重ロード回避)
        if y_loaded is not None:
            y, sr = y_loaded, sr_loaded
        else:
            y, sr = load_audio(in_path)
        if field_mode:
            y = denoise(y, sr)
        events = detect_events(y, sr)

    if analysis is not None:
        events = select_events(events, analysis.snr_db)

    if events:
        bpm, grid_per_beat = estimate_grid(events)  # 格子系(2分/3分)も同時推定(#39)
        notes = quantize_events(
            events, bpm, mono=(engine == "mono"), grid_per_beat=grid_per_beat
        )
    else:
        bpm = BPM_DEFAULT
        grid_per_beat = GRID_PER_BEAT
        notes = []

    score = to_score(notes, bpm)
    if out_musicxml:
        write_musicxml(score, out_musicxml)  # 譜面は常に格子側(楽譜=量子化表現)
    if out_midi:
        # C3二重表現(Issue #38): MIDIエクスポートは grid(格子) / raw(実タイミング) を選択可能
        if timing == "raw":
            write_midi_raw(notes, out_midi, bpm=bpm)
        else:
            write_midi(score, out_midi)

    result = {
        "input": str(in_path),
        "engine": engine,
        "n_events": len(events),
        "n_notes": len(notes),
        "bpm": bpm,
        "grid_per_beat": grid_per_beat,
        "timing": timing,
        "notes": notes,
    }
    if analysis is not None:
        result["field_report"] = asdict(analysis.report)
    if out_pdf:
        if not out_musicxml:
            raise ValueError("--pdf にはMusicXML出力(-o)が必要")
        result["engrave"] = write_pdf(out_musicxml, out_pdf)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="earpipe — 採譜エンジン spike v0")
    sub = p.add_subparsers(dest="command", required=True)
    pt = sub.add_parser("transcribe", help="音声ファイルを五線譜MusicXMLに採譜")
    pt.add_argument("input", help="入力音声(wav/mp3等)")
    pt.add_argument("-o", "--output", help="MusicXML出力先(既定: 入力名.musicxml)")
    pt.add_argument("--midi", help="MIDI出力先(任意)")
    pt.add_argument("--pdf", help="五線譜PDF出力先(任意。ADR-004: Verovio)")
    pt.add_argument(
        "--field-mode", action="store_true",
        help="フィールド録音モード(C8): SNR適応の選択的抽出+非音程成分の分類報告",
    )
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
    pt.add_argument(
        "--timing", choices=("grid", "raw"), default="grid",
        help="MIDIエクスポートのタイミング表現(C3二重表現)。grid=格子(既定・楽譜整合) / raw=実タイミング(評価・DAW向け)",
    )
    args = p.parse_args(argv)

    out = args.output or str(Path(args.input).with_suffix(".musicxml"))
    result = transcribe_file(
        args.input,
        out_musicxml=out,
        out_midi=args.midi,
        out_pdf=args.pdf,
        engine=args.engine,
        sensitivity=args.sensitivity,
        postfilter=args.postfilter,
        field_mode=args.field_mode,
        timing=args.timing,
    )
    summary = {k: v for k, v in result.items() if k != "notes"}
    summary["output"] = out
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
