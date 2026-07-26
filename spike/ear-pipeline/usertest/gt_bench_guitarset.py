"""GuitarSet正解ベンチ(#147): 弦別ヘキサフォニック注釈を正解とする第4のGT群。

ユーザー発案「弦の単音ずつ拾う」の検証手段化。GuitarSet(Zenodo 3371780)は
弦ごとのピックアップで録音され、6弦それぞれのnote_midi注釈(=ほぼ完全な正解)を持つ。
comping(伴奏=和音中心)スタイルから決定論的に選んだサブセットで、
既存evaluate(LCS音高列F1+縦積み再現率)を計測する。

データはローカルのみ(gitignore配下)。無ければskip。
使い方:
    .venv/bin/python usertest/gt_bench_guitarset.py            # キャッシュ利用
    .venv/bin/python usertest/gt_bench_guitarset.py --force    # 採譜やり直し
    .venv/bin/python usertest/gt_bench_guitarset.py -n 4       # 曲数制限(スモーク)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gt_bench_yume as gb  # evaluate/lcs/_midi_notes を再利用

USERTEST = Path(__file__).resolve().parent
SPIKE = USERTEST.parent
VENV_PY = SPIKE / ".venv" / "bin" / "python"
GS_DIR = USERTEST / "input" / "guitarset"
OUT_DIR = USERTEST / "output" / "guitarset"
TRS_TIMEOUT = 1800
ONSET_CLUSTER_SEC = 0.05  # 同一ストロークとみなす弦間オンセット差(ヘキサ実測は数ms)

# 決定論的サブセット: 各スタイルの若番2曲(comp) — 和音中心のcompingのみ
STYLES = ("BN", "Funk", "Jazz", "Rock", "SS")
SONGS_PER_STYLE = 2


def pick_songs() -> list[str]:
    jams = sorted(p.stem for p in (GS_DIR / "annotation").glob("*_comp.jams"))
    picked = []
    for st in STYLES:
        hits = [s for s in jams if f"_{st}" in s]
        picked += hits[:SONGS_PER_STYLE]
    return picked


def jams_to_ref(jams_path: Path) -> dict:
    """弦別note_midi(6本)を統合し、オンセット群化でevents/chords形式の参照を作る。"""
    d = json.loads(jams_path.read_text())
    notes = []
    for a in d["annotations"]:
        if a["namespace"] != "note_midi":
            continue
        for n in a["data"]:
            notes.append((float(n["time"]), int(round(float(n["value"])))))
    notes.sort()
    clusters: list[list] = []
    for t, m in notes:
        if clusters and t - clusters[-1][0][0] < ONSET_CLUSTER_SEC:
            clusters[-1].append((t, m))
        else:
            clusters.append([(t, m)])
    chords: dict[str, dict] = {}
    events = []
    for c in clusters:
        mids = sorted({m for _, m in c})
        name = "-".join(map(str, mids))
        chords.setdefault(name, {"midis": mids})
        events.append({"beat": round(c[0][0], 3), "chord": name})
    return {"scope": f"GuitarSet {jams_path.stem} (弦別注釈全曲)",
            "chords": chords, "events": events}


def transcribe(song: str, force: bool) -> dict | None:
    audio = GS_DIR / "audio" / f"{song}_mic.wav"
    if not audio.exists():
        return None
    tdir = OUT_DIR / song
    meta = tdir / "transcribe.json"
    if meta.exists() and not force:
        return json.loads(meta.read_text())
    tdir.mkdir(parents=True, exist_ok=True)
    cmd = [str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(audio),
           "-o", str(tdir / "out.musicxml"), "--midi", str(tdir / "out.mid"),
           "--tab", str(tdir / "out_tab.pdf"), "--engine", "auto", "--title", song,
           # #147剪定前提(a): confidence/実オンセット込みノート列を機械可読で残す
           "--emit", f"notesjson={tdir / 'notes.json'}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=TRS_TIMEOUT)
    if r.returncode != 0:
        print(f"[fail] {song}: {r.stderr[-200:]}")
        return None
    payload = json.loads(r.stdout)
    slim = {k: payload[k] for k in ("engine", "bpm", "bpm_source", "n_notes") if k in payload}
    slim["notes"] = gb._midi_notes(tdir / "out.mid")
    meta.write_text(json.dumps(slim, ensure_ascii=False))
    return slim


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("-n", type=int, default=0, help="曲数制限(0=全サブセット)")
    args = ap.parse_args()

    if not (GS_DIR / "annotation").exists():
        print("[skip] GuitarSet注釈なし(ローカル専用: Zenodo 3371780からDL)")
        return 0
    songs = pick_songs()
    if args.n:
        songs = songs[: args.n]
    if not (GS_DIR / "audio").exists():
        print("[skip] GuitarSet音声なし(audio_mono-mic.zipを展開してください)")
        return 0

    rows = {}
    for song in songs:
        ref = jams_to_ref(GS_DIR / "annotation" / f"{song}.jams")
        trs = transcribe(song, args.force)
        if trs is None:
            continue
        res = gb.evaluate(ref, trs, gap_sec=0)  # 全曲が参照範囲(窓カット無効)
        rows[song] = res
        print(json.dumps({"song": song, **{k: res[k] for k in (
            "n_hyp_notes_window", "n_ref_notes", "matched", "stack_recall",
            "stack_events", "precision", "recall", "f1")}}, ensure_ascii=False))

    if rows:
        import statistics as st
        f1s = [r["f1"] for r in rows.values()]
        sts = [r["stack_recall"] for r in rows.values() if r["stack_recall"] is not None]
        print(f"\n== 集計(n={len(rows)}): F1 mean={st.mean(f1s):.3f} "
              f"/ 縦積み再現率 mean={st.mean(sts):.3f} ==")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
