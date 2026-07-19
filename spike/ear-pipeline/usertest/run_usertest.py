"""体験テスト一括実行: usertest/input/ の全音源を採譜し、聴き比べ素材一式を作る。

各曲について MusicXML / MIDI / 五線譜PDF / JSONサマリー / 採譜再生音wav を生成し、
viewer.html が読む manifest.js を書き出す。完全ローカル処理（外部送信なし）。

使い方:
    .venv/bin/python usertest/run_usertest.py            # 未処理の曲だけ処理
    .venv/bin/python usertest/run_usertest.py --force    # 全曲やり直し

ファイル名が field_ で始まる音源は --field-mode を自動付与する。
poly（basic-pitch）が失敗した曲は mono にフォールバックし、その旨を記録する。
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

USERTEST = Path(__file__).resolve().parent
SPIKE = USERTEST.parent
VENV_PY = SPIKE / ".venv" / "bin" / "python"
BP_PYTHON = SPIKE.parent.parent / "tools" / "ai-ears" / ".venv312" / "bin" / "python"

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".aiff", ".aif", ".ogg"}
RENDER_SR = 22050

# 既知曲のラベル（台帳は曲IDで管理。ローカル表示用の短い説明のみ）
KNOWN_LABELS = {
    "u1": "U1 ピアノ曲（スタジオ品質・中庸テンポ）",
    "u2": "U2 弾き語り（ボーカル＋アコースティックギター）",
    "u4": "U4 バンド（ドラム・ベース・ギター・ボーカル）",
}


def transcribe(in_path: Path, engine: str) -> tuple[dict, float]:
    """パイプラインをサブプロセス実行し、(サマリーdict, 処理秒)を返す。失敗時は例外。"""
    name = in_path.stem
    out_xml = USERTEST / "output" / f"{name}.musicxml"
    out_mid = USERTEST / "output" / f"{name}.mid"
    out_pdf = USERTEST / "output" / f"{name}.pdf"
    cmd = [
        str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(in_path),
        "-o", str(out_xml), "--midi", str(out_mid), "--pdf", str(out_pdf),
        "--engine", engine,
    ]
    if engine == "poly":
        cmd += ["--sensitivity", "auto"]
    if name.startswith("field_"):
        cmd += ["--field-mode"]
    env = {**os.environ, "EARPIPE_BP_PYTHON": str(BP_PYTHON)}
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=SPIKE, env=env, capture_output=True, text=True, timeout=1800
    )
    elapsed = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"{engine} failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}")
    summary = json.loads(proc.stdout)
    return summary, elapsed


def render_midi(mid_path: Path, wav_path: Path) -> None:
    """MIDI→再生音wav（pretty_midi内蔵シンセ。G0'の聴き比べペアと同方式）。"""
    import numpy as np
    import pretty_midi
    import soundfile as sf

    pm = pretty_midi.PrettyMIDI(str(mid_path))
    audio = pm.synthesize(fs=RENDER_SR)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0:
        audio = audio / peak * 0.9
    sf.write(str(wav_path), audio, RENDER_SR)


def process_song(in_path: Path, force: bool) -> dict:
    name = in_path.stem
    meta_path = USERTEST / "output" / f"{name}.json"
    render_path = USERTEST / "renders" / f"{name}_pitchsieve.wav"
    if meta_path.exists() and render_path.exists() and not force:
        print(f"[skip] {name}（処理済み。やり直しは --force）")
        return json.loads(meta_path.read_text())

    print(f"[run ] {name}: poly採譜を開始...")
    fallback_note = None
    try:
        summary, elapsed = transcribe(in_path, engine="poly")
    except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        fallback_note = f"polyが失敗したためmonoで再実行: {e}"
        print(f"[warn] {name}: {fallback_note}")
        summary, elapsed = transcribe(in_path, engine="mono")

    print(f"[run ] {name}: 再生音を合成...")
    render_midi(USERTEST / "output" / f"{name}.mid", render_path)

    meta = {
        "id": name,
        "label": KNOWN_LABELS.get(name, name),
        "original": f"input/{in_path.name}",
        "render": f"renders/{render_path.name}",
        "pdf": f"output/{name}.pdf",
        "musicxml": f"output/{name}.musicxml",
        "midi": f"output/{name}.mid",
        "engine": summary.get("engine"),
        "bpm": summary.get("bpm"),
        "n_notes": summary.get("n_notes"),
        "n_events": summary.get("n_events"),
        "tempo_map": summary.get("tempo_map"),
        "adaptive": summary.get("adaptive"),
        "field_report": summary.get("field_report"),
        "processing_sec": round(elapsed, 1),
        "fallback_note": fallback_note,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[done] {name}: {meta['n_notes']}音符 / BPM{meta['bpm']} / {elapsed:.0f}秒")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="処理済みの曲もやり直す")
    args = ap.parse_args()

    inputs = sorted(
        p for p in (USERTEST / "input").iterdir() if p.suffix.lower() in AUDIO_EXTS
    )
    if not inputs:
        print("input/ に音源がありません", file=sys.stderr)
        return 1

    songs = [process_song(p, args.force) for p in inputs]

    manifest = USERTEST / "manifest.js"
    manifest.write_text(
        "window.MANIFEST = " + json.dumps({"songs": songs}, ensure_ascii=False, indent=2) + ";\n"
    )
    print(f"\nmanifest.js 更新（{len(songs)}曲）。viewer.html を開いて聴き比べできます。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
