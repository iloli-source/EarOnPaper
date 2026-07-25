"""汎用: TAB表示つき演奏動画ベンチ (#144) — gt-<name>/audio.m4a + reference.json を評価。

夢見る(gt-yume)方式の正解付きベンチを任意の動画へ一般化する。分離なし直採譜
(ギター単体動画前提)・TAB成果物レベルの配列LCSでnote F1を計測。

使い方: .venv/bin/python usertest/gt_bench_tabvid.py gt-muzyx [--force]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

USERTEST = Path(__file__).resolve().parent
sys.path.insert(0, str(USERTEST))
sys.path.insert(0, str(USERTEST.parent))
import gt_bench_yume as gb  # evaluate/LCS/成果物レベル変換を再利用

VENV_PY = USERTEST.parent / ".venv" / "bin" / "python"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="usertest/input/ 配下のディレクトリ名 (例: gt-muzyx)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    in_dir = USERTEST / "input" / args.name
    ref_path = in_dir / "reference.json"
    audio = in_dir / "audio.m4a"
    if not ref_path.exists() or not audio.exists():
        print(f"[skip] {args.name}: reference.json / audio.m4a なし(ローカル専用)")
        return 0
    ref = json.loads(ref_path.read_text())
    out_dir = USERTEST / "output" / args.name
    meta = out_dir / "transcribe.json"
    src = audio
    if ref.get("separate"):
        # 伴奏つき動画: Demucs 6-stemのguitarを対象にする(キャッシュ・再分離しない)
        stem_dir = out_dir / "stems"
        hits = list(stem_dir.rglob("guitar.wav")) if stem_dir.exists() else []
        if not hits:
            stem_dir.mkdir(parents=True, exist_ok=True)
            r0 = subprocess.run(
                [str(VENV_PY), "-m", "earpipe.pipeline", "separate", str(audio),
                 "--out-dir", str(stem_dir)],
                capture_output=True, text=True, timeout=1800)
            hits = list(stem_dir.rglob("guitar.wav"))
            if r0.returncode != 0 or not hits:
                print(f"[fail] 分離失敗: {r0.stderr[-200:]}")
                return 1
        src = hits[0]
    if not meta.exists() or args.force:
        out_dir.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(src),
             "-o", str(out_dir / "out.musicxml"), "--midi", str(out_dir / "out.mid"),
             "--tab", str(out_dir / "out_tab.pdf"), "--engine", "auto",
             "--title", args.name],
            capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"[fail] {r.stderr[-300:]}")
            return 1
        payload = json.loads(r.stdout)
        slim = {k: payload[k] for k in ("engine", "bpm", "bpm_source", "n_notes") if k in payload}
        slim["notes"] = gb._midi_notes(out_dir / "out.mid")
        meta.write_text(json.dumps(slim, ensure_ascii=False))
    trs = json.loads(meta.read_text())
    res = gb.evaluate(ref, trs)
    print(json.dumps({"song": args.name, **{k: res[k] for k in (
        "n_hyp_notes_window", "n_ref_notes", "matched", "precision", "recall", "f1")}},
        ensure_ascii=False))
    (out_dir / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
