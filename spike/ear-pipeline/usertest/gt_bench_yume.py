"""正解付き実曲ベンチ第1号: 夢見る少女じゃいられない (#144・DS-05東スポ氏提案)。

作曲者・織田哲郎本人の演奏動画(ギター抜きステム+生ギター)を「絶対的な正解」とし、
同一運指の忠実TAB動画から転記した参照データ(イントロ・リフ1周目)に対して
実曲のnoteレベル精度を計測する。以後の精度改善(#114)はこの数値の改善で証明する。

参照データ(usertest/input/gt-yume/reference.json)は著作権配慮でgitignore配下・
再配布しない。無い環境ではその旨を表示して終了する。

使い方:
    .venv/bin/python usertest/gt_bench_yume.py            # キャッシュ利用
    .venv/bin/python usertest/gt_bench_yume.py --force    # 採譜やり直し

メトリクス(v1・正直表示):
- 配列レベル(主): 参照音高列とのLCSアラインメントで matched/precision/recall/F1。
  時刻に依存せず、動画冒頭のトーク等のオフセットに頑健
- 運指レベル: 音高一致した音のうち参照TABと同じ(弦,フレット)だった率(#142対照)
- 分離なし直採譜と--stem guitar(Demucs)の両方を計測し、分離起因/採譜起因を切り分け
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # earpipe import用

USERTEST = Path(__file__).resolve().parent
SPIKE = USERTEST.parent
VENV_PY = SPIKE / ".venv" / "bin" / "python"
IN_DIR = USERTEST / "input" / "gt-yume"
OUT_DIR = USERTEST / "output" / "gt-yume"
CLIP_SEC = 40  # イントロを覆う長さ(リフ1周目+2周目)
TRS_TIMEOUT = 1800


def run(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def clip_audio() -> Path | None:
    src = IN_DIR / "honnin.m4a"
    if not src.exists():
        print("[skip] 本人音源なし(yt-dlpでhonnin.m4aを取得してください)")
        return None
    clip = IN_DIR / f"honnin_intro{CLIP_SEC}.m4a"
    if not clip.exists():
        r = run(["ffmpeg", "-y", "-i", str(src), "-t", str(CLIP_SEC), "-c:a", "aac", str(clip)], 120)
        if r.returncode != 0:
            print("[fail] 切出し失敗")
            return None
    return clip


def _midi_notes(mid_path: Path) -> list[dict]:
    """MIDIから (start秒, midi) を時系列で読む(CLI JSONのnotesは空になるため)。"""
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
                out.append({"start": s * spb, "midi": msg.note})
    out.sort(key=lambda n: (n["start"], n["midi"]))
    return out


def _guitar_stem(clip: Path, force: bool) -> Path | None:
    """Demucs 6-stem(separateサブコマンド)でguitar.wavを得る(キャッシュ)。"""
    stem_dir = OUT_DIR / "stems"
    hits = list(stem_dir.rglob("guitar.wav")) if stem_dir.exists() else []
    if hits and not force:
        return hits[0]
    stem_dir.mkdir(parents=True, exist_ok=True)
    print("[sep ] Demucs 6-stem...")
    r = run([str(VENV_PY), "-m", "earpipe.pipeline", "separate", str(clip),
             "--out-dir", str(stem_dir)], TRS_TIMEOUT)
    hits = list(stem_dir.rglob("guitar.wav"))
    if r.returncode != 0 or not hits:
        print(f"[fail] 分離失敗: {r.stderr[-200:]}")
        return None
    return hits[0]


def transcribe(clip: Path, variant: str, force: bool) -> dict | None:
    """variant: 'direct'(分離なし) / 'guitar'(Demucs 6-stemのguitar.wav)。"""
    tdir = OUT_DIR / variant
    meta = tdir / "transcribe.json"
    if meta.exists() and not force:
        return json.loads(meta.read_text())
    tdir.mkdir(parents=True, exist_ok=True)
    src = clip
    if variant == "guitar":
        # 分離は常にキャッシュ(Demucsはマルチスレッドで非決定のため、--forceでも
        # 再分離しない=ベンチ素材を固定して採譜側だけを比較する)
        g = _guitar_stem(clip, False)
        if g is None:
            return None
        src = g
    cmd = [str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(src),
           "-o", str(tdir / "out.musicxml"), "--midi", str(tdir / "out.mid"),
           "--tab", str(tdir / "out_tab.pdf"), "--engine", "auto",
           "--title", f"yume_{variant}"]
    print(f"[trs ] {variant}...")
    r = run(cmd, TRS_TIMEOUT)
    if r.returncode != 0:
        print(f"[fail] {variant}: {r.stderr[-300:]}")
        return None
    payload = json.loads(r.stdout)
    slim = {k: payload[k] for k in ("engine", "bpm", "bpm_source", "n_notes") if k in payload}
    slim["notes"] = _midi_notes(tdir / "out.mid")
    meta.write_text(json.dumps(slim, ensure_ascii=False))
    return slim


def ref_note_seq(ref: dict) -> list[tuple[float, int]]:
    """参照を (beat, midi) の時系列列に展開(同時和音は低い順)。"""
    out = []
    for ev in ref["events"]:
        for m in sorted(ref["chords"][ev["chord"]]["midis"]):
            out.append((float(ev["beat"]), m))
    return out


def hyp_note_seq(trs: dict) -> list[tuple[float, int]]:
    """成果物(ギターTAB)レベルの音列: 音域折り込み+同一オンセット重複除去。

    参照はギターTABのため、TAB層と同じ fold_to_range を適用して評価する
    (ギターで物理的に不可能なサブオクターブはTABでは実音に折り畳まれる)。
    """
    from earpipe.services.notate.tab import fold_to_range

    seen = set()
    out = []
    for n in sorted(trs["notes"], key=lambda n: (n["start"], n["midi"])):
        folded, _ = fold_to_range(int(n["midi"]))
        key = (round(float(n["start"]), 2), folded)
        if key in seen:
            continue
        seen.add(key)
        out.append((float(n["start"]), folded))
    return out


def lcs_match(ref_seq: list[int], hyp_seq: list[int]) -> int:
    """音高列のLCS長(順序保存の一致音数)。"""
    dp = [0] * (len(hyp_seq) + 1)
    for a in ref_seq:
        prev = 0
        for j, b in enumerate(hyp_seq, 1):
            cur = dp[j]
            dp[j] = prev + 1 if a == b else max(dp[j], dp[j - 1])
            prev = cur
    return dp[-1]


def evaluate(ref: dict, trs: dict) -> dict:
    ref_notes = ref_note_seq(ref)
    hyp_notes = hyp_note_seq(trs)
    ref_pitches = [m for _, m in ref_notes]
    # 参照はイントロのみ。冒頭トーク等に頑健なよう、hypothesis側は
    # 「参照音集合に最初に一致した音〜LCS的に届く範囲+余裕」の窓で評価する
    ref_set = set(ref_pitches)
    first = next((i for i, (_, m) in enumerate(hyp_notes) if m in ref_set), 0)
    # イントロ終端の切れ目(2秒超の無音ギャップ=Aメロ前のブレイク)で窓を閉じる
    end = len(hyp_notes)
    for i in range(first + 1, len(hyp_notes)):
        if hyp_notes[i][0] - hyp_notes[i - 1][0] > 2.0:
            end = i
            break
    window = hyp_notes[first:end]
    hyp_pitches = [m for _, m in window]
    matched = lcs_match(ref_pitches, hyp_pitches)
    precision = matched / len(hyp_pitches) if hyp_pitches else 0.0
    recall = matched / len(ref_pitches) if ref_pitches else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "engine": trs.get("engine"),
        "bpm": trs.get("bpm"),
        "bpm_source": trs.get("bpm_source"),
        "n_hyp_notes_total": len(hyp_notes),
        "n_hyp_notes_window": len(hyp_pitches),
        "n_ref_notes": len(ref_pitches),
        "matched": matched,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ref_path = IN_DIR / "reference.json"
    if not ref_path.exists():
        print("[skip] 参照データなし(ローカル専用・再配布しない)")
        return 0
    ref = json.loads(ref_path.read_text())
    clip = clip_audio()
    if clip is None:
        return 1

    rows = {}
    for variant in ("direct", "guitar"):
        trs = transcribe(clip, variant, args.force)
        if trs:
            rows[variant] = evaluate(ref, trs)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 正解付き実曲ベンチ: 夢見る少女じゃいられない (#144)",
        "",
        f"正解: 作曲者本人演奏動画 / 参照: {ref['scope']}",
        "指標は成果物(ギターTAB)レベルの配列LCS(音域折り込み+重複除去・時刻非依存)。数値は今後の精度改善(#114)のベースライン。",
        "",
        "| variant | engine | BPM(出所) | 検出音数(窓/全) | 参照音数 | 一致 | precision | recall | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for v, r in rows.items():
        lines.append(
            f"| {v} | {r['engine']} | {round(r['bpm'])}({r['bpm_source']}) "
            f"| {r['n_hyp_notes_window']}/{r['n_hyp_notes_total']} | {r['n_ref_notes']} "
            f"| {r['matched']} | {r['precision']} | {r['recall']} | {r['f1']} |")
    report = OUT_DIR / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("\n".join(lines))
    print(f"\n→ {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
