"""パイプライン統括とCLI: 音声ファイル → 耳 → 量子化 → 五線譜MusicXML/MIDI。

使い方: pipeline.py transcribe input.wav -o out.musicxml [--midi out.mid]
完全ローカル処理(外部送信なし)。
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path


from earpipe.services.ear import (
    apply_postfilter,
    detect_events,
    detect_events_adaptive,
    detect_events_poly,
    select_events,
)
from earpipe.services.ear.tuning import correct_tuning_file
from earpipe.services.notate import (
    to_score,
    write_midi,
    write_midi_raw,
    write_musicxml,
    write_pdf,
    write_tab_pdf,
)
from earpipe.services.rhythm import (
    BPM_DEFAULT,
    GRID_PER_BEAT,
    estimate_grid,
    estimate_tempo_map,
    quantize_events,
)
from earpipe.services.stem import analyze_field, denoise, load_audio, trim_leading_silence_file


def transcribe_file(
    in_path: str | Path,
    out_musicxml: str | Path | None = None,
    out_midi: str | Path | None = None,
    out_pdf: str | Path | None = None,
    out_tab: str | Path | None = None,
    out_tab_plain: str | Path | None = None,
    engine: str = "mono",
    sensitivity: str = "auto",
    postfilter: bool = False,
    field_mode: bool = False,
    timing: str = "grid",
    title: str | None = None,
    chord_diagrams: bool = True,
) -> dict:
    """音声ファイルを採譜する。engine: mono(pYIN単音) / poly(basic-pitch多声)。

    poly の感度は密度適応 sensitivity="auto" が既定(Issue #54):
    normal/high両感度で検出し、high/normal検出数比≥2.3で「normalが取りこぼす
    高密度曲」と判定してhighを採用する(PD15曲で完全分離を実測)。
    normal/high の明示指定(#32)と #31(幽霊除去 postfilter)も選べる。postfilter の既定は False —
    PD15曲実測で倍音フィルタが本物のオクターブ重ねを誤除去し平均で逆効果だったため
    (bench_out/results_rhythm_configs.json)。合成ケースでは設計どおり動くため
    オプトインで残し、再設計の方向性は Issue #31 クローズコメントに記録。

    field_mode の制約(レビュー#40 M7): 降噪(denoise)が効くのは mono 経路のみ。
    poly は bp_worker がファイルパス入力のため降噪波形を渡せず、SNR適応の
    選択フィルタ(select_events)のみ適用される。降噪波形の一時ファイル経由は
    将来課題。
    戻り値: engine / n_events / n_notes / bpm / notes。
    """
    # 先頭無音トリム: 曲前の無音は楽譜の頭を休符にして精度を落とすため、
    # 音が鳴ったところから採譜する(ユーザー実証 2026-07-20: 0.67秒カットで精度向上)。
    # カットがあった場合のみ一時wavが作られ、本関数終了時に削除する。
    in_path_orig = in_path
    trimmed_path, trimmed_sec = trim_leading_silence_file(in_path)
    trim_tmp = trimmed_path if trimmed_path != Path(in_path_orig) else None

    # C1基準ピッチ補正(#55): A=440から8cents以上ずれていれば補正済み一時wavに差し替える
    # (in-tune入力は無補正パススルー)。一時ファイルは本関数終了時に削除する。
    # 削除対象は「補正で新規作成された一時ファイル」のみ。str/Path混在でも
    # 入力ファイル本体を誤って消さないよう、実体パスの一致で判定する(修正済みバグ)
    corrected_path, tuning_offset = correct_tuning_file(trimmed_path)
    tuned_tmp = corrected_path if corrected_path != trimmed_path else None
    in_path = corrected_path

    analysis = None
    y_loaded = None
    if field_mode:
        y_loaded, sr_loaded = load_audio(in_path)
        analysis = analyze_field(y_loaded, sr_loaded)

    adaptive_report = None
    if engine == "poly":
        if sensitivity == "auto":
            selection = detect_events_adaptive(in_path)
            events = selection.events
            adaptive_report = {
                "profile": selection.profile,
                "ratio": round(selection.ratio, 3) if selection.ratio != float("inf") else "inf",
                "n_normal": selection.n_normal,
                "n_high": selection.n_high,
            }
        else:
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

    # 曲名メタデータの貫通(#42): 未指定なら入力ファイル名を使う
    score = to_score(notes, bpm, title=title or Path(in_path).stem)
    if out_musicxml:
        write_musicxml(score, out_musicxml)  # 譜面は常に格子側(楽譜=量子化表現)
    if out_midi:
        # C3二重表現(Issue #38): MIDIエクスポートは grid(格子) / raw(実タイミング) を選択可能
        if timing == "raw":
            write_midi_raw(notes, out_midi, bpm=bpm)
        else:
            write_midi(score, out_midi)

    if tuned_tmp is not None:
        tuned_tmp.unlink(missing_ok=True)
    if trim_tmp is not None:
        trim_tmp.unlink(missing_ok=True)

    result = {
        "input": str(in_path_orig),
        "trimmed_leading_sec": round(trimmed_sec, 3),
        "tuning_offset_cents": round(tuning_offset, 1),
        "engine": engine,
        "n_events": len(events),
        "n_notes": len(notes),
        "bpm": bpm,
        "grid_per_beat": grid_per_beat,
        # C2区間別テンポ系列(#56): 分析出力として先行提供。記譜は単一テンポ格子
        # (区間別格子での記譜は将来課題。tempo_map.py docstring参照)
        "tempo_map": [
            [round(s.start_sec, 3), s.bpm] for s in estimate_tempo_map(events)
        ],
        "timing": timing,
        "notes": notes,
    }
    if adaptive_report is not None:
        result["adaptive"] = adaptive_report
    if analysis is not None:
        result["field_report"] = asdict(analysis.report)
    if out_pdf:
        if not out_musicxml:
            raise ValueError("--pdf にはMusicXML出力(-o)が必要")
        result["engrave"] = write_pdf(out_musicxml, out_pdf)
    if out_tab:
        # TAB譜出力プロファイル(NF-045)。五線譜と独立に生成できる
        result["tab"] = write_tab_pdf(
            notes, bpm, out_tab, title=title or Path(in_path_orig).stem,
            chord_diagrams=chord_diagrams,
        )
    if out_tab_plain:
        # 押さえ図なし版（コードネームのみ）。ビューアのトグル用に同時生成
        result["tab_plain"] = write_tab_pdf(
            notes, bpm, out_tab_plain, title=title or Path(in_path_orig).stem,
            chord_diagrams=False,
        )
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="earpipe — 採譜エンジン spike v0")
    sub = p.add_subparsers(dest="command", required=True)
    pt = sub.add_parser("transcribe", help="音声ファイルを五線譜MusicXMLに採譜")
    pt.add_argument("input", help="入力音声(wav/mp3等)")
    pt.add_argument("-o", "--output", help="MusicXML出力先(既定: 入力名.musicxml)")
    pt.add_argument("--midi", help="MIDI出力先(任意)")
    pt.add_argument("--pdf", help="五線譜PDF出力先(任意。ADR-004: Verovio)")
    pt.add_argument("--tab", help="ギターTAB譜PDF出力先(任意。6弦標準EADGBE・NF-045)")
    pt.add_argument("--tab-plain", dest="tab_plain", help="押さえ図なしTAB(コードネームのみ)の出力先(任意)")
    pt.add_argument(
        "--chord-diagrams", dest="chord_diagrams", action="store_true", default=True,
        help="TABのコード帯に押さえ図を表示(既定ON)",
    )
    pt.add_argument(
        "--no-chord-diagrams", dest="chord_diagrams", action="store_false",
        help="コード帯はコードネームのみ(押さえ図なし)",
    )
    pt.add_argument("--title", help="譜面タイトル(既定: 入力ファイル名)")
    pt.add_argument(
        "--field-mode", action="store_true",
        help="フィールド録音モード(C8): SNR適応の選択的抽出+非音程成分の分類報告",
    )
    pt.add_argument(
        "--engine", choices=("mono", "poly"), default="mono",
        help="mono=pYIN単音(既定) / poly=basic-pitch多声",
    )
    pt.add_argument(
        "--sensitivity", choices=("auto", "normal", "high"), default="auto",
        help="poly検出感度。auto=密度適応の自動選択(既定・#54) / high=弱音を拾う低閾値(#32)",
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
        out_tab=args.tab,
        out_tab_plain=args.tab_plain,
        chord_diagrams=args.chord_diagrams,
        engine=args.engine,
        sensitivity=args.sensitivity,
        postfilter=args.postfilter,
        field_mode=args.field_mode,
        timing=args.timing,
        title=args.title,
    )
    summary = {k: v for k, v in result.items() if k != "notes"}
    summary["output"] = out
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
