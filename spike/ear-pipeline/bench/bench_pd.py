"""PD正解つきベンチ: 正解MIDI→音声レンダリング→採譜→正解と突合。

- 正解: score.logical-arts.jp の無料PD楽譜MIDI + ユーザー提供2曲
- 比較: BP素点(ear_poly生イベント) vs 自社spike(量子化+記譜)
- 指標: Note F1(音高一致+開始±tol) と ears.py 総合
- 各曲は先頭60秒に統一(長尺曲の実行時間対策。結果に明記)
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pretty_midi
import soundfile as sf

from earpipe.ear_poly import detect_events_poly
from earpipe.pipeline import transcribe_file

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tools" / "ai-ears" / "testdata" / "pd-corpus"
OUT = CORPUS / "bench_out"
EARS_PY = ROOT / "tools" / "ai-ears" / "ears.py"
EARS_VENV = ROOT / "tools" / "ai-ears" / ".venv" / "bin" / "python"
CLIP_SEC = 60.0
SR = 22050

SONGS = [
    ("user-samples/Turkish_March_K331_C-Am", "trk_march", "ユーザー提供・高速+和音"),
    ("user-samples/Romanze_Castellana_G-Em", "romanze", "ユーザー提供"),
    ("furusato", "furusato", "民謡"),
    ("sakura", "sakura", "民謡"),
    ("kojo_no_tsuki", "kojo", "民謡伴奏"),
    ("hamabe_no_uta", "hamabe", "民謡伴奏"),
    ("hana", "hana", "民謡伴奏"),
    ("fur_elise", "elise", "和音中"),
    ("gymnopedie1", "gym1", "和音ゆっくり"),
    ("traumerei", "traum", "和音中"),
    ("moonlight_1st", "moon1", "和音厚"),
    ("chopin_prelude7", "prel7", "和音短"),
    ("gnossienne1", "gnoss1", "拍子自由"),
    ("minute_waltz", "waltz", "高速"),
    ("promenade", "prom", "変拍子"),
]


def clip_midi(pm: pretty_midi.PrettyMIDI, sec: float) -> list[tuple[float, float, int]]:
    notes = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            if n.start < sec:
                notes.append((n.start, min(n.end, sec), n.pitch))
    return sorted(notes)


def render(pm: pretty_midi.PrettyMIDI, sec: float, dest: Path):
    audio = pm.synthesize(fs=SR)
    audio = audio[: int(sec * SR)]
    peak = np.max(np.abs(audio)) or 1.0
    sf.write(dest, audio / peak * 0.9, SR)


def note_f1(gt: list, pred: list, tol: float) -> tuple[float, float, float]:
    used = set()
    tp = 0
    for s, _e, p in pred:
        best, best_d = None, tol
        for i, (gs, _ge, gp) in enumerate(gt):
            if i in used or gp != p:
                continue
            d = abs(gs - s)
            if d <= best_d:
                best, best_d = i, d
        if best is not None:
            used.add(best)
            tp += 1
    prec = tp / len(pred) if pred else 0.0
    rec = tp / len(gt) if gt else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return f1, prec, rec


def midi_notes(path: Path) -> list:
    pm = pretty_midi.PrettyMIDI(str(path))
    return clip_midi(pm, CLIP_SEC)


def events_to_midi(events, dest: Path):
    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=0)
    for ev in events:
        inst.notes.append(pretty_midi.Note(velocity=80, pitch=int(ev.midi), start=float(ev.onset), end=float(max(ev.offset, ev.onset + 0.05))))
    pm.instruments.append(inst)
    pm.write(str(dest))


def ears_total(original: Path, transcription: Path) -> float | None:
    try:
        r = subprocess.run(
            [str(EARS_VENV), str(EARS_PY), "compare", "--original", str(original), "--transcription", str(transcription), "--json"],
            capture_output=True, text=True, timeout=600,
        )
        data = json.loads(r.stdout)
        return data.get("total") or data.get("総合")
    except Exception:
        return None


def main():
    OUT.mkdir(exist_ok=True)
    rows = []
    for rel, slug, cat in SONGS:
        gt_path = CORPUS / f"{rel}.mid"
        if not gt_path.exists():
            rows.append({"slug": slug, "status": "GT missing"})
            continue
        try:
            pm = pretty_midi.PrettyMIDI(str(gt_path))
            gt = clip_midi(pm, CLIP_SEC)
            wav = OUT / f"{slug}.wav"
            render(pm, CLIP_SEC, wav)

            # BP素点
            raw_events = [e for e in detect_events_poly(wav) if e.onset < CLIP_SEC]
            bp_mid = OUT / f"{slug}_bp.mid"
            events_to_midi(raw_events, bp_mid)
            bp = midi_notes(bp_mid)

            # 自社spike
            spike_mid = OUT / f"{slug}_spike.mid"
            transcribe_file(wav, out_midi=spike_mid, engine="poly")
            sp = midi_notes(spike_mid)

            row = {"slug": slug, "cat": cat, "gt_notes": len(gt), "status": "ok"}
            for name, pred in (("bp", bp), ("spike", sp)):
                f1a, pa, ra = note_f1(gt, pred, 0.1)
                f1b, _, _ = note_f1(gt, pred, 0.2)
                row[f"{name}_n"] = len(pred)
                row[f"{name}_f1_100ms"] = round(f1a, 3)
                row[f"{name}_p"] = round(pa, 3)
                row[f"{name}_r"] = round(ra, 3)
                row[f"{name}_f1_200ms"] = round(f1b, 3)
            row["bp_ears"] = ears_total(wav, bp_mid)
            row["spike_ears"] = ears_total(wav, spike_mid)
            rows.append(row)
            print(f"{slug}: gt={len(gt)} bp_f1={row['bp_f1_100ms']} spike_f1={row['spike_f1_100ms']}")
        except Exception as e:
            rows.append({"slug": slug, "status": f"FAIL {type(e).__name__}: {e}"})
            print(f"{slug}: FAIL {e}")
    (OUT / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("saved results.json")


_MODES = {"--score-rhythm", "--rhythm-configs", "--dual-timing"}
if __name__ == "__main__" and not (_MODES & set(sys.argv)):
    main()


def main_score_rhythm():
    """キャッシュ済み bench_out の出力に対して楽譜レベルKPI(score_rhythm)を再評価する。

    使い方: python bench_pd.py --score-rhythm  (要: 既存の bench_out/*.mid)
    """
    sys.path.insert(0, str(ROOT / "tools" / "ai-ears"))
    from score_metrics import score_rhythm_paths

    rows = []
    for rel, slug, cat in SONGS:
        gt_path = CORPUS / f"{rel}.mid"
        bp_mid = OUT / f"{slug}_bp.mid"
        spike_mid = OUT / f"{slug}_spike.mid"
        if not (gt_path.exists() and bp_mid.exists() and spike_mid.exists()):
            rows.append({"slug": slug, "cat": cat, "status": "cache missing"})
            continue
        bp = score_rhythm_paths(gt_path, bp_mid)
        sp = score_rhythm_paths(gt_path, spike_mid)
        rows.append({
            "slug": slug, "cat": cat, "status": "ok",
            "bp_total": bp["total"], "bp_f1": bp["beat_f1"], "bp_dur": bp["dur_agreement"],
            "sp_total": sp["total"], "sp_f1": sp["beat_f1"], "sp_dur": sp["dur_agreement"],
            "delta": round(sp["total"] - bp["total"], 4),
        })
    ok = [r for r in rows if r["status"] == "ok"]
    if ok:
        avg_bp = sum(r["bp_total"] for r in ok) / len(ok)
        avg_sp = sum(r["sp_total"] for r in ok) / len(ok)
        wins = sum(1 for r in ok if r["delta"] > 0.005)
        ties = sum(1 for r in ok if abs(r["delta"]) <= 0.005)
        print(f"# score_rhythm 再評価 (n={len(ok)})")
        print(f"平均: BP素点={avg_bp:.3f} / 自社spike={avg_sp:.3f} / Δ={avg_sp-avg_bp:+.3f}")
        print(f"勝敗: spike改善 {wins} / 同点 {ties} / 劣後 {len(ok)-wins-ties}")
        print()
        print("| 曲 | 分類 | BP total(f1/dur) | spike total(f1/dur) | Δ |")
        print("|---|---|---|---|---|")
        for r in ok:
            print(f"| {r['slug']} | {r['cat']} | {r['bp_total']:.3f} ({r['bp_f1']:.2f}/{r['bp_dur']:.2f}) | {r['sp_total']:.3f} ({r['sp_f1']:.2f}/{r['sp_dur']:.2f}) | {r['delta']:+.3f} |")
    for r in rows:
        if r["status"] != "ok":
            print(f"| {r['slug']} | {r['cat']} | {r['status']} | | |")


if __name__ == "__main__" and "--score-rhythm" in sys.argv:
    main_score_rhythm()
    sys.exit(0)


def main_rhythm_configs():
    """#31/#32 の効果測定: 4構成の前後比較(正解基準)。

    構成: bp素点 / spike基本(量子化のみ) / +幽霊除去(#31) / +高感度(#32) / 両方
    指標: Note F1@100ms(正解MIDI基準) と score_rhythm(楽譜レベルKPI #33)
    使い方: python bench_pd.py --rhythm-configs
    """
    sys.path.insert(0, str(ROOT / "tools" / "ai-ears"))
    from score_metrics import score_rhythm_paths

    from earpipe.notate import to_score, write_midi
    from earpipe.postfilter import apply_postfilter
    from earpipe.quantize import BPM_DEFAULT, estimate_tempo, quantize_events

    def spike_midi_from(events, dest: Path):
        bpm = estimate_tempo(events) if events else BPM_DEFAULT
        notes = quantize_events(events, bpm, mono=False)
        write_midi(to_score(notes, bpm), dest)
        return dest

    configs = ["bp", "base", "ghost", "rescue", "both"]
    rows = []
    for rel, slug, cat in SONGS:
        gt_path = CORPUS / f"{rel}.mid"
        wav = OUT / f"{slug}.wav"
        if not (gt_path.exists() and wav.exists()):
            rows.append({"slug": slug, "cat": cat, "status": "cache missing"})
            continue
        try:
            gt = midi_notes(gt_path)
            normal = [e for e in detect_events_poly(wav) if e.onset < CLIP_SEC]
            high = [
                e for e in detect_events_poly(wav, sensitivity="high") if e.onset < CLIP_SEC
            ]
            variants = {
                "bp": None,  # 素点はイベントそのまま(量子化なし)
                "base": normal,
                "ghost": apply_postfilter(normal),
                "rescue": high,
                "both": apply_postfilter(high),
            }
            row = {"slug": slug, "cat": cat, "gt_notes": len(gt), "status": "ok"}
            for name in configs:
                mid = OUT / f"{slug}_cfg_{name}.mid"
                if name == "bp":
                    events_to_midi(normal, mid)
                else:
                    spike_midi_from(variants[name], mid)
                pred = midi_notes(mid)
                f1, p_, r_ = note_f1(gt, pred, 0.1)
                sr_ = score_rhythm_paths(gt_path, mid)
                row[f"{name}_f1"] = round(f1, 3)
                row[f"{name}_p"] = round(p_, 3)
                row[f"{name}_r"] = round(r_, 3)
                row[f"{name}_sr"] = sr_["total"]
            rows.append(row)
            print(
                f"{slug}: f1 bp={row['bp_f1']} base={row['base_f1']} ghost={row['ghost_f1']} "
                f"rescue={row['rescue_f1']} both={row['both_f1']}"
            )
        except Exception as e:  # 1曲の失敗で全体を止めない(失敗は正直に記録)
            rows.append({"slug": slug, "cat": cat, "status": f"FAIL {type(e).__name__}: {e}"})
            print(f"{slug}: FAIL {e}")

    ok = [r for r in rows if r["status"] == "ok"]
    if ok:
        print(f"\n# rhythm-configs 集計 (n={len(ok)})")
        print("| 構成 | F1@100ms平均 | precision平均 | recall平均 | score_rhythm平均 |")
        print("|---|---|---|---|---|")
        for name in configs:
            af1 = sum(r[f"{name}_f1"] for r in ok) / len(ok)
            ap = sum(r[f"{name}_p"] for r in ok) / len(ok)
            ar = sum(r[f"{name}_r"] for r in ok) / len(ok)
            asr = sum(r[f"{name}_sr"] for r in ok) / len(ok)
            print(f"| {name} | {af1:.3f} | {ap:.3f} | {ar:.3f} | {asr:.3f} |")
    (OUT / "results_rhythm_configs.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1)
    )
    print("saved results_rhythm_configs.json")


if __name__ == "__main__" and "--rhythm-configs" in sys.argv:
    main_rhythm_configs()
    sys.exit(0)


def main_dual_timing():
    """#38 C3二重表現の効果測定: 格子化ロスの解消を正解基準で確認する。

    比較(いずれも rescue=高感度・#32の推奨構成):
      bp   = 素点イベント(量子化なし)          … 上限参照
      grid = 従来経路(量子化→格子MIDI)        … 格子化ロスを含む
      raw  = 二重表現のraw側(実タイミングMIDI) … ロス解消の検証対象
    指標: F1@100ms(正解MIDI基準)。raw が bp と同等なら格子化ロスは解消。
    使い方: python bench_pd.py --dual-timing
    """
    sys.path.insert(0, str(ROOT / "tools" / "ai-ears"))
    from score_metrics import score_rhythm_paths

    from earpipe.services.notate import to_score, write_midi, write_midi_raw
    from earpipe.services.rhythm import BPM_DEFAULT, estimate_tempo, quantize_events

    rows = []
    for rel, slug, cat in SONGS:
        gt_path = CORPUS / f"{rel}.mid"
        wav = OUT / f"{slug}.wav"
        if not (gt_path.exists() and wav.exists()):
            rows.append({"slug": slug, "cat": cat, "status": "cache missing"})
            continue
        try:
            gt = midi_notes(gt_path)
            events = [
                e for e in detect_events_poly(wav, sensitivity="high") if e.onset < CLIP_SEC
            ]
            bpm = estimate_tempo(events) if events else BPM_DEFAULT
            notes = quantize_events(events, bpm, mono=False)

            bp_mid = OUT / f"{slug}_dual_bp.mid"
            events_to_midi(events, bp_mid)
            grid_mid = OUT / f"{slug}_dual_grid.mid"
            write_midi(to_score(notes, bpm), grid_mid)
            raw_mid = OUT / f"{slug}_dual_raw.mid"
            write_midi_raw(notes, raw_mid, bpm=bpm)

            row = {"slug": slug, "cat": cat, "gt_notes": len(gt), "status": "ok"}
            for name, mid in (("bp", bp_mid), ("grid", grid_mid), ("raw", raw_mid)):
                f1, p_, r_ = note_f1(gt, midi_notes(mid), 0.1)
                row[f"{name}_f1"] = round(f1, 3)
            # 格子側は楽譜レベルKPIも併記(同一出力から両指標が取れることの実証)
            row["grid_sr"] = score_rhythm_paths(gt_path, grid_mid)["total"]
            rows.append(row)
            print(f"{slug}: f1 bp={row['bp_f1']} grid={row['grid_f1']} raw={row['raw_f1']}")
        except Exception as e:
            rows.append({"slug": slug, "cat": cat, "status": f"FAIL {type(e).__name__}: {e}"})
            print(f"{slug}: FAIL {e}")

    ok = [r for r in rows if r["status"] == "ok"]
    if ok:
        print(f"\n# dual-timing 集計 (n={len(ok)})")
        print("| 表現 | F1@100ms平均 |")
        print("|---|---|")
        for name in ("bp", "grid", "raw"):
            print(f"| {name} | {sum(r[f'{name}_f1'] for r in ok) / len(ok):.3f} |")
        print(f"| grid score_rhythm平均 | {sum(r['grid_sr'] for r in ok) / len(ok):.3f} |")
    (OUT / "results_dual_timing.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1)
    )
    print("saved results_dual_timing.json")


if __name__ == "__main__" and "--dual-timing" in sys.argv:
    main_dual_timing()
    sys.exit(0)
