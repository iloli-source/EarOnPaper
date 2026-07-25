"""Guitar-TECHS実測ベンチ(#114/#144): 真値MIDI付き実ギター録音でnote F1を計測。

Guitar-TECHS (CC BY 4.0・Zenodo 14963133) のchords系サブセットを使い、
DI(ライン直) と micamp(アンプマイク=歪み実録) の両系統で現行エンジンの
noteレベルF1(onset±50/±100ms・音高一致・貪欲1対1=bench_pd.note_f1と同手順)を測る。

夢見るベンチ(単曲・配列指標)を補完する多曲・時間ベースの正解付きベンチ。
データはgitignore配下(usertest/input/guitar-techs/)・無ければskip。

使い方:
    .venv/bin/python usertest/gt_bench_gtechs.py --limit 6   # サンプル
    .venv/bin/python usertest/gt_bench_gtechs.py             # 全曲
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

USERTEST = Path(__file__).resolve().parent
SPIKE = USERTEST.parent
sys.path.insert(0, str(SPIKE))
sys.path.insert(0, str(SPIKE / "bench"))
VENV_PY = SPIKE / ".venv" / "bin" / "python"
IN_DIR = USERTEST / "input" / "guitar-techs"
OUT_DIR = USERTEST / "output" / "guitar-techs"
TRS_TIMEOUT = 1800


def _midi_truth(mid_path: Path) -> list[tuple[float, float, int]]:
    """真値MIDI → (onset秒, offset秒, midi) 列。"""
    import mido

    m = mido.MidiFile(str(mid_path))
    tempo_us = 500000
    for tr in m.tracks:
        for msg in tr:
            if msg.type == "set_tempo":
                tempo_us = msg.tempo
                break
    spb = tempo_us / 1e6 / m.ticks_per_beat
    out = []
    for tr in m.tracks:
        t = 0
        on: dict[int, int] = {}
        for msg in tr:
            t += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                on[msg.note] = t
            elif msg.type in ("note_off", "note_on") and msg.note in on:
                s = on.pop(msg.note)
                out.append((s * spb, t * spb, msg.note))
    return sorted(out)


def _transcribe(wav: Path, out_dir: Path, force: bool) -> list[tuple[float, float, int]] | None:
    meta = out_dir / "notes.json"
    if meta.exists() and not force:
        return [tuple(x) for x in json.loads(meta.read_text())]
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(wav),
         "-o", str(out_dir / "out.musicxml"), "--midi", str(out_dir / "out.mid"),
         "--engine", "auto", "--timing", "raw"],
        capture_output=True, text=True, timeout=TRS_TIMEOUT,
    )
    if r.returncode != 0:
        print(f"[fail] {wav.name}: {r.stderr[-200:]}")
        return None
    notes = _midi_truth(out_dir / "out.mid")
    meta.write_text(json.dumps(notes))
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--subset", default="P1_chords")
    args = ap.parse_args()

    base = IN_DIR / args.subset / args.subset
    if not base.exists():
        print("[skip] Guitar-TECHSデータなし(ローカル専用)")
        return 0
    from bench_pd import note_f1  # 既存の採点手順を再利用(±tol・貪欲1対1)

    pieces = sorted(p.stem.replace("midi_", "") for p in (base / "midi").glob("*.mid"))
    if args.limit:
        pieces = pieces[: args.limit]
    rows = []
    for name in pieces:
        truth = _midi_truth(base / "midi" / f"midi_{name}.mid")
        for variant in ("directinput", "micamp"):
            wav = base / "audio" / variant / f"{variant}_{name}.wav"
            if not wav.exists():
                continue
            est = _transcribe(wav, OUT_DIR / args.subset / name / variant, args.force)
            if est is None:
                continue
            f1_100, p100, r100 = note_f1(truth, est, tol=0.1)
            f1_50, _, _ = note_f1(truth, est, tol=0.05)
            rows.append({"piece": name, "variant": variant, "n_truth": len(truth),
                         "n_est": len(est), "f1_100": round(f1_100, 3),
                         "p_100": round(p100, 3), "r_100": round(r100, 3),
                         "f1_50": round(f1_50, 3)})
            print(f"{name}/{variant}: F1@100ms={f1_100:.3f} P={p100:.3f} R={r100:.3f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Guitar-TECHS実測ベンチ (#114/#144)", "",
             "| piece | variant | 真値音数 | 検出 | F1@100ms | P | R | F1@50ms |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['piece']} | {r['variant']} | {r['n_truth']} | {r['n_est']} "
                     f"| {r['f1_100']} | {r['p_100']} | {r['r_100']} | {r['f1_50']} |")
    if rows:
        import statistics
        for v in ("directinput", "micamp"):
            vs = [r["f1_100"] for r in rows if r["variant"] == v]
            if vs:
                lines.append(f"\n**{v} 平均F1@100ms: {statistics.mean(vs):.3f}** (n={len(vs)})")
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"\n→ {OUT_DIR / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
