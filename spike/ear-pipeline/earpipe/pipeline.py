"""パイプライン統括とCLI: 音声ファイル → 耳 → 量子化 → 五線譜MusicXML/MIDI。

使い方: pipeline.py transcribe input.wav -o out.musicxml [--midi out.mid]
完全ローカル処理(外部送信なし)。
"""

import argparse
import json
import sys
import shutil
import tempfile
from dataclasses import asdict, replace
from pathlib import Path


from earpipe.services.ear import (
    apply_postfilter,
    bp_python_path,
    choose_engine,
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
from earpipe.services.emitters import (
    EmitContext,
    default_emit_path,
    emit as run_emit,
    emitter_keys,
)
from earpipe.services.notate.analysis_dispatch import (
    AnalysisContext,
    default_analysis_path,
    dispatch_analysis,
)
from earpipe.services.notate.score_diff import diff_notes
from earpipe.services.quality.client import run_compare
from earpipe.services.rights import rights_notice, rights_summary
from earpipe.services.stem.chunk import split_into_chunks
from earpipe.services.notate.dispatch import (
    DispatchContext,
    default_out_path,
    dispatch_format,
)
from earpipe.services.rhythm import (
    BPM_DEFAULT,
    GRID_PER_BEAT,
    anchor_to_zero,
    estimate_grid,
    estimate_tempo_map,
    quantize_events,
)
from earpipe.services.stem import (
    MELODIC_STEMS,
    STEMS,
    analyze_field,
    denoise,
    load_audio,
    separate_stems,
    trim_leading_silence_file,
)


def transcribe_file(
    in_path: str | Path,
    out_musicxml: str | Path | None = None,
    out_midi: str | Path | None = None,
    out_pdf: str | Path | None = None,
    out_tab: str | Path | None = None,
    out_tab_plain: str | Path | None = None,
    engine: str = "auto",
    sensitivity: str = "auto",
    postfilter: bool = False,
    field_mode: bool = False,
    timing: str = "grid",
    title: str | None = None,
    chord_diagrams: bool = True,
    tab_monophonic: bool = False,
    stem: str | None = None,
    formats: list[tuple[str, str]] | None = None,
    analyses: list[tuple[str, str]] | None = None,
    emits: list[tuple[str, str, dict]] | None = None,
) -> dict:
    """音声ファイルを採譜する。engine: auto(既定・#64) / mono(pYIN単音) / poly(basic-pitch多声)。

    auto は音源のポリフォニーを推定して mono/poly を自動選択する(engine_select.choose_engine)。
    混合音源(伴奏あり)はpoly、純単旋律はmonoが選ばれる。poly不能な環境ではmonoへ正直に退避。

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
    in_path_orig = in_path

    # ステム分離(F-003): --stem 指定時は先に音源を4ステム分離し、指定ステムだけを
    # 以降の採譜対象にする(楽器毎に分けて譜面化するユーザー要望)。分離は重い前処理で
    # アーティファクトが採譜を悪化させうるためオプトイン(先行リサーチの反映)。
    # 分離wavは一時ディレクトリに出力し、本関数終了時に片付ける。
    stem_tmp_dir = None
    stem_used = None
    if stem is not None:
        if stem not in STEMS:
            raise ValueError(f"--stem は {STEMS} のいずれか(指定: {stem!r})")
        stem_tmp_dir = Path(tempfile.mkdtemp(prefix="earpipe_stem_"))
        result_sep = separate_stems(in_path, stem_tmp_dir)
        if stem not in result_sep.stems:
            raise ValueError(f"ステム {stem!r} が分離結果に存在しません")
        in_path = result_sep.stems[stem]
        stem_used = stem

    # 先頭無音トリム: 曲前の無音は楽譜の頭を休符にして精度を落とすため、
    # 音が鳴ったところから採譜する(ユーザー実証 2026-07-20: 0.67秒カットで精度向上)。
    # カットがあった場合のみ一時wavが作られ、本関数終了時に削除する。
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

    # エンジン自動選択(#64): 混合音源はmono(pYIN単旋律)だとほぼ拾えず、純単旋律は
    # poly(basic-pitch)だとオクターブ倍音を誤検出する。音源のポリフォニーを推定して
    # 切り替える。先に安価なmono検出を回し、被覆率も判定材料にする。
    engine_choice = None
    resolved_engine = engine
    mono_events_cache = None
    if engine == "auto":
        if y_loaded is not None:
            y, sr = y_loaded, sr_loaded
        else:
            y, sr = load_audio(in_path)
        if field_mode:
            y = denoise(y, sr)
        mono_events_cache = detect_events(y, sr)
        engine_choice = choose_engine(
            y, sr, mono_events_cache, poly_available=bp_python_path() is not None
        )
        resolved_engine = engine_choice.engine

    adaptive_report = None
    if resolved_engine == "poly":
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
    elif mono_events_cache is not None:
        # auto選択でmonoに決まった場合は再検出せず流用する(二重検出回避)
        events = mono_events_cache
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
            events, bpm, mono=(resolved_engine == "mono"), grid_per_beat=grid_per_beat
        )
        # 記譜アンカー: フェードイン等でトリムが届かない残り無音が先頭休符に
        # ならないよう、最初の音符を0拍目に揃える(格子側のみ。実タイミング保持)
        notes, anchored_lead_beats = anchor_to_zero(notes)
    else:
        bpm = BPM_DEFAULT
        grid_per_beat = GRID_PER_BEAT
        notes = []
        anchored_lead_beats = 0.0

    # 曲名メタデータの貫通(#42): 未指定なら入力ファイル名を使う。
    # in_path はトリム/補正後の一時ファイルを指すため、必ず元入力名(in_path_orig)を使う
    # (バグ修正: 一時ファイル名 earpipe_xxxx_trimmed が譜面タイトルに漏れていた)
    base_title = title or Path(in_path_orig).stem
    # ステム分離時はどの楽器の譜面か分かるようステム名を併記する
    effective_title = f"{base_title} ({stem_used})" if stem_used else base_title
    score = to_score(notes, bpm, title=effective_title)
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
    if stem_tmp_dir is not None:
        shutil.rmtree(stem_tmp_dir, ignore_errors=True)

    result = {
        "input": str(in_path_orig),
        "stem": stem_used,
        "trimmed_leading_sec": round(trimmed_sec, 3),
        "anchored_lead_beats": round(anchored_lead_beats, 3),
        "tuning_offset_cents": round(tuning_offset, 1),
        "engine": resolved_engine,
        "engine_requested": engine,
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
    if engine_choice is not None:
        result["engine_select"] = {
            "engine": engine_choice.engine,
            "polyphony": engine_choice.polyphony,
            "mono_coverage": engine_choice.mono_coverage,
            "poly_available": engine_choice.poly_available,
            "fell_back": engine_choice.fell_back,
            "reason": engine_choice.reason,
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
            chord_diagrams=chord_diagrams, monophonic=tab_monophonic,
        )
    if out_tab_plain:
        # 押さえ図なし版（コードネームのみ）。ビューアのトグル用に同時生成
        result["tab_plain"] = write_tab_pdf(
            notes, bpm, out_tab_plain, title=title or Path(in_path_orig).stem,
            chord_diagrams=False,
        )

    # 出力形式ディスパッチ(#109): FORMAT_REGISTRY 登録の非レガシー形式
    # (簡譜/リードシート/GP5/UST/ABC/LilyPond)を --format 経由で生成する。
    # 五線譜/MIDI/PDF/TAB は上の専用オプションが担うため対象外。
    if formats:
        ctx = DispatchContext(
            notes=notes,
            bpm=bpm,
            title=effective_title,
            musicxml_path=Path(out_musicxml) if out_musicxml else None,
        )
        outputs = []
        for key, fmt_out in formats:
            path, meta = dispatch_format(key, ctx, fmt_out)
            outputs.append(
                {
                    "key": key,
                    "path": str(path),
                    "lossy": meta.lossy,
                    "lossy_note": meta.lossy_note,  # F-104: lossy を隠さない
                }
            )
        result["formats"] = outputs

    # 解析テキスト出力ディスパッチ(#109 B-2a): 移動ド(F-100)/ローマ数字度数・
    # ナッシュビル(F-091)は登録簿の「形式」ではなく採譜結果の派生注釈。--analysis 経由。
    if analyses:
        actx = AnalysisContext(notes=notes, bpm=bpm)
        analysis_outputs = []
        for key, ana_out in analyses:
            path = dispatch_analysis(key, actx, ana_out)
            analysis_outputs.append({"key": key, "path": str(path)})
        result["analyses"] = analysis_outputs

    # 汎用エミッタ(#109 B-2): 孤立実装済み機能をオプトインで副次出力する。
    # 既定の五線譜/MIDI/PDF/TAB 出力は変えない(既存挙動不変)。
    if emits:
        ectx = EmitContext(
            notes=notes,
            bpm=bpm,
            title=effective_title,
            musicxml_path=Path(out_musicxml) if out_musicxml else None,
            audio_path=Path(in_path),
        )
        emit_outputs = []
        for key, emit_out, params in emits:
            ctx_with_params = replace(ectx, params=params)
            path = run_emit(key, ctx_with_params, emit_out)
            emit_outputs.append({"key": key, "path": str(path)})
        result["emits"] = emit_outputs

    return result


def _parse_format_specs(
    specs: list[str] | None, input_path: str
) -> list[tuple[str, str]] | None:
    """``["jianpu=out.txt", "abc"]`` を ``[(key, out_path), ...]`` に解決する。

    ``KEY=PATH`` 形式でパスを明示でき、省略時は登録簿の拡張子から既定パスを組む。
    """
    if not specs:
        return None
    parsed: list[tuple[str, str]] = []
    for spec in specs:
        key, sep, path = spec.partition("=")
        key = key.strip()
        out_path = path.strip() if sep else default_out_path(key, input_path)
        parsed.append((key, out_path))
    return parsed


def _parse_analysis_specs(
    specs: list[str] | None, input_path: str
) -> list[tuple[str, str]] | None:
    """``["movable_do=out.txt", "roman"]`` を ``[(key, out_path), ...]`` に解決する。

    ``KEY=PATH`` でパスを明示でき、省略時は '入力名.KEY.txt' を組む。
    """
    if not specs:
        return None
    parsed: list[tuple[str, str]] = []
    for spec in specs:
        key, sep, path = spec.partition("=")
        key = key.strip()
        out_path = path.strip() if sep else default_analysis_path(key, input_path)
        parsed.append((key, out_path))
    return parsed


def _parse_emit_specs(
    specs: list[str] | None, input_path: str
) -> list[tuple[str, str, dict]] | None:
    """``["simplify=out.xml#level=0.7", "validate"]`` を ``[(key, path, params), ...]`` に解決。

    文法: ``KEY[=PATH][#k=v,k=v]``。PATH 省略時は '入力名.KEY.拡張子'、
    ``#`` 以降はエミッタ固有パラメータ(カンマ区切りの k=v)。
    """
    if not specs:
        return None
    parsed: list[tuple[str, str, dict]] = []
    for spec in specs:
        head, sep_p, param_str = spec.partition("#")
        params: dict[str, str] = {}
        if sep_p:
            for kv in param_str.split(","):
                if not kv.strip():
                    continue
                pk, _, pv = kv.partition("=")
                params[pk.strip()] = pv.strip()
        key, sep, path = head.partition("=")
        key = key.strip()
        out_path = path.strip() if sep else default_emit_path(key, input_path)
        parsed.append((key, out_path, params))
    return parsed


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
        "--tab-mono", dest="tab_mono", action="store_true",
        help="TAB譜を各拍の主旋律1音に絞る(多声ステム抽出時に演奏可能な単音TABにする)",
    )
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
        "--engine", choices=("auto", "mono", "poly"), default="auto",
        help="auto=音源のポリフォニー推定でmono/poly自動選択(既定・#64) / "
             "mono=pYIN単音 / poly=basic-pitch多声",
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
    pt.add_argument(
        "--stem", choices=STEMS, default=None,
        help="ステム分離(F-003)して指定楽器だけを採譜(vocals/drums/bass/other・要Demucs)",
    )
    pt.add_argument(
        "--format", dest="formats", action="append", metavar="KEY[=PATH]", default=None,
        help="追加の出力形式(F-104 FORMAT_REGISTRY・複数指定可)。例: --format jianpu=out.txt。"
             "PATH省略時は '入力名.KEY.拡張子'。対応: jianpu/leadsheet/ust/abc/lilypond",
    )
    pt.add_argument(
        "--analysis", dest="analyses", action="append", metavar="KEY[=PATH]", default=None,
        help="解析テキスト出力(F-091/F-100・複数指定可)。例: --analysis movable_do。"
             "PATH省略時は '入力名.KEY.txt'。対応: movable_do/roman/nashville",
    )
    pt.add_argument(
        "--emit", dest="emits", action="append", metavar="KEY[=PATH][#k=v]", default=None,
        help="孤立実装済み機能のオプトイン副次出力(#109 B-2・複数指定可)。"
             "例: --emit validate / --emit simplify#level=0.7。既定の記譜出力は不変。"
             f"対応: {'/'.join(emitter_keys())}",
    )

    # 楽器毎に分けて譜面化(F-003): 1回の分離で旋律ステム各々を別々の譜面にする
    ps = sub.add_parser("separate-transcribe", help="ステム分離して楽器毎に別々の譜面を生成")
    ps.add_argument("input", help="入力音声(wav/mp3等)")
    ps.add_argument("--out-dir", required=True, help="ステム別の譜面出力先ディレクトリ")
    ps.add_argument("--title", help="譜面タイトル(既定: 入力ファイル名+ステム名)")
    ps.add_argument(
        "--include-drums", action="store_true",
        help="drums(非音程)も採譜対象に含める(既定: 旋律ステムのみ)",
    )

    # 長尺音源の分割(F-004): 無音優先で max-sec を超えないチャンクへ
    pc = sub.add_parser("chunk", help="長尺音源を無音優先で複数wavに分割(F-004)")
    pc.add_argument("input", help="入力音声(wav/mp3等)")
    pc.add_argument("--out-dir", required=True, help="チャンクwavの出力先ディレクトリ")
    pc.add_argument("--max-sec", type=float, default=600.0, help="1チャンクの最大秒(既定600)")

    # 譜面差分(2つの採譜結果の意味論的差分): A/B の音源を採譜して音符列を比較
    pd = sub.add_parser("diff", help="2音源を採譜して音符列の意味論的差分を出力")
    pd.add_argument("a", help="基準側の音源(例: 正解/旧版)")
    pd.add_argument("b", help="比較側の音源(例: 採譜結果/新版)")
    pd.add_argument("-o", "--out", help="差分JSONの出力先(既定: 標準出力)")
    pd.add_argument("--engine", choices=("auto", "mono", "poly"), default="auto", help="採譜エンジン")

    # AIの耳による比較評価(外部ツール ai-ears/ears.py compare を起動)
    pcmp = sub.add_parser("compare", help="AIの耳(ai-ears)で原音とtranscriptionを比較評価")
    pcmp.add_argument("original", help="原音(参照)")
    pcmp.add_argument("transcription", help="採譜結果(MusicXML/MIDI等)")
    pcmp.add_argument("--report", help="評価レポートの出力先(任意)")

    # 権利ガイダンス表示(F-073): 採譜物の配布/販売前の著作権注意を教育的に示す
    sub.add_parser("rights", help="採譜物の権利ガイダンス(配布/販売前の著作権注意)を表示")

    # マイク/ライン録音入力(F-005): 録音してwav保存、任意でそのまま採譜(要 sounddevice)
    pr = sub.add_parser("record", help="マイク/ラインから録音してwav保存(任意で採譜・要sounddevice)")
    pr.add_argument("--out", required=True, help="録音wavの出力先")
    pr.add_argument("--seconds", type=float, default=10.0, help="録音秒数(既定10)")
    pr.add_argument("--samplerate", type=int, default=44100, help="サンプルレート(既定44100)")
    pr.add_argument("--transcribe", action="store_true", help="録音後そのまま採譜する")

    args = p.parse_args(argv)

    if args.command == "separate-transcribe":
        return _run_separate_transcribe(args)
    if args.command == "chunk":
        return _run_chunk(args)
    if args.command == "diff":
        return _run_diff(args)
    if args.command == "compare":
        return _run_compare(args)
    if args.command == "rights":
        print(rights_notice())
        return 0
    if args.command == "record":
        return _run_record(args)

    out = args.output or str(Path(args.input).with_suffix(".musicxml"))
    formats = _parse_format_specs(args.formats, args.input)
    analyses = _parse_analysis_specs(args.analyses, args.input)
    emits = _parse_emit_specs(args.emits, args.input)
    result = transcribe_file(
        args.input,
        out_musicxml=out,
        out_midi=args.midi,
        out_pdf=args.pdf,
        out_tab=args.tab,
        out_tab_plain=args.tab_plain,
        chord_diagrams=args.chord_diagrams,
        tab_monophonic=args.tab_mono,
        engine=args.engine,
        sensitivity=args.sensitivity,
        postfilter=args.postfilter,
        field_mode=args.field_mode,
        timing=args.timing,
        title=args.title,
        stem=args.stem,
        formats=formats,
        analyses=analyses,
        emits=emits,
    )
    summary = {k: v for k, v in result.items() if k != "notes"}
    summary["output"] = out
    summary["rights"] = rights_summary()  # F-073: 権利注意を成果物に添える
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _run_separate_transcribe(args) -> int:
    """楽器毎に分けて譜面化(F-003): 分離は1回だけ行い、各旋律ステムを別譜面に採譜。"""
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.title or Path(args.input).stem

    stem_dir = Path(tempfile.mkdtemp(prefix="earpipe_sep_"))
    try:
        sep = separate_stems(args.input, stem_dir)
        targets = STEMS if args.include_drums else MELODIC_STEMS
        per_stem = []
        for name in targets:
            if name not in sep.stems:
                continue
            out_xml = out_dir / f"{base}_{name}.musicxml"
            out_pdf = out_dir / f"{base}_{name}.pdf"
            # 分離済みwavを直接採譜する(stem=Noneで二重分離を避ける)。
            # drumsは非音程なので音程の正しさは保証されない(正直な注記)。
            r = transcribe_file(
                sep.stems[name], out_musicxml=out_xml, out_pdf=out_pdf,
                title=f"{base} ({name})",
            )
            per_stem.append(
                {"stem": name, "n_notes": r["n_notes"],
                 "engine": r["engine"], "output": str(out_xml)}
            )
    finally:
        shutil.rmtree(stem_dir, ignore_errors=True)

    print(json.dumps({"input": args.input, "out_dir": str(out_dir),
                      "model": sep.model, "stems": per_stem},
                     ensure_ascii=False, indent=2))
    return 0


def _run_chunk(args) -> int:
    """長尺音源分割(F-004): 無音優先で max-sec を超えないチャンク wav を書き出す。"""
    import soundfile as sf

    y, sr = load_audio(args.input)
    chunks = split_into_chunks(y, sr, max_sec=args.max_sec)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ch in chunks:
        path = out_dir / f"chunk_{ch.index:03d}.wav"
        sf.write(str(path), ch.samples, int(sr))
        written.append({"index": ch.index, "path": str(path),
                        "start_sec": round(ch.start_sec, 3), "end_sec": round(ch.end_sec, 3)})
    print(json.dumps({"input": args.input, "out_dir": str(out_dir),
                      "n_chunks": len(written), "chunks": written},
                     ensure_ascii=False, indent=2))
    return 0


def _run_diff(args) -> int:
    """譜面差分: A/B 両音源を採譜し、音符列の意味論的差分(diff_notes)を出力する。"""
    ra = transcribe_file(args.a, engine=args.engine)
    rb = transcribe_file(args.b, engine=args.engine)
    diffs = diff_notes(ra["notes"], rb["notes"])
    payload = {"a": args.a, "b": args.b, "diff_count": len(diffs), "diffs": diffs}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def _run_compare(args) -> int:
    """AIの耳(外部 ai-ears)で比較評価を実行し、その出力と終了コードを中継する。"""
    proc = run_compare(args.original, args.transcription, args.report)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


def _record_audio(seconds: float, samplerate: int):
    """マイク/ラインから seconds 秒を録音し mono 波形(np.ndarray)を返す(F-005)。

    sounddevice は任意依存(ハードウェア必須でCI不可)。未導入時は導入方法を示して
    RuntimeError を送出する(黙って失敗しない)。
    """
    try:
        import sounddevice as sd
    except ImportError as e:  # 任意依存
        raise RuntimeError(
            "マイク録音には sounddevice が必要です: `pip install sounddevice`"
            "(PortAudio が要る場合あり)。録音済みファイルなら `transcribe` を使ってください。"
        ) from e
    frames = int(float(seconds) * int(samplerate))
    audio = sd.rec(frames, samplerate=int(samplerate), channels=1, dtype="float32")
    sd.wait()
    return audio.reshape(-1)


def _run_record(args) -> int:
    """マイク/ライン録音入力(F-005): 録音してwav保存、任意でそのまま採譜する。"""
    import soundfile as sf

    try:
        audio = _record_audio(args.seconds, args.samplerate)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    sf.write(args.out, audio, int(args.samplerate))
    result = {"out": args.out, "seconds": args.seconds, "samplerate": args.samplerate}
    if args.transcribe:
        out_xml = str(Path(args.out).with_suffix(".musicxml"))
        r = transcribe_file(args.out, out_musicxml=out_xml)
        result["transcribed"] = {"n_notes": r["n_notes"], "output": out_xml}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
