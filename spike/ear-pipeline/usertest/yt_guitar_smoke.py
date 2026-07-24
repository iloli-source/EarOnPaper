"""実曲スモーク: YouTubeギター音源10本 → 分離 → 採譜 → 譜面再生音との突合。

生データ駆動の精度改善基盤(ユーザー指示 2026-07-24):
- テスト実施時は必ず本スクリプトを回す(合成データPD15のみの判断は禁物 — #136で
  「PD15緑でも実曲の歪みギターでテンポ推定破綻」を実証済み)
- 精度改善は本コーパスのメトリクス改善で効果を証明してから採用する
- 譜面→再生音を合成して原音ステムと音対音で突合し、譜面の正しさの
  数値エビデンス(クロマ一致・オンセット相関)と聴き比べ素材を残す

著作権: yt-dlpローカル実行・私的テスト利用(F-006裁定と同方針)。音源は
gitignore済みの usertest/input/yt-guitar/ に保存し再配布しない。

使い方:
    .venv/bin/python usertest/yt_guitar_smoke.py             # 全10本(キャッシュ利用)
    .venv/bin/python usertest/yt_guitar_smoke.py --limit 1   # 疎通確認
    .venv/bin/python usertest/yt_guitar_smoke.py --force     # 分離・採譜をやり直し
初回のみDLでネットワークを使う。2回目以降は同一素材で回帰比較できる。
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

USERTEST = Path(__file__).resolve().parent
SPIKE = USERTEST.parent
VENV_PY = SPIKE / ".venv" / "bin" / "python"
IN_DIR = USERTEST / "input" / "yt-guitar"
OUT_DIR = USERTEST / "output" / "yt-guitar"
CLIP_SEC = 90
DL_TIMEOUT = 300
SEP_TIMEOUT = 1200
TRS_TIMEOUT = 1200

# ジャンル多様な10本(検索クエリ→最初の一致をDL)。ID=保存ファイル名。
QUERIES = [
    ("acoustic_fingerstyle", "acoustic fingerstyle guitar solo instrumental"),
    ("classical", "classical guitar spanish romance instrumental"),
    ("blues", "blues guitar solo instrumental slow"),
    ("rock_distorted", "rock guitar riff distorted instrumental"),
    ("metal", "metal guitar instrumental riff"),
    ("jazz", "jazz guitar instrumental standard"),
    ("clean_arpeggio", "clean electric guitar arpeggio ballad instrumental"),
    ("jpop_cover", "guitar cover j-pop instrumental"),
    ("funk_cutting", "funk rhythm guitar cutting instrumental"),
    ("slide_country", "slide guitar country instrumental"),
]

# 警告しきい値(#136/#137の実測に基づく)
DENSITY_WARN = 12.0        # notes/sec: これ超は倍音過検出の疑い(#137)
CHROMA_MARGIN_WARN = 0.05  # クロマ一致が無作為対照+この値以下なら音高が怪しい
TEMPO_AGREE_TOL = 0.08     # エンジンBPMとlibrosa独立推定の相対差(倍半は同一視)


def run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def download(track_id: str, query: str) -> Path | None:
    """ytsearchで1本DLし90秒に切出す。既存ならスキップ(冪等・回帰の固定素材)。"""
    clip = IN_DIR / f"{track_id}.m4a"
    if clip.exists() and clip.stat().st_size > 0:
        print(f"[skip] DL済み: {track_id}")
        return clip
    IN_DIR.mkdir(parents=True, exist_ok=True)
    raw = IN_DIR / f"{track_id}_full.m4a"
    print(f"[dl  ] {track_id}: {query}")
    proc = run([
        "yt-dlp", f"ytsearch1:{query}",
        "--no-playlist", "-x", "--audio-format", "m4a",
        "--match-filter", "duration < 600 & duration > 60",
        "--print", "after_move:filepath", "--no-simulate",
        "-o", str(IN_DIR / f"{track_id}_full.%(ext)s"),
    ], DL_TIMEOUT)
    got = proc.stdout.strip().splitlines()
    src = Path(got[-1]) if got else raw
    if proc.returncode != 0 or not src.exists():
        print(f"[fail] DL失敗: {track_id}: {proc.stderr[-300:]}")
        return None
    trim = run([
        "ffmpeg", "-y", "-i", str(src), "-t", str(CLIP_SEC),
        "-c", "copy", str(clip),
    ], 120)
    if trim.returncode != 0 or not clip.exists():
        # copy不可なコンテナは再エンコードで切出す
        trim = run(["ffmpeg", "-y", "-i", str(src), "-t", str(CLIP_SEC),
                    "-c:a", "aac", str(clip)], 300)
        if trim.returncode != 0:
            print(f"[fail] 切出し失敗: {track_id}")
            return None
    src.unlink(missing_ok=True)
    return clip


def separate(track_id: str, clip: Path, force: bool) -> Path | None:
    """Demucs 6-stem分離(キャッシュ)→ guitar.wav を返す。"""
    stem_dir = OUT_DIR / track_id / "stems"
    hits = list(stem_dir.rglob("guitar.wav")) if stem_dir.exists() else []
    if hits and not force:
        print(f"[skip] 分離済み: {track_id}")
        return hits[0]
    if stem_dir.exists():
        shutil.rmtree(stem_dir)
    stem_dir.mkdir(parents=True, exist_ok=True)
    print(f"[sep ] {track_id}: Demucs 6-stem...")
    proc = run([str(VENV_PY), "-m", "earpipe.pipeline", "separate",
                str(clip), "--out-dir", str(stem_dir)], SEP_TIMEOUT)
    hits = list(stem_dir.rglob("guitar.wav"))
    if proc.returncode != 0 or not hits:
        print(f"[fail] 分離失敗: {track_id}: {proc.stderr[-300:]}")
        return None
    return hits[0]


def transcribe(track_id: str, guitar_wav: Path, force: bool) -> dict | None:
    """guitarステムを採譜(五線譜/TAB/MIDI)しJSONサマリーを返す(キャッシュ)。"""
    tdir = OUT_DIR / track_id
    meta = tdir / "transcribe.json"
    if meta.exists() and not force:
        print(f"[skip] 採譜済み: {track_id}")
        return json.loads(meta.read_text())
    print(f"[trs ] {track_id}: 採譜...")
    proc = run([
        str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(guitar_wav),
        "-o", str(tdir / "guitar.musicxml"), "--midi", str(tdir / "guitar.mid"),
        "--tab", str(tdir / "guitar_tab.pdf"), "--tab-mono", "--engine", "auto",
        "--title", track_id,
    ], TRS_TIMEOUT)
    if proc.returncode != 0:
        print(f"[fail] 採譜失敗: {track_id}: {proc.stderr[-300:]}")
        return None
    payload = json.loads(proc.stdout)
    payload.pop("notes", None)  # サマリーには音符全列を保存しない
    meta.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    return payload


def render_and_crosscheck(track_id: str, guitar_wav: Path) -> dict | None:
    """譜面(MIDI)→再生音wavを合成し、原音ステムと音対音で突合する(エビデンス)。

    - chroma_cos: 再生音と原音のクロマ(12音クラス)フレーム余弦の平均
    - chroma_control: 音クラスをシャッフルした無作為対照(これを大きく上回るべき)
    - onset_corr: オンセット強度エンベロープの相関(リズムの一致度)
    """
    import librosa
    import numpy as np
    import pretty_midi
    import soundfile as sf

    tdir = OUT_DIR / track_id
    mid = tdir / "guitar.mid"
    render = tdir / "render.wav"
    if not mid.exists():
        return None
    pm = pretty_midi.PrettyMIDI(str(mid))
    audio = pm.synthesize(fs=22050)
    if audio.size == 0:
        return None
    audio = audio / (float(np.max(np.abs(audio))) or 1.0) * 0.9
    sf.write(str(render), audio, 22050)

    y_ref, sr = librosa.load(str(guitar_wav), sr=22050, mono=True)
    y_hat = audio.astype(np.float32)
    n = min(len(y_ref), len(y_hat))
    y_ref, y_hat = y_ref[:n], y_hat[:n]

    hop = 2048
    c_ref = librosa.feature.chroma_cqt(y=y_ref, sr=sr, hop_length=hop)
    c_hat = librosa.feature.chroma_cqt(y=y_hat, sr=sr, hop_length=hop)
    m = min(c_ref.shape[1], c_hat.shape[1])
    c_ref, c_hat = c_ref[:, :m], c_hat[:, :m]
    act = (c_ref.sum(0) > 1e-3) & (c_hat.sum(0) > 1e-3)

    def _norm(M):
        d = np.linalg.norm(M, axis=0, keepdims=True)
        d[d == 0] = 1.0
        return M / d

    cos = float(((_norm(c_ref[:, act]) * _norm(c_hat[:, act])).sum(0)).mean()) if act.any() else 0.0
    rng = np.random.default_rng(0)
    c_sh = c_hat.copy()
    rng.shuffle(c_sh)  # 音クラス行の入替=音高情報を壊した対照
    control = float(((_norm(c_ref[:, act]) * _norm(c_sh[:, act])).sum(0)).mean()) if act.any() else 0.0

    o_ref = librosa.onset.onset_strength(y=y_ref, sr=sr)
    o_hat = librosa.onset.onset_strength(y=y_hat, sr=sr)
    k = min(len(o_ref), len(o_hat))
    onset_corr = float(np.corrcoef(o_ref[:k], o_hat[:k])[0, 1]) if k > 8 else 0.0

    # 独立テンポ(音響)との一致: 倍半(0.5/1/2倍)は同一視
    eng_bpm = None
    tempo_agree = None
    tj = tdir / "transcribe.json"
    if tj.exists():
        eng_bpm = json.loads(tj.read_text()).get("bpm")
    lib_bpm = float(np.median(librosa.feature.tempo(y=y_ref, sr=sr, aggregate=None)))
    if eng_bpm:
        ratios = [abs(eng_bpm * f / lib_bpm - 1.0) for f in (0.5, 1.0, 2.0)]
        tempo_agree = min(ratios) <= TEMPO_AGREE_TOL

    dur = n / sr
    return {
        "chroma_cos": round(cos, 3),
        "chroma_control": round(control, 3),
        "onset_corr": round(onset_corr, 3),
        "librosa_bpm": round(lib_bpm, 1),
        "tempo_agree": tempo_agree,
        "clip_sec": round(dur, 1),
    }


def evaluate(track_id: str, trs: dict, cross: dict | None) -> dict:
    """1曲のメトリクスを合成し警告を判定する。"""
    dur = (cross or {}).get("clip_sec") or CLIP_SEC
    density = trs.get("n_notes", 0) / max(1.0, dur)
    tab = trs.get("tab") or {}
    warns = []
    if trs.get("bpm_source") == "default":
        warns.append("bpm_default退避(#136系)")
    if trs.get("bpm_source") == "audio":
        warns.append("格子破綻→音響フォールバック(#137由来)")
    if density > DENSITY_WARN:
        warns.append(f"過検出疑い {density:.1f}音/秒(#137)")
    if cross and cross["chroma_cos"] <= cross["chroma_control"] + CHROMA_MARGIN_WARN:
        warns.append("クロマ一致が対照と同水準(音高が怪しい)")
    if cross and cross.get("tempo_agree") is False:
        warns.append("テンポが独立推定と不一致(#136系)")
    if tab.get("n_overlaps", 0) > 0:
        warns.append(f"TAB数字重なり{tab['n_overlaps']}(#139)")
    return {
        "id": track_id,
        "engine": trs.get("engine"),
        "bpm": trs.get("bpm"),
        "bpm_source": trs.get("bpm_source"),
        "n_notes": trs.get("n_notes"),
        "density": round(density, 1),
        "tab": {k: tab.get(k) for k in
                ("n_notes_placed", "n_dropped", "n_octave_shifted", "n_overlaps")},
        "crosscheck": cross,
        "warnings": warns,
    }


def write_report(rows: list[dict]) -> Path:
    lines = [
        "# 実曲スモーク(YouTubeギター10本) レポート",
        "",
        "採譜→譜面再生音を合成し原音ステムと突合した数値エビデンス。",
        "chroma_cos が control を大きく上回るほど音高が原音と一致(聴き比べ素材は各 render.wav)。",
        "",
        "| id | engine | BPM(出所) | 音数 | 密度/s | chroma(対照) | onset相関 | テンポ一致 | 警告 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        c = r.get("crosscheck") or {}
        agree = {True: "✅", False: "❌", None: "—"}[c.get("tempo_agree")]
        lines.append(
            f"| {r['id']} | {r['engine']} | {r['bpm']}({r['bpm_source']}) | {r['n_notes']} "
            f"| {r['density']} | {c.get('chroma_cos', '—')}({c.get('chroma_control', '—')}) "
            f"| {c.get('onset_corr', '—')} | {agree} "
            f"| {'; '.join(r['warnings']) or 'なし'} |"
        )
    out = OUT_DIR / "report.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="先頭N本だけ(疎通確認用)")
    ap.add_argument("--force", action="store_true", help="分離・採譜をやり直す(DLは常にキャッシュ)")
    args = ap.parse_args()

    targets = QUERIES[: args.limit] if args.limit else QUERIES
    rows = []
    for track_id, query in targets:
        clip = download(track_id, query)
        if clip is None:
            rows.append({"id": track_id, "engine": None, "bpm": None,
                         "bpm_source": None, "n_notes": None, "density": 0,
                         "tab": {}, "crosscheck": None, "warnings": ["DL失敗"]})
            continue
        guitar = separate(track_id, clip, args.force)
        if guitar is None:
            rows.append({"id": track_id, "engine": None, "bpm": None,
                         "bpm_source": None, "n_notes": None, "density": 0,
                         "tab": {}, "crosscheck": None, "warnings": ["分離失敗"]})
            continue
        trs = transcribe(track_id, guitar, args.force)
        if trs is None:
            rows.append({"id": track_id, "engine": None, "bpm": None,
                         "bpm_source": None, "n_notes": None, "density": 0,
                         "tab": {}, "crosscheck": None, "warnings": ["採譜失敗"]})
            continue
        cross = render_and_crosscheck(track_id, guitar)
        rows.append(evaluate(track_id, trs, cross))

    report = write_report(rows)
    n_warn = sum(1 for r in rows if r["warnings"])
    print(f"\n完了: {len(rows)}本 / 警告あり {n_warn}本 → {report}")
    for r in rows:
        mark = "⚠️ " if r["warnings"] else "✅ "
        print(f"{mark}{r['id']}: bpm={r['bpm']}({r['bpm_source']}) "
              f"{'; '.join(r['warnings']) or 'OK'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
